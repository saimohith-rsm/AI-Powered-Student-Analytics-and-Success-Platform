# Smart Campus Analytics

An enterprise-ready, explainable AI-powered student success analytics and intervention platform built with Django 5.2+. The platform unifies academic results, attendance tracking, LMS activity, placement readiness, skills assessments, and extracurricular engagement to compute explainable success scores, detect at-risk students, dispatch automated email advisories, and track closed-loop counseling workflows.

---

## Key Features

- **Multi-Indicator AI Risk Engine**: Computes explainable, composite student success scores (0–100) combining CGPA (30%), attendance (25%), LMS engagement (15%), placement readiness (15%), and backlog penalties (-10 points per active backlog).
- **Automated Risk Email Alerts**: Proactively dispatches official email advisories to at-risk students (`CRITICAL` and `HIGH` risk tiers) and faculty mentors with customized risk factor breakdowns, remedial tutoring schedules, and counselor notes.
- **Batch CSV & Excel Risk Checker**: Pre-import file inspection tool allowing administrators and faculty to upload student datasets for instant risk evaluation, explainable risk flag inspection, and optional direct database import.
- **Closed-Loop Counseling & Interventions**: Tracks remedial tutoring, attendance counseling, and career mentorship with follow-up milestones, counselor assignments, and resolution notes.
- **Role-Based Workspaces & Governance**: Granular server-side role isolation across **Administrators**, **Faculty Counselors**, **Placement Officers**, and **Students** with FERPA-aligned data isolation.
- **REST APIs & Request Throttling**: Authenticated REST endpoints with rate limiting (`60/hour` anonymous, `600/hour` authenticated) for institutional integrations.
- **Production-Ready Architecture**: Configured with WhiteNoise compressed manifest static storage, environment-driven security headers (HSTS, SSL redirect, secure cookies), Docker containerization, and PostgreSQL readiness via `dj-database-url`.

---

## System Requirements

- **Python**: 3.12+ (matches CI and Docker runtime).
- **Database**: PostgreSQL 15+ (recommended for production); SQLite 3.35+ (supported for local development).
- **Environment Tools**: `pip`, `virtualenv` or `venv`, and `git`.

---

## Local Development Setup

### 1. Clone & Set Up Virtual Environment

**Windows PowerShell:**
```powershell
cd smart-campus-analytics-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cd smart-campus-analytics-main
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
```

### 2. Configure Environment Variables
Open `.env` and set a strong `SECRET_KEY`. For local development, the defaults in `.env.example` are pre-configured for SQLite and console email output.

### 3. Initialize Database & Run Server

```bash
# Apply database migrations
python manage.py migrate

# (Optional) Seed realistic demonstration data for development
python manage.py generate_sample_data --count 40
python manage.py run_analytics_engine

# Start the local development server
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.

---

## Environment Variables Reference

| Variable | Type | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | string | *Required in prod* | Cryptographic signing key for sessions, CSRF, and tokens. |
| `DEBUG` | boolean | `False` | Enables debug mode. **Must be `False` in production.** |
| `ALLOWED_HOSTS` | list | `localhost,127.0.0.1` | Comma-separated hostnames allowed to serve the application. |
| `CSRF_TRUSTED_ORIGINS` | list | `""` | Comma-separated HTTPS scheme-qualified origins for CSRF protection. |
| `DATABASE_URL` | string | `sqlite:///db.sqlite3` | Database connection URL (`postgres://user:pass@host:5432/db` in prod). |
| `DB_CONN_MAX_AGE` | integer | `60` | Persistent database connection lifetime in seconds. |
| `DB_SSL_REQUIRE` | boolean | `False` | Enforces SSL connection to the database. |
| `TIME_ZONE` | string | `Asia/Kolkata` | Application timezone. |
| `DJANGO_EMAIL_BACKEND` | string | `...console.EmailBackend` | Email backend (`...smtp.EmailBackend` for production SMTP). |
| `DEFAULT_FROM_EMAIL` | string | `alerts@smartcampus.edu` | Sender email address displayed on alert advisories. |
| `EMAIL_HOST` | string | `localhost` | SMTP server hostname. |
| `EMAIL_PORT` | integer | `587` | SMTP server port. |
| `EMAIL_HOST_USER` | string | `""` | SMTP authentication username. |
| `EMAIL_HOST_PASSWORD` | string | `""` | SMTP authentication password/app token. |
| `EMAIL_USE_TLS` | boolean | `True` | Enables TLS for secure SMTP delivery. |
| `SECURE_SSL_REDIRECT` | boolean | `True` (when `!DEBUG`) | Forces HTTPS redirection. |
| `SESSION_COOKIE_SECURE` | boolean | `True` (when `!DEBUG`) | Restricts session cookies to HTTPS connections. |
| `CSRF_COOKIE_SECURE` | boolean | `True` (when `!DEBUG`) | Restricts CSRF cookies to HTTPS connections. |
| `SECURE_HSTS_SECONDS` | integer | `31536000` | HTTP Strict Transport Security duration in seconds. |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | boolean | `True` (when `!DEBUG`) | Applies HSTS policy to all subdomains. |
| `SECURE_HSTS_PRELOAD` | boolean | `True` (when `!DEBUG`) | Enables browser HSTS preloading. |
| `USE_X_FORWARDED_HOST` | boolean | `True` (when `!DEBUG`) | Trusts reverse-proxy host headers (e.g. Render, NGINX). |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | integer | `5242880` (5 MB) | Maximum memory limit for file uploads. |
| `API_ANON_RATE` | string | `60/hour` | Rate limit for unauthenticated REST API requests. |
| `API_USER_RATE` | string | `600/hour` | Rate limit for authenticated REST API requests. |

---

## CSV Student Dataset Import & Risk Verification

### A. Web Interface
1. Sign in with an Administrator or Faculty account.
2. Navigate to **Risk Monitoring &rarr; Check CSV for Student Risk** (`/risk-checker/`).
3. Select any standard `.csv`, `.xlsx`, or `.xls` file:
   - **Check Risk (Preview Only)**: Evaluates students in-memory and displays an interactive diagnostic table without persisting to the database.
   - **Check & Import to DB**: Validates rows, saves student profiles and academic records, and computes initial success snapshots.
4. Download a pre-formatted template via **Download Sample CSV** (`/risk-checker/template/`).

### B. Command-Line Import
```bash
python manage.py import_student_data sample_student_import_template.csv
```

---

## Automated Risk Email Alerts

The platform includes a built-in advisory dispatch system:
- **Individual Alert**: Under `/risk-monitoring/`, click **Send Alert** next to any at-risk student to preview their triggering factors and send a personalized email advisory with an optional counselor guidance note.
- **Batch Alerts**: Click **Send Batch Alert Emails** in the At-Risk Workspace header to notify all students in the current view simultaneously.
- **Audit Trail**: Every alert automatically creates an in-progress [InterventionRecord](file:///s:/smart-campus-analytics-main/apps/interventions/models.py) to track counseling progress.

---

## Testing & Quality Assurance

Run the automated test suite and code quality checks:

```bash
# 1. Django system checks
python manage.py check

# 2. Check for missing database migrations
python manage.py makemigrations --check --dry-run

# 3. Run all test suites
python manage.py test

# 4. Lint with Ruff
ruff check .

# 5. Verify byte-compilation
python -m compileall -q apps config tests

# 6. Verify static assets collection
python manage.py collectstatic --noinput

# 7. Production security deployment check
python manage.py check --deploy
```

---

## Production Deployment

### Option 1: Docker Deployment
Build and run using the optimized multi-stage Docker container:

```bash
# Build and run with Docker Compose
docker compose up --build -d
```

The Dockerfile is configured with:
- Non-root system user (`app:app`) for enhanced container security.
- Automatic migration execution on container startup.
- Gunicorn WSGI server with configurable worker concurrency (`WEB_CONCURRENCY`).
- Pre-compiled WhiteNoise compressed manifest static files.

### Option 2: Render Blueprint Deployment
The repository includes a ready-to-deploy [render.yaml](file:///s:/smart-campus-analytics-main/render.yaml) blueprint:
1. Connect this repository to your [Render](https://render.com) dashboard.
2. Create a new **Blueprint** service.
3. Render automatically provisions the Python web service and managed PostgreSQL database.
4. Set `ALLOWED_HOSTS` to your production domain and confirm `DEBUG=False`.

---

## Project Structure

```
smart-campus-analytics-main/
├── .github/workflows/ci.yml       # Automated CI pipeline (lint, tests, security checks)
├── apps/
│   ├── accounts/                 # User model, roles (Admin, Faculty, Student), auth
│   ├── academics/                # Semester results, assessments, subjects
│   ├── analytics/                # Risk engine, scoring, snapshots, alert service, CSV checker
│   ├── attendance/               # Attendance logs and session records
│   ├── engagement/               # Extracurricular activities and leadership logs
│   ├── feedback/                 # Student and faculty sentiment feedback
│   ├── interventions/            # Closed-loop counseling records and status tracking
│   ├── lms/                      # LMS activity logs and assignment metrics
│   ├── placements/               # Placement assessments, readiness, applications
│   ├── skills/                   # Technical and soft skill assessments
│   └── students/                 # Student profiles, departments, import service
├── config/                       # Settings, root URLs, WSGI, ASGI
├── static/                       # CSS, JS, branding assets, sample datasets
├── templates/                    # Jinja/Django templates (dashboards, modals, errors)
├── tests/                        # Unit, integration, and security test suites
├── Dockerfile                    # Production container specification
├── docker-compose.yml            # Local container orchestration
├── render.yaml                   # Infrastructure-as-code deployment blueprint
├── requirements.txt              # Production Python dependencies
├── requirements-dev.txt          # Development & test dependencies
└── manage.py                     # CLI management script
```

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
