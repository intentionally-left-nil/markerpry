from collections.abc import Sequence

from ..constraint import Comparator, ConstraintLike, FlagConstraint, coerce
from ..node import BooleanNode, CompareNode, ContainsNode, Environment, Node


def evaluate(node: Node, environment: Environment) -> Node:
    """Partially or fully evaluate a node tree against an environment."""
    return node.modify(leaf=lambda leaf_node: _evaluate_leaf(leaf_node, environment))


def _evaluate_leaf(node: Node, environment: Environment) -> Node:
    # modify() only ever hands a leaf here for a non-OperatorNode, so there's no
    # OperatorNode branch to guard against.
    if isinstance(node, BooleanNode):
        return _evaluate_boolean_node(node, environment)
    if isinstance(node, CompareNode):
        return _evaluate_compare_node(node, environment)
    if isinstance(node, ContainsNode):
        return _evaluate_contains_node(node, environment)
    raise AssertionError(f"unreachable: unknown leaf node type {type(node).__name__}")


def _evaluate_boolean_node(node: BooleanNode, environment: Environment) -> Node:
    return node  # No need to create a new BooleanNode since they're immutable


def _evaluate_compare_node(node: CompareNode, environment: Environment) -> Node:
    if node.key not in environment:
        return node
    result = _evaluate_constraints(environment[node.key], node.comparator, node.literal)
    return node if result is None else BooleanNode(result)


def _evaluate_contains_node(node: ContainsNode, environment: Environment) -> Node:
    if node.key not in environment:
        return node
    comparator: Comparator = "not in" if node.negate else "in"
    result = _evaluate_constraints(
        environment[node.key], comparator, node.literal, key_on_left=node.key_on_left
    )
    return node if result is None else BooleanNode(result)


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
