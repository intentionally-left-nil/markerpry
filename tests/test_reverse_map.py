import pytest
from markerpry.node import BooleanNode, CompareNode, ContainsNode, Environment
from markerpry.parser import REVERSE_MAP, parse
from packaging.markers import Marker
from packaging.version import Version

test_cases: list[tuple[str, str, dict[str, str]]] = []
for op, reverse_op in REVERSE_MAP.items():
    if op == "~=":
        continue

    # Test with a value before, equal to, and after 3.7
    for version in ["3.6", "3.7", "3.8"]:
        test_cases.append(
            (
                f'python_version {op} "3.7"',
                f'"3.7" {reverse_op} python_version',
                {"python_version": version},
            )
        )


@pytest.mark.parametrize(
    ("marker_str", "reversed_marker_str", "env"),
    test_cases,
)
def test_reverse_map_equivalence(marker_str: str, reversed_marker_str: str, env: dict[str, str]):
    """Test that a marker and its reversed form evaluate to the same result."""
    # For example: python < "3.7" should evaluate the same as "3.7" > python
    # where the new operator comes from REVERSE_MAP
    marker = Marker(marker_str)
    reversed_marker = Marker(reversed_marker_str)

    result = marker.evaluate(env)
    reversed_result = reversed_marker.evaluate(env)

    assert result == reversed_result, (
        f"Markers not equivalent for env={env}:\n"
        f"{marker_str} evaluated to {result}\n"
        f"{reversed_marker_str} evaluated to {reversed_result}"
    )


@pytest.mark.parametrize(
    ("marker_str", "reversed_marker_str", "env"),
    test_cases,
)
def test_reverse_map_equivalence_compare_node(
    marker_str: str, reversed_marker_str: str, env: dict[str, str]
):
    """Test that a marker and its REVERSE_MAP-rewritten form parse into equivalent CompareNodes."""
    node = parse(marker_str)
    reversed_node = parse(reversed_marker_str)
    assert isinstance(node, CompareNode)
    assert isinstance(reversed_node, CompareNode)

    markerpry_env: Environment = {"python_version": [Version(env["python_version"])]}
    result = node.evaluate(markerpry_env)
    reversed_result = reversed_node.evaluate(markerpry_env)

    assert result == reversed_result, (
        f"CompareNodes not equivalent for env={env}:\n"
        f"{marker_str} evaluated to {result}\n"
        f"{reversed_marker_str} evaluated to {reversed_result}"
    )
    assert isinstance(result, BooleanNode)


# "in"/"not in" have no REVERSE_MAP entry, so check each key_on_left case
# against packaging.Marker instead of a reversed-form equivalence.
contains_test_cases: list[tuple[str, dict[str, str]]] = []
for version in ["2.6", "2.7", "3.6", "2.7.1"]:
    contains_test_cases.extend(
        [
            ('"2.7" in python_version', {"python_version": version}),  # key_on_left=False
            ('"2.7" not in python_version', {"python_version": version}),  # key_on_left=False
            ('python_version in "2.7"', {"python_version": version}),  # key_on_left=True
            ('python_version not in "2.7"', {"python_version": version}),  # key_on_left=True
        ]
    )


@pytest.mark.parametrize(("marker_str", "env"), contains_test_cases)
def test_contains_node_key_on_left_matches_packaging(marker_str: str, env: dict[str, str]):
    """Test that ContainsNode's key_on_left-driven evaluate() matches packaging.Marker."""
    node = parse(marker_str)
    assert isinstance(node, ContainsNode)

    markerpry_env: Environment = {"python_version": [Version(env["python_version"])]}
    result = node.evaluate(markerpry_env)
    assert isinstance(result, BooleanNode)

    packaging_result = Marker(marker_str).evaluate(env)
    assert result.state == packaging_result, (
        f"ContainsNode not equivalent to packaging.Marker for env={env}:\n"
        f"{marker_str} (key_on_left={node.key_on_left}) evaluated to {result.state}, "
        f"packaging evaluated to {packaging_result}"
    )
