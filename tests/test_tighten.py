from collections.abc import Sequence
from typing import Literal

import pytest
from markerpry import evaluate
from markerpry.modifiers.tighten import tighten_chain, tighten_ranges
from markerpry.node import (
    FALSE,
    BooleanNode,
    CompareNode,
    ContainsNode,
    Environment,
    Node,
    OperatorNode,
)
from markerpry.parser import parse
from packaging.markers import Marker
from packaging.version import Version

# Merge tests: same-key CompareNode clauses within an and-chain get folded
# into the tightest equivalent one or two clauses.
merge_testdata = [
    (
        "redundant_bound_dropped",
        'python_version >= "3.8" and python_version >= "3.9"',
        'python_version >= "3.9"',
    ),
    (
        "equality_collapses_with_floor",
        'python_version == "3.8" and python_version >= "3.7"',
        'python_version == "3.8"',
    ),
    (
        "exact_point_collapse",
        'python_version >= "3.8" and python_version <= "3.8"',
        'python_version == "3.8"',
    ),
    (
        "triple_equal_collapses_with_floor",
        'python_version === "3.8" and python_version >= "3.8"',
        'python_version == "3.8"',
    ),
    (
        "tie_break_exclusive_wins_on_equal_max",
        'python_version <= "3.10" and python_version < "3.10"',
        'python_version < "3.10"',  # exclusive admits fewer values, so it wins the tie
    ),
    (
        "tie_break_exclusive_wins_on_equal_min",
        'python_version >= "3.8" and python_version > "3.8"',
        'python_version > "3.8"',  # exclusive admits fewer values, so it wins the tie
    ),
    (
        "three_plus_clauses_same_key",
        'python_version >= "3.8" and python_version >= "3.9" and python_version < "3.12"',
        'python_version >= "3.9" and python_version < "3.12"',
    ),
    (
        "mergeable_clauses_interleaved_with_opaque_clause",
        'python_version >= "3.8" and extra == "docs" and python_version < "3.10"',
        # the merged group is spliced in at the position of its first member;
        # the opaque "extra" clause keeps its place relative to what's left
        'python_version >= "3.8" and python_version < "3.10" and extra == "docs"',
    ),
    (
        "prerelease_bound_is_a_valid_version",
        'python_version >= "3.8.0b1" and python_version >= "3.9"',
        'python_version >= "3.9"',
    ),
]


@pytest.mark.parametrize(
    ("name", "marker_str", "expected_str"),
    merge_testdata,
    ids=[x[0] for x in merge_testdata],
)
def test_tighten_ranges_merges(name: str, marker_str: str, expected_str: str):
    result = tighten_ranges(parse(marker_str))
    assert str(result) == expected_str


def test_tighten_chain_contradictory_bounds_becomes_false():
    """Test that an empty intersection emits FALSE directly from tighten_chain."""
    low = CompareNode("python_version", "<", "3.10")
    high = CompareNode("python_version", ">=", "3.12")
    assert tighten_chain("and", [low, high]) == [FALSE]


def test_tighten_ranges_contradictory_bounds_collapses_whole_and_chain():
    """Test that a contradictory group collapses the whole and-chain, siblings included."""
    tree = parse('python_version < "3.10" and python_version >= "3.12" and os_name == "posix"')
    assert tighten_ranges(tree) == FALSE


def test_tighten_ranges_leaves_not_equal_and_non_version_literals_unmerged():
    """Test that != clauses and non-Version literals on a repeated key are left untouched."""
    floor = CompareNode("python_version", ">=", "3.8")
    not_equal = CompareNode("python_version", "!=", "3.9")
    non_version = CompareNode("python_version", ">=", "not-a-version")
    tree = OperatorNode("and", OperatorNode("and", floor, not_equal), non_version)

    assert tighten_ranges(tree) is tree


def test_tighten_ranges_leaves_compatible_release_unmerged():
    """Test that a ~= clause on a repeated key is left untouched -- it has no interval meaning."""
    floor = CompareNode("python_version", ">=", "3.8")
    compatible_release = CompareNode("python_version", "~=", "3.9")
    tree = OperatorNode("and", floor, compatible_release)

    assert tighten_ranges(tree) is tree


def test_tighten_ranges_leaves_contains_node_on_same_key_unmerged():
    """Test that a ContainsNode sharing a key with a merge group is left untouched."""
    floor = CompareNode("python_version", ">=", "3.8")
    ceiling = CompareNode("python_version", ">=", "3.9")
    membership = ContainsNode("python_version", "3.9", key_on_left=True)
    tree = OperatorNode("and", OperatorNode("and", floor, ceiling), membership)

    result = tighten_ranges(tree)

    assert isinstance(result, OperatorNode)
    assert result.right is membership


def test_tighten_chain_is_a_no_op_for_or():
    """Test that tighten_chain returns an or-chain's nodes unchanged, by identity."""
    nodes = [CompareNode("python_version", ">=", "3.8"), CompareNode("python_version", ">=", "3.9")]
    assert tighten_chain("or", nodes) is nodes


def test_tighten_ranges_leaves_or_nested_subtree_untouched():
    """Test that a differently-operated or-subtree inside an and-chain isn't descended into."""
    or_subtree = OperatorNode(
        "or", CompareNode("os_name", "==", "posix"), CompareNode("os_name", "==", "nt")
    )
    tree = OperatorNode(
        "and",
        OperatorNode("and", CompareNode("python_version", ">=", "3.8"), or_subtree),
        CompareNode("python_version", ">=", "3.9"),
    )

    result = tighten_ranges(tree)

    assert str(result) == 'python_version >= "3.9" and (os_name == "posix" or os_name == "nt")'


# Identity no-op tests: tighten_ranges() must return the exact same tree object
# when there's nothing to merge, mirroring test_modify_with_no_callbacks_is_identity
# and test_evaluate_identity_when_nothing_resolves.
no_op_testdata = [
    ("no_repeated_key", parse('python_version >= "3.8" and os_name == "posix"')),
    ("already_maximally_tight", parse('python_version >= "3.8" and python_version < "3.10"')),
]


@pytest.mark.parametrize(("name", "tree"), no_op_testdata, ids=[x[0] for x in no_op_testdata])
def test_tighten_ranges_no_op_identity(name: str, tree: Node):
    assert tighten_ranges(tree) is tree


def test_tighten_chain_composes_with_a_second_chain_callback():
    """Test that tighten_chain composes with another chain callback in one modify() pass."""
    tree = parse('python_version >= "3.8" and python_version >= "3.9" and extra == "docs"')

    def drop_extra(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
        return [
            node for node in nodes if not (isinstance(node, CompareNode) and node.key == "extra")
        ]

    result = tree.modify(chain=lambda op, ns: drop_extra(op, tighten_chain(op, ns)))

    assert str(result) == 'python_version >= "3.9"'


# Roundtrip tests: a tightened marker must evaluate the same as the original
# across a battery of environments, even though its string form may differ
# (e.g. "<=" tightening to "<").
roundtrip_markers = [
    'python_version >= "3.8" and python_version >= "3.9"',
    'python_version <= "3.10" and python_version < "3.10"',
    'python_version >= "3.8" and python_version < "3.10" and extra == "docs"',
    # A real setup.cfg/pyproject shape: a compiled-extension package that
    # dropped support for old pythons in a later release, expressed as two
    # separately-added, now-overlapping python_version floors.
    'python_version >= "3.6" and python_version >= "3.7" and sys_platform == "linux"',
]
roundtrip_environments: list[Environment] = [
    {"python_version": [Version("3.7")], "extra": ["docs"], "sys_platform": ["linux"]},
    {"python_version": [Version("3.8")], "extra": ["docs"], "sys_platform": ["linux"]},
    {"python_version": [Version("3.9")], "extra": ["tests"], "sys_platform": ["darwin"]},
    {"python_version": [Version("3.10")], "extra": ["docs"], "sys_platform": ["linux"]},
    {"python_version": [Version("3.11")], "extra": ["docs"], "sys_platform": ["win32"]},
    {"python_version": [Version("3.12")], "extra": ["docs"], "sys_platform": ["linux"]},
]
roundtrip_testdata = [
    (marker_str, env) for marker_str in roundtrip_markers for env in roundtrip_environments
]


@pytest.mark.parametrize(("marker_str", "env"), roundtrip_testdata)
def test_tighten_ranges_roundtrip_evaluates_equivalently(marker_str: str, env: Environment):
    """Test that a tightened marker evaluates like the original and agrees with packaging.Marker."""
    original = parse(marker_str)
    tightened = parse(str(tighten_ranges(original)))

    original_result = evaluate(original, env)
    assert original_result == evaluate(tightened, env)

    assert isinstance(original_result, BooleanNode)
    packaging_env = {key: str(values[0]) for key, values in env.items()}
    assert original_result.state == Marker(marker_str).evaluate(packaging_env)
