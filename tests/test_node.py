import pytest
from markerpry.node import FALSE, TRUE, BooleanNode, ExpressionNode, OperatorNode


def test_boolean_node_contains():
    """Test that BooleanNode never contains any keys."""
    node = BooleanNode(True)
    assert "python_version" not in node
    assert "os_name" not in node
    assert "" not in node


def test_expression_node_contains():
    """Test that ExpressionNode contains only its lhs key."""
    expr = ExpressionNode("python_version", ">=", "3.7")

    assert "python_version" in expr
    assert "os_name" not in expr
    assert "python_implementation" not in expr
    assert "" not in expr


def test_operator_node_contains():
    """Test that OperatorNode contains keys from both its children."""
    expr1 = ExpressionNode("python_version", ">=", "3.7")
    expr2 = ExpressionNode("os_name", "==", "posix")
    and_node = OperatorNode("and", expr1, expr2)

    assert "python_version" in and_node
    assert "os_name" in and_node
    assert "python_implementation" not in and_node
    assert "" not in and_node


def test_operator_node_nested_contains():
    """Test that OperatorNode correctly checks deeply nested expressions."""
    expr1 = ExpressionNode("python_version", ">=", "3.7")
    expr2 = ExpressionNode("os_name", "==", "posix")
    and_node = OperatorNode("and", expr1, expr2)
    expr3 = ExpressionNode("implementation_name", "==", "cpython")
    or_node = OperatorNode("or", and_node, expr3)

    assert "python_version" in or_node
    assert "os_name" in or_node
    assert "implementation_name" in or_node
    assert "platform_machine" not in or_node
    assert "" not in or_node


def test_operator_node_with_boolean_contains():
    """Test that OperatorNode with boolean children still checks remaining expressions."""
    expr = ExpressionNode("python_version", ">=", "3.7")
    true_node = BooleanNode(True)
    and_node = OperatorNode("and", true_node, expr)

    assert "python_version" in and_node
    assert "os_name" not in and_node
    assert "" not in and_node


def test_boolean_equality():
    """Test boolean node equality with both BooleanNodes and Python bools."""
    assert BooleanNode(True) == BooleanNode(True)
    assert BooleanNode(True) != BooleanNode(False)
    assert TRUE == TRUE
    assert BooleanNode(True) == TRUE
    # New tests for bool comparison
    assert TRUE == True  # noqa: E712
    assert FALSE == False  # noqa: E712
    assert TRUE != False  # noqa: E712
    assert FALSE != True  # noqa: E712


def test_boolean_coercion():
    """Test that BooleanNode can be used in boolean contexts."""
    assert bool(TRUE) is True
    assert bool(FALSE) is False
    # Test in if statement
    if TRUE:
        assert True
    else:
        pytest.fail("TRUE should be truthy")
    if FALSE:
        pytest.fail("FALSE should be falsy")
    else:
        assert True
    # Test with and/or
    combined_and = TRUE and True
    assert combined_and
    combined_and_falsy = FALSE and True
    assert not combined_and_falsy
    combined_or = TRUE or False
    assert combined_or
    combined_or_falsy = FALSE or False
    assert not combined_or_falsy


def test_resolved_attribute():
    """Test that the resolved attribute is True iff a node is a BooleanNode"""
    assert BooleanNode(True).resolved
    assert BooleanNode(False).resolved
    assert not ExpressionNode("python_version", ">=", "3.7").resolved
    assert not OperatorNode(
        "and",
        ExpressionNode("os_name", "==", "posix"),
        ExpressionNode("python_version", ">=", "3.7"),
    ).resolved


def test_non_boolean_node_coercion():
    """Test that non-boolean nodes cannot be coerced to bool."""
    expr = ExpressionNode("python_version", ">=", "3.7")
    op = OperatorNode(
        "and",
        ExpressionNode("os_name", "==", "posix"),
        ExpressionNode("python_version", ">=", "3.7"),
    )

    with pytest.raises(TypeError, match="Cannot convert ExpressionNode to bool"):
        bool(expr)

    with pytest.raises(TypeError, match="Cannot convert OperatorNode to bool"):
        bool(op)

    # Test in if statement
    with pytest.raises(TypeError, match="Cannot convert ExpressionNode to bool"):
        _ = 1 if expr else 0

    with pytest.raises(TypeError, match="Cannot convert OperatorNode to bool"):
        _ = 1 if op else 0


# In/NotIn operator tests
in_operator_testdata = [
    (
        "in_check_rhs",
        ExpressionNode(lhs="value", comparator="in", rhs="python_version"),
        "python_version",
        True,  # Should check rhs
    ),
    (
        "in_check_lhs",
        ExpressionNode(lhs="value", comparator="in", rhs="python_version"),
        "value",
        False,  # lhs is not a dependency
    ),
    (
        "in_check_other",
        ExpressionNode(lhs="value", comparator="in", rhs="python_version"),
        "other_key",
        False,  # other keys not included
    ),
    (
        "not_in_check_rhs",
        ExpressionNode(lhs="value", comparator="not in", rhs="python_version"),
        "python_version",
        True,  # Should check rhs
    ),
    (
        "not_in_check_lhs",
        ExpressionNode(lhs="value", comparator="not in", rhs="python_version"),
        "value",
        False,  # lhs is not a dependency
    ),
    (
        "not_in_check_other",
        ExpressionNode(lhs="value", comparator="not in", rhs="python_version"),
        "other_key",
        False,  # other keys not included
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "key", "expected"),
    in_operator_testdata,
    ids=[x[0] for x in in_operator_testdata],
)
def test_in_operator_contains(name: str, expr: ExpressionNode, key: str, expected: bool):
    """Test that 'in' and 'not in' expressions check the correct keys."""
    assert (key in expr) == expected


# String representation tests for in/not in
in_str_testdata = [
    (
        "in_version",
        ExpressionNode(lhs="3.7", comparator="in", rhs="python_version"),
        '"3.7" in python_version',
    ),
    (
        "in_platform",
        ExpressionNode(lhs="linux", comparator="in", rhs="sys_platform"),
        '"linux" in sys_platform',
    ),
    (
        "not_in_version",
        ExpressionNode(lhs="3.7", comparator="not in", rhs="python_version"),
        '"3.7" not in python_version',
    ),
    (
        "not_in_platform",
        ExpressionNode(lhs="linux", comparator="not in", rhs="sys_platform"),
        '"linux" not in sys_platform',
    ),
    (
        "triple_equal_version",
        ExpressionNode(lhs="python_version", comparator="===", rhs="3.7"),
        'python_version === "3.7"',
    ),
    (
        "triple_equal_platform",
        ExpressionNode(lhs="sys_platform", comparator="===", rhs="linux"),
        'sys_platform === "linux"',
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "expected_str"),
    in_str_testdata,
    ids=[x[0] for x in in_str_testdata],
)
def test_in_operator_str(name: str, expr: ExpressionNode, expected_str: str):
    """Test string representation of 'in' and 'not in' expressions."""
    assert str(expr) == expected_str


# Expression node contains tests
expression_contains_testdata = [
    (
        "normal_comparison_lhs",
        ExpressionNode(lhs="python_version", comparator=">=", rhs="3.7"),
        "python_version",
        True,  # lhs is the key for normal comparisons
    ),
    (
        "normal_comparison_rhs",
        ExpressionNode(lhs="python_version", comparator=">=", rhs="3.7"),
        "3.7",
        False,  # rhs is not a key for normal comparisons
    ),
    (
        "in_operator_lhs",
        ExpressionNode(lhs="3.7", comparator="in", rhs="python_version"),
        "3.7",
        False,  # lhs is not a key for 'in' operator
    ),
    (
        "in_operator_rhs",
        ExpressionNode(lhs="3.7", comparator="in", rhs="python_version"),
        "python_version",
        True,  # rhs is the key for 'in' operator
    ),
    (
        "not_in_operator_lhs",
        ExpressionNode(lhs="3.7", comparator="not in", rhs="python_version"),
        "3.7",
        False,  # lhs is not a key for 'not in' operator
    ),
    (
        "not_in_operator_rhs",
        ExpressionNode(lhs="3.7", comparator="not in", rhs="python_version"),
        "python_version",
        True,  # rhs is the key for 'not in' operator
    ),
    (
        "normal_comparison_other",
        ExpressionNode(lhs="python_version", comparator=">=", rhs="3.7"),
        "other_key",
        False,  # unrelated keys are never contained
    ),
    (
        "in_operator_other",
        ExpressionNode(lhs="3.7", comparator="in", rhs="python_version"),
        "other_key",
        False,  # unrelated keys are never contained
    ),
    (
        "triple_equal_lhs",
        ExpressionNode(lhs="python_version", comparator="===", rhs="3.7"),
        "python_version",
        True,  # lhs is the key for triple equal comparison
    ),
    (
        "triple_equal_rhs",
        ExpressionNode(lhs="python_version", comparator="===", rhs="3.7"),
        "3.7",
        False,  # rhs is not a key for triple equal comparison
    ),
    (
        "triple_equal_other",
        ExpressionNode(lhs="python_version", comparator="===", rhs="3.7"),
        "other_key",
        False,  # unrelated keys are never contained
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "key", "expected"),
    expression_contains_testdata,
    ids=[x[0] for x in expression_contains_testdata],
)
def test_expression_contains(name: str, expr: ExpressionNode, key: str, expected: bool):
    """Test that __contains__ works correctly for all expression types."""
    assert (key in expr) == expected
