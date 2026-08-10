from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, assert_never, override

from .constraint import ComparisonOperator, ConstraintLike

Environment = Mapping[str, Sequence[ConstraintLike]]

LeafModifier = Callable[["Node"], "Node"]
ChainModifier = Callable[[Literal["and", "or"], Sequence["Node"]], Sequence["Node"]]


class Node(ABC):
    """Base class for all nodes in the marker expression tree."""

    def modify(
        self, *, leaf: LeafModifier | None = None, chain: ChainModifier | None = None
    ) -> "Node":
        """Rewrite the tree bottom-up via leaf/chain callbacks."""
        return leaf(self) if leaf is not None else self

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
    def modify(
        self, *, leaf: LeafModifier | None = None, chain: ChainModifier | None = None
    ) -> "Node":
        pieces = _flatten_chain(self, self.operator)
        modified = [piece.modify(leaf=leaf, chain=chain) for piece in pieces]
        result_pieces = chain(self.operator, modified) if chain is not None else modified

        # Nodes are frozen dataclasses, so identity, not equality, is the
        # right and cheap "did anything change" test for the whole chain.
        if len(result_pieces) == len(pieces) and all(
            r is p for r, p in zip(result_pieces, pieces, strict=True)
        ):
            return self

        if not result_pieces:
            return TRUE if self.operator == "and" else FALSE

        result: Node = result_pieces[0]
        for piece in result_pieces[1:]:
            result = OperatorNode.combine(self.operator, result, piece)
        return result

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


def _flatten_chain(node: Node, operator: Literal["and", "or"]) -> list[Node]:
    # A differently-operated subtree is one opaque chain member, never descended into.
    if isinstance(node, OperatorNode) and node.operator == operator:
        return _flatten_chain(node._left, operator) + _flatten_chain(node._right, operator)
    return [node]
