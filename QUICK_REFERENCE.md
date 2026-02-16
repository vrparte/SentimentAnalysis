# Quick Reference Guide

## Common Operations

### Starting the System

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat

# Stop services
docker compose down
```

### Database Operations

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Create migration
docker compose exec api alembic revision --autogenerate -m "description"

# Access PostgreSQL
docker compose exec postgres psql -U director_monitor -d director_monitor
```

### User Management

```bash
# Create admin user
docker compose exec api python -m app.cli create-admin \
  --username admin \
  --password admin123 \
  --email admin@example.com

# Create MD user
docker compose exec api python -m app.cli create-admin \
  --username md_user \
  --password md123 \
  --email md@example.com \
  --role md
```

### Monitoring Operations

```bash
# Trigger manual scan
docker compose exec api python -m app.cli run-scan

# Generate report for today
docker compose exec api python -m app.cli generate-report

# Generate report for specific date
docker compose exec api python -m app.cli generate-report --date 2024-01-15
```

### Seeding Directors

```bash
# Seed from YAML file
docker compose exec api python -m app.seed directors.yaml
```

### API Usage

```bash
# Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# List directors
curl http://localhost:8000/api/directors/ \
  -H "Authorization: Bearer $TOKEN"

# Create director
curl -X POST http://localhost:8000/api/directors/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "aliases": ["J. Doe"],
    "context_terms": ["ABC Corp", "independent director"],
    "negative_terms": ["actor", "footballer"],
    "provider_gdelt_enabled": true,
    "provider_bing_enabled": true
  }'

# Trigger scan
curl -X POST http://localhost:8000/api/admin/trigger-scan \
  -H "Authorization: Bearer $TOKEN"

# List mentions
curl "http://localhost:8000/api/items/?severity=high" \
  -H "Authorization: Bearer $TOKEN"

# Get report
curl http://localhost:8000/api/reports/1/pdf \
  -H "Authorization: Bearer $TOKEN" \
  --output report.pdf
```

## File Locations

### Configuration
- `.env`: Environment variables (copy from `.env.example`)
- `app/config.py`: Configuration class (Pydantic Settings)

### Code Entry Points
- `app/api/main.py`: FastAPI application entry point
- `app/worker/tasks.py`: Celery task definitions
- `app/worker/celery_app.py`: Celery configuration
- `app/cli.py`: Command-line interface

### Key Business Logic
- `app/core/entity_resolution.py`: Director matching algorithm
- `app/core/classification.py`: Sentiment/severity classification
- `app/core/deduplication.py`: Duplicate detection
- `app/core/reporting.py`: Report generation

### Data Models
- `app/models/director.py`: Director model
- `app/models/article.py`: Article model
- `app/models/mention.py`: Mention model (links director to article)
- `app/models/report.py`: Report model

### Search Providers
- `app/providers/base.py`: Abstract base class
- `app/providers/gdelt.py`: GDELT implementation
- `app/providers/bing.py`: Bing News implementation
- `app/providers/serpapi.py`: SerpAPI implementation

## Key Concepts

### Director Configuration
- **full_name**: Primary name to search for
- **aliases**: Alternative names (e.g., "J. Doe" for "John Doe")
- **context_terms**: Terms that should appear with name (e.g., "ABC Corp", "board")
- **negative_terms**: Terms that indicate false positive (e.g., "actor", "footballer")
- **provider_*_enabled**: Enable/disable specific providers per director

### Confidence Scoring
- Range: 0.0 to 1.0
- Thresholds:
  - `< 0.3`: Not matched (excluded)
  - `0.3 - 0.5`: Low confidence (review queue)
  - `0.5 - 0.75`: Medium confidence (included)
  - `>= 0.75`: High confidence (alerts if high severity)

### Classification
- **Sentiment**: POSITIVE, NEGATIVE, NEUTRAL, MIXED
- **Severity**: LOW, MEDIUM, HIGH
- **Category**: REGULATORY_ENFORCEMENT, LEGAL_COURT, FINANCIAL_CORPORATE, GOVERNANCE_BOARD_APPOINTMENT, AWARDS_RECOGNITION, PERSONAL_REPUTATION, OTHER

### Mention States
- **is_confirmed**: True if valid mention, False if false positive
- **is_reviewed**: True if manually reviewed
- **alert_sent**: True if alert email sent

## Troubleshooting

### Jobs not running
```bash
# Check Celery Beat logs
docker compose logs beat

# Check Redis connection
docker compose exec redis redis-cli ping

# Check worker logs
docker compose logs worker
```

### Provider issues
```bash
# Test GDELT (should always work)
curl "https://api.gdeltproject.org/api/v2/doc/doc?query=test&mode=artlist&maxrecords=5&format=json"

# Check provider availability
# Look for "Provider {name} search error" in worker logs
```

### Database issues
```bash
# Check PostgreSQL connection
docker compose exec postgres pg_isready -U director_monitor

# View recent articles
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT id, title, url FROM articles ORDER BY created_at DESC LIMIT 10;"

# View recent mentions
docker compose exec postgres psql -U director_monitor -d director_monitor -c "SELECT id, director_id, confidence, severity FROM mentions ORDER BY created_at DESC LIMIT 10;"
```

### Low confidence scores
- Add more context terms for directors
- Review negative terms (may be too broad)
- Check article extraction quality
- Review entity resolution logic in `app/core/entity_resolution.py`

### Email not sending
```bash
# Check SMTP configuration in .env
# Test SMTP connection (Python script)
docker compose exec api python -c "
import smtplib
from app.config import settings
server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
server.starttls()
server.login(settings.smtp_user, settings.smtp_pass)
print('SMTP connection successful')
server.quit()
"
```

## Development Workflow

### Adding a new provider
1. Create new file in `app/providers/` (e.g., `newsapi.py`)
2. Inherit from `SearchProvider` in `base.py`
3. Implement `search()` and `is_available()` methods
4. Add provider to `process_director()` in `tasks.py`
5. Add configuration in `config.py` if needed
6. Update `.env.example` with API key

### Modifying classification logic
1. Edit `app/core/classification.py`
2. Modify keyword lists or LLM prompt
3. Test with sample articles
4. Check classification results in database

### Changing deduplication strategy
1. Edit `app/core/deduplication.py`
2. Modify matching logic in `deduplicate_articles()`
3. Test with duplicate articles
4. Monitor deduplication effectiveness

### Customizing reports
1. Edit `REPORT_TEMPLATE` in `app/core/reporting.py`
2. Modify Jinja2 template HTML
3. Adjust CSS styling
4. Test report generation

## Performance Tuning

### Worker concurrency
Edit `docker-compose.yml`:
```yaml
worker:
  command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=8
```

### Database connection pooling
Edit `app/database.py`:
```python
engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

### Article processing limit
Edit `app/worker/tasks.py`:
```python
# In process_director(), change limit
for article_dict in deduplicated[:50]:  # Increase from 20
```

### Query limits
Edit `app/config.py`:
```python
max_articles_per_director_per_provider: int = 100  # Increase from 50
```



