# Step-by-Step Guide: Running and Testing the Project

This guide walks you through setting up, running, and testing the Director Media Monitoring System.

## Prerequisites

Before starting, ensure you have:
- **Docker** and **Docker Compose** installed
- At least 4GB of free disk space
- An internet connection (for downloading images and fetching articles)

---

## Step 1: Initial Setup

### 1.1 Create Environment File

First, create a `.env` file in the project root. You can create a minimal version to get started:

```bash
# Create .env file
cat > .env << EOF
# Company Settings
COMPANY_NAME=Test Company
TIMEZONE=Asia/Kolkata
RUN_TIME_HHMM=07:30

# Database (uses defaults from docker-compose.yml)
DATABASE_URL=postgresql://director_monitor:director_monitor@postgres:5432/director_monitor

# Redis
REDIS_URL=redis://redis:6379/0

# Providers (GDELT works without API key)
PROVIDERS_ENABLED=gdelt

# Optional: Add these if you have API keys
BING_NEWS_KEY=
SERPAPI_KEY=

# Classification (heuristic is default, LLM optional)
USE_LLM=false
LLM_API_KEY=

# Email (optional for testing)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_USE_TLS=true
FROM_EMAIL=noreply@example.com
RECIPIENTS_MD=
RECIPIENTS_ADMIN=

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=change-this-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Storage
STORAGE_TYPE=local
LOCAL_STORAGE_DIR=/app/storage

# Logging
LOG_LEVEL=INFO
EOF
```

> **Note**: For production, generate a secure SECRET_KEY using: `openssl rand -hex 32`

---

## Step 2: Start the Services

### 2.1 Build and Start Docker Containers

```bash
# Build images and start all services
docker compose up --build -d

# Check that all services are running
docker compose ps
```

You should see 5 services:
- `postgres` - Database
- `redis` - Message broker
- `api` - FastAPI web server
- `worker` - Celery worker
- `beat` - Celery beat scheduler

### 2.2 Verify Services are Healthy

```bash
# Check API health endpoint
curl http://localhost:8000/health

# Should return: {"status":"ok"}

# Check logs to ensure services started correctly
docker compose logs api
docker compose logs worker
docker compose logs beat
```

If you see errors, wait a few seconds and check again (services may need time to start).

---

## Step 3: Database Setup

### 3.1 Run Migrations

```bash
# Run database migrations to create tables
docker compose exec api alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, Initial schema
```

### 3.2 Verify Database Tables

```bash
# Connect to PostgreSQL and list tables
docker compose exec postgres psql -U director_monitor -d director_monitor -c "\dt"
```

You should see tables: `directors`, `articles`, `extracted_contents`, `mentions`, `reports`, `users`, `settings`, `alembic_version`

---

## Step 4: Create Admin User

### 4.1 Create Admin Account

```bash
docker compose exec api python -m app.cli create-admin \
  --username admin \
  --password admin123 \
  --email admin@example.com
```

You should see: `User admin created successfully`

### 4.2 (Optional) Create MD User

```bash
docker compose exec api python -m app.cli create-admin \
  --username md_user \
  --password md123 \
  --email md@example.com \
  --role md
```

---

## Step 5: Add Test Directors

### 5.1 Create Directors YAML File

Create a `directors.yaml` file in the project root:

```yaml
directors:
  - full_name: "Ratan Tata"
    aliases: ["R. Tata", "Ratan N. Tata"]
    context_terms: ["Tata Group", "Tata Sons", "chairman", "Mumbai"]
    negative_terms: ["cricket", "sports"]
    known_entities: ["Tata Steel", "TCS", "Tata Motors"]
    provider_gdelt_enabled: true
    provider_bing_enabled: false
    provider_serpapi_enabled: false
    is_active: true

  - full_name: "Nandan Nilekani"
    aliases: ["N. Nilekani"]
    context_terms: ["Infosys", "UIDAI", "Aadhaar", "Bangalore"]
    negative_terms: []
    known_entities: ["Infosys Technologies", "Nilekani"]
    provider_gdelt_enabled: true
    provider_bing_enabled: false
    is_active: true
```

### 5.2 Seed Directors

```bash
# Seed directors from YAML file
docker compose exec api python -m app.seed directors.yaml
```

You should see: `Seeded 2 directors`

### 5.3 Verify Directors

```bash
# List directors via API (you'll need to login first, see next step)
# Or check database directly:
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT id, full_name FROM directors;"
```

---

## Step 6: Access the Web Dashboard

### 6.1 Login to Dashboard

1. Open your browser and go to: **http://localhost:8000**
2. You'll be redirected to the login page
3. Login with:
   - Username: `admin`
   - Password: `admin123`

### 6.2 Explore the Dashboard

- **Directors**: View/manage directors
- **Items**: View mentions/articles
- **Reports**: View generated reports
- **Review Queue**: Review low-confidence items

### 6.3 Check API Documentation

Visit: **http://localhost:8000/docs** for interactive API documentation (Swagger UI)

---

## Step 7: Run a Manual Scan (Testing)

### 7.1 Trigger Monitoring Scan

```bash
# Trigger a manual monitoring scan
docker compose exec api python -m app.cli run-scan
```

You should see: `Scan queued. Check worker logs for progress.`

### 7.2 Monitor Worker Logs

```bash
# Watch worker logs in real-time
docker compose logs -f worker
```

You should see:
- Processing directors
- Searching providers (GDELT)
- Finding articles
- Processing articles
- Creating mentions

**Note**: The scan may take 2-5 minutes depending on:
- Number of directors
- Number of articles found
- Provider response times

### 7.3 Check Results

```bash
# Check how many articles were found
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT COUNT(*) FROM articles;"

# Check how many mentions were created
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT COUNT(*) FROM mentions;"

# View recent mentions
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT m.id, d.full_name, m.confidence, m.severity, a.title FROM mentions m JOIN directors d ON m.director_id = d.id JOIN articles a ON m.article_id = a.id ORDER BY m.created_at DESC LIMIT 5;"
```

### 7.4 View Results in Web UI

1. Go to **http://localhost:8000/items**
2. You should see mentions/articles with:
   - Director name
   - Article title
   - Confidence score
   - Sentiment (positive/negative/neutral)
   - Severity (low/medium/high)

---

## Step 8: Generate a Report

### 8.1 Generate Daily Report

```bash
# Generate report for today
docker compose exec api python -m app.cli generate-report

# Or generate for a specific date
docker compose exec api python -m app.cli generate-report --date 2024-01-15
```

You should see: `Report generation queued. Check worker logs for progress.`

### 8.2 Check Report Generation

```bash
# Watch logs
docker compose logs -f worker | grep -i report

# List generated reports
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT id, report_date, html_path FROM reports ORDER BY report_date DESC LIMIT 5;"
```

### 8.3 View Report in Web UI

1. Go to **http://localhost:8000/reports**
2. Click on a report to view HTML version
3. Click "Download PDF" to download PDF version

### 8.4 View Report Files

```bash
# List report files (inside container)
docker compose exec api ls -lh /app/storage/

# Or if you mounted storage volume, check ./storage/ directory
ls -lh storage/
```

---

## Step 9: Testing Different Components

### 9.1 Test via API

#### Get Access Token

```bash
# Login and get token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

#### List Directors

```bash
curl -X GET "http://localhost:8000/api/directors/" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

#### Create a Director

```bash
curl -X POST "http://localhost:8000/api/directors/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Director",
    "aliases": ["T. Director"],
    "context_terms": ["Test Corp"],
    "negative_terms": [],
    "provider_gdelt_enabled": true,
    "is_active": true
  }' | python -m json.tool
```

#### List Mentions/Items

```bash
# List all mentions
curl -X GET "http://localhost:8000/api/items/" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Filter by severity
curl -X GET "http://localhost:8000/api/items/?severity=high" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Filter by director
curl -X GET "http://localhost:8000/api/items/?director_id=1" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

#### Trigger Scan via API

```bash
curl -X POST "http://localhost:8000/api/admin/trigger-scan" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

## Step 10: Run Unit Tests

### 10.1 Run All Tests

```bash
# Run all tests
docker compose exec api pytest tests/ -v

# Run with coverage
docker compose exec api pytest tests/ -v --cov=app --cov-report=term-missing
```

### 10.2 Run Specific Test Files

```bash
# Test classification
docker compose exec api pytest tests/test_classification.py -v

# Test deduplication
docker compose exec api pytest tests/test_deduplication.py -v

# Test entity resolution
docker compose exec api pytest tests/test_entity_resolution.py -v

# Test URL utils
docker compose exec api pytest tests/test_url_utils.py -v
```

### 10.3 Expected Test Results

You should see tests passing. Example output:
```
tests/test_classification.py::test_classify_heuristic_negative_high PASSED
tests/test_classification.py::test_classify_heuristic_positive PASSED
tests/test_deduplication.py::test_deduplicate_articles PASSED
...
```

---

## Step 11: Verify System Components

### 11.1 Check Celery Tasks

```bash
# Check if Celery Beat is scheduled
docker compose exec api celery -A app.worker.celery_app inspect scheduled

# Check active tasks
docker compose exec api celery -A app.worker.celery_app inspect active
```

### 11.2 Check Database State

```bash
# Summary of data
docker compose exec postgres psql -U director_monitor -d director_monitor << EOF
SELECT 
  (SELECT COUNT(*) FROM directors) as directors,
  (SELECT COUNT(*) FROM articles) as articles,
  (SELECT COUNT(*) FROM mentions) as mentions,
  (SELECT COUNT(*) FROM reports) as reports;
EOF
```

### 11.3 Check Provider Availability

```bash
# Test GDELT provider directly
docker compose exec api python -c "
from app.providers import GDELTProvider
provider = GDELTProvider()
print(f'GDELT available: {provider.is_available()}')
result = provider.search(type('QuerySpec', (), {'query': 'test', 'max_results': 1, 'date_from': None})())
print(f'GDELT test search returned {len(result)} articles')
"
```

---

## Step 12: Common Testing Scenarios

### 12.1 Test Full Workflow

1. **Add a director** (via UI or API)
2. **Trigger scan** (via CLI or API)
3. **Wait for processing** (check worker logs)
4. **View mentions** (via UI or API)
5. **Generate report** (via CLI or API)
6. **View report** (via UI)

### 12.2 Test Entity Resolution

Add a director with specific context terms and verify that articles are matched correctly:

```yaml
directors:
  - full_name: "Elon Musk"
    context_terms: ["Tesla", "SpaceX", "CEO"]
    negative_terms: ["music", "singer"]
    provider_gdelt_enabled: true
    is_active: true
```

After a scan, check that mentions have appropriate confidence scores.

### 12.3 Test Classification

Look for mentions in the database and verify classification:

```bash
docker compose exec postgres psql -U director_monitor -d director_monitor -c "
SELECT 
  d.full_name,
  a.title,
  m.sentiment,
  m.severity,
  m.category,
  m.confidence
FROM mentions m
JOIN directors d ON m.director_id = d.id
JOIN articles a ON m.article_id = a.id
ORDER BY m.created_at DESC
LIMIT 10;
"
```

### 12.4 Test Deduplication

Run two scans in a row and verify that duplicate articles are not processed twice:

```bash
# First scan
docker compose exec api python -m app.cli run-scan
# Wait for completion

# Check article count
COUNT1=$(docker compose exec -T postgres psql -U director_monitor -d director_monitor -t -c "SELECT COUNT(*) FROM articles;")

# Second scan
docker compose exec api python -m app.cli run-scan
# Wait for completion

# Check article count again (should be same or similar)
COUNT2=$(docker compose exec -T postgres psql -U director_monitor -d director_monitor -t -c "SELECT COUNT(*) FROM articles;")

echo "Articles before second scan: $COUNT1"
echo "Articles after second scan: $COUNT2"
```

---

## Troubleshooting Common Issues

### Services Won't Start

```bash
# Check Docker is running
docker --version
docker compose --version

# Check ports are available
netstat -an | grep -E ":(5432|6379|8000)"

# View detailed logs
docker compose logs
```

### Database Connection Errors

```bash
# Restart database
docker compose restart postgres

# Wait for database to be ready
docker compose exec postgres pg_isready -U director_monitor

# Run migrations again
docker compose exec api alembic upgrade head
```

### Worker Not Processing Tasks

```bash
# Check Redis is running
docker compose exec redis redis-cli ping

# Restart worker and beat
docker compose restart worker beat

# Check worker logs
docker compose logs worker | tail -50
```

### No Articles Found

- Check that directors are active: `SELECT * FROM directors WHERE is_active = true;`
- Check provider is enabled: GDELT should work without API key
- Check worker logs for provider errors
- Try a very common name like "Ratan Tata" or "Elon Musk" for testing

### Reports Not Generating

```bash
# Check if mentions exist
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT COUNT(*) FROM mentions;"

# Check worker logs for errors
docker compose logs worker | grep -i report

# Check storage directory exists and is writable
docker compose exec api ls -ld /app/storage
docker compose exec api touch /app/storage/test.txt && docker compose exec api rm /app/storage/test.txt
```

---

## Next Steps

After successfully running and testing:

1. **Configure for Production**:
   - Set strong SECRET_KEY
   - Configure proper email SMTP settings
   - Set up S3 storage (optional)
   - Configure monitoring (Sentry, etc.)

2. **Add Real Directors**:
   - Create directors.yaml with actual director data
   - Seed directors
   - Configure appropriate context terms

3. **Set Up Scheduling**:
   - Verify Celery Beat schedule in `.env` (RUN_TIME_HHMM)
   - Monitor daily runs

4. **Review and Refine**:
   - Check review queue for false positives
   - Adjust director context/negative terms
   - Fine-tune confidence thresholds

---

## Quick Reference Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f [service_name]

# Access database
docker compose exec postgres psql -U director_monitor -d director_monitor

# Run CLI commands
docker compose exec api python -m app.cli [command]

# Run tests
docker compose exec api pytest tests/ -v

# Restart service
docker compose restart [service_name]
```

---

## Summary

You've now:
✅ Set up the environment
✅ Started all services
✅ Created admin user
✅ Added test directors
✅ Run a monitoring scan
✅ Generated a report
✅ Tested the API
✅ Run unit tests

The system is ready for use! Continue exploring the web UI and API to familiarize yourself with all features.



