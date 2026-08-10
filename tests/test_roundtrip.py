import itertools
import re

import pytest
from markerpry import evaluate
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
    assert str(expr) == marker_str


# Complex nested expression tests
complex_to_str_testdata = [
    (
        'python_version >= "3.8" and (os_name == "posix" and platform_machine == "x86_64")',
        'python_version >= "3.8" and os_name == "posix" and platform_machine == "x86_64"',
    ),
    (
        '(python_version >= "3.8" and os_name == "posix") and platform_machine == "x86_64"',
        'python_version >= "3.8" and os_name == "posix" and platform_machine == "x86_64"',
    ),
    (
        '(os_name == "posix" or os_name == "nt") or os_name == "darwin"',
        'os_name == "posix" or os_name == "nt" or os_name == "darwin"',
    ),
    (
        '(python_version >= "3.8" and os_name == "posix") '
        'or (python_version < "3.8" and os_name == "nt")',
        '(python_version >= "3.8" and os_name == "posix") '
        'or (python_version < "3.8" and os_name == "nt")',
    ),
    (
        '(os_name == "posix" or os_name == "nt") and (python_version >= "3.8" and '
        '(platform_machine == "x86_64" or platform_machine == "arm64"))',
        '(os_name == "posix" or os_name == "nt") and python_version >= "3.8" and '
        '(platform_machine == "x86_64" or platform_machine == "arm64")',
    ),
    (
        '(python_version >= "3.8" and os_name == "posix") '
        'and (platform_machine == "x86_64" and implementation_name == "cpython")',
        'python_version >= "3.8" and os_name == "posix" and '
        'platform_machine == "x86_64" and implementation_name == "cpython"',
    ),
]


@pytest.mark.parametrize(
    ("marker_str", "expected"),
    complex_to_str_testdata,
    ids=[x[0] for x in complex_to_str_testdata],
)
def test_complex_to_str(marker_str: str, expected: str):
    expr = parse(marker_str)
    assert str(expr) == expected


def test_deeply_nested_to_str():
    # Test with a complex expression that has multiple levels of nesting
    marker_str = (
        '(python_version >= "3.8" and os_name == "posix") or '
        '(sys_platform == "linux" and (implementation_name == "cpython" or '
        'platform_machine == "x86_64"))'
    )
    expr = parse(marker_str)
    assert str(expr) == marker_str


def test_multiple_and_to_str():
    # Test with multiple AND operators
    marker_str = (
        'python_version >= "3.8" and os_name == "posix" and '
        'platform_machine == "x86_64" and implementation_name == "cpython"'
    )
    expr = parse(marker_str)
    assert str(expr) == marker_str


def test_multiple_or_to_str():
    # Test with multiple OR operators
    marker_str = 'os_name == "posix" or os_name == "nt" or os_name == "darwin" or os_name == "aix"'
    expr = parse(marker_str)
    assert str(expr) == marker_str


def test_mixed_precedence_to_str():
    marker_str = '(os_name == "posix" or python_version >= "3.8") and os_name == "nt"'
    expr = parse(marker_str)
    assert str(expr) == marker_str


# Parenthesization boundary tests
# Letters are atom placeholders; substituting True/False turns a template
# into a plain Python boolean expression, an oracle independent of markerpry.
_BOUNDARY_ATOMS: dict[str, tuple[str, str, str]] = {
    "A": ("os_name", "posix", "nt"),
    "B": ("sys_platform", "linux", "win32"),
    "C": ("implementation_name", "cpython", "pypy"),
    "D": ("platform_machine", "x86_64", "arm64"),
}


def _substitute(template: str, replacements: dict[str, str]) -> str:
    return re.sub(r"[ABCD]", lambda match: replacements[match.group()], template)


def _atoms_in(template: str) -> tuple[str, ...]:
    return tuple(letter for letter in _BOUNDARY_ATOMS if letter in template)


def _atom_value(letter: str, truth: bool) -> str:
    _, true_value, false_value = _BOUNDARY_ATOMS[letter]
    return true_value if truth else false_value


_LITERAL_REPLACEMENTS = {
    letter: f'{var} == "{true_value}"' for letter, (var, true_value, _) in _BOUNDARY_ATOMS.items()
}

paren_shape_testdata = [
    ("A", "A"),
    ("(A)", "A"),
    ("A and B", "A and B"),
    ("A or B", "A or B"),
    ("(A or B)", "A or B"),
    ("(A or (B))", "A or B"),
    ("((A) or B)", "A or B"),
    ("A and B and C", "A and B and C"),
    ("(A and B) and C", "A and B and C"),
    ("A and (B and C)", "A and B and C"),
    ("A or B or C", "A or B or C"),
    ("(A or B) or C", "A or B or C"),
    ("A or (B or C)", "A or B or C"),
    ("(A and B) or C", "(A and B) or C"),
    ("(A or B) and C", "(A or B) and C"),
    ("A and (B or C)", "A and (B or C)"),
    ("A or (B and C)", "A or (B and C)"),
    ("A and B and C and D", "A and B and C and D"),
    ("(A and B) and (C and D)", "A and B and C and D"),
    ("((A and B) and C) and D", "A and B and C and D"),
    ("A and (B and (C and D))", "A and B and C and D"),
    ("A or B or C or D", "A or B or C or D"),
    ("((A or B) or C) or D", "A or B or C or D"),
    ("A or (B or (C or D))", "A or B or C or D"),
    ("(A and B and C) or D", "(A and B and C) or D"),
    ("A or (B and C and D)", "A or (B and C and D)"),
    ("(A and B) or (C and D)", "(A and B) or (C and D)"),
    ("(A or B) and (C or D)", "(A or B) and (C or D)"),
    ("A and ((B or C) and D)", "A and (B or C) and D"),
    ("(A or (B and C)) or D", "A or (B and C) or D"),
    ("((A and B) or C) and D", "((A and B) or C) and D"),
    ("((A or B) and C) or D", "((A or B) and C) or D"),
]


@pytest.mark.parametrize(
    ("template", "expected"),
    paren_shape_testdata,
    ids=[row[0] for row in paren_shape_testdata],
)
def test_paren_minimization(template: str, expected: str):
    marker_str = _substitute(template, _LITERAL_REPLACEMENTS)
    assert str(parse(marker_str)) == _substitute(expected, _LITERAL_REPLACEMENTS)


@pytest.mark.parametrize(
    "template",
    [row[0] for row in paren_shape_testdata],
    ids=[row[0] for row in paren_shape_testdata],
)
def test_paren_minimization_preserves_semantics(template: str):
    """Test that minimizing a template's parens never changes its boolean value.

    Walks every True/False assignment of the template's atoms and compares
    markerpry's parse-then-evaluate result against a plain Python boolean oracle.
    """
    marker_str = _substitute(template, _LITERAL_REPLACEMENTS)
    minimized = str(parse(marker_str))
    atoms = _atoms_in(template)
    for assignment in itertools.product((False, True), repeat=len(atoms)):
        truth_by_letter = dict(zip(atoms, assignment, strict=True))
        truth_literals = {letter: str(truth) for letter, truth in truth_by_letter.items()}
        ground_truth = eval(_substitute(template, truth_literals))
        env = {
            _BOUNDARY_ATOMS[letter][0]: _atom_value(letter, truth)
            for letter, truth in truth_by_letter.items()
        }
        actual = Marker(minimized).evaluate(env)
        assignment_str = ", ".join(f"{k}={v}" for k, v in truth_by_letter.items())
        assert actual == ground_truth, (
            f"{template!r} minimized to {minimized!r} with {assignment_str}"
        )


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
    simplified = evaluate(node, {"implementation_name": ["pypy"]})
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
