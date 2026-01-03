# Code Quality - Ruff & Pre-commit

This project uses [Ruff](https://docs.astral.sh/ruff/) for Python linting and formatting, with pre-commit hooks to automatically check code quality.

## Installation

Development dependencies are already in `pyproject.toml`. Install them:

```bash
uv sync --all-extras
```

## Pre-commit Hooks

Pre-commit hooks automatically run when you commit code.

### Setup (one-time)

```bash
uv run pre-commit install
```

### Usage

Hooks run automatically on `git commit`. To run them manually:

```bash
# Run on all files
uv run pre-commit run --all-files

# Run on staged files only
uv run pre-commit run
```

### Skip Hooks (not recommended)

If you need to bypass hooks temporarily:

```bash
git commit --no-verify -m "Your message"
```

## Ruff

Ruff is a fast Python linter and formatter written in Rust.

### Check Linting

```bash
uv run ruff check .
```

### Auto-fix Linting Issues

```bash
uv run ruff check --fix .
```

### Check Formatting

```bash
uv run ruff format --check .
```

### Auto-format Code

```bash
uv run ruff format .
```

### Both Lint and Format

```bash
# Using provided scripts
./scripts/lint.sh   # Check only
./scripts/format.sh # Auto-fix

# Or manually
uv run ruff check --fix . && uv run ruff format .
```

## Configuration

Ruff is configured in `pyproject.toml`:

- **Line length**: 100 characters
- **Python version**: 3.10+
- **Enabled rules**:
  - `E` - pycodestyle errors
  - `W` - pycodestyle warnings
  - `F` - pyflakes
  - `I` - isort (import sorting)
  - `B` - flake8-bugbear
  - `C4` - flake8-comprehensions
  - `UP` - pyupgrade
  - `ARG` - flake8-unused-arguments
  - `SIM` - flake8-simplify

- **Formatting**:
  - Double quotes
  - Space indentation
  - Magic trailing commas preserved

## CI/CD Integration

For CI/CD pipelines, run:

```bash
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
```

## Editor Integration

### VS Code

Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=astral-sh.ruff):

```bash
code --install-extension astral-sh.ruff
```

Configure in `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "astral-sh.ruff",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "astral-sh.ruff"
  }
}
```

### PyCharm

Ruff support is built into PyCharm 2023.2+. Enable in:
Settings → Tools → External Tools → Ruff

### Vim/Neovim

Using [nvim-lspconfig](https://github.com/neovim/nvim-lspconfig):

```lua
require('lspconfig').ruff_lsp.setup{}
```

### Emacs

Using [lsp-mode](https://github.com/emacs-lsp/lsp-mode):

```elisp
(use-package lsp-mode
  :config
  (lsp-register-custom-settings
   '(("ruff-lsp.ruffExecutable" "uv run ruff"))))
```

## Troubleshooting

### Pre-commit not found

Use `uv run pre-commit` instead of just `pre-commit`:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

### Ruff not found

Use `uv run ruff`:

```bash
uv run ruff check .
uv run ruff format .
```

### Hook fails but you want to commit anyway

```bash
git commit --no-verify -m "WIP: work in progress"
```

Then fix issues later and amend:

```bash
./scripts/format.sh
git add .
git commit --amend --no-verify
```

## Benefits

- **Fast**: Ruff is 10-100x faster than traditional linters
- **Comprehensive**: Replaces multiple tools (flake8, isort, black, etc.)
- **Auto-fix**: Most issues can be fixed automatically
- **Consistent**: Enforces consistent code style across the project
- **Pre-commit**: Catches issues before they reach the repository
