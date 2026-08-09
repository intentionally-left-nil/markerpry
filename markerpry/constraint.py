import re
from dataclasses import dataclass
from typing import Literal, Protocol, cast

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

Comparator = Literal["==", "===", "!=", ">", "<", ">=", "<=", "in", "not in", "~="]
ComparisonOperator = Literal["==", "===", "!=", ">", "<", ">=", "<=", "~="]


class Constraint(Protocol):
    """A value in the environment that can decide a comparator/literal pair."""

    def evaluate(
        self, comparator: Comparator, literal: str, *, key_on_left: bool = False
    ) -> bool | None:
        """True/False if decidable, None if not."""
        ...


@dataclass(frozen=True)
class StringConstraint:
    """A bare `str` environment value: exact-equality and substring tests."""

    value: str

    def evaluate(
        self, comparator: Comparator, literal: str, *, key_on_left: bool = False
    ) -> bool | None:
        if comparator == "==" or comparator == "===":
            return self.value == literal
        if comparator == "!=":
            return self.value != literal
        if comparator == "in" or comparator == "not in":
            # key_on_left: key in "literal" (is this value a substring of literal)
            # not key_on_left: "literal" in key (is literal a substring of this value)
            is_member = self.value in literal if key_on_left else literal in self.value
            return not is_member if comparator == "not in" else is_member
        return None


@dataclass(frozen=True)
class PatternConstraint:
    """A bare `re.Pattern[str]` environment value: only `==`/`!=` are decidable."""

    regex: re.Pattern[str]

    def evaluate(
        self, comparator: Comparator, literal: str, *, key_on_left: bool = False
    ) -> bool | None:
        if comparator == "==" or comparator == "===":
            return self.regex.match(literal) is not None
        if comparator == "!=":
            return not self.regex.match(literal)
        # Patterns don't support membership tests - only == and != are decidable for them.
        return None


@dataclass(frozen=True)
class ExactConstraint:
    """A bare `Version` environment value: rich comparators via `SpecifierSet`."""

    version: Version

    def evaluate(
        self, comparator: Comparator, literal: str, *, key_on_left: bool = False
    ) -> bool | None:
        if comparator == "in" or comparator == "not in":
            # From: https://peps.python.org/pep-0508/#environment-markers
            # The <marker_op> operators that are not in <version_cmp> perform
            # the same as they do for strings in Python
            return StringConstraint(str(self.version)).evaluate(
                comparator, literal, key_on_left=key_on_left
            )
        try:
            specifier = SpecifierSet(f"{comparator} {literal}")
        except InvalidSpecifier:
            return None
        return specifier.contains(self.version)


@dataclass(frozen=True)
class FlagConstraint:
    """A bare `bool` environment value: unconditionally decides every comparator."""

    state: bool

    def evaluate(
        self, comparator: Comparator, literal: str, *, key_on_left: bool = False
    ) -> bool | None:
        return self.state


# A comparator's truth value against an increasing Version moves in one
# direction only, so checking it at both interval boundaries is sufficient.
_INCREASING_COMPARATORS = {">", ">="}
_DECREASING_COMPARATORS = {"<", "<="}
_MONOTONIC_COMPARATORS = _INCREASING_COMPARATORS | _DECREASING_COMPARATORS


@dataclass(frozen=True)
class RangeConstraint:
    """A `[min, max]` interval of versions (either bound optional)."""

    min: Version | None
    max: Version | None
    include_min: bool = True
    include_max: bool = False

    def _contains(self, version: Version) -> bool:
        if self.min is not None and (
            version < self.min or (version == self.min and not self.include_min)
        ):
            return False
        return not (
            self.max is not None
            and (version > self.max or (version == self.max and not self.include_max))
        )

    def _single_point(self) -> Version | None:
        if (
            self.min is not None
            and self.max is not None
            and self.min == self.max
            and self.include_min
            and self.include_max
        ):
            return self.min
        return None

    def _evaluate_equality(self, comparator: Comparator, literal: str) -> bool | None:
        try:
            version = Version(literal)
        except InvalidVersion:
            return None
        contains = self._contains(version)
        single_point = self._single_point()
        if comparator == "!=":
            if not contains:
                return True
            if single_point is not None:
                return False
            return None
        # "==" and "===" behave the same for a plain version comparison.
        if contains:
            return True if single_point is not None else None
        return False

    def _evaluate_monotonic(self, comparator: ComparisonOperator, literal: str) -> bool | None:
        try:
            specifier = SpecifierSet(f"{comparator} {literal}")
        except InvalidSpecifier:
            return None
        min_holds = specifier.contains(self.min) if self.min is not None else None
        max_holds = specifier.contains(self.max) if self.max is not None else None
        if comparator in _INCREASING_COMPARATORS:
            if min_holds is True:
                return True
            if max_holds is False:
                return False
            return None
        if min_holds is False:
            return False
        if max_holds is True:
            return True
        return None

    def evaluate(
        self, comparator: Comparator, literal: str, *, key_on_left: bool = False
    ) -> bool | None:
        if comparator in ("==", "===", "!="):
            return self._evaluate_equality(comparator, literal)
        if comparator in _MONOTONIC_COMPARATORS:
            return self._evaluate_monotonic(cast(ComparisonOperator, comparator), literal)
        # in / not in / ~= are undecidable for an interval - no observed need,
        # and guessing wrong is worse than staying conditional.
        return None


ConstraintLike = Constraint | str | Version | re.Pattern[str] | bool


def coerce(value: ConstraintLike) -> Constraint:
    """Wrap a bare str/Version/re.Pattern/bool value as its matching Constraint.

    An already-wrapped `Constraint` passes through unchanged.
    """
    if isinstance(value, bool):
        return FlagConstraint(value)
    if isinstance(value, str):
        return StringConstraint(value)
    if isinstance(value, re.Pattern):
        return PatternConstraint(value)
    if isinstance(value, Version):
        return ExactConstraint(value)
    return value
