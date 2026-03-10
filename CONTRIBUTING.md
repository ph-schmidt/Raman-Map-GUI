# CONTRIBUTING.md

Thank you for your interest in contributing to this project!  
To keep the codebase clean, consistent, and maintainable, please follow the guidelines below.

---

## 1. Development environment

This project uses `uv`.

No manual virtual environment setup is required.  
`uv` will automatically create a virtual environment and install all dependencies.

### Quick start

Clone the repository and run the application:

```bash
git clone https://github.com/ph-schmidt/Raman-Map-GUI.git
cd Raman-Map-GUI
uv run ramangui
```

This command will:
- Create a local virtual environment
- Install all required dependencies
- Run the application

### Requirements

- `git` 
- `uv`

That’s it — you’re ready to develop.

---

## 2. Code style and formatting (required)

All code **must** be formatted and linted before committing.

Run the following commands from the project root:

```bash
uv run black src
uv run ruff check --fix
```

These tools enforce:
- Consistent formatting (Black)
- Import ordering, style, and correctness (Ruff)
- Docstring conventions (Google style)

Commits that do not pass these checks may be rejected during review.

---

## 3. Checking formatting without modifying files

To verify formatting **without changing code**, use:

```bash
uv run black --check src
uv run ruff check src
```

This is useful before pushing or when debugging CI failures.

---

## 4. Docstrings

All public modules, classes, and functions **must include docstrings**.

### Requirements

- Google docstring style
- One-line summary followed by a blank line (PEP 257 / Ruff D205)
- Document parameters and return values where applicable

### Example

```python
def example(x: int) -> int:
    """Return the square of a number.

    Args:
        x: Input value.

    Returns:
        The square of the input.
    """
    return x * x
```

---


## 9. Thank you

Your contributions help improve code quality and long-term maintainability.  
Thank you for taking the time to follow these guidelines!