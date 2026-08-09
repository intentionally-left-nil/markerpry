# Markerpry

[![PyPI - Version](https://img.shields.io/pypi/v/markerpry.svg)](https://pypi.org/project/markerpry)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/markerpry.svg)](https://pypi.org/project/markerpry)

---

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
  - [Parsing Markers](#parsing-markers)
  - [Tree Navigation](#tree-navigation)
  - [String Representation](#string-representation)
  - [Evaluation](#evaluation)
- [License](#license)

## Installation

```console
pip install markerpry
```

## Usage

Markerpry provides a powerful way to parse, manipulate and evaluate Python package environment markers.

### Parsing Markers

Use the `parse()` method to create a tree structure from a marker string:

```python
from markerpry import parse

# Parse a marker expression into a tree
tree = parse('python_version >= "3.7" and (os_name == "posix" or platform_system == "Linux")')
```

The parse method returns a tree where each node is one of:

- `BooleanNode`: Represents True/False values
- `ExpressionNode`: Represents comparisons like `python_version >= "3.7"`
- `OperatorNode`: Represents logical operations (`and`/`or`) between nodes

### Tree Navigation

The tree can be navigated using the `left` and `right` properties of nodes. These properties
return `None` for leaf nodes (BooleanNode and ExpressionNode):

```python
# For operator nodes (and/or), access child nodes
left_expr = tree.left  # python_version >= "3.7"
right_expr = tree.right  # (os_name == "posix" or platform_system == "Linux")

# For nested expressions, continue traversing
nested_left = right_expr.left  # os_name == "posix"
nested_right = right_expr.right  # platform_system == "Linux"

# Leaf nodes have no children
assert nested_left.left is None
assert nested_left.right is None
```

### Checking for Keys

You can check if a marker expression contains a specific environment key using the `in` operator:

```python
# Check if a marker depends on specific environment keys
tree = parse('python_version >= "3.7" and os_name == "posix"')

assert "python_version" in tree
assert "os_name" in tree
assert "platform_machine" not in tree
```

### String Representation

The tree can be converted back to a string using `str()`, which produces a format compatible with `packaging.markers.Marker`:

```python
# Convert tree back to string
marker_string = str(tree)
# 'python_version >= "3.7" and (os_name == "posix" or platform_system == "Linux")'

# Use with packaging.markers
from packaging.markers import Marker

marker = Marker(str(tree))
```

### Evaluation

The `evaluate()` method partially evaluates the tree based on the provided environment:

```python
from packaging.version import Version
import re

# Define an environment with known values
env = {
    "python_version": [Version("3.8")],
    "os_name": ["posix"],
    "platform_system": ["Linux"],
    "implementation_name": [re.compile("py.*")],  # Matches python, pypy, etc.
}

# Evaluate the tree
result = tree.evaluate(env)

# The result will be a simplified tree or a BooleanNode
# In this case, it would evaluate to BooleanNode(True)
```

The evaluation process:

#### Environment Values

Each environment key can contain a list of different types of values:

- `Version` objects: Used for version comparisons (`python_version`, etc.)
  - Work with all comparators (`==`, `!=`, `<`, `<=`, `>`, `>=`)
  - Version strings are parsed using `packaging.specifiers.SpecifierSet`
- `str` values: Used for exact string matching
  - Only work with equality comparators (`==`, `!=`)
  - Other comparators (`<`, `<=`, `>`, `>=`) will leave the expression unevaluated
- `re.Pattern` objects: Used for pattern matching
  - Only work with equality comparators (`==`, `!=`)
  - `==` checks if the pattern matches
  - `!=` checks if the pattern doesn't match

#### Multiple Values

When multiple values are provided for an environment key:

```python
env = {"python_version": [Version("3.8"), Version("3.9")], "os_name": ["posix", "nt"]}
```

- The expression is evaluated against each value
- Results are combined with OR logic (any match makes it true)
- If no values match, the expression remains unevaluated

#### Tree Simplification

The evaluation simplifies boolean operations where possible:

```python
# For OR operations:
True or X  => True        # Short circuits to True
False or X => X          # Continues evaluation with X

# For AND operations:
False and X => False     # Short circuits to False
True and X  => X        # Continues evaluation with X
```

For example:

```python
# Original: python_version >= "3.7" and (os_name == "posix" or platform_system == "Linux")
env = {"python_version": [Version("3.6")]}
# Evaluates to: False and (os_name == "posix" or platform_system == "Linux")
# Simplifies to: False

env = {"python_version": [Version("3.8")], "os_name": ["posix"]}
# Evaluates to: True and (True or platform_system == "Linux")
# Simplifies to: True
```

If any parts of the expression can't be evaluated (due to missing environment values or incompatible comparators), they remain as expressions in the resulting tree.

## License

`markerpry` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and packaging.

```console
# Install dependencies (including dev tools) into a local virtualenv
uv sync

# Run the test suite
uv run pytest

# Run linters
uv run isort --check --diff .
uv run black --check --diff .
uv run mypy --check-untyped-defs markerpry tests

# Build the package
uv build
```

