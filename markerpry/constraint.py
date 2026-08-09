import re
from dataclasses import dataclass
from typing import Literal, Protocol

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

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
