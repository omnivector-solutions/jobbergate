# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is **jobbergate-cli**, a command-line interface for Jobbergate - a job templating and submission system that integrates with Slurm. The CLI allows users to create Job Scripts from templates and submit them to a Slurm cluster. It is part of a larger monorepo that includes `jobbergate-core`, `jobbergate-api`, and `jobbergate-agent`.

**Technology Stack:**

- Python 3.10+
- [Typer](https://typer.tiangolo.com/) for CLI building
- [Poetry](https://python-poetry.org/) for dependency management
- [Rich](https://rich.readthedocs.io/) for terminal output formatting
- [inquirer](https://python-inquirer.readthedocs.io/) for interactive prompts

## Development Commands

### Environment Setup

```bash
# create fresh virtual environment
uv venv -p 3.12 --clear

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Testing

```bash
# Run all tests
make test
# or: poetry run pytest

# Run specific test file
poetry run pytest tests/subapps/applications/test_tools.py -v

# Run a single test
poetry run pytest tests/subapps/applications/test_tools.py::test_name -v

# Run tests with coverage (configured to require 85% minimum)
poetry run pytest --cov=jobbergate_cli --cov-report=term
```

### Code Quality

```bash
# Run linting
make lint
# or: poetry run ruff check tests jobbergate_cli

# Run type checking
make mypy
# or: poetry run mypy jobbergate_cli --pretty

# Format code
make format
# or: poetry run ruff format tests jobbergate_cli

# Run all quality checks (test, lint, mypy, format)
make qa
```

### Running the CLI

```bash
# After installation, use the jobbergate command
poetry run jobbergate --help
poetry run jobbergate applications --help
poetry run jobbergate job-scripts --help
poetry run jobbergate job-submissions --help
```

### Cleanup

```bash
make clean  # Removes all generated files, caches, and build artifacts
```

## Architecture

### High-Level Structure

The CLI is organized into subapps under `jobbergate_cli/subapps/`:

- **applications/** - Manage Jobbergate applications (templates) and the questionnaire system that gathers user input to fill them up
- **job_scripts/** - Create and manage job scripts from applications
- **job_submissions/** - Submit and track jobs on Slurm clusters
- **clusters/** - Manage cluster configurations

### Key Architectural Components

**Main Entry Point (`main.py`):**

- Uses Typer to build the CLI app
- Registers subapps for applications, job-scripts, and job-submissions
- Handles authentication commands (login, logout, show-token)
- Implements custom error handling via decorators
- Supports compatibility mode for legacy command structure

**Context System (`context.py` + `config.py`):**

- `JobbergateContext` is injected via Typer's context system
- Provides access to the HTTP client, authentication handler, and output settings
- `Settings` class (pydantic-based) loads configuration from environment variables or `.env` files
- Cache directory at `~/.local/share/jobbergate3` by default

**Authentication (`auth.py`):**

- Uses OAuth2 device code flow via `jobbergate-core`
- Tokens cached in `JOBBERGATE_USER_TOKEN_DIR`
- Supports opening browser automatically or copying verification URLs to clipboard

**API Communication (`requests.py`):**

- `make_request()` function wraps httpx client calls
- Handles request/response serialization with Pydantic models
- Provides detailed error messages and suggested solutions based on status codes
- Supports saving responses to files

**Question System (`subapps/applications/questions.py`):**

- Abstract question types: `Text`, `Integer`, `List`, `Checkbox`, `Confirm`, `BooleanList`, `Directory`, `File`, `Const`
- Supports validation (integer bounds, custom validators)
- Questions can be conditionally skipped via `ignore` parameter

**Application Runtime (`subapps/applications/tools.py`):**

- `ApplicationRuntime` executes Jobbergate applications (Python modules) to gather answers
- Loads application source code dynamically using `exec()`
- Supports workflow methods (`mainflow`, custom workflows)
- Handles template file management and configuration

### Important Design Patterns

**Dynamic Application Loading:**
Applications are Python modules that define a `JobbergateApplication` class. These are loaded from:

1. Remote API (downloaded and cached)
2. Local filesystem (for development)

The application source is executed in an isolated namespace and instantiated to gather user answers through interactive questions.

**Dual Output Modes:**

- Standard mode: Rich-formatted tables and panels
- Raw mode (`--raw`): JSON output for scripting
- Full mode (`--full`): Show all fields (not just summary)

**Error Handling:**

- Custom `Abort` exception with rich terminal output
- Decorators (`handle_abort`, `handle_authentication_error`) wrap the main app
- All errors provide user-friendly messages + support contact info

### Dependencies on jobbergate-core

This package depends on `jobbergate-core` (via relative path in pyproject.toml). The core package provides:

- Authentication handlers
- SDK for API communication
- Shared schemas and models

When making changes, be aware that `jobbergate-core` is a sibling package in the monorepo.

## Environment Variables

Key environment variables (see `config.py` for full list):

- `ARMADA_API_BASE` - API base URL (default: <https://apis.vantagecompute.ai>)
- `JOBBERGATE_CACHE_DIR` - Cache directory (default: ~/.local/share/jobbergate3)
- `JOBBERGATE_DEBUG` - Enable debug logging
- `OIDC_DOMAIN` - OAuth domain
- `OIDC_CLIENT_ID` - OAuth client ID
- `DEFAULT_CLUSTER_NAME` - Default Slurm cluster
- `SBATCH_PATH` - Path to sbatch (enables "onsite mode" for local Slurm)

## Testing Practices

**Test Organization:**

- Tests mirror the source structure under `tests/`
- Fixtures in `conftest.py` files
- Heavy use of mocking for API calls (respx, pytest-mock)

**Important Test Settings (in pyproject.toml):**

- Tests run with random order (`pytest-random-order`)
- Coverage threshold: 85%
- Test environment variables are set via `pytest-env` plugin

**Mocking:**

- HTTP requests are mocked using `respx` or `pytest-responsemock`
- Authentication is typically mocked to avoid real OAuth flows
- File system operations may use temporary directories

## Common Development Tasks

**Adding a New Question Type:**

1. Define the class in `jobbergate_cli/subapps/applications/questions.py`
2. Add tests in `tests/subapps/applications/`

**Adding a New CLI Command:**

1. Add command function in appropriate subapp's `app.py`
2. Use Typer decorators for arguments/options
3. Access context via `ctx.obj` (type: `ContextProtocol`)
4. Use `make_request()` for API calls
5. Use `render_dict()`, `render_json()`, or `terminal_message()` for output

**Modifying API Schemas:**

1. Update Pydantic models in `schemas.py`
2. Ensure compatibility with `jobbergate-api`
3. Update corresponding request/response handling in subapp tools

## Important Notes

- This is a **monorepo subproject** - sibling packages are in `../jobbergate-core`, `../jobbergate-api`, etc.
- The CLI communicates with a remote API but can also work in "onsite mode" with local Slurm
- Application definitions (Python modules) are user-provided and executed dynamically - be mindful of security
- Always run `make qa` before committing to ensure code quality
- The project uses Poetry's stickywheel plugin to resolve relative dependencies at build time
