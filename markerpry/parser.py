from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, cast

from packaging._parser import Op, Value, Variable
from packaging.markers import Marker

from markerpry.node import CompareNode, ComparisonOperator, ContainsNode, Node, OperatorNode

REVERSE_MAP: Mapping[ComparisonOperator, ComparisonOperator] = MappingProxyType(
    {
        "==": "==",
        "===": "===",
        "!=": "!=",
        ">": "<",
        "<": ">",
        ">=": "<=",
        "<=": ">=",
        "~=": "~=",
    }
)


def parse(marker_str: str) -> Node:
    """
    Parse a PEP 508 marker string into a Node tree.

    Args:
        marker_str: A string containing a PEP 508 marker expression

    Returns:
        A Node representing the parsed marker expression

    Raises:
        packaging.markers.InvalidMarker: If the marker string is invalid
    """
    marker = Marker(marker_str)
    return parse_marker(marker)


def parse_marker(marker: Marker) -> Node:
    """
    Parse a packaging.marker.Marker object into a Node tree.

    Args:
        marker: A packaging.marker.Marker instance.

    Returns:
        A Node representing the parsed marker expression
    """
    return _parse_marker(marker._markers)


def _parse_marker(marker: Any) -> Node:

    if isinstance(marker, (tuple, list)):
        while len(marker) > 3 and "and" in marker:
            operator_index = marker.index("and")
            before = marker[: operator_index - 1]
            term = marker[operator_index - 1 : operator_index + 2]
            after = marker[operator_index + 2 :]
            marker = list(before) + [term] + list(after)

        while len(marker) > 3 and "or" in marker:
            operator_index = marker.index("or")
            before = marker[: operator_index - 1]
            term = marker[operator_index - 1 : operator_index + 2]
            after = marker[operator_index + 2 :]
            marker = list(before) + [term] + list(after)

        if len(marker) == 1:
            return _parse_marker(marker[0])
        if len(marker) == 3:
            lhs, comparator, rhs = marker
            if comparator in ("and", "or"):
                return OperatorNode(
                    operator=marker[1],
                    _left=_parse_marker(lhs),
                    _right=_parse_marker(rhs),
                )
            if (
                isinstance(lhs, (Variable, Value))
                and isinstance(rhs, (Variable, Value))
                and isinstance(comparator, Op)
                and (
                    comparator.value == "=="
                    or comparator.value == "==="
                    or comparator.value == "!="
                    or comparator.value == ">"
                    or comparator.value == "<"
                    or comparator.value == ">="
                    or comparator.value == "<="
                    or comparator.value == "~="
                    or comparator.value == "in"
                    or comparator.value == "not in"
                )
            ):
                if comparator.value in ("in", "not in"):
                    negate = comparator.value == "not in"
                    if isinstance(lhs, Variable):
                        # The key is on the left, e.g. python_version in "2.7"
                        return ContainsNode(
                            key=lhs.value, literal=rhs.value, key_on_left=True, negate=negate
                        )
                    # The key is on the right, e.g. "windows" in sys_platform
                    return ContainsNode(
                        key=rhs.value, literal=lhs.value, key_on_left=False, negate=negate
                    )
                if isinstance(lhs, Value):
                    # The marker is reversed, e.g. "3.0" < python_version
                    # Flip it around to simplify the logic
                    return CompareNode(
                        key=rhs.value,
                        comparator=REVERSE_MAP[cast(ComparisonOperator, comparator.value)],
                        literal=lhs.value,
                    )
                return CompareNode(
                    key=lhs.value,
                    comparator=cast(ComparisonOperator, comparator.value),
                    literal=rhs.value,
                )

    raise NotImplementedError(f"Unknown marker {type(marker)}: {marker}")
