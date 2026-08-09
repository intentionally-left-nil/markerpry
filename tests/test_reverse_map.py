import pytest
from markerpry.parser import REVERSE_MAP
from packaging.markers import Marker

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
