import pytest
from markerpry.node import CompareNode, ContainsNode, Node, OperatorNode
from markerpry.parser import parse, parse_marker
from packaging.markers import Marker

# Basic comparison tests
basic_markers = [
    ("os_name == 'nt'", CompareNode(key="os_name", comparator="==", literal="nt")),
    (
        "sys_platform == 'win32'",
        CompareNode(key="sys_platform", comparator="==", literal="win32"),
    ),
    (
        "platform_machine == 'x86_64'",
        CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
    ),
    (
        "platform_python_implementation == 'CPython'",
        CompareNode(key="platform_python_implementation", comparator="==", literal="CPython"),
    ),
]


@pytest.mark.parametrize(
    ("marker_str", "expected"), basic_markers, ids=[x[0] for x in basic_markers]
)
def test_basic_markers(marker_str: str, expected):
    result = parse(marker_str)
    assert result == expected


# Version comparison tests
version_markers = [
    (
        "python_version >= '3.8'",
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
    ),
    (
        "python_full_version < '3.9.7'",
        CompareNode(key="python_full_version", comparator="<", literal="3.9.7"),
    ),
    (
        "implementation_version == '3.8.10'",
        CompareNode(key="implementation_version", comparator="==", literal="3.8.10"),
    ),
]


@pytest.mark.parametrize(
    ("marker_str", "expected"), version_markers, ids=[x[0] for x in version_markers]
)
def test_version_markers(marker_str: str, expected):
    result = parse(marker_str)
    assert result == expected


# Simple boolean operation tests
boolean_markers = [
    (
        "python_version >= '3.8' and os_name == 'posix'",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="python_version", comparator=">=", literal="3.8"),
            _right=CompareNode(key="os_name", comparator="==", literal="posix"),
        ),
    ),
    (
        "os_name == 'nt' or os_name == 'posix'",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="os_name", comparator="==", literal="nt"),
            _right=CompareNode(key="os_name", comparator="==", literal="posix"),
        ),
    ),
]


@pytest.mark.parametrize(
    ("marker_str", "expected"), boolean_markers, ids=[x[0] for x in boolean_markers]
)
def test_boolean_markers(marker_str: str, expected):
    result = parse(marker_str)
    assert result == expected


# Nested AND operation tests
nested_and_markers = [
    (
        "python_version >= '3.8' and (os_name == 'posix' and platform_machine == 'x86_64')",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="python_version", comparator=">=", literal="3.8"),
            _right=OperatorNode(
                operator="and",
                _left=CompareNode(key="os_name", comparator="==", literal="posix"),
                _right=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
            ),
        ),
    ),
    (
        "(python_version >= '3.8' and os_name == 'posix') and platform_machine == 'x86_64'",
        OperatorNode(
            operator="and",
            _left=OperatorNode(
                operator="and",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.8"),
                _right=CompareNode(key="os_name", comparator="==", literal="posix"),
            ),
            _right=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
        ),
    ),
]


@pytest.mark.parametrize(
    ("marker_str", "expected"), nested_and_markers, ids=[x[0] for x in nested_and_markers]
)
def test_nested_and_markers(marker_str: str, expected):
    result = parse(marker_str)
    assert result == expected


# Complex nested AND operation tests
complex_and_markers = [
    (
        "python_version >= '3.8' and (os_name == 'posix' and platform_machine == 'x86_64') "
        "and python_version < '4.0'",
        OperatorNode(
            operator="and",
            _left=OperatorNode(
                operator="and",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.8"),
                _right=OperatorNode(
                    operator="and",
                    _left=CompareNode(key="os_name", comparator="==", literal="posix"),
                    _right=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
                ),
            ),
            _right=CompareNode(key="python_version", comparator="<", literal="4.0"),
        ),
    ),
    (
        "(python_version >= '3.8' and os_name == 'posix') "
        "and (platform_machine == 'x86_64' and python_version < '4.0')",
        OperatorNode(
            operator="and",
            _left=OperatorNode(
                operator="and",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.8"),
                _right=CompareNode(key="os_name", comparator="==", literal="posix"),
            ),
            _right=OperatorNode(
                operator="and",
                _left=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
                _right=CompareNode(key="python_version", comparator="<", literal="4.0"),
            ),
        ),
    ),
]


@pytest.mark.parametrize(
    ("marker_str", "expected"), complex_and_markers, ids=[x[0] for x in complex_and_markers]
)
def test_complex_and_markers(marker_str: str, expected):
    result = parse(marker_str)
    assert result == expected


# Invalid marker tests
invalid_markers = [
    "python_version",  # Missing operator and value
    "python_version ==",  # Missing value
    "== '3.8'",  # Missing variable
    "python_version = '3.8'",  # Invalid operator (single =)
    'python_version == "3.8',  # Unclosed quote
    "python_version == '3.8",  # Unclosed quote
    "python_version == 3.8",  # Missing quotes
    "invalid_var == '3.8'",  # Unknown environment marker
    "PYTHON_VERSION == '3.8'",  # Case sensitive
    # Invalid boolean logic
    "python_version >= '3.8' and",  # Incomplete AND
    "and os_name == 'posix'",  # AND with missing left side
    "python_version >= '3.8' or",  # Incomplete OR
    "or os_name == 'posix'",  # OR with missing left side
    "python_version >= '3.8' and and os_name == 'posix'",  # Double AND
    "python_version >= '3.8' or or os_name == 'posix'",  # Double OR
]


@pytest.mark.parametrize("marker_str", invalid_markers, ids=invalid_markers)
def test_invalid_markers(marker_str: str):
    with pytest.raises((ValueError, SyntaxError)):
        parse(marker_str)


# Mixed AND/OR operation tests
mixed_op_markers = [
    (
        "os_name == 'nt' or python_version >= '3.8' and platform_machine == 'x86_64'",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="os_name", comparator="==", literal="nt"),
            _right=OperatorNode(
                operator="and",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.8"),
                _right=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
            ),
        ),
    ),
    (
        "(os_name == 'nt' or python_version >= '3.8') and platform_machine == 'x86_64'",
        OperatorNode(
            operator="and",
            _left=OperatorNode(
                operator="or",
                _left=CompareNode(key="os_name", comparator="==", literal="nt"),
                _right=CompareNode(key="python_version", comparator=">=", literal="3.8"),
            ),
            _right=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
        ),
    ),
    (
        "os_name == 'nt' and python_version >= '3.8' or platform_machine == 'x86_64'",
        OperatorNode(
            operator="or",
            _left=OperatorNode(
                operator="and",
                _left=CompareNode(key="os_name", comparator="==", literal="nt"),
                _right=CompareNode(key="python_version", comparator=">=", literal="3.8"),
            ),
            _right=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
        ),
    ),
    (
        "os_name == 'nt' or python_version >= '3.8' or platform_machine == 'x86_64'",
        OperatorNode(
            operator="or",
            _left=OperatorNode(
                operator="or",
                _left=CompareNode(key="os_name", comparator="==", literal="nt"),
                _right=CompareNode(key="python_version", comparator=">=", literal="3.8"),
            ),
            _right=CompareNode(key="platform_machine", comparator="==", literal="x86_64"),
        ),
    ),
]


@pytest.mark.parametrize(
    ("marker_str", "expected"), mixed_op_markers, ids=[x[0] for x in mixed_op_markers]
)
def test_mixed_op_markers(marker_str: str, expected):
    result = parse(marker_str)
    assert result == expected


# Operator precedence and associativity tests
precedence_testdata = [
    (
        "left_associative_and",
        "python_version >= '3.7' and os_name == 'posix' and implementation_name == 'cpython'",
        OperatorNode(
            operator="and",
            _left=OperatorNode(
                operator="and",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.7"),
                _right=CompareNode(key="os_name", comparator="==", literal="posix"),
            ),
            _right=CompareNode(key="implementation_name", comparator="==", literal="cpython"),
        ),
    ),
    (
        "left_associative_or",
        "python_version >= '3.7' or os_name == 'posix' or implementation_name == 'cpython'",
        OperatorNode(
            operator="or",
            _left=OperatorNode(
                operator="or",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.7"),
                _right=CompareNode(key="os_name", comparator="==", literal="posix"),
            ),
            _right=CompareNode(key="implementation_name", comparator="==", literal="cpython"),
        ),
    ),
    (
        "and_higher_precedence_than_or",
        "python_version >= '3.7' or os_name == 'posix' and implementation_name == 'cpython'",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="python_version", comparator=">=", literal="3.7"),
            _right=OperatorNode(
                operator="and",
                _left=CompareNode(key="os_name", comparator="==", literal="posix"),
                _right=CompareNode(key="implementation_name", comparator="==", literal="cpython"),
            ),
        ),
    ),
    (
        "and_higher_precedence_multiple",
        "python_version >= '3.7' or os_name == 'posix' and implementation_name == 'cpython' "
        "or sys_platform == 'linux'",
        OperatorNode(
            operator="or",
            _left=OperatorNode(
                operator="or",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.7"),
                _right=OperatorNode(
                    operator="and",
                    _left=CompareNode(key="os_name", comparator="==", literal="posix"),
                    _right=CompareNode(
                        key="implementation_name", comparator="==", literal="cpython"
                    ),
                ),
            ),
            _right=CompareNode(key="sys_platform", comparator="==", literal="linux"),
        ),
    ),
    (
        "mixed_precedence_complex",
        "python_version >= '3.7' and os_name == 'posix' or implementation_name == 'cpython' "
        "and sys_platform == 'linux'",
        OperatorNode(
            operator="or",
            _left=OperatorNode(
                operator="and",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.7"),
                _right=CompareNode(key="os_name", comparator="==", literal="posix"),
            ),
            _right=OperatorNode(
                operator="and",
                _left=CompareNode(key="implementation_name", comparator="==", literal="cpython"),
                _right=CompareNode(key="sys_platform", comparator="==", literal="linux"),
            ),
        ),
    ),
    (
        "explicit_precedence_matches_implicit",
        "(python_version >= '3.7' and os_name == 'posix') "
        "or (implementation_name == 'cpython' and sys_platform == 'linux')",
        OperatorNode(
            operator="or",
            _left=OperatorNode(
                operator="and",
                _left=CompareNode(key="python_version", comparator=">=", literal="3.7"),
                _right=CompareNode(key="os_name", comparator="==", literal="posix"),
            ),
            _right=OperatorNode(
                operator="and",
                _left=CompareNode(key="implementation_name", comparator="==", literal="cpython"),
                _right=CompareNode(key="sys_platform", comparator="==", literal="linux"),
            ),
        ),
    ),
]


@pytest.mark.parametrize(
    ("name", "marker_str", "expected"),
    precedence_testdata,
    ids=[x[0] for x in precedence_testdata],
)
def test_operator_precedence(name: str, marker_str: str, expected: Node):
    """Test that operator precedence and associativity rules are correctly applied."""
    result = parse(marker_str)
    assert result == expected


# Real-world marker string tests
real_world_markers = [
    (
        "tilde_match_version",
        'python_version ~= "3.7"',
    ),
    (
        "triple_equal_version",
        'python_version === "3.7"',
    ),
    ("in_syntax", '"windows" in sys_platform'),
    ("in_syntax_reversed", 'python_version in "2.7"'),
    (
        "lhs_rhs_reversed",
        'python_version < "2.7" or ("3.0" <= python_version and python_version < "3.2")',
    ),
]


@pytest.mark.parametrize(
    ("name", "marker_str"),
    real_world_markers,
    ids=[x[0] for x in real_world_markers],
)
def test_real_world_markers_roundtrip(name: str, marker_str: str):
    """Test that real-world marker strings can be parsed and converted back to strings."""
    from packaging.markers import Marker

    # Verify the marker is valid according to packaging
    Marker(marker_str)

    # Parse and convert back to string
    tree = parse(marker_str)
    result_str = str(tree)

    # Parse the result string again to verify it produces the same tree
    result_tree = parse(result_str)
    assert result_tree == tree


def test_parse_marker():
    marker = Marker("os_name == 'nt'")
    result = parse_marker(marker)
    assert result == CompareNode(key="os_name", comparator="==", literal="nt")


# Reversed comparator tests
reversed_comparator_testdata = [
    (
        "reversed_greater_than",
        '"3.0" < python_version',
        CompareNode(key="python_version", comparator=">", literal="3.0"),
    ),
    (
        "reversed_less_than",
        '"3.0" > python_version',
        CompareNode(key="python_version", comparator="<", literal="3.0"),
    ),
    (
        "reversed_greater_equal",
        '"3.0" <= python_version',
        CompareNode(key="python_version", comparator=">=", literal="3.0"),
    ),
    (
        "reversed_less_equal",
        '"3.0" >= python_version',
        CompareNode(key="python_version", comparator="<=", literal="3.0"),
    ),
    (
        "reversed_equal",
        '"3.0" == python_version',
        CompareNode(key="python_version", comparator="==", literal="3.0"),
    ),
    (
        "reversed_not_equal",
        '"3.0" != python_version',
        CompareNode(key="python_version", comparator="!=", literal="3.0"),
    ),
    (
        "reversed_triple_equal",
        '"3.0" === python_version',
        CompareNode(key="python_version", comparator="===", literal="3.0"),
    ),
    (
        "reversed_tilde_equal",
        '"3.0" ~= python_version',
        CompareNode(key="python_version", comparator="~=", literal="3.0"),
    ),
]


@pytest.mark.parametrize(
    ("name", "marker_str", "expected"),
    reversed_comparator_testdata,
    ids=[x[0] for x in reversed_comparator_testdata],
)
def test_reversed_comparators(name: str, marker_str: str, expected: Node):
    """Test that reversed comparators (e.g. '3.0' <= python_version) are normalized correctly."""
    result = parse(marker_str)
    assert result == expected


# Tests for operand ordering and variable/value combinations
operand_order_markers = [
    (
        "normal_comparison",
        'python_version >= "3.7"',
        CompareNode(key="python_version", comparator=">=", literal="3.7"),
    ),
    (
        "reversed_comparison",
        '"3.7" <= python_version',
        CompareNode(key="python_version", comparator=">=", literal="3.7"),
    ),
    (
        "normal_in",
        '"win32" in sys_platform',
        ContainsNode(key="sys_platform", literal="win32", key_on_left=False),
    ),
    (
        "reversed_in",
        'sys_platform in "win32"',
        ContainsNode(key="sys_platform", literal="win32", key_on_left=True),
    ),
    (
        "normal_not_in",
        '"win32" not in sys_platform',
        ContainsNode(key="sys_platform", literal="win32", key_on_left=False, negate=True),
    ),
    (
        "reversed_not_in",
        'sys_platform not in "win32"',
        ContainsNode(key="sys_platform", literal="win32", key_on_left=True, negate=True),
    ),
]


@pytest.mark.parametrize(
    ("name", "marker_str", "expected"),
    operand_order_markers,
    ids=[x[0] for x in operand_order_markers],
)
def test_operand_ordering(name: str, marker_str: str, expected: Node | None):
    """Test that operand ordering is handled correctly for different operators."""
    result = parse(marker_str)
    assert result == expected
    # Also verify that the string representation can be parsed back
    result_str = str(result)
    result_tree = parse(result_str)
    assert result_tree == result
