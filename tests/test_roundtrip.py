import pytest
from markerpry.node import BooleanNode
from markerpry.parser import parse
from packaging.markers import Marker


# Basic node string representation tests
def test_boolean_str():
    assert str(BooleanNode(True)) == "True"
    assert str(BooleanNode(False)) == "False"


@pytest.mark.parametrize(
    "marker_str",
    [
        'python_version >= "3.8"',
        'os_name == "posix"',
        'platform_machine != "x86_64"',
        'sys_platform < "3.0"',
        'implementation_name <= "cpython"',
    ],
)
def test_expression_to_str(marker_str: str):
    expr = parse(marker_str)
    assert str(expr) == marker_str


@pytest.mark.parametrize(
    "marker_str",
    [
        'os_name == "posix" and python_version >= "3.8"',
        'os_name == "posix" or os_name == "nt"',
    ],
)
def test_operator_to_str(marker_str: str):
    expr = parse(marker_str)
    assert str(expr) == f"({marker_str})"


# Complex nested expression tests
@pytest.mark.parametrize(
    "marker_str",
    [
        'python_version >= "3.8" and (os_name == "posix" and platform_machine == "x86_64")',
        '(python_version >= "3.8" and os_name == "posix") and platform_machine == "x86_64"',
        '(os_name == "posix" or os_name == "nt") or os_name == "darwin"',
        '(python_version >= "3.8" and os_name == "posix") '
        'or (python_version < "3.8" and os_name == "nt")',
        '(os_name == "posix" or os_name == "nt") and (python_version >= "3.8" and '
        '(platform_machine == "x86_64" or platform_machine == "arm64"))',
    ],
)
def test_complex_to_str(marker_str: str):
    expr = parse(marker_str)
    assert str(expr) == f"({marker_str})"


def test_deeply_nested_to_str():
    # Test with a complex expression that has multiple levels of nesting
    marker_str = (
        '(python_version >= "3.8" and os_name == "posix") or '
        '(sys_platform == "linux" and (implementation_name == "cpython" or '
        'platform_machine == "x86_64"))'
    )
    expr = parse(marker_str)
    assert str(expr) == f"({marker_str})"


def test_multiple_and_to_str():
    # Test with multiple AND operators
    marker_str = (
        'python_version >= "3.8" and os_name == "posix" and '
        'platform_machine == "x86_64" and implementation_name == "cpython"'
    )
    expected = (
        '(((python_version >= "3.8" and os_name == "posix") and '
        'platform_machine == "x86_64") and implementation_name == "cpython")'
    )
    expr = parse(marker_str)
    assert str(expr) == expected


def test_multiple_or_to_str():
    # Test with multiple OR operators
    marker_str = 'os_name == "posix" or os_name == "nt" or os_name == "darwin" or os_name == "aix"'
    expected = (
        '(((os_name == "posix" or os_name == "nt") or os_name == "darwin") or os_name == "aix")'
    )
    expr = parse(marker_str)
    assert str(expr) == expected


def test_mixed_precedence_to_str():
    marker_str = '(os_name == "posix" or python_version >= "3.8") and os_name == "nt"'
    expected = '((os_name == "posix" or python_version >= "3.8") and os_name == "nt")'
    expr = parse(marker_str)
    assert str(expr) == expected


@pytest.mark.parametrize(
    "marker_str",
    [
        'python_version >= "3.8"',
        'os_name == "posix"',
        'platform_machine != "x86_64"',
        'sys_platform < "3.0"',
        'implementation_name <= "cpython"',
    ],
)
def test_roundtrip(marker_str: str):
    """Test that parsing and converting back to string preserves the original."""
    ast = parse(marker_str)
    assert str(Marker(str(ast))).replace('"', "'") == marker_str.replace('"', "'")


def test_simplify():
    marker_str = (
        '(implementation_name == "cpython" and python_version >= "3.8") or os_name == "posix"'
    )
    node = parse(marker_str)
    simplified = node.evaluate({"implementation_name": ["pypy"]})
    assert str(Marker(str(simplified))).replace('"', "'") == 'os_name == "posix"'.replace('"', "'")


# In/NotIn operator roundtrip tests
in_operator_roundtrip_testdata = [
    (
        "in_version",
        '"3.7" in python_version',
        "python_version",
    ),
    (
        "in_platform",
        '"linux" in sys_platform',
        "sys_platform",
    ),
    (
        "not_in_version",
        '"3.7" not in python_version',
        "python_version",
    ),
    (
        "not_in_platform",
        '"linux" not in sys_platform',
        "sys_platform",
    ),
]


@pytest.mark.parametrize(
    ("name", "marker_str", "expected_key"),
    in_operator_roundtrip_testdata,
    ids=[x[0] for x in in_operator_roundtrip_testdata],
)
def test_in_operator_roundtrip(name: str, marker_str: str, expected_key: str):
    """Test that 'in' and 'not in' expressions can be parsed and formatted correctly."""
    node = parse(marker_str)
    # Test string roundtrip
    assert str(node) == marker_str
    # Test dependency key is preserved
    assert expected_key in node
