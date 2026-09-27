# Fork of ugram project

# Ugram

 ## Lien cloudfront
- Frontend prod URL: `https://d32n58cbhk5j71.cloudfront.net`



## Architecture du projet [voir la section Architecture](#-architecture--livrable-0)

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://python.org)
[![Code Style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An Instagram-like web application built with **FastAPI** and **PostgreSQL**. Uses **[uv](https://docs.astral.sh/uv/)** for fast dependency management.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **Docker** (for the database)
- **uv** — Install it with:

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

- **Task** — A modern task runner (like Make). Install it with:

```bash
# Linux/macOS
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin

# Windows (PowerShell)
winget install Task.Task
```

### Installation

```bash
# Clone the repository
git clone https://github.com/GLO3112-classrooms/ugram-h2026-team-02.git
cd ugram-h2026-team-02

# Install dependencies (Backend + Frontend)
task install
```

### Running the Application

```bash
# Start backend and frontend concurrently
task start
```

Local development uses the Docker Postgres instance from `backend/docker-compose.yml`. RDS is not used by default in development.

```bash
# Optional: connect the backend to the real RDS instance instead of local Postgres
export RDS_DATABASE_URL="postgresql://<user>:<pass>@<rds-endpoint>:5432/ugram"
task be:start:rds
```

- Backend API: **http://localhost:8001**
- Frontend: **http://localhost:5173**

---

## 📖 API Documentation

Once the server is running, explore the API:

| Documentation | URL |
| :--- | :--- |
| **Swagger UI** | [http://localhost:8001/docs](http://localhost:8001/docs) |
| **ReDoc** | [http://localhost:8001/redoc](http://localhost:8001/redoc) |

---

## 🔥 Popular Keywords

The trends sidebar is based on actual image search activity and is reproducible from persisted search data.

- Event source:
  - `GET /images/hashtags/{hashtag}`
  - `GET /images/description/{keyword}`
- Time windows:
  - `all_time`
  - `today` (current UTC day on the backend server)
- Counting unit: searches
- Output shape: `GET /images/trending-keywords?limit=10&window=all_time`
- Processing:
  - search requests enqueue rows in `search_events`
  - a separate worker aggregates them into `search_trends_daily`
  - the trends endpoint reads from `search_trends_daily`
- The trends endpoint uses a short in-process TTL cache for repeated reads, but it does not process pending events on read.
- Image searches keep only in-flight request deduplication; repeated completed searches still make a fresh request and count as a fresh search.
- Signed S3 `view_url` values are cached in-process on the backend with TTL and bounded size so repeated reads can reuse the same URLs while they remain valid.

---

## 📂 Project Structure

```
ugram/
├── backend/                 # FastAPI backend
│   ├── src/                 # Source code
│   └── tests/               # Test suite
├── frontend/                # React frontend
│   ├── src/                 # React components
│   └── package.json         # Frontend dependencies
├── Taskfile.yml             # Task runner commands
└── README.md
```

---

## 🛠️ Development

### Available Commands

This project uses [Task](https://taskfile.dev/) as a task runner:

```bash
task              # List all commands
task install      # Install all dependencies (be + fe)
task start        # Start both backend and frontend
task check        # Run all checks (format, lint, test)
task lint         # Lint project (be + fe)
task format       # Format project (be + fe)
task test         # Run tests
```

### Infra Setup (Terraform + AWS)

#### Minimal deployment architecture
- Frontend: static Vite build uploaded to S3 and served through CloudFront.
- Frontend prod URL: `https://d32n58cbhk5j71.cloudfront.net`
- Backend: Docker image built from `backend/`, pushed to ECR, then deployed to Elastic Beanstalk.
- Backend public access: CloudFront sits in front of the Elastic Beanstalk environment for HTTPS.
- Terraform: provisions and updates the AWS resources for both frontend and backend.

**Quick glossary**
- `.tf` files: Infra code (HCL).
- `.tfvars`: Env values already filled for dev/prod.
- `backend/*.hcl`: Remote state location (already provisioned—don’t edit).
- `plan`: read‑only diff of what Terraform would change.
- `apply`: actually makes the changes shown in the plan.

#### 1) Install tools
- AWS CLI (`brew install awscli` or AWS pkg)
- Terraform ≥ 1.9.7 (`brew install terraform` or `tfenv install 1.9.7 && tfenv use 1.9.7`)
- Configure AWS credentials: run `aws configure` (or set `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_DEFAULT_REGION`). Never commit keys.

> Note: Remote state (S3 bucket + DynamoDB lock table) is already provisioned for you.

#### 2) Dev environment (day-to-day)
```bash
cd infra
export AWS_DEFAULT_REGION=us-east-2  # optional if not set by aws configure
task plan-dev              # safe preview
task apply-dev             # applies; confirm with 'yes'
```
This will create/update the dev S3 bucket (`ugram-images-dev-<account_id>`) with CORS for localhost.

#### 2.1) Which deploy task should you run?
- During development, keep using the local stack first with `task start`, and only deploy once the change works locally.
- Infra changes only (`infra/*.tf`, `dev.tfvars`, permissions, buckets, networking): `task apply-dev`
- Backend changes only (`backend/`): `task deploy-backend-dev`
- Frontend changes only (`frontend/`): `task deploy-frontend-dev`
- Full dev rollout (infra + backend + frontend): `task deploy-dev`
- Frontend build against the deployed dev backend without uploading: `task fe:build-dev`

Typical examples:
- You changed FastAPI routes, backend config, or Docker setup: run `task deploy-backend-dev`
- You changed React pages/components only: run `task deploy-frontend-dev`
- You changed both sides, or changed infra/backend URL assumptions: run `task deploy-dev`

#### 3) Deployment automation
- Dev deploys automatically when a PR is merged into `main`. The GitHub Actions workflow runs `task deploy-dev`.
- Prod Terraform is planned automatically when a PR is merged into `main`.
- Prod deploys from a published GitHub Release. Release creation is manual; the GitHub Actions workflow handles the prod rollout.

#### 4) Prod (only if you’re allowed)
- Use prod credentials (`aws configure` with prod keys, or set prod env vars).
- Ensure `prod.tfvars` has the real frontend origin.
```bash
cd infra
task plan-prod
task apply-prod
```
CI runs `plan` on PRs. Prod rollout is gated by a manual GitHub Release publication and should not be run locally as a full deploy task.

#### 5) Small tweaks
- Need a new allowed origin? Edit `allowed_origins` in `dev.tfvars` or `prod.tfvars`, then rerun `plan`/`apply`.
- Reformat files: `task fmt-dev`.
- Cleaning dev entirely: `terraform destroy -var-file=dev.tfvars` (rare; dev only).

### Observability Strategy

Our observability strategy is intentionally simple: detect platform issues quickly, identify whether the failure is frontend, backend, or database related, and then pivot to the right tool for diagnosis.

- **Metrics and health**: AWS CloudWatch is the primary source for infrastructure visibility on deployed environments. We monitor Elastic Beanstalk health, backend EC2 status and CPU, RDS CPU/storage/memory/latency, and CloudFront error rate and origin latency.
- **Logs**: Backend application logs and Elastic Beanstalk health logs are streamed to CloudWatch Logs. Saved CloudWatch queries help inspect recent backend errors and health events without searching raw logs manually.
- **Application errors**: Frontend and backend both send errors to Sentry when DSNs are configured. Sentry is used for stack traces, release correlation, and request-level debugging, with sensitive fields scrubbed before events are sent.
- **Alerting**: CloudWatch alarms publish to SNS and can be forwarded to Slack when monitoring is enabled for the environment, so infrastructure regressions are surfaced without waiting for manual checks.

In practice, the workflow is: start with the CloudWatch dashboard to confirm service health, check CloudWatch Logs for backend/runtime issues, and use Sentry when the problem is application-level or tied to a specific release.

### Frontend Type Generation

The frontend uses **auto-generated TypeScript types** from the backend's OpenAPI schema to ensure type safety:

```bash
# Generate types from backend API (backend must be running)
task fe:generate-types
```

This generates `src/types/api-schema.ts` with all API types. See [`frontend/TYPE_GENERATION.md`](frontend/TYPE_GENERATION.md) for details.


### Managing Dependencies

```bash
# Add a production dependency
cd backend
uv add <package>

# Add a development dependency (from root)
uv add --dev <package>
```

---

## 🤝 Contributing

1. Copy `.env.example` to `.env` and configure your environment variables
2. Install pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```
3. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages:
   - `feat: add user profile page`
   - `fix: resolve login redirect issue`
   - `docs: update README`

---

## 🔐 Environment Variables

### Development

Copy `.env.example` to `.env` and configure the following variables:

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | JWT secret key for token signing | - | Yes |
| `ALGORITHM` | JWT hashing algorithm | `HS256` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time in minutes | `30` | Yes |
| `FRONTEND_URL` | Allowed frontend origin(s), comma-separated if needed | `http://localhost:5173` | Yes |
| `DATABASE_MODE` | Which database target to use: `local`, `rds`, or `custom` | `local` | Yes |
| `LOCAL_DATABASE_URL` | Local PostgreSQL connection string used in dev | `postgresql://user:pass@localhost:5433/ugram` | Yes when `DATABASE_MODE=local` |
| `RDS_DATABASE_URL` | Real AWS RDS connection string | - | Yes when `DATABASE_MODE=rds` |
| `DATABASE_URL` | Custom override connection string | - | Yes when `DATABASE_MODE=custom` |
| `MAX_UPLOAD_SIZE_BYTES` | Maximum accepted upload size in bytes | `10485760` | No |

Default development flow:

```bash
DATABASE_MODE=local
LOCAL_DATABASE_URL=postgresql://user:pass@localhost:5433/ugram
```

To intentionally run against RDS:

```bash
DATABASE_MODE=rds
RDS_DATABASE_URL=postgresql://<user>:<pass>@<rds-endpoint>:5432/ugram
```

**Generate a secure SECRET_KEY:**
```bash
openssl rand -hex 32
```


## 📄 License

This project is developed as part of a university course.

---

## 🏗️ Architecture — Livrable 0

Cette section décrit l'architecture technique du projet Ugram et les technologies choisies par l'équipe.

### Frontend

| Technologie | Description |
| :--- | :--- |
| **React** | Librairie UI principale |
| **TypeScript** | Typage statique pour JavaScript |
| **Vite** | Build tool et dev server rapide |
| **Tailwind CSS** | Framework CSS utilitaire |

### Backend

| Technologie | Description |
| :--- | :--- |
| **Python** | Langage de programmation |
| **FastAPI** | Framework REST moderne et performant |
| **SQLAlchemy** | ORM pour la gestion de la base de données |
| **Boto3** | SDK AWS pour Python |
| **PyJWT** | Gestion des tokens JWT |

### Base de Données

| Service | Usage |
| :--- | :--- |
| **PostgreSQL (local dev) / RDS (prod)** | Base de données relationnelle principale |
| **DynamoDB** | Base de données NoSQL (sessions, cache) |
