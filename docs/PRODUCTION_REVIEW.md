# Production Review Notes

## Changes made in this review

- Replaced the development-only settings defaults with environment-driven configuration, production secret-key enforcement, allowed-host and CSRF origin parsing, secure-cookie/HTTPS/HSTS controls, request-size limits, API throttling, and console logging.
- Added WhiteNoise static-file serving, Gunicorn, PostgreSQL driver support, and the `xlrd` dependency for legacy `.xls` imports.
- Added a Render blueprint and adjusted Docker to run as a non-root user with Gunicorn; removed automatic synthetic-data generation from production startup.
- Restricted faculty student access to the assigned department, limited analytics recalculation to the faculty member's department, restricted import access to administrators, and restricted intervention management to faculty/administrators with department checks.
- Fixed latest-snapshot aggregation so historic snapshots do not inflate dashboard/summary counts; recalculation updates the current day's snapshot instead of creating a new one on every repeat run.
- Added a separate placement-risk classification using the existing database field and exposed source-data availability in the explanation payload.
- Hardened CSV/Excel imports with extension/size validation, safer temporary-file cleanup, numeric/range/email/department validation, correct semester assignment, optional skills/engagement/feedback imports, and non-sensitive error responses.
- Added CSV formula-injection protection, fixed the broken sample-template download and placement dashboard link, and improved responsive/accessibility styles.
- Updated README, `.env.example`, `.gitignore`, CI configuration, and critical tests.

## Checks completed in the review environment

- Python syntax compilation: `python -m compileall -q apps config tests` — passed.
- YAML parsing for `render.yaml`, `.github/workflows/ci.yml`, and `docker-compose.yml` — passed.

## Checks still required before calling the live deployment production-ready

The review container did not have Django, Django REST Framework, `dj-database-url`, or WhiteNoise installed, and network access prevented installing them. Therefore the Django test suite, migrations check, Ruff lint, `collectstatic`, and `check --deploy` could not be executed here. Run the README quality commands in a Python 3.12 virtual environment after installing `requirements-dev.txt`; fix any environment-specific failures before merging/deploying. Then verify the real PostgreSQL connection, static assets, account roles, import/export flows, backups, and HTTPS on the target host.

The source ZIP did not include a `.git` directory or authenticated GitHub session, so this review cannot truthfully claim a commit or push to the configured remote. The reviewed source is provided as a separate ZIP for inspection and application to the repository.
