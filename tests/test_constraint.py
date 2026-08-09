import re

import pytest
from markerpry.constraint import (
    Comparator,
    ConstraintLike,
    ExactConstraint,
    FlagConstraint,
    PatternConstraint,
    StringConstraint,
    coerce,
)
from packaging.version import Version

# StringConstraint tests
string_testdata = [
    ("equality_true", StringConstraint("posix"), "==", "posix", True),
    ("equality_false", StringConstraint("posix"), "==", "nt", False),
    ("triple_equal_true", StringConstraint("posix"), "===", "posix", True),
    ("inequality_true", StringConstraint("posix"), "!=", "nt", True),
    ("inequality_false", StringConstraint("posix"), "!=", "posix", False),
    ("greater_than_undecidable", StringConstraint("posix"), ">", "posix", None),
    ("less_than_undecidable", StringConstraint("posix"), "<", "posix", None),
    ("greater_equal_undecidable", StringConstraint("posix"), ">=", "posix", None),
    ("less_equal_undecidable", StringConstraint("posix"), "<=", "posix", None),
    ("compatible_release_undecidable", StringConstraint("posix"), "~=", "posix", None),
    ("in_substring_true", StringConstraint("linux2"), "in", "linux", True),
    ("in_substring_false", StringConstraint("linux2"), "in", "darwin", False),
    ("not_in_substring_false", StringConstraint("linux2"), "not in", "linux", False),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    string_testdata,
    ids=[x[0] for x in string_testdata],
)
def test_string_constraint_evaluate(
    name: str,
    constraint: StringConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal) == expected


# StringConstraint/ExactConstraint key_on_left tests - which operand's value is checked
# for membership in the other depends on which side of `in`/`not in` the environment key
# was on, so this is exercised separately from the main evaluate() tables above.
key_on_left_testdata = [
    ("string_in_key_on_left_true", StringConstraint("linux"), "in", "linux2", True),
    ("string_in_key_on_left_false", StringConstraint("linux2"), "in", "linux", False),
    ("string_not_in_key_on_left_true", StringConstraint("linux2"), "not in", "linux", True),
    ("exact_in_key_on_left_true", ExactConstraint(Version("2.7")), "in", "2.7", True),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    key_on_left_testdata,
    ids=[x[0] for x in key_on_left_testdata],
)
def test_key_on_left_evaluate(
    name: str,
    constraint: StringConstraint | ExactConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal, key_on_left=True) == expected


# PatternConstraint tests
pattern_testdata = [
    ("match_true", PatternConstraint(re.compile("linux.*")), "==", "linux2", True),
    ("match_false", PatternConstraint(re.compile("linux.*")), "==", "darwin", False),
    ("triple_equal_match_true", PatternConstraint(re.compile("linux.*")), "===", "linux2", True),
    ("inequality_true", PatternConstraint(re.compile("linux.*")), "!=", "darwin", True),
    ("inequality_false", PatternConstraint(re.compile("linux.*")), "!=", "linux2", False),
    ("greater_than_undecidable", PatternConstraint(re.compile("linux.*")), ">", "linux2", None),
    (
        "compatible_release_undecidable",
        PatternConstraint(re.compile("linux.*")),
        "~=",
        "linux2",
        None,
    ),
    ("in_undecidable", PatternConstraint(re.compile("linux.*")), "in", "linux", None),
    ("not_in_undecidable", PatternConstraint(re.compile("linux.*")), "not in", "linux", None),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    pattern_testdata,
    ids=[x[0] for x in pattern_testdata],
)
def test_pattern_constraint_evaluate(
    name: str,
    constraint: PatternConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal) == expected


# ExactConstraint tests
exact_testdata = [
    ("greater_than_true", ExactConstraint(Version("3.8")), ">", "3.7", True),
    ("less_than_false", ExactConstraint(Version("3.8")), "<", "3.7", False),
    ("equality_true", ExactConstraint(Version("3.7")), "==", "3.7", True),
    ("triple_equal_true", ExactConstraint(Version("3.7")), "===", "3.7", True),
    ("compatible_release_true", ExactConstraint(Version("3.7.5")), "~=", "3.7", True),
    ("compatible_release_false", ExactConstraint(Version("4.0")), "~=", "3.7", False),
    (
        "invalid_specifier_undecidable",
        ExactConstraint(Version("3.7")),
        ">",
        "not-a-version",
        None,
    ),
    ("in_true", ExactConstraint(Version("2.7")), "in", "2.7", True),
    ("not_in_false", ExactConstraint(Version("2.7")), "not in", "2.7", False),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    exact_testdata,
    ids=[x[0] for x in exact_testdata],
)
def test_exact_constraint_evaluate(
    name: str,
    constraint: ExactConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal) == expected


# FlagConstraint tests - unconditionally decides every comparator/literal pair
flag_testdata = [
    ("true_with_equality", FlagConstraint(True), "==", "CPython", True),
    ("false_with_equality", FlagConstraint(False), "==", "CPython", False),
    ("true_with_ordering", FlagConstraint(True), "<", "3.7", True),
    ("true_with_in", FlagConstraint(True), "in", "3.7", True),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    flag_testdata,
    ids=[x[0] for x in flag_testdata],
)
def test_flag_constraint_evaluate(
    name: str, constraint: FlagConstraint, comparator: Comparator, literal: str, expected: bool
):
    assert constraint.evaluate(comparator, literal) == expected


# coerce() tests
_pattern = re.compile("linux.*")
coerce_testdata = [
    ("bare_str", "posix", StringConstraint("posix")),
    ("bare_true", True, FlagConstraint(True)),
    ("bare_false", False, FlagConstraint(False)),
    ("bare_version", Version("3.7"), ExactConstraint(Version("3.7"))),
    ("bare_pattern", _pattern, PatternConstraint(_pattern)),
    ("already_string", StringConstraint("posix"), StringConstraint("posix")),
    ("already_flag", FlagConstraint(True), FlagConstraint(True)),
    ("already_exact", ExactConstraint(Version("3.7")), ExactConstraint(Version("3.7"))),
    ("already_pattern", PatternConstraint(_pattern), PatternConstraint(_pattern)),
]


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    coerce_testdata,
    ids=[x[0] for x in coerce_testdata],
)
def test_coerce(name: str, value: ConstraintLike, expected: ConstraintLike):
    assert coerce(value) == expected


def test_coerce_already_coerced_is_passthrough():
    """coerce() returns an already-wrapped Constraint unchanged, not a copy."""
    string_constraint = StringConstraint("posix")
    assert coerce(string_constraint) is string_constraint
