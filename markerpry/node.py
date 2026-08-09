from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, assert_never, override

from .constraint import Comparator, ComparisonOperator, ConstraintLike, FlagConstraint, coerce

Environment = Mapping[str, Sequence[ConstraintLike]]


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


def _evaluate_constraints(
    values: Sequence[ConstraintLike],
    comparator: Comparator,
    literal: str,
    *,
    key_on_left: bool = False,
) -> bool | None:
    result: bool | None = None
    for value in values:
        constraint = coerce(value)
        if isinstance(constraint, FlagConstraint):
            return constraint.state
        evaluated = constraint.evaluate(comparator, literal, key_on_left=key_on_left)
        result = result if evaluated is None else result or evaluated
    return result


@dataclass(frozen=True)
class CompareNode(Node):
    """A node representing a comparison expression (e.g., python_version > '3.7')."""

    key: str
    comparator: ComparisonOperator
    literal: str

    @override
    def __str__(self) -> str:
        return f'{self.key} {self.comparator} "{self.literal}"'

    @override
    def __contains__(self, key: str) -> bool:
        return self.key == key

    @override
    def evaluate(self, environment: Environment) -> "Node":
        if self.key not in environment:
            return self
        result = _evaluate_constraints(environment[self.key], self.comparator, self.literal)
        return self if result is None else BooleanNode(result)


@dataclass(frozen=True)
class ContainsNode(Node):
    """A node representing a membership test (e.g., '3.7' in python_version)."""

    key: str
    literal: str
    key_on_left: bool
    negate: bool = False

    @override
    def __str__(self) -> str:
        comparator = "not in" if self.negate else "in"
        if self.key_on_left:
            return f'{self.key} {comparator} "{self.literal}"'
        return f'"{self.literal}" {comparator} {self.key}'

    @override
    def __contains__(self, key: str) -> bool:
        return self.key == key

    @override
    def evaluate(self, environment: Environment) -> "Node":
        if self.key not in environment:
            return self
        comparator: Comparator = "not in" if self.negate else "in"
        result = _evaluate_constraints(
            environment[self.key], comparator, self.literal, key_on_left=self.key_on_left
        )
        return self if result is None else BooleanNode(result)


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
        left = self._operand_str(self._left)
        right = self._operand_str(self._right)
        return f"{left} {self.operator} {right}"

    def _operand_str(self, node: "Node") -> str:
        if isinstance(node, OperatorNode) and node.operator != self.operator:
            return f"({node})"
        return str(node)

    @override
    def evaluate(self, environment: Environment) -> "Node":
        left = self._left.evaluate(environment)
        right = self._right.evaluate(environment)

        # If neither child changed, return self
        if left is self._left and right is self._right:
            return self

        return OperatorNode.combine(self.operator, left, right)

    @classmethod
    def combine(cls, operator: Literal["and", "or"], left: Node, right: Node) -> Node:
        """The and/or short-circuit simplification of two already-evaluated child nodes."""
        if operator == "or":
            if isinstance(left, BooleanNode):
                return TRUE if left.state else right
            if isinstance(right, BooleanNode):
                return TRUE if right.state else left
            return cls(operator, left, right)
        elif operator == "and":
            if isinstance(left, BooleanNode):
                return right if left.state else FALSE
            if isinstance(right, BooleanNode):
                return left if right.state else FALSE
            return cls(operator, left, right)
        else:
            assert_never(operator)

    @override
    def __contains__(self, key: str) -> bool:
        # OperatorNode contains keys from both children
        return key in self._left or key in self._right
