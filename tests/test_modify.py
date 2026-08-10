from collections.abc import Sequence
from typing import Literal

import pytest
from markerpry.node import (
    FALSE,
    TRUE,
    BooleanNode,
    CompareNode,
    ContainsNode,
    Node,
    OperatorNode,
)
from markerpry.parser import parse

# No-callback identity tests
no_callback_testdata = [
    ("boolean_node", BooleanNode(True)),
    ("compare_node", CompareNode("python_version", ">=", "3.7")),
    ("contains_node", ContainsNode("python_version", "3.7", key_on_left=False)),
    (
        "one_level_and",
        OperatorNode("and", CompareNode("a", "==", "1"), CompareNode("b", "==", "2")),
    ),
    (
        "one_level_or",
        OperatorNode("or", CompareNode("a", "==", "1"), CompareNode("b", "==", "2")),
    ),
    (
        "chained_and",
        OperatorNode(
            "and",
            OperatorNode("and", CompareNode("a", "==", "1"), CompareNode("b", "==", "2")),
            CompareNode("c", "==", "3"),
        ),
    ),
    (
        "mixed_and_or",
        OperatorNode(
            "and",
            OperatorNode("or", CompareNode("a", "==", "1"), CompareNode("b", "==", "2")),
            CompareNode("c", "==", "3"),
        ),
    ),
    (
        "real_world_marker",
        parse('python_version < "2.7" or ("3.0" <= python_version and python_version < "3.2")'),
    ),
]


@pytest.mark.parametrize(
    ("name", "tree"), no_callback_testdata, ids=[x[0] for x in no_callback_testdata]
)
def test_modify_with_no_callbacks_is_identity(name: str, tree: Node):
    assert tree.modify() is tree


def test_modify_leaf_only_folds_extra_clauses_by_shape():
    """Test that a leaf callback folds nodes by shape (key), not by literal value."""
    extras_and = OperatorNode(
        "and",
        CompareNode("extra", "==", "docs"),
        CompareNode("platform_system", "==", "Linux"),
    )
    python_version = CompareNode("python_version", ">=", "3.8")
    tree = OperatorNode("or", extras_and, python_version)

    def fold_extra(node: Node) -> Node:
        return FALSE if isinstance(node, CompareNode) and node.key == "extra" else node

    result = tree.modify(leaf=fold_extra)

    assert result is python_version


def test_modify_chain_flattens_same_operator_runs_and_stops_at_boundaries():
    """Test that chain() flattens a maximal same-operator run and stops at operator boundaries."""
    a = CompareNode("a", "==", "1")
    b = CompareNode("b", "==", "2")
    c = CompareNode("c", "==", "3")
    d = CompareNode("d", "==", "4")
    e = CompareNode("e", "==", "5")
    or_subtree = OperatorNode("or", d, e)
    inner_and = OperatorNode("and", OperatorNode("and", a, b), c)
    tree = OperatorNode("and", inner_and, or_subtree)

    calls: list[tuple[Literal["and", "or"], list[Node]]] = []

    def record_chain(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
        calls.append((operator, list(nodes)))
        return nodes

    result = tree.modify(chain=record_chain)

    assert calls == [("or", [d, e]), ("and", [a, b, c, or_subtree])]
    assert result is tree


def test_modify_chain_sees_pieces_already_modified_by_leaf():
    """Test that chain receives each piece after leaf has already modified it."""
    a = CompareNode("a", "==", "1")
    b = CompareNode("b", "==", "2")
    folded_b = CompareNode("b", "==", "folded")
    tree = OperatorNode("and", a, b)

    def fold_b(node: Node) -> Node:
        return folded_b if node is b else node

    seen: list[Node] = []

    def record_chain(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
        seen.extend(nodes)
        return nodes

    tree.modify(leaf=fold_b, chain=record_chain)

    assert seen == [a, folded_b]


def test_modify_chain_can_drop_duplicate_pieces():
    """Test that a chain callback can drop duplicate pieces from a flattened run."""
    a = CompareNode("a", "==", "1")
    b = CompareNode("b", "==", "2")
    tree = OperatorNode("and", OperatorNode("and", a, b), a)

    def dedupe(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
        deduped: list[Node] = []
        for node in nodes:
            if node not in deduped:
                deduped.append(node)
        return deduped

    assert tree.modify(chain=dedupe) == OperatorNode("and", a, b)


def test_modify_chain_can_grow_the_piece_list():
    """Test that a chain callback can return more pieces than it received."""
    a = CompareNode("a", "==", "1")
    b = CompareNode("b", "==", "2")
    c = CompareNode("c", "==", "3")
    tree = OperatorNode("and", a, b)

    def append_c(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
        return [*nodes, c]

    result = tree.modify(chain=append_c)

    assert result == OperatorNode("and", OperatorNode("and", a, b), c)


def test_modify_chain_collapsing_to_one_piece_returns_it_directly():
    """Test that a chain callback collapsing pieces to one returns that piece by identity."""
    a = CompareNode("a", "==", "1")
    b = CompareNode("b", "==", "2")
    tree = OperatorNode("and", a, b)

    def keep_first(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
        return [nodes[0]]

    assert tree.modify(chain=keep_first) is a


# Empty chain result tests
chain_empty_result_testdata = [
    ("and", TRUE),
    ("or", FALSE),
]


@pytest.mark.parametrize(
    ("operator", "expected"),
    chain_empty_result_testdata,
    ids=[x[0] for x in chain_empty_result_testdata],
)
def test_modify_chain_empty_result_becomes_identity_element(
    operator: Literal["and", "or"], expected: BooleanNode
):
    tree = OperatorNode(operator, CompareNode("a", "==", "1"), CompareNode("b", "==", "2"))
    assert tree.modify(chain=lambda op, nodes: []) == expected


def test_modify_chain_empty_result_shortcircuits_surrounding_expression():
    """Test that an empty chain result short-circuits a surrounding expression via combine()."""
    dropped = OperatorNode("or", CompareNode("a", "==", "1"), CompareNode("b", "==", "2"))
    sibling = CompareNode("c", "==", "3")
    tree = OperatorNode("and", dropped, sibling)

    def drop_or_groups(operator: Literal["and", "or"], nodes: Sequence[Node]) -> Sequence[Node]:
        return [] if operator == "or" else nodes

    assert tree.modify(chain=drop_or_groups) == FALSE


def test_modify_leaf_never_receives_an_operator_node():
    """Test that a leaf callback never receives an OperatorNode."""
    tree = parse(
        '(python_version >= "3.8" and os_name == "posix") or '
        '(sys_platform == "linux" and implementation_name == "cpython")'
    )
    seen_types: set[type] = set()

    def record_leaf(node: Node) -> Node:
        seen_types.add(type(node))
        return node

    tree.modify(leaf=record_leaf)

    assert seen_types == {CompareNode}
