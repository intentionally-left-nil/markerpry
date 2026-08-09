import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, assert_never, override

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

Environment = dict[str, list[str | Version | re.Pattern[str] | bool]]
Comparator = Literal["==", "===", "!=", ">", "<", ">=", "<=", "in", "not in", "~="]


class Node(ABC):
    """Base class for all nodes in the marker expression tree."""

    @abstractmethod
    def evaluate(self, environment: Environment) -> "Node":
        """Partially or fully evaluates the node based on the environment"""
        pass

    @override
    @abstractmethod
    def __str__(self) -> str:
        """Return a string representation of this node."""
        pass

    @property
    def left(self) -> "Node | None":
        return None

    @property
    def right(self) -> "Node | None":
        return None

    @property
    def resolved(self) -> bool:
        return False

    @abstractmethod
    def __contains__(self, key: str) -> bool:
        """Return whether this node contains the given key."""
        pass

    def __bool__(self) -> bool:
        """
        Prevent accidental boolean coercion of non-boolean nodes.
        Only BooleanNode should be used in boolean contexts.
        """
        raise TypeError(f"Cannot convert {self.__class__.__name__} to bool - use evaluate() first")


@dataclass(frozen=True)
class BooleanNode(Node):
    """A node representing a boolean literal value."""

    state: bool

    @override
    def __str__(self) -> str:
        return str(self.state)

    @override
    def evaluate(self, environment: Environment) -> "Node":
        return self  # No need to create new BooleanNode since they're immutable

    @override
    def __contains__(self, key: str) -> bool:
        return False  # BooleanNode never contains any keys

    def __bool__(self) -> bool:
        return self.state

    @property
    @override
    def resolved(self) -> bool:
        return True

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, BooleanNode):
            return self.state == other.state
        if isinstance(other, bool):
            return bool(self) == other
        return NotImplemented


TRUE = BooleanNode(True)
FALSE = BooleanNode(False)


@dataclass(frozen=True)
class ExpressionNode(Node):
    """A node representing a comparison expression (e.g., python_version > '3.7')."""

    lhs: str
    comparator: Comparator
    rhs: str
    inverted: bool = False

    @override
    def __str__(self) -> str:
        rhs_is_value = not self.inverted
        if self.comparator in ("in", "not in"):
            rhs_is_value = not rhs_is_value

        lhs = str(self.lhs)
        rhs = str(self.rhs)
        if rhs_is_value:
            rhs = f'"{rhs}"'
        else:
            lhs = f'"{lhs}"'
        return f"{lhs} {self.comparator} {rhs}"

    @override
    def __contains__(self, key: str) -> bool:
        return self._key() == key

    @override
    def evaluate(self, environment: Environment) -> "Node":
        if self._key() not in environment:
            return self
        values = environment[self._key()]
        result: bool | None = None
        for value in values:
            if isinstance(value, str):
                eval = self._evaluate_string(value)
                result = result if eval is None else result or eval
            elif isinstance(value, re.Pattern):
                eval = self._evaluate_pattern(value)
                result = result if eval is None else result or eval
            elif isinstance(value, Version):
                eval = self._evaluate_version(value)
                result = result if eval is None else result or eval
            elif isinstance(value, bool):
                result = value
                break
            else:
                assert_never(value)
        return self if result is None else BooleanNode(result)

    def _evaluate_string(self, value: str) -> "bool | None":
        if self.comparator == "==" or self.comparator == "===":
            return value == self._value()
        elif self.comparator == "!=":
            return value != self._value()
        elif self.comparator == "in":
            return value in self._value() if self.inverted else self._value() in value
        elif self.comparator == "not in":
            return value not in self._value() if self.inverted else self._value() not in value
        else:
            return None

    def _evaluate_pattern(self, value: re.Pattern[str]) -> "bool | None":
        if self.comparator == "==" or self.comparator == "===":
            return value.match(self._value()) is not None
        elif self.comparator == "!=":
            return not value.match(self._value())
        else:
            return None

    def _evaluate_version(self, value: Version) -> "bool | None":
        if self.comparator in ("in", "not in"):
            # From: https://peps.python.org/pep-0508/#environment-markers
            # The <marker_op> operators that are not in <version_cmp> perform
            # the same as they do for strings in Python
            return self._evaluate_string(str(value))
        try:
            specifier = SpecifierSet(f"{self.comparator} {self._value()}")
        except InvalidSpecifier:
            return None
        return specifier.contains(value)

    def _key(self) -> str:
        if self.comparator in ("in", "not in"):
            return self.lhs if self.inverted else self.rhs
        return self.rhs if self.inverted else self.lhs

    def _value(self) -> str:
        if self.comparator in ("in", "not in"):
            return self.rhs if self.inverted else self.lhs
        return self.lhs if self.inverted else self.rhs


@dataclass(frozen=True)
class OperatorNode(Node):
    """A node representing a boolean operation (and/or) between two child nodes."""

    operator: Literal["and", "or"]
    _left: Node
    _right: Node

    @property
    @override
    def left(self) -> "Node | None":
        return self._left

    @property
    @override
    def right(self) -> "Node | None":
        return self._right

    @override
    def __str__(self) -> str:
        return f"({self._left} {self.operator} {self._right})"

    @override
    def evaluate(self, environment: Environment) -> "Node":
        left = self._left.evaluate(environment)
        right = self._right.evaluate(environment)

        # If neither child changed, return self
        if left is self._left and right is self._right:
            return self

        if self.operator == "or":
            if isinstance(left, BooleanNode):
                return TRUE if left.state else right
            if isinstance(right, BooleanNode):
                return TRUE if right.state else left
            return OperatorNode(self.operator, left, right)
        elif self.operator == "and":
            if isinstance(left, BooleanNode):
                return right if left.state else FALSE
            if isinstance(right, BooleanNode):
                return left if right.state else FALSE
            return OperatorNode(self.operator, left, right)
        else:
            assert_never(self.operator)

    @override
    def __contains__(self, key: str) -> bool:
        # OperatorNode contains keys from both children
        return key in self._left or key in self._right
