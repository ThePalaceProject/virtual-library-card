# Project: Virtual Library Card

## Project Description

Virtual Library Card is a Django web application that allows library patrons to sign up for digital
library cards online. It integrates with library systems to issue cards, verify patron eligibility
by location, and expose a REST API compatible with Overdrive/Palace patron verification flows.

## Tech Stack

**Core Framework:**

- Python 3.12+
- Django (< 7.0)
- Django REST Framework

**Data & Storage:**
- PostgreSQL (psycopg2-binary)
- AWS S3 / MinIO (local dev) via django-storages

**Development & Testing:**
- pytest, pytest-django, tox
- Poetry (package management)
- pre-commit (linting/formatting)
- mypy with django-stubs (type checking)

## Code Conventions

- Pre-commit for linting/formatting code (black, isort, autoflake, pyupgrade)
- Poetry for package management
- `pyproject.toml` for project configuration
- Type hint all code with mypy validation using the `mypy_django_plugin`
- Use f-strings for string formatting
- Imports at the top of files; add a comment if a local import is necessary
- Use immutable data structures for global and class-level constants
- isort profile is `"black"` with `combine_as_imports = true`

## Project Structure

- `/virtual_library_card` - Django project configuration package
  - `/settings/base.py` - Base Django settings
  - `/settings/dev.py` - Development overrides and environment variable wiring
  - `urls.py` - Top-level URL routing (API + website)
  - `card_number.py`, `geoloc.py`, `storage.py`, `tokens.py` etc. - Shared utilities
- `/virtuallibrarycard` - Main Django application
  - `models.py` - Database models (`CustomUser`, `Library`, `LibraryCard`, `LibraryPlace`, `Place`, etc.)
  - `admin.py` - Django admin customization
  - `/forms` - Form definitions
  - `/views` - View handlers split by concern (`views_api.py`, `views_library_card.py`, etc.)
  - `/business_rules` - Business logic layer
  - `/widgets` - Custom form widgets
  - `/management` - Django management commands
  - `/migrations` - Django ORM migrations
  - `/templates` - App-level Django/Jinja2 templates
- `/tests` - Test suite
  - `base.py` - `BaseUnitTest` and `BaseAdminUnitTest` base classes; `TestData` factory helpers
  - `/views` - View tests
  - `/admin` - Admin UI tests
  - `/business_rules` - Business logic tests
  - `/files` - File handling tests
  - `/misc` - Miscellaneous tests
- `/templates` - Project-level Django/Jinja2 templates
- `/static` - Static assets (CSS, JS)
- `/locale` - Translation files
- `/docker` - Docker configuration
- `/ci` - CI utilities (MinIO setup scripts)

## Architecture Overview

- **Website layer** — Django views and Jinja2 templates for the patron-facing card signup flow
- **API layer** — DRF views under `/api/` and `/PATRONAPI/` (Overdrive-compatible) for patron
  verification and PIN testing
- **Business rules layer** — `virtuallibrarycard/business_rules/` contains domain logic decoupled
  from views
- **Data layer** — Django ORM models in `models.py`; migrations under `virtuallibrarycard/migrations/`
- Both the website and API can be independently toggled via `HAS_WEBSITE` / `HAS_API` settings flags

## Development Workflow

### Running the Dev Server

```bash
python manage.py runserver --settings=virtual_library_card.settings.dev
```

Or with Docker Compose (includes PostgreSQL + MinIO, accessible at http://localhost:8000):

```bash
docker-compose up -d
# Default credentials: test@test.com / test
```

### Running Tests

```bash
# Run all tests
tox -e py312-docker -- --no-cov

# Run a specific test file
tox -e py312-docker -- --no-cov tests/path/to/test_file.py

# Run with coverage (default)
tox -e py312-docker -- tests/path/to/test_file.py

# Run directly with pytest (requires local DB)
pytest tests
```

### Type Checking

```bash
mypy
```

### Database Migrations

```bash
# Create a new empty migration
python manage.py makemigrations --settings=virtual_library_card.settings.dev

# Apply migrations
python manage.py migrate --settings=virtual_library_card.settings.dev
```

After creating a migration, review the generated file and remove auto-generated comments. Explain
any non-obvious changes in a comment.

## Contributing Guidelines

- All new features require corresponding tests
- Maintain test coverage above existing levels
- Follow existing naming conventions and patterns
- Branches should be created with the following prefixes:
  - `feature/` for new features
    - When creating a PR for a feature branch, add the `feature` label to the PR
  - `bugfix/` for bug fixes
    - When creating a PR for a bugfix branch, add the `bug` label to the PR
  - `chore/` for cleanup, refactors, or non-functional changes
    - Do not add any labels to PRs for chore branches
- Any PR that contains a database migration should have the `DB migration` label added to it
- Any PR that makes breaking changes to the public API should have the `incompatible changes` label
- Use clear, descriptive commit messages
- When creating a PR always use the template at `.github/pull_request_template.md`
  - Check the correct boxes in the `Checklist` section
- If given a Jira ticket number (e.g. PP-123), include it in the PR title
  - Example: `Add email verification step to card signup (PP-123)`

## Instructions for Claude

**Type Annotations:**
- Always add comprehensive type hints for new functions
- Use specific types rather than `Any` when possible
- Import types from `typing` or `collections.abc` as needed
  - Example: `def issue_card(library: Library, user: CustomUser) -> LibraryCard:`
- Use `django-stubs` QuerySet generics where applicable (e.g. `QuerySet[Library]`)
- In the rare case a type ignore is needed, only ignore specific codes and add a comment explaining why
  - Example: `# type: ignore[assignment]  # detailed explanation`

**Error Handling:**
- Follow existing error handling patterns in the codebase
- Log errors at appropriate severity levels using Django's logging framework
- Include context in error messages

**Performance:**
- Avoid N+1 query problems — use `select_related` / `prefetch_related` as needed
- Consider caching for expensive or repeated operations

**Testing Requirements:**
- Write tests for all new functions and views using `BaseUnitTest` (or `BaseAdminUnitTest` for admin)
- Use `TestData` helpers (`create_library`, `create_user`, `create_library_card`) for test fixtures
- Include integration tests for API endpoints via DRF's test client
- Mock external service calls (geolocation, S3, email)
- Test error conditions and edge cases
- Name test classes after the class or module under test (e.g. `TestLibraryCard`, `TestApiViews`),
  not after behaviors or scenarios. Add test methods to existing classes rather than creating new
  classes for specific scenarios.

**Documentation:**
- Add docstrings to public functions and class methods
- Update module-level docstrings if functionality changes
- Private/internal helpers warrant a short one-line comment if the intent is non-obvious

**Pre-commit Hooks:**
- Pre-commit hooks run automatically on commit (black, isort, autoflake, pyupgrade, mypy, etc.)
- If a hook fails and makes file changes, re-stage the modified files and commit again without
  amending the commit message

### Ongoing Updates

- Update CLAUDE.md with any new information about the codebase, architecture, or development practices
- Whenever making major changes to the project, update CLAUDE.md accordingly
- When interrupted or given new information, update CLAUDE.md so the guidance is available in future conversations
