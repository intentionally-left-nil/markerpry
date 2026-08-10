from collections.abc import Sequence
from typing import Literal

from packaging.version import InvalidVersion, Version

from ..constraint import RangeConstraint
from ..node import FALSE, CompareNode, Node

_MERGEABLE_COMPARATORS = {"==", "===", "<", "<=", ">", ">="}


def tighten_ranges(node: Node) -> Node:
    """Merge and simplify same-key version-range CompareNode clauses in and-chains."""
    return node.modify(chain=tighten_chain)


def tighten_chain(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
    """Merge same-key version-range CompareNode clauses within one and-chain."""
    if operator == "or":
        return nodes

    groups: dict[str, list[CompareNode]] = {}
    for node in nodes:
        if isinstance(node, CompareNode) and _is_merge_candidate(node):
            groups.setdefault(node.key, []).append(node)
    mergeable_keys = {key for key, members in groups.items() if len(members) >= 2}
    if not mergeable_keys:
        return nodes

    replacements = {key: _tighten_group(key, groups[key]) for key in mergeable_keys}
    result: list[Node] = []
    emitted_keys: set[str] = set()
    for node in nodes:
        if not (
            isinstance(node, CompareNode)
            and _is_merge_candidate(node)
            and node.key in mergeable_keys
        ):
            result.append(node)
        elif node.key not in emitted_keys:
            result.extend(replacements[node.key])
            emitted_keys.add(node.key)
    return result


def _is_merge_candidate(node: CompareNode) -> bool:
    if node.comparator not in _MERGEABLE_COMPARATORS:
        return False
    try:
        Version(node.literal)
    except InvalidVersion:
        return False
    return True


def _tighten_group(key: str, members: Sequence[CompareNode]) -> Sequence[Node]:
    intersection: RangeConstraint | None = _to_range(members[0])
    for member in members[1:]:
        intersection = None if intersection is None else intersection.intersect(_to_range(member))
    if intersection is None:
        return [FALSE]
    emitted = _from_range(key, intersection)
    return members if _same_clauses(emitted, members) else emitted


def _to_range(node: CompareNode) -> RangeConstraint:
    version = Version(node.literal)
    if node.comparator == ">":
        return RangeConstraint(min=version, max=None, include_min=False)
    if node.comparator == ">=":
        return RangeConstraint(min=version, max=None)
    if node.comparator == "<":
        return RangeConstraint(min=None, max=version)
    if node.comparator == "<=":
        return RangeConstraint(min=None, max=version, include_max=True)
    if node.comparator == "==" or node.comparator == "===":
        return RangeConstraint(min=version, max=version, include_max=True)
    raise AssertionError(f"unreachable: non-mergeable comparator {node.comparator!r}")


def _from_range(key: str, interval: RangeConstraint) -> Sequence[CompareNode]:
    if (
        interval.min is not None
        and interval.min == interval.max
        and interval.include_min
        and interval.include_max
    ):
        return [CompareNode(key, "==", str(interval.min))]
    result: list[CompareNode] = []
    if interval.min is not None:
        result.append(CompareNode(key, ">=" if interval.include_min else ">", str(interval.min)))
    if interval.max is not None:
        result.append(CompareNode(key, "<=" if interval.include_max else "<", str(interval.max)))
    return result


def _same_clauses(emitted: Sequence[CompareNode], members: Sequence[CompareNode]) -> bool:
    emitted_shapes = sorted((node.comparator, node.literal) for node in emitted)
    member_shapes = sorted((node.comparator, node.literal) for node in members)
    return emitted_shapes == member_shapes
