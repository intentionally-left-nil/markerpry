import re
from typing import Literal

import pytest
from markerpry.constraint import (
    ExactConstraint,
    FlagConstraint,
    PatternConstraint,
    StringConstraint,
)
from markerpry.node import (
    BooleanNode,
    CompareNode,
    ContainsNode,
    Environment,
    Node,
    OperatorNode,
)
from markerpry.parser import parse
from packaging.markers import Marker
from packaging.version import Version

# Basic string comparison tests
string_testdata = [
    (
        "string_equality_true",
        CompareNode(key="os_name", comparator="==", literal="posix"),
        {"os_name": ["posix"]},
        BooleanNode(True),
    ),
    (
        "string_equality_false",
        CompareNode(key="os_name", comparator="==", literal="nt"),
        {"os_name": ["posix"]},
        BooleanNode(False),
    ),
    (
        "string_inequality_true",
        CompareNode(key="os_name", comparator="!=", literal="nt"),
        {"os_name": ["posix"]},
        BooleanNode(True),
    ),
    (
        "string_inequality_false",
        CompareNode(key="os_name", comparator="!=", literal="posix"),
        {"os_name": ["posix"]},
        BooleanNode(False),
    ),
    (
        "string_invalid_operator",
        CompareNode(key="os_name", comparator=">", literal="posix"),
        {"os_name": ["posix"]},
        CompareNode(key="os_name", comparator=">", literal="posix"),
    ),
    (
        "string_in_operator",
        ContainsNode(key="os_name", literal="posix", key_on_left=False),
        {"os_name": ["posix"]},
        BooleanNode(True),
    ),
    (
        "inverted_string_in_operator",
        ContainsNode(key="os_name", literal="posix", key_on_left=True),
        {"os_name": ["posix"]},
        BooleanNode(True),
    ),
    (
        "inverted_string_not_in_operator",
        ContainsNode(key="os_name", literal="posix", key_on_left=True, negate=True),
        {"os_name": ["posix"]},
        BooleanNode(False),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    string_testdata,
    ids=[x[0] for x in string_testdata],
)
def test_string_evaluate(name: str, expr: Node, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


# Resolved attribute tests
resolved_testdata = [
    (
        "string_equality_true",
        CompareNode(key="os_name", comparator="==", literal="posix"),
        {"os_name": ["posix"]},
        True,
    ),
    (
        "string_equality_false",
        CompareNode(key="os_name", comparator="==", literal="nt"),
        {"os_name": ["posix"]},
        True,
    ),
    (
        "string_equality_incomplete",
        CompareNode(key="os_name", comparator="==", literal="nt"),
        {"python_version": [Version("3.7")]},
        False,
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    resolved_testdata,
    ids=[x[0] for x in resolved_testdata],
)
def test_resolved_attribute_on_evaluate(
    name: str, expr: CompareNode, env: Environment, expected: bool
):
    result = expr.evaluate(env)
    assert result.resolved == expected


# Version comparison tests
version_testdata = [
    (
        "version_greater_than_true",
        CompareNode(key="python_version", comparator=">", literal="3.7"),
        {"python_version": [Version("3.8")]},
        BooleanNode(True),
    ),
    (
        "version_greater_than_false",
        CompareNode(key="python_version", comparator=">", literal="3.8"),
        {"python_version": [Version("3.7")]},
        BooleanNode(False),
    ),
    (
        "version_greater_equal_true",
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
        {"python_version": [Version("3.8")]},
        BooleanNode(True),
    ),
    (
        "version_less_than_true",
        CompareNode(key="python_version", comparator="<", literal="3.8"),
        {"python_version": [Version("3.7")]},
        BooleanNode(True),
    ),
    (
        "version_less_equal_true",
        CompareNode(key="python_version", comparator="<=", literal="3.8"),
        {"python_version": [Version("3.8")]},
        BooleanNode(True),
    ),
    (
        "version_compatible_release_true",
        CompareNode(key="python_version", comparator="~=", literal="3.7"),
        {"python_version": [Version("3.7.5")]},
        BooleanNode(True),
    ),
    (
        "version_compatible_release_false",
        CompareNode(key="python_version", comparator="~=", literal="3.7"),
        {"python_version": [Version("4.0")]},
        BooleanNode(False),
    ),
    (
        "version_in_true",
        ContainsNode(key="python_version", literal="2.7", key_on_left=False),
        {"python_version": [Version("2.7")]},
        BooleanNode(True),
    ),
    (
        "inverted_version_in_true",
        ContainsNode(key="python_version", literal="2.7", key_on_left=True),
        {"python_version": [Version("2.7")]},
        BooleanNode(True),
    ),
    (
        "version_not_in_false",
        ContainsNode(key="python_version", literal="2.7", key_on_left=False, negate=True),
        {"python_version": [Version("2.7")]},
        BooleanNode(False),
    ),
    (
        "inverted_version_not_in_false",
        ContainsNode(key="python_version", literal="2.7", key_on_left=True, negate=True),
        {"python_version": [Version("2.7")]},
        BooleanNode(False),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    version_testdata,
    ids=[x[0] for x in version_testdata],
)
def test_version_evaluate(name: str, expr: Node, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


contains_node_value_testdata = [
    (
        "contains_node_pattern_undecidable",
        ContainsNode(key="sys_platform", literal="linux", key_on_left=False),
        {"sys_platform": [re.compile("linux.*")]},
        ContainsNode(key="sys_platform", literal="linux", key_on_left=False),
    ),
    (
        "contains_node_boolean_short_circuit",
        ContainsNode(key="python_implementation", literal="CPython", key_on_left=True),
        {"python_implementation": [True]},
        BooleanNode(True),
    ),
    (
        "contains_node_missing_key",
        ContainsNode(key="missing_key", literal="value", key_on_left=True),
        {},
        ContainsNode(key="missing_key", literal="value", key_on_left=True),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    contains_node_value_testdata,
    ids=[x[0] for x in contains_node_value_testdata],
)
def test_contains_node_value_types_evaluate(
    name: str, expr: ContainsNode, env: Environment, expected: Node
):
    result = expr.evaluate(env)
    assert result == expected


# Multiple value tests
multiple_value_testdata = [
    (
        "multiple_values_match_first",
        CompareNode(key="python_version", comparator="==", literal="3.8"),
        {"python_version": [Version("3.7"), Version("3.8"), Version("3.9")]},
        BooleanNode(True),
    ),
    (
        "multiple_values_match_none",
        CompareNode(key="python_version", comparator="==", literal="3.6"),
        {"python_version": [Version("3.7"), Version("3.8"), Version("3.9")]},
        BooleanNode(False),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    multiple_value_testdata,
    ids=[x[0] for x in multiple_value_testdata],
)
def test_multiple_values_evaluate(name: str, expr: CompareNode, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


# Pre-coerced Constraint tests - an environment may hold already-wrapped Constraint
# instances directly; evaluate() must accept those identically to bare values.
pre_coerced_environment_testdata = [
    (
        "compare_node_string",
        CompareNode(key="os_name", comparator="==", literal="posix"),
        {"os_name": [StringConstraint("posix")]},
        BooleanNode(True),
    ),
    (
        "compare_node_pattern",
        CompareNode(key="sys_platform", comparator="==", literal="linux2"),
        {"sys_platform": [PatternConstraint(re.compile("linux.*"))]},
        BooleanNode(True),
    ),
    (
        "compare_node_exact",
        CompareNode(key="python_version", comparator=">=", literal="3.7"),
        {"python_version": [ExactConstraint(Version("3.8"))]},
        BooleanNode(True),
    ),
    (
        "compare_node_flag",
        CompareNode(key="python_implementation", comparator="==", literal="CPython"),
        {"python_implementation": [FlagConstraint(True)]},
        BooleanNode(True),
    ),
    (
        "contains_node_string",
        ContainsNode(key="sys_platform", literal="linux", key_on_left=False),
        {"sys_platform": [StringConstraint("linux2")]},
        BooleanNode(True),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    pre_coerced_environment_testdata,
    ids=[x[0] for x in pre_coerced_environment_testdata],
)
def test_evaluate_with_pre_coerced_environment(
    name: str, expr: Node, env: Environment, expected: Node
):
    result = expr.evaluate(env)
    assert result == expected


# Missing environment tests
missing_env_testdata = [
    (
        "missing_key",
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
        {},
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
    ),
    (
        "empty_value_list",
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
        {"python_version": []},
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
    ),
    (
        "different_key_present",
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
        {"os_name": ["posix"]},
        CompareNode(key="python_version", comparator=">=", literal="3.8"),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    missing_env_testdata,
    ids=[x[0] for x in missing_env_testdata],
)
def test_missing_env_evaluate(name: str, expr: CompareNode, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


# Regex pattern tests
regex_testdata = [
    (
        "regex_exact_match_true",
        CompareNode(key="sys_platform", comparator="==", literal="linux"),
        {"sys_platform": [re.compile("linux")]},
        BooleanNode(True),
    ),
    (
        "regex_exact_match_false",
        CompareNode(key="sys_platform", comparator="==", literal="darwin"),
        {"sys_platform": [re.compile("linux")]},
        BooleanNode(False),
    ),
    (
        "regex_pattern_match_true",
        CompareNode(key="sys_platform", comparator="==", literal="linux2"),
        {"sys_platform": [re.compile("linux.*")]},
        BooleanNode(True),
    ),
    (
        "regex_pattern_match_false",
        CompareNode(key="sys_platform", comparator="==", literal="darwin"),
        {"sys_platform": [re.compile("linux.*")]},
        BooleanNode(False),
    ),
    (
        "regex_inequality_true",
        CompareNode(key="sys_platform", comparator="!=", literal="darwin"),
        {"sys_platform": [re.compile("linux.*")]},
        BooleanNode(True),
    ),
    (
        "regex_inequality_false",
        CompareNode(key="sys_platform", comparator="!=", literal="linux2"),
        {"sys_platform": [re.compile("linux.*")]},
        BooleanNode(False),
    ),
    (
        "regex_invalid_operator",
        CompareNode(key="sys_platform", comparator=">", literal="linux"),
        {"sys_platform": [re.compile("linux.*")]},
        CompareNode(key="sys_platform", comparator=">", literal="linux"),
    ),
    (
        "regex_multiple_patterns",
        CompareNode(key="sys_platform", comparator="==", literal="linux2"),
        {
            "sys_platform": [
                re.compile("darwin.*"),
                re.compile("linux.*"),
                re.compile("win32"),
            ]
        },
        BooleanNode(True),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    regex_testdata,
    ids=[x[0] for x in regex_testdata],
)
def test_regex_evaluate(name: str, expr: CompareNode, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


# Boolean literal tests
boolean_literal_testdata = [
    (
        "boolean_literal_true",
        CompareNode("python_implementation", "==", "CPython"),
        {"python_implementation": [True]},
        BooleanNode(True),
    ),
    (
        "boolean_literal_false",
        CompareNode("python_implementation", "==", "CPython"),
        {"python_implementation": [False]},
        BooleanNode(False),
    ),
    (
        "boolean_true_with_other_values",
        CompareNode("python_implementation", "==", "CPython"),
        {"python_implementation": ["PyPy", True, "CPython"]},
        BooleanNode(True),
    ),
    (
        "boolean_false_with_other_values",
        CompareNode("python_implementation", "==", "CPython"),
        {"python_implementation": ["CPython", False, "CPython"]},
        BooleanNode(False),
    ),
    (
        "boolean_in_and_operator",
        OperatorNode(
            operator="and",
            _left=CompareNode("python_implementation", "==", "CPython"),
            _right=CompareNode("python_version", ">=", "3.7"),
        ),
        {
            "python_implementation": [True],
            "python_version": [Version("3.8")],
        },
        BooleanNode(True),
    ),
    (
        "boolean_in_or_operator",
        OperatorNode(
            operator="or",
            _left=CompareNode("python_implementation", "==", "CPython"),
            _right=CompareNode("python_version", ">=", "3.7"),
        ),
        {
            "python_implementation": [False],
            "python_version": [Version("3.6")],
        },
        BooleanNode(False),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    boolean_literal_testdata,
    ids=[x[0] for x in boolean_literal_testdata],
)
def test_boolean_literal_evaluate(name: str, expr: Node, env: Environment, expected: Node):
    """Test evaluation of boolean literals in various contexts."""
    result = expr.evaluate(env)
    assert result == expected


operator_testdata = [
    # AND operations with partial evaluation
    (
        "and_right_true_left_unknown",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="missing_key", comparator="==", literal="value"),
            _right=CompareNode(key="os_name", comparator="==", literal="posix"),
        ),
        {"os_name": ["posix"]},  # right evaluates to True
        CompareNode(key="missing_key", comparator="==", literal="value"),  # Returns left expression
    ),
    (
        "and_left_true_right_unknown",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="missing_key", comparator="==", literal="value"),
        ),
        {"os_name": ["posix"]},  # left evaluates to True
        CompareNode(
            key="missing_key", comparator="==", literal="value"
        ),  # Returns right expression
    ),
    (
        "and_left_false_shortcircuit",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="missing_key", comparator="==", literal="value"),
        ),
        {"os_name": ["nt"]},  # left evaluates to False
        BooleanNode(False),  # Short circuits to False
    ),
    # OR operations with partial evaluation
    (
        "or_right_false_left_unknown",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="missing_key", comparator="==", literal="value"),
            _right=CompareNode(key="os_name", comparator="==", literal="posix"),
        ),
        {"os_name": ["nt"]},  # right evaluates to False
        CompareNode(key="missing_key", comparator="==", literal="value"),  # Returns left expression
    ),
    (
        "or_left_false_right_unknown",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="missing_key", comparator="==", literal="value"),
        ),
        {"os_name": ["nt"]},  # left evaluates to False
        CompareNode(
            key="missing_key", comparator="==", literal="value"
        ),  # Returns right expression
    ),
    (
        "or_left_true_shortcircuit",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="missing_key", comparator="==", literal="value"),
        ),
        {"os_name": ["posix"]},  # left evaluates to True
        BooleanNode(True),  # Short circuits to True
    ),
    # No evaluation possible
    (
        "both_operands_unknown",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="key1", comparator="==", literal="value1"),
            _right=CompareNode(key="key2", comparator="==", literal="value2"),
        ),
        {},  # nothing can be evaluated
        OperatorNode(  # Returns unchanged node
            operator="and",
            _left=CompareNode(key="key1", comparator="==", literal="value1"),
            _right=CompareNode(key="key2", comparator="==", literal="value2"),
        ),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    operator_testdata,
    ids=[x[0] for x in operator_testdata],
)
def test_operator_evaluate(name: str, expr: OperatorNode, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


def test_complex_partial_evaluation():
    """Test a complex tree where only part of it can be evaluated."""
    # "(python_version >= '3.8' and os_name == 'posix') or
    #  (sys_platform == 'linux' and implementation_name == 'cpython')"
    expr = parse(
        "(python_version >= '3.8' and os_name == 'posix') or "
        "(sys_platform == 'linux' and implementation_name == 'cpython')"
    )

    # Environment that:
    # - Doesn't have python_version or os_name (left tree can't evaluate)
    # - Has sys_platform as linux (first part of right tree evaluates to True)
    # - Has implementation_name as cpython (second part evaluates to True)
    env: Environment = {
        "sys_platform": ["linux"],
        "implementation_name": ["cpython"],
    }

    # Expected:
    # - Left side stays as is because environment is missing
    # - Right side evaluates to True because both parts are True
    # - Overall result is True because one side of OR is True
    expected = BooleanNode(True)

    result = expr.evaluate(env)
    assert result == expected


# OR short-circuit tests
or_shortcircuit_testdata = [
    (
        "or_left_true_shortcircuit",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="missing_key", comparator="==", literal="value"),
        ),
        {"os_name": ["posix"]},  # right side can't evaluate but not needed
        BooleanNode(True),
    ),
    (
        "or_right_true_shortcircuit",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="missing_key", comparator="==", literal="value"),
            _right=CompareNode(key="os_name", comparator="==", literal="posix"),
        ),
        {"os_name": ["posix"]},  # left side can't evaluate but not needed
        BooleanNode(True),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    or_shortcircuit_testdata,
    ids=[x[0] for x in or_shortcircuit_testdata],
)
def test_or_shortcircuit_evaluate(name: str, expr: OperatorNode, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


partial_eval_testdata = [
    (
        "or_left_not_bool",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="missing_key", comparator="==", literal="value"),
            _right=CompareNode(key="os_name", comparator="==", literal="posix"),
        ),
        {"os_name": ["nt"]},  # right evaluates to False
        CompareNode(key="missing_key", comparator="==", literal="value"),
    ),
    (
        "or_right_not_bool",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="missing_key", comparator="==", literal="value"),
        ),
        {"os_name": ["nt"]},  # left evaluates to False
        CompareNode(key="missing_key", comparator="==", literal="value"),
    ),
    (
        "and_left_not_bool",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="missing_key", comparator="==", literal="value"),
            _right=CompareNode(key="os_name", comparator="==", literal="posix"),
        ),
        {"os_name": ["posix"]},  # right evaluates to True
        CompareNode(key="missing_key", comparator="==", literal="value"),
    ),
    (
        "and_right_not_bool",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="missing_key", comparator="==", literal="value"),
        ),
        {"os_name": ["posix"]},  # left evaluates to True
        CompareNode(key="missing_key", comparator="==", literal="value"),
    ),
    (
        "neither_side_bool",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="key1", comparator="==", literal="value1"),
            _right=CompareNode(key="key2", comparator="==", literal="value2"),
        ),
        {},  # nothing evaluates
        OperatorNode(
            operator="and",
            _left=CompareNode(key="key1", comparator="==", literal="value1"),
            _right=CompareNode(key="key2", comparator="==", literal="value2"),
        ),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    partial_eval_testdata,
    ids=[x[0] for x in partial_eval_testdata],
)
def test_partial_evaluation(name: str, expr: OperatorNode, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


# Full evaluation tests
full_eval_testdata = [
    (
        "and_both_true",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="python_version", comparator=">=", literal="3.8"),
        ),
        {"os_name": ["posix"], "python_version": [Version("3.8")]},
        BooleanNode(True),
    ),
    (
        "and_both_false",
        OperatorNode(
            operator="and",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="python_version", comparator=">=", literal="3.8"),
        ),
        {"os_name": ["nt"], "python_version": [Version("3.7")]},
        BooleanNode(False),
    ),
    (
        "or_both_false",
        OperatorNode(
            operator="or",
            _left=CompareNode(key="os_name", comparator="==", literal="posix"),
            _right=CompareNode(key="python_version", comparator=">=", literal="3.8"),
        ),
        {"os_name": ["nt"], "python_version": [Version("3.7")]},
        BooleanNode(False),
    ),
]


@pytest.mark.parametrize(
    ("name", "expr", "env", "expected"),
    full_eval_testdata,
    ids=[x[0] for x in full_eval_testdata],
)
def test_full_evaluation(name: str, expr: OperatorNode, env: Environment, expected: Node):
    result = expr.evaluate(env)
    assert result == expected


# OperatorNode.combine() tests
combine_testdata = [
    (
        "or_left_true",
        "or",
        BooleanNode(True),
        CompareNode("os_name", "==", "posix"),
        BooleanNode(True),
    ),
    (
        "or_left_false",
        "or",
        BooleanNode(False),
        CompareNode("os_name", "==", "posix"),
        CompareNode("os_name", "==", "posix"),
    ),
    (
        "or_right_true",
        "or",
        CompareNode("os_name", "==", "posix"),
        BooleanNode(True),
        BooleanNode(True),
    ),
    (
        "or_right_false",
        "or",
        CompareNode("os_name", "==", "posix"),
        BooleanNode(False),
        CompareNode("os_name", "==", "posix"),
    ),
    (
        "or_neither_boolean",
        "or",
        CompareNode("os_name", "==", "posix"),
        CompareNode("python_version", ">=", "3.7"),
        OperatorNode(
            "or",
            CompareNode("os_name", "==", "posix"),
            CompareNode("python_version", ">=", "3.7"),
        ),
    ),
    (
        "and_left_true",
        "and",
        BooleanNode(True),
        CompareNode("os_name", "==", "posix"),
        CompareNode("os_name", "==", "posix"),
    ),
    (
        "and_left_false",
        "and",
        BooleanNode(False),
        CompareNode("os_name", "==", "posix"),
        BooleanNode(False),
    ),
    (
        "and_right_true",
        "and",
        CompareNode("os_name", "==", "posix"),
        BooleanNode(True),
        CompareNode("os_name", "==", "posix"),
    ),
    (
        "and_right_false",
        "and",
        CompareNode("os_name", "==", "posix"),
        BooleanNode(False),
        BooleanNode(False),
    ),
    (
        "and_neither_boolean",
        "and",
        CompareNode("os_name", "==", "posix"),
        CompareNode("python_version", ">=", "3.7"),
        OperatorNode(
            "and",
            CompareNode("os_name", "==", "posix"),
            CompareNode("python_version", ">=", "3.7"),
        ),
    ),
]


@pytest.mark.parametrize(
    ("name", "operator", "left", "right", "expected"),
    combine_testdata,
    ids=[x[0] for x in combine_testdata],
)
def test_combine(
    name: str, operator: Literal["and", "or"], left: Node, right: Node, expected: Node
):
    """Test that combine() applies the and/or short-circuit simplification directly."""
    assert OperatorNode.combine(operator, left, right) == expected


# Comparison tests with packaging.Marker
packaging_comparison_testdata = [
    # Basic in/not in tests
    (
        "in_no_match",
        '"2.7" in python_version',
        {"python_version": ["2.6"]},
        False,
    ),
    (
        "in_exact_match",
        '"2.7" in python_version',
        {"python_version": ["2.7"]},
        True,
    ),
    (
        "in_partial_match",
        '"2." in python_version',
        {"python_version": ["2.7"]},
        True,
    ),
    (
        "not_in_match",
        '"2.7" not in python_version',
        {"python_version": ["3.6"]},
        True,
    ),
    # Basic in/not in tests using Version specs
    (
        "in_no_match",
        '"2.7" in python_version',
        {"python_version": [Version("2.6")]},
        False,
    ),
    (
        "in_exact_match",
        '"2.7" in python_version',
        {"python_version": [Version("2.7")]},
        True,
    ),
    (
        "in_partial_match",
        '"2." in python_version',
        {"python_version": [Version("2.7")]},
        True,
    ),
    (
        "not_in_match",
        '"2.7" not in python_version',
        {"python_version": [Version("3.6")]},
        True,
    ),
    # Inverted in/not in tests
    (
        "in_no_match_inverted",
        '"2.7" not in python_version',
        {"python_version": ["3.6"]},
        True,
    ),
    (
        "in_exact_match_inverted",
        '"2.7" not in python_version',
        {"python_version": ["2.7"]},
        False,
    ),
    (
        "inverted_in_partial_match",
        'python_version in "2."',
        {"python_version": ["2.7"]},
        False,
    ),
    (
        "inverted_not_in_match",
        'python_version not in "2.7"',
        {"python_version": ["3.6"]},
        True,
    ),
    # Version comparison tests
    (
        "version_equals",
        'python_version == "3.7"',
        {"python_version": ["3.7"]},
        True,
    ),
    (
        "version_not_equals",
        'python_version != "3.7"',
        {"python_version": ["3.8"]},
        True,
    ),
    (
        "version_greater_than",
        'python_version > "3.7"',
        {"python_version": [Version("3.8")]},
        True,
    ),
    (
        "version_less_than",
        'python_version < "3.7"',
        {"python_version": [Version("3.6")]},
        True,
    ),
    (
        "version_greater_equal",
        'python_version >= "3.7"',
        {"python_version": [Version("3.7")]},
        True,
    ),
    (
        "version_less_equal",
        'python_version <= "3.7"',
        {"python_version": [Version("3.7")]},
        True,
    ),
    # Complex version tests
    (
        "version_micro_level",
        'python_version == "3.7.2"',
        {"python_version": [Version("3.7.2")]},
        True,
    ),
    (
        "version_pre_release",
        'python_version == "3.7.0b2"',
        {"python_version": [Version("3.7.0b2")]},
        True,
    ),
    (
        "version_post_release",
        'python_version == "3.7.0.post1"',
        {"python_version": [Version("3.7.0.post1")]},
        True,
    ),
    # Multiple version comparisons
    (
        "version_and",
        'python_version >= "3.6" and python_version < "4.0"',
        {"python_version": [Version("3.7")]},
        True,
    ),
    (
        "version_or",
        'python_version < "3.0" or python_version >= "3.6"',
        {"python_version": [Version("3.7")]},
        True,
    ),
    # Edge cases
    (
        "version_zero",
        'python_version == "0.0"',
        {"python_version": [Version("0.0")]},
        True,
    ),
    (
        "version_dev",
        'python_version == "3.7.0.dev1"',
        {"python_version": [Version("3.7.0.dev1")]},
        True,
    ),
    (
        "version_local",
        'python_version == "3.7.0+local"',
        {"python_version": [Version("3.7.0+local")]},
        True,
    ),
    # Mixed environment tests
    (
        "mixed_version_and_platform",
        'python_version >= "3.6" and sys_platform == "linux"',
        {"python_version": [Version("3.7")], "sys_platform": ["linux"]},
        True,
    ),
    (
        "mixed_version_and_implementation",
        'python_version >= "3.6" and implementation_name == "cpython"',
        {"python_version": [Version("3.7")], "implementation_name": ["cpython"]},
        True,
    ),
]


@pytest.mark.parametrize(
    ("name", "marker_str", "env", "expected"),
    packaging_comparison_testdata,
    ids=[x[0] for x in packaging_comparison_testdata],
)
def test_packaging_comparison(name: str, marker_str: str, env: Environment, expected: bool):
    """Test that our evaluation matches packaging.Marker's evaluation."""
    # Parse and evaluate with our implementation
    our_node = parse(marker_str)
    our_result = our_node.evaluate(env)
    assert isinstance(our_result, BooleanNode)
    assert our_result.state == expected

    # Evaluate with packaging.Marker
    packaging_marker = Marker(marker_str)
    # Convert our environment format to packaging's format
    packaging_env = {k: str(v[0]) for k, v in env.items()}
    packaging_result = packaging_marker.evaluate(packaging_env)
    assert packaging_result == expected
