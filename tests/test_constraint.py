import re

import pytest
from markerpry.constraint import (
    Comparator,
    ConstraintLike,
    ExactConstraint,
    FlagConstraint,
    PatternConstraint,
    RangeConstraint,
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


# RangeConstraint tests
#
# A RangeConstraint's correctness is entirely about comparator/boundary
# interactions, so rather than a handful of representative cases, each table
# below fixes one constraint and sweeps every literal position around it --
# below, at, inside, and above its bounds -- the way you'd audit interval
# arithmetic by hand.

# -- A single point (min == max, both bounds closed) is a plain version in
# disguise: every comparator must be decidable, since there's no "inside"
# position left to be ambiguous about.
_POINT = RangeConstraint(Version("3.8"), Version("3.8"), include_min=True, include_max=True)

range_point_equality_testdata = [
    # literal == "3.8" exactly, just spelled with an explicit patch of zero
    ("point_eq_zero_padded_spelling", _POINT, "==", "3.8.0", True),
    ("point_ne_zero_padded_spelling", _POINT, "!=", "3.8.0", False),
    ("point_triple_eq_zero_padded_spelling", _POINT, "===", "3.8.0", True),
    # below the point
    ("point_eq_lower_patch", _POINT, "==", "3.7.9", False),
    ("point_ne_lower_patch", _POINT, "!=", "3.7.9", True),
    ("point_eq_prerelease_of_point", _POINT, "==", "3.8.0b1", False),
    ("point_ne_prerelease_of_point", _POINT, "!=", "3.8.0b1", True),
    ("point_eq_dev_of_point", _POINT, "==", "3.8.0.dev1", False),
    ("point_ne_dev_of_point", _POINT, "!=", "3.8.0.dev1", True),
    # above the point
    ("point_eq_higher_minor", _POINT, "==", "3.9", False),
    ("point_ne_higher_minor", _POINT, "!=", "3.9", True),
    ("point_eq_higher_patch", _POINT, "==", "3.8.1", False),
    ("point_ne_higher_patch", _POINT, "!=", "3.8.1", True),
    ("point_eq_post_of_point", _POINT, "==", "3.8.0.post1", False),
    ("point_ne_post_of_point", _POINT, "!=", "3.8.0.post1", True),
    ("point_triple_eq_higher_minor", _POINT, "===", "3.9", False),
    # local versions sort after their public version, so still "above"
    ("point_eq_local_of_point", _POINT, "==", "3.8.0+local", False),
    ("point_ne_local_of_point", _POINT, "!=", "3.8.0+local", True),
    # malformed literal: undecidable, not an error
    ("point_eq_invalid_literal", _POINT, "==", "not-a-version", None),
    ("point_ne_invalid_literal", _POINT, "!=", "not-a-version", None),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    range_point_equality_testdata,
    ids=[x[0] for x in range_point_equality_testdata],
)
def test_range_constraint_point_equality_evaluate(
    name: str,
    constraint: RangeConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal) == expected


# -- Same fixed point, ordering comparators: "3.8 <comparator> literal" must
# resolve consistently with where the literal actually sorts relative to 3.8.
range_point_ordering_testdata = [
    # literal below the point -> "3.8 < literal" is False, "3.8 > literal" is True
    ("point_lt_lower_patch", _POINT, "<", "3.7.9", False),
    ("point_le_lower_patch", _POINT, "<=", "3.7.9", False),
    ("point_gt_lower_patch", _POINT, ">", "3.7.9", True),
    ("point_ge_lower_patch", _POINT, ">=", "3.7.9", True),
    ("point_lt_prerelease_of_point", _POINT, "<", "3.8.0b1", False),
    ("point_le_prerelease_of_point", _POINT, "<=", "3.8.0b1", False),
    ("point_gt_prerelease_of_point", _POINT, ">", "3.8.0b1", True),
    ("point_ge_prerelease_of_point", _POINT, ">=", "3.8.0b1", True),
    ("point_lt_dev_of_point", _POINT, "<", "3.8.0.dev1", False),
    ("point_ge_dev_of_point", _POINT, ">=", "3.8.0.dev1", True),
    # literal exactly equal to the point -> "<"/">" are False, "<="/">=" are True
    ("point_lt_equal_literal", _POINT, "<", "3.8.0", False),
    ("point_le_equal_literal", _POINT, "<=", "3.8.0", True),
    ("point_gt_equal_literal", _POINT, ">", "3.8.0", False),
    ("point_ge_equal_literal", _POINT, ">=", "3.8.0", True),
    # literal above the point -> "3.8 < literal" is True, "3.8 > literal" is False
    ("point_lt_higher_minor", _POINT, "<", "3.9", True),
    ("point_le_higher_minor", _POINT, "<=", "3.9", True),
    ("point_gt_higher_minor", _POINT, ">", "3.9", False),
    ("point_ge_higher_minor", _POINT, ">=", "3.9", False),
    ("point_lt_higher_patch", _POINT, "<", "3.8.1", True),
    ("point_ge_higher_patch", _POINT, ">=", "3.8.1", False),
    ("point_lt_post_of_point", _POINT, "<", "3.8.0.post1", True),
    ("point_ge_post_of_point", _POINT, ">=", "3.8.0.post1", False),
    # malformed literal: undecidable, not an error
    ("point_lt_invalid_literal", _POINT, "<", "not-a-version", None),
    ("point_ge_invalid_literal", _POINT, ">=", "not-a-version", None),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    range_point_ordering_testdata,
    ids=[x[0] for x in range_point_ordering_testdata],
)
def test_range_constraint_point_ordering_evaluate(
    name: str,
    constraint: RangeConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal) == expected


# PEP 440 forbids a local version identifier in an ordered (<,<=,>,>=)
# specifier clause, so building the SpecifierSet for these raises
# InvalidSpecifier -- correctly undecidable, same as any other malformed
# literal, even though "==" and "!=" (which don't go through SpecifierSet)
# handle the same literal above just fine.
range_point_local_version_ordering_testdata = [
    ("point_lt_local_version_undecidable", _POINT, "<", "3.8.0+local", None),
    ("point_le_local_version_undecidable", _POINT, "<=", "3.8.0+local", None),
    ("point_gt_local_version_undecidable", _POINT, ">", "3.8.0+local", None),
    ("point_ge_local_version_undecidable", _POINT, ">=", "3.8.0+local", None),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    range_point_local_version_ordering_testdata,
    ids=[x[0] for x in range_point_local_version_ordering_testdata],
)
def test_range_constraint_point_local_version_ordering_evaluate(
    name: str,
    constraint: RangeConstraint,
    comparator: Comparator,
    literal: str,
    expected: None,
):
    assert constraint.evaluate(comparator, literal) == expected


# -- A genuine interval, [3.7, 3.11) -- min included, max excluded, the same
# shape as a `Requires-Python: >=3.7,<3.11` floor+ceiling. Equality only
# decides when the literal falls entirely outside the interval; being
# *inside* -- even sitting exactly on the included boundary -- still means
# "could be any of several versions", so it stays undecidable.
_RANGE = RangeConstraint(Version("3.7"), Version("3.11"))

range_containment_testdata = [
    ("below_range_eq_decidable_false", _RANGE, "==", "3.0", False),
    ("below_range_ne_decidable_true", _RANGE, "!=", "3.0", True),
    # 3.7 is the included minimum -- a real member, but one of several
    ("at_included_min_eq_stays_undecidable", _RANGE, "==", "3.7", None),
    ("at_included_min_ne_stays_undecidable", _RANGE, "!=", "3.7", None),
    ("just_inside_start_eq_stays_undecidable", _RANGE, "==", "3.7.1", None),
    ("just_inside_start_ne_stays_undecidable", _RANGE, "!=", "3.7.1", None),
    ("well_inside_eq_stays_undecidable", _RANGE, "==", "3.9", None),
    ("well_inside_ne_stays_undecidable", _RANGE, "!=", "3.9", None),
    ("just_before_end_eq_stays_undecidable", _RANGE, "==", "3.10.9", None),
    ("just_before_end_ne_stays_undecidable", _RANGE, "!=", "3.10.9", None),
    # 3.11 is the excluded maximum -- not a real member at all, so this is
    # decidable, unlike the included-boundary case above
    ("at_excluded_max_eq_decidable_false", _RANGE, "==", "3.11", False),
    ("at_excluded_max_ne_decidable_true", _RANGE, "!=", "3.11", True),
    ("above_range_eq_decidable_false", _RANGE, "==", "4.0", False),
    ("above_range_ne_decidable_true", _RANGE, "!=", "4.0", True),
    # a prerelease of the floor sorts below the floor, so it's below the
    # range entirely, not "at" it
    ("prerelease_of_min_is_below_range_eq_decidable_false", _RANGE, "==", "3.7.0rc1", False),
    ("prerelease_of_min_is_below_range_ne_decidable_true", _RANGE, "!=", "3.7.0rc1", True),
    ("containment_invalid_literal_eq_undecidable", _RANGE, "==", "not-a-version", None),
    ("containment_invalid_literal_ne_undecidable", _RANGE, "!=", "not-a-version", None),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    range_containment_testdata,
    ids=[x[0] for x in range_containment_testdata],
)
def test_range_constraint_containment_evaluate(
    name: str,
    constraint: RangeConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal) == expected


# -- Same [3.7, 3.11) interval, ordering comparators: decided by sampling
# both boundaries against the query, which is sound because a comparator's
# truth value is monotonic in version (see constraint.py). Walking every
# position from below the floor to above the ceiling is what gives
# confidence the sampling is wired to the right boundary for each direction.
range_monotonic_boundary_testdata = [
    ("below_range_lt_decidable_false", _RANGE, "<", "3.0", False),
    ("below_range_ge_decidable_true", _RANGE, ">=", "3.0", True),
    ("just_inside_start_lt_stays_undecidable", _RANGE, "<", "3.7.1", None),
    ("just_inside_start_ge_stays_undecidable", _RANGE, ">=", "3.7.1", None),
    ("well_inside_lt_stays_undecidable", _RANGE, "<", "3.9", None),
    ("well_inside_ge_stays_undecidable", _RANGE, ">=", "3.9", None),
    ("just_before_end_lt_stays_undecidable", _RANGE, "<", "3.10.9", None),
    ("just_before_end_ge_stays_undecidable", _RANGE, ">=", "3.10.9", None),
    ("above_range_lt_decidable_true", _RANGE, "<", "4.0", True),
    ("above_range_ge_decidable_false", _RANGE, ">=", "4.0", False),
    # 3.7 is the included minimum: "<"/">=" each have a boundary to lock
    # onto, but "<="/">" straddle it for the same reason 3.7 itself is a
    # real member that disagrees with the rest of the range.
    ("at_included_min_lt_decidable_false", _RANGE, "<", "3.7", False),
    ("at_included_min_le_stays_undecidable", _RANGE, "<=", "3.7", None),
    ("at_included_min_gt_stays_undecidable", _RANGE, ">", "3.7", None),
    ("at_included_min_ge_decidable_true", _RANGE, ">=", "3.7", True),
    # 3.11 is the excluded maximum: no real member is >= 3.11 or fails
    # < 3.11, but boundary sampling tests the literal 3.11 against the
    # query as if it were a real member, so "<" and ">=" can't tell this
    # apart from a genuine straddle -- a known conservative gap from
    # ignoring include_max here, not a wrong answer, just a missed one.
    ("at_excluded_max_lt_stays_undecidable_conservative_gap", _RANGE, "<", "3.11", None),
    ("at_excluded_max_le_decidable_true", _RANGE, "<=", "3.11", True),
    ("at_excluded_max_gt_decidable_false", _RANGE, ">", "3.11", False),
    ("at_excluded_max_ge_stays_undecidable_conservative_gap", _RANGE, ">=", "3.11", None),
    # a prerelease of the floor sorts below the floor -- below the range
    ("prerelease_of_min_is_below_range_lt_decidable_false", _RANGE, "<", "3.7.0rc1", False),
    ("prerelease_of_min_is_below_range_ge_decidable_true", _RANGE, ">=", "3.7.0rc1", True),
    # a post-release of the floor sorts above it -- just inside, not at it
    ("post_release_of_min_is_inside_range_lt_stays_undecidable", _RANGE, "<", "3.7.0.post1", None),
    ("post_release_of_min_is_inside_range_ge_stays_undecidable", _RANGE, ">=", "3.7.0.post1", None),
    # a dev release of the ceiling sorts below it -- inside the open range,
    # not at the excluded boundary
    ("dev_release_of_max_is_inside_range_lt_stays_undecidable", _RANGE, "<", "3.11.0.dev1", None),
    ("dev_release_of_max_is_inside_range_ge_stays_undecidable", _RANGE, ">=", "3.11.0.dev1", None),
    # an explicit "0.0" floor (distinct from an unbounded min=None) is still
    # just an ordinary boundary to sample
    (
        "explicit_zero_floor_lt_decidable_true",
        RangeConstraint(Version("0.0"), Version("3.0")),
        "<",
        "5.0",
        True,
    ),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    range_monotonic_boundary_testdata,
    ids=[x[0] for x in range_monotonic_boundary_testdata],
)
def test_range_constraint_monotonic_boundary_evaluate(
    name: str,
    constraint: RangeConstraint,
    comparator: Comparator,
    literal: str,
    expected: bool | None,
):
    assert constraint.evaluate(comparator, literal) == expected


# -- in / not in / ~= : always undecidable for an interval, regardless of
# whether it's a point or a genuine range
range_undecidable_testdata = [
    ("in_undecidable", RangeConstraint(Version("3.9"), None), "in", "3.9", None),
    ("not_in_undecidable", RangeConstraint(Version("3.9"), None), "not in", "3.9", None),
    ("compatible_release_undecidable", RangeConstraint(Version("3.9"), None), "~=", "3.9", None),
    ("in_undecidable_for_a_point", _POINT, "in", "3.8", None),
    ("not_in_undecidable_for_a_point", _POINT, "not in", "3.8", None),
]


@pytest.mark.parametrize(
    ("name", "constraint", "comparator", "literal", "expected"),
    range_undecidable_testdata,
    ids=[x[0] for x in range_undecidable_testdata],
)
def test_range_constraint_always_undecidable_evaluate(
    name: str,
    constraint: RangeConstraint,
    comparator: Comparator,
    literal: str,
    expected: None,
):
    assert constraint.evaluate(comparator, literal) == expected


def test_range_constraint_key_on_left_is_irrelevant():
    """RangeConstraint never supports in/not in, so key_on_left cannot change the answer."""
    constraint = RangeConstraint(Version("3.9"), None)
    assert constraint.evaluate("in", "3.9", key_on_left=True) is None
    assert constraint.evaluate("not in", "3.9", key_on_left=True) is None


# RangeConstraint.intersect() tests
intersect_testdata = [
    (
        "both_unbounded",
        RangeConstraint(None, None),
        RangeConstraint(None, None),
        RangeConstraint(None, None),
    ),
    (
        "one_side_unbounded",
        RangeConstraint(Version("3.8"), None),
        RangeConstraint(None, Version("3.11")),
        RangeConstraint(Version("3.8"), Version("3.11")),
    ),
    (
        "overlapping",
        RangeConstraint(Version("3.7"), Version("3.11")),
        RangeConstraint(Version("3.9"), Version("3.12")),
        RangeConstraint(Version("3.9"), Version("3.11")),
    ),
    (
        "disjoint",
        RangeConstraint(Version("3.7"), Version("3.9")),
        RangeConstraint(Version("3.10"), Version("3.12")),
        None,
    ),
    (
        "touching_at_a_point_inclusive_inclusive",
        RangeConstraint(None, Version("3.10"), include_max=True),
        RangeConstraint(Version("3.10"), None, include_min=True),
        RangeConstraint(Version("3.10"), Version("3.10"), include_min=True, include_max=True),
    ),
    (
        "touching_at_a_point_inclusive_exclusive",
        RangeConstraint(None, Version("3.10"), include_max=True),
        RangeConstraint(Version("3.10"), None, include_min=False),
        None,
    ),
    (
        "one_range_fully_containing_the_other",
        RangeConstraint(Version("3.0"), Version("4.0")),
        RangeConstraint(Version("3.5"), Version("3.6")),
        RangeConstraint(Version("3.5"), Version("3.6")),
    ),
]


@pytest.mark.parametrize(
    ("name", "left", "right", "expected"),
    intersect_testdata,
    ids=[x[0] for x in intersect_testdata],
)
def test_range_constraint_intersect(
    name: str,
    left: RangeConstraint,
    right: RangeConstraint,
    expected: RangeConstraint | None,
):
    assert left.intersect(right) == expected


def test_range_constraint_intersect_is_symmetric():
    """Test that intersect() gives the same result regardless of argument order."""
    left = RangeConstraint(Version("3.7"), Version("3.11"))
    right = RangeConstraint(Version("3.9"), Version("3.12"))
    assert left.intersect(right) == right.intersect(left)


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
