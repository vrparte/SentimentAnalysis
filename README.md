# Director Sentiment Analysis System

A production-grade system for monitoring public online sources for mentions of independent directors, detecting good or bad news, and generating readable reports for Managing Directors.

## Features

- **Daily Monitoring**: Automated daily scans at configurable times (default 07:30 IST)
- **Multi-Provider Support**: GDELT, Bing News Search, SerpAPI, RSS feeds
- **Smart Deduplication**: URL canonicalization, content hashing, and similarity detection
- **Entity Resolution**: Reduces false positives through context matching and confidence scoring
- **Classification**: Heuristic-based + optional LLM-powered sentiment/severity classification
- **Reports**: HTML and PDF daily digest reports
- **Alerts**: Immediate email alerts for high-severity items
- **Web Dashboard**: Admin and MD interfaces for managing directors and viewing reports
- **Review Queue**: Low-confidence items flagged for manual review

## Tech Stack

- Python 3.11+
- FastAPI for API server
- PostgreSQL for storage
- Redis + Celery (Celery Beat) for scheduling
- SQLAlchemy + Alembic for ORM/migrations
- Jinja2 for HTML templates
- WeasyPrint for PDF generation
- Trafilatura for article extraction
- Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd director-sentiment-analysis
   ```

2. **Create `.env` file from example:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and configure:**
   - `COMPANY_NAME`: Your company name
   - `BING_NEWS_KEY`: Bing News Search API key (optional)
   - `SERPAPI_KEY`: SerpAPI key (optional)
   - `SMTP_*`: Email configuration
   - `LLM_API_KEY`: OpenAI API key (optional, for LLM classification)

4. **Start services:**
   ```bash
   docker compose up --build
   ```

5. **Run migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

6. **Create admin user:**
   ```bash
   docker compose exec api python -m app.cli create-admin --username admin --password admin123 --email admin@example.com
   ```

7. **Seed sample directors:**
   ```bash
   docker compose exec api python -m app.seed directors.yaml
   ```

8. **Access the dashboard:**
   - Web UI: http://localhost:8000
   - API docs: http://localhost:8000/docs

## Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `COMPANY_NAME`: Company name for reports
- `RUN_TIME_HHMM`: Daily job time (default: 07:30)
- `TIMEZONE`: Timezone (default: Asia/Kolkata)
- `PROVIDERS_ENABLED`: Comma-separated list (e.g., `gdelt,bing`)
- `CONFIDENCE_THRESHOLD_ALERT`: Alert threshold (default: 0.75)
- `USE_LLM`: Enable LLM classification (default: false)

### Adding Directors

#### Via Web UI

1. Login as admin
2. Navigate to "Directors" page
3. Click "Add Director"
4. Fill in:
   - Full name (required)
   - Aliases (comma-separated)
   - Context terms (e.g., company name, "independent director")
   - Negative terms (to exclude false positives)
   - Enable/disable providers

#### Via Seed File

Create `directors.yaml`:

```yaml
directors:
  - full_name: "John Doe"
    aliases: ["J. Doe", "John D."]
    context_terms: ["ABC Corp", "independent director", "Mumbai"]
    negative_terms: ["actor", "footballer"]
    known_entities: ["XYZ Ltd", "Board Member"]
```

Then run:
```bash
docker compose exec api python -m app.seed directors.yaml
```

## Usage

### Manual Scan

Trigger a manual monitoring run:

```bash
docker compose exec api python -m app.cli run-scan
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/admin/trigger-scan \
  -H "Authorization: Bearer <token>"
```

### Viewing Reports

1. **Via Web UI:**
   - Login as MD or Admin
   - Navigate to "Reports" page
   - Click on any report to view HTML or download PDF

2. **Via API:**
   ```bash
   GET /api/reports
   GET /api/reports/{report_id}
   GET /api/reports/{report_id}/pdf
   ```

## Architecture

```
director-media-monitoring/
├── api/              # FastAPI application
├── worker/           # Celery workers
├── providers/        # Search provider implementations
├── core/             # Shared logic (dedupe, classification, etc.)
├── models/           # SQLAlchemy models
├── migrations/       # Alembic migrations
├── templates/        # Jinja2 templates
├── static/           # CSS, JS, images
├── tests/            # Test suite
└── docker-compose.yml
```

## Monitoring Job Flow

1. **Query Building**: For each director, build multiple search queries (recall + precision)
2. **Provider Search**: Query enabled providers (GDELT, Bing, etc.)
3. **Article Fetch**: Fetch and extract article content
4. **Entity Resolution**: Match articles to directors with confidence scoring
5. **Deduplication**: Remove duplicate articles
6. **Classification**: Determine sentiment, severity, category
7. **Storage**: Store mentions in database
8. **Report Generation**: Generate daily digest (HTML + PDF)
9. **Email**: Send alerts (high severity) and daily digest

## Data Retention

- Items are retained for 365 days by default
- Weekly cleanup task removes old data
- Reports are stored indefinitely (configurable)

## Deployment

### Production Deployment

1. **Set production environment variables**
2. **Use production-grade secrets management**
3. **Configure S3-compatible storage** 
4. **Set up monitoring** (Sentry, logs aggregation)
5. **Configure reverse proxy** (nginx) for API
6. **Set up SSL certificates**

### Docker Compose Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```


