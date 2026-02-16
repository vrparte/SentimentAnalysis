# Director Media Monitoring System - Codebase Explanation

This document provides a comprehensive explanation of how the codebase works, its architecture, and key components.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Components](#key-components)
3. [Data Flow](#data-flow)
4. [Directory Structure](#directory-structure)
5. [Core Modules Deep Dive](#core-modules-deep-dive)
6. [API Endpoints](#api-endpoints)
7. [Worker Tasks & Scheduling](#worker-tasks--scheduling)
8. [Database Models](#database-models)

---

## Architecture Overview

The system follows a **microservices-like architecture** with the following layers:

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Web Server                    │
│  (REST API + Web UI for admin/directors management)     │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              Celery Workers (Background Tasks)           │
│  - Daily monitoring scans                                │
│  - Article processing                                    │
│  - Report generation                                     │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              Core Business Logic                         │
│  - Deduplication                                         │
│  - Entity Resolution (with Indian name matching)         │
│  - Classification (multilingual + India-specific)        │
│  - Language Detection (langid/langdetect)                │
│  - Reporting                                             │
│  - India Utilities (name patterns, context terms)        │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              Search Providers                            │
│  - GDELT (global news)                                   │
│  - Bing News (multilingual)                              │
│  - SerpAPI (Google News)                                 │
│  - RSS (feed support)                                    │
│  - NewsData.io (India-focused, 10+ languages)           │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              PostgreSQL Database                         │
│  - Directors (with India-specific fields)                │
│  - Articles (language, country, state, city, trust)      │
│  - Mentions (expanded risk categories)                   │
│  - Reports, Users, Settings                              │
└─────────────────────────────────────────────────────────┘
```

### Key Technologies

- **FastAPI**: Web framework for REST API and web UI
- **Celery**: Distributed task queue for background jobs
- **Redis**: Message broker for Celery
- **PostgreSQL**: Primary database with JSON support
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations
- **langid/langdetect**: Language detection for multilingual content
- **bcrypt**: Password hashing
- **JWT**: Token-based authentication
- **Trafilatura**: Article content extraction
- **WeasyPrint**: PDF report generation

---

## Key Components

### 1. **Configuration** (`app/config.py`)

Central configuration management using Pydantic Settings:
- Reads from `.env` file
- Provides type-safe access to all settings
- Includes: database, Redis, providers, email, LLM, storage settings
- **India-specific**: `COUNTRY_PROFILE` (default: "default", can be set to "IN"), `NEWSDATA_API_KEY` for India-focused news provider

### 2. **Database** (`app/database.py`)

- Creates SQLAlchemy engine and session factory
- Provides `get_db()` dependency for FastAPI routes
- `Base` class for all models

### 3. **Models** (`app/models/`)

SQLAlchemy ORM models representing database tables:
- `Director`: Directors being monitored
  - **Standard fields**: full_name, aliases, context_terms, negative_terms, provider flags, is_active
  - **India-specific fields**: first_name, middle_names, last_name, company_name, company_industry, listed_exchange, hq_state, hq_city, india_context_profile (JSON), provider_newsdata_enabled
- `Article`: Raw article metadata from search providers
  - **Standard fields**: url, canonical_url, title, source, published_at, snippet, provider_name
  - **Multilingual/regional fields**: language, country, state, district, city, source_type, source_trust_score
- `ExtractedContent`: Full article content extracted from URLs (content, content_hash, extraction_method)
- `Mention`: Links directors to articles with classification results
  - **Expanded categories**: Includes India-specific risk categories (LITIGATION, CORPORATE_GOVERNANCE, ESG_SOCIAL_POLITICAL)
- `Report`: Daily digest reports (HTML + PDF paths, stats JSON)
- `User`: Authentication (Admin/MD roles)

### 4. **Search Providers** (`app/providers/`)

Abstract base class (`base.py`) with concrete implementations:
- **GDELTProvider**: Free global news database (no API key, supports language/country filters)
- **BingNewsProvider**: Microsoft Bing News API (multilingual support)
- **SerpAPIProvider**: SerpAPI (Google News, supports country/language params)
- **RSSProvider**: RSS feed support
- **NewsDataProvider**: NewsData.io API (India-focused, supports 10+ Indian languages, region filters)

All providers implement:
- `search(query_spec)`: Returns `List[CandidateArticle]` with language, country, state, city metadata
- `is_available()`: Checks if provider is configured

**Provider Features**:
- Language and country filtering in queries
- State/city metadata extraction where available
- Source trust scoring (mainstream, regional, tabloid, etc.)
- Multilingual support (especially NewsData.io for Indian languages)

### 5. **Core Business Logic** (`app/core/`)

#### Deduplication (`deduplication.py`)
- **URL canonicalization**: Normalizes URLs (removes tracking params, etc.)
- **Content hashing**: SHA256 hash of normalized content
- **Simhash**: For similarity detection (not used in main flow but available)
- **Multi-level matching**: Checks exact URL, canonical URL, title+source+date, content hash

#### Entity Resolution (`entity_resolution.py`)
- **Name matching**: Finds director names in article text (word boundaries)
  - **Indian name patterns**: Supports honorifics (Shri, Dr., Prof.), initials (R. Kumar), multiple spellings
  - **Structured name matching**: Uses first_name, middle_names, last_name for better precision
- **Context term matching**: Counts how many context terms appear
- **Negative term filtering**: Excludes articles with negative terms
- **Location disambiguation**: Uses company HQ state/city to boost confidence for matching locations
- **Confidence scoring**: 
  - Name in title: +0.5
  - Name in snippet: +0.3
  - Name in content: +0.2
  - Context terms: +0.1 each (max +0.3)
  - Location match (state): +0.1
  - Location match (city): +0.05
  - Negative terms: -1.0 (excludes)

#### Classification (`classification.py`)
- **Heuristic-based**: Keyword matching for sentiment/severity/category
  - Sentiment: POSITIVE, NEGATIVE, NEUTRAL, MIXED
  - Severity: LOW, MEDIUM, HIGH (considering source trust score)
  - Category: Expanded with India-specific risk categories:
    - REGULATORY_ENFORCEMENT (SEBI, RBI, ED, CBI, SFIO, NCLT, MCA)
    - LEGAL_COURT (Supreme Court, High Court, litigation)
    - LITIGATION (civil, criminal cases)
    - CORPORATE_GOVERNANCE (board disputes, related-party transactions)
    - ESG_SOCIAL_POLITICAL (controversies, protests, public outcry)
    - FINANCIAL_CORPORATE, GOVERNANCE_BOARD_APPOINTMENT, AWARDS_RECOGNITION, etc.
  - **India-specific keywords**: SEBI, RBI, ED, CBI, NCLT, NCLAT, MCA, High Court, Supreme Court, etc.
  - **Multilingual support**: Handles Hindi and other Indian language keywords
- **LLM-based** (optional): Uses OpenAI GPT for classification
- Generates summary bullets and "why it matters" text
- **Source credibility**: Incorporates source trust scores in severity assessment

#### Reporting (`reporting.py`)
- Generates HTML reports using Jinja2 templates
- Converts HTML to PDF using WeasyPrint
- Includes statistics, director breakdowns, low-confidence items
- Stores reports in storage directory

#### Article Extraction (`article_extraction.py`)
- Uses Trafilatura library to extract clean article content
- Handles timeouts and retries
- Stores extracted content in database

#### Language Detection (`language_detection.py`)
- **Automatic language detection**: Uses `langid` (preferred) or `langdetect` (fallback)
- **Indic script detection**: Heuristic detection for Devanagari, Tamil, Telugu scripts
- **ISO 639-1 codes**: Returns standard language codes (en, hi, ta, te, etc.)
- **Integration**: Language detection runs after article extraction to populate Article.language

#### India Utilities (`india_utils.py`)
- **Indian name pattern generation**: Creates multiple name variations (honorifics, initials, spellings)
- **India-specific keywords**: Regulatory (SEBI, RBI, ED, CBI, SFIO), legal (High Court, Supreme Court), Hindi legal terms
- **State/city mappings**: Indian state abbreviations and full names
- **Source classification**: Categorizes sources as mainstream_national, credible_regional, vernacular_regional, partisan, tabloid
- **Trust scoring**: Assigns trust scores (0-100) based on source classification

#### Email (`email.py`)
- Sends immediate alerts for high-severity items
- Sends daily digest reports
- Uses SMTP configuration from settings

### 6. **Worker Tasks** (`app/worker/tasks.py`)

Celery tasks that run in background:

1. **`daily_monitoring_job`**: Main entry point
   - Runs daily at configured time (default 07:30 IST)
   - Queues `process_director` for each active director

2. **`process_director`**: Processes one director
   - Builds search queries (recall + precision queries, with India-specific enhancements if country_profile="IN")
   - Searches all enabled providers (including NewsData.io if enabled)
   - Passes language/country/state filters to providers based on director metadata
   - Deduplicates results
   - Queues `process_article` for each new article (up to 20 per director)

3. **`process_article`**: Processes one article
   - Fetches and extracts article content
   - Runs entity resolution (matches to director)
   - Classifies (sentiment, severity, category)
   - Creates Mention record
   - Queues alert if high severity

4. **`generate_daily_report`**: Generates daily digest
   - Aggregates mentions from date range
   - Generates HTML and PDF
   - Sends email

5. **`cleanup_old_data`**: Data retention
   - Deletes old mentions/articles (default 365 days)

### 7. **API Endpoints** (`app/api/`)

FastAPI routers:
- **`auth.py`**: JWT authentication (login, token refresh)
- **`directors.py`**: CRUD for directors (Admin only)
- **`items.py`**: List mentions/articles with filters
- **`reports.py`**: List/generate/download reports
- **`admin.py`**: Admin operations (trigger scan, etc.)
- **`settings.py`**: Application settings management
- **`web.py`**: Web UI routes (Jinja2 templates)

### 8. **Web UI** (`app/templates/`)

Jinja2 HTML templates:
- `login.html`: User login
- `directors.html`: Director management
- `items.html`: View mentions/articles
- `reports.html`: View/download reports
- `review_queue.html`: Review low-confidence items
- `base.html`: Base template with navigation

---

## Data Flow

### Daily Monitoring Flow

```
1. Celery Beat triggers daily_monitoring_job (07:30 IST)
   ↓
2. daily_monitoring_job:
   - Gets all active directors
   - Queues process_director for each director
   ↓
3. process_director (for each director):
   - Builds queries (e.g., "John Doe", "John Doe AND SEBI", etc.)
   - For each enabled provider (GDELT, Bing, etc.):
     - Calls provider.search(query_spec)
     - Gets CandidateArticle objects
   - Deduplicates against existing articles (last 7 days)
   - Queues process_article for each new article (limit 20 per director)
   ↓
4. process_article (for each article):
   - Checks if Article exists (by canonical URL)
   - If new, creates Article record
   - Fetches and extracts content (Trafilatura)
   - Stores ExtractedContent
   - Runs entity resolution (resolve_director):
     - Matches director name in title/snippet/content
     - Checks context terms
     - Filters negative terms
     - Computes confidence score
   - If confidence >= threshold (0.3), creates Mention:
     - Runs classification (heuristic or LLM)
     - Sets sentiment, severity, category
     - Generates summary bullets
   - If severity=HIGH and confidence>=0.75, queues send_alert
   ↓
5. send_alert:
   - Sends immediate email alert
   - Marks mention.alert_sent = True
```

### Report Generation Flow

```
1. Celery Beat triggers generate_daily_report (after monitoring, or manually)
   ↓
2. generate_daily_report:
   - Gets all mentions from date range (last 24h)
   - Groups by director
   - Computes statistics
   - Renders HTML template with:
     - Executive summary (stats)
     - Director sections (top mentions)
     - Low-confidence items (review queue)
   - Converts HTML to PDF (WeasyPrint)
   - Saves to storage directory
   - Creates Report record
   - Sends email with report link
```

### Query Building Strategy

For each director, multiple queries are built:

1. **Recall query**: Just the name - `"John Doe"` (catches everything)
2. **Precision query**: Name + context terms - `"John Doe" AND ("ABC Corp" OR "independent director")`
3. **Regulatory query**: Name + regulatory keywords - `"John Doe" AND ("SEBI" OR "RBI" OR "ED")`
4. **Positive query**: Name + positive keywords - `"John Doe" AND ("award" OR "appointed")`
5. **Legal query**: Name + legal keywords - `"John Doe" AND ("court" OR "fraud")`

This strategy balances **recall** (don't miss anything) and **precision** (filter false positives).

---

## Directory Structure

```
app/
├── api/                    # FastAPI endpoints
│   ├── main.py            # FastAPI app initialization
│   ├── auth.py            # Authentication (JWT)
│   ├── directors.py       # Director CRUD
│   ├── items.py           # Mentions/articles listing
│   ├── reports.py         # Report management
│   ├── admin.py           # Admin operations
│   ├── settings.py        # Settings management
│   └── web.py             # Web UI routes
│
├── core/                   # Core business logic
│   ├── deduplication.py   # URL/content deduplication
│   ├── entity_resolution.py  # Director matching (with Indian name patterns)
│   ├── classification.py  # Sentiment/severity/category (multilingual + India-specific)
│   ├── reporting.py       # HTML/PDF report generation
│   ├── article_extraction.py  # Content extraction
│   ├── email.py           # Email sending
│   ├── url_utils.py       # URL canonicalization
│   ├── language_detection.py  # Language detection (langid/langdetect)
│   └── india_utils.py     # India-specific utilities (name patterns, keywords, trust scoring)
│
├── models/                 # SQLAlchemy models
│   ├── director.py        # Director model
│   ├── article.py         # Article & ExtractedContent
│   ├── mention.py         # Mention model (with enums)
│   ├── report.py          # Report model
│   ├── user.py            # User model
│   └── setting.py         # Settings model
│
├── providers/              # Search provider implementations
│   ├── base.py            # Abstract base class
│   ├── gdelt.py           # GDELT provider
│   ├── bing.py            # Bing News provider
│   ├── serpapi.py         # SerpAPI provider
│   ├── rss.py             # RSS provider
│   └── newsdata.py        # NewsData.io provider (India-focused)
│
├── worker/                 # Celery workers
│   ├── celery_app.py      # Celery configuration & Beat schedule
│   └── tasks.py           # Task definitions
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── directors.html
│   ├── items.html
│   ├── reports.html
│   └── review_queue.html
│
├── static/                 # Static files (CSS, JS, images)
│
├── cli.py                  # CLI commands (create-admin, run-scan, etc.)
├── seed.py                 # Seed script (load directors from YAML)
├── config.py               # Configuration (Pydantic Settings)
└── database.py             # Database connection
```

---

## Core Modules Deep Dive

### Entity Resolution (`entity_resolution.py`)

**Purpose**: Match articles to directors with confidence scores.

**Key Functions**:
- `find_name_in_text()`: Checks if any director name appears (word boundaries)
- `find_terms_in_text()`: Counts context term matches
- `check_negative_terms()`: Excludes articles with negative terms
- `compute_confidence()`: Calculates 0.0-1.0 score
- `resolve_director()`: Returns best matching director or None

**Confidence Scoring**:
```
Name in title:        +0.5
Name in snippet:      +0.3
Name in content:      +0.2
Context terms:        +0.1 each (max +0.3)
Location match (state): +0.1
Location match (city):  +0.05
Negative terms:       -1.0 (excludes article)
```

**Indian Name Matching**:
- Supports honorifics: "Shri John Doe", "Dr. John Doe", "Prof. John Doe"
- Handles initials: "J. Doe", "John D.", "J.A. Doe"
- Uses structured names (first_name, middle_names, last_name) for better pattern generation
- Multiple spellings via aliases

**Example**:
- Article title: "Shri John Doe appointed to ABC Corp board"
- Director: full_name="John Doe", first_name="John", last_name="Doe", context_terms=["ABC Corp", "board"], hq_state="Maharashtra"
- Article location: state="Maharashtra"
- Confidence: 0.5 (name in title, matches "Shri John Doe") + 0.2 (2 context terms) + 0.1 (state match) = 0.8

### Classification (`classification.py`)

**Purpose**: Determine sentiment, severity, and category.

**Heuristic Approach**:
1. Checks keywords in full text (title + snippet + content)
2. Negative high-severity keywords → NEGATIVE, HIGH (e.g., "fraud", "arrested")
3. Negative medium-severity keywords → NEGATIVE, MEDIUM (e.g., "investigation", "notice")
4. Positive keywords → POSITIVE, LOW (e.g., "appointed", "award")
5. Category keywords → Sets category (REGULATORY, LEGAL, FINANCIAL, etc.)

**LLM Approach** (optional):
- Uses OpenAI GPT to classify
- More accurate but slower and costs money
- Falls back to heuristic if unavailable

### Deduplication (`deduplication.py`)

**Purpose**: Prevent duplicate articles from being processed.

**Matching Strategies**:
1. **Exact URL match**: Same URL
2. **Canonical URL match**: Normalized URLs match (removes tracking params)
3. **Content hash match**: SHA256 hash of normalized content
4. **Title + Source + Date**: Same title, source, and publication date

**Implementation**:
- Builds lookup sets from existing articles (last 7 days)
- Checks each candidate article against all sets
- Only adds articles that don't match any criteria

### Query Building (`worker/tasks.py` → `build_queries()`)

**Purpose**: Generate effective search queries for each director.

**Strategy**:
- Multiple queries per director (max 5)
- Balance recall (catch everything) and precision (filter false positives)
- Includes regulatory, legal, and positive keyword queries

**Example for director "John Doe" with context_terms=["ABC Corp"] and country_profile="IN"**:
1. `"John Doe"` (recall)
2. `"John Doe" AND ("ABC Corp")` (precision)
3. `"John Doe" AND ("SEBI" OR "RBI" OR "ED" OR ...)` (regulatory - India-specific)
4. `"John Doe" AND ("Supreme Court" OR "High Court" OR ...)` (legal - India-specific)
5. `"John Doe" AND ("गिरफ्तार" OR "जांच" OR ...)` (Hindi legal terms if country=IN)
6. `"John Doe" AND ("award" OR "appointed" OR ...)` (positive)

**India-specific enhancements**:
- Adds India regulatory terms (SEBI, RBI, ED, CBI, SFIO, NCLT, NCLAT, MCA) automatically
- Includes Hindi legal keywords for better coverage of vernacular sources
- Location-based queries when director has hq_state/hq_city set

---

## API Endpoints

### Authentication
- `POST /api/login`: Get JWT token
- `POST /api/refresh`: Refresh token

### Directors (Admin only)
- `GET /api/directors/`: List all directors
- `GET /api/directors/{id}`: Get director
- `POST /api/directors/`: Create director
- `PUT /api/directors/{id}`: Update director
- `DELETE /api/directors/{id}`: Delete director

### Items (Articles/Mentions)
- `GET /api/items/`: List mentions with filters (date, director, severity, etc.)
- `GET /api/items/{id}`: Get mention details
- `PUT /api/items/{id}/review`: Review low-confidence item

### Reports
- `GET /api/reports/`: List all reports
- `GET /api/reports/{id}`: Get report
- `GET /api/reports/{id}/html`: View HTML report
- `GET /api/reports/{id}/pdf`: Download PDF report
- `POST /api/reports/generate`: Generate report for date

### Admin
- `POST /api/admin/trigger-scan`: Manually trigger monitoring scan

### Web UI
- `GET /login`: Login page
- `GET /directors`: Director management (Admin)
- `GET /items`: View mentions
- `GET /reports`: View reports
- `GET /review-queue`: Review low-confidence items

---

## Worker Tasks & Scheduling

### Celery Configuration (`worker/celery_app.py`)

- **Broker/Backend**: Redis
- **Timezone**: Configurable (default: Asia/Kolkata)
- **Task timeout**: 1 hour

### Beat Schedule

1. **Daily Monitoring**:
   - Task: `daily_monitoring_job`
   - Schedule: Configurable (default: 07:30 IST daily)
   - Runs: Every day at specified time

2. **Weekly Cleanup**:
   - Task: `cleanup_old_data`
   - Schedule: Sunday 02:00 IST
   - Deletes data older than retention period (default: 365 days)

### Task Chain

```
daily_monitoring_job
  ↓
process_director (for each director)
  ↓
process_article (for each article, up to 20 per director)
  ↓
send_alert (if high severity)
```

Tasks are **asynchronous** and run in parallel (up to 4 workers by default).

---

## Database Models

### Director
- **Fields**: full_name, first_name, middle_names, last_name, aliases (JSON), context_terms (JSON), negative_terms (JSON), company_name, company_industry, listed_exchange, hq_state, hq_city, india_context_profile (JSON), provider flags (gdelt, bing, serpapi, rss, newsdata), is_active
- **Relationships**: One-to-many with Mention

### Article
- **Fields**: url, canonical_url, title, source, published_at, snippet, provider_name, fetch_status, **language**, **country**, **state**, **district**, **city**, **source_type**, **source_trust_score**
- **Relationships**: One-to-one with ExtractedContent, One-to-many with Mention

### ExtractedContent
- **Fields**: content (full text), content_hash (SHA256), extraction_method
- **Relationships**: Many-to-one with Article

### Mention
- **Fields**: director_id, article_id, confidence (0.0-1.0), sentiment, severity, category (includes India-specific: LITIGATION, CORPORATE_GOVERNANCE, ESG_SOCIAL_POLITICAL), summary_bullets (JSON), why_it_matters, is_reviewed, is_confirmed, alert_sent
- **Relationships**: Many-to-one with Director, Many-to-one with Article

### Report
- **Fields**: report_date, html_path, pdf_path, stats (JSON)
- **Relationships**: None (standalone)

### User
- **Fields**: username, email, hashed_password, role (ADMIN/MD), is_active
- **Relationships**: None

---

## Key Design Decisions

1. **Deduplication at multiple levels**: Prevents duplicate processing
2. **Confidence scoring**: Reduces false positives, enables review queue
3. **Multiple search queries**: Balances recall and precision
4. **Asynchronous processing**: Celery tasks allow parallel processing
5. **Provider abstraction**: Easy to add new search providers
6. **Heuristic + LLM classification**: Fast default, accurate optional
7. **HTML + PDF reports**: Human-readable format
8. **Email alerts**: Immediate notification for high-severity items

---

## Configuration

All configuration is in `.env` file (see `.env.example`):

- **Company**: COMPANY_NAME, TIMEZONE, RUN_TIME_HHMM
- **Database**: DATABASE_URL
- **Redis**: REDIS_URL
- **Providers**: PROVIDERS_ENABLED, BING_NEWS_KEY, SERPAPI_KEY, NEWSDATA_API_KEY (India-focused)
- **India-specific**: COUNTRY_PROFILE (set to "IN" for India defaults)
- **Classification**: USE_LLM, LLM_API_KEY, LLM_MODEL, CONFIDENCE_THRESHOLD_ALERT
- **Email**: SMTP_*, FROM_EMAIL, RECIPIENTS_MD, RECIPIENTS_ADMIN
- **Storage**: STORAGE_TYPE, LOCAL_STORAGE_DIR (or S3_*)
- **Security**: SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

---

## Extension Points

1. **Add new provider**: Create class inheriting `SearchProvider` in `providers/`
2. **Custom classification**: Modify `classification.py` or add new classifier
3. **Different storage**: Implement S3 storage (code structure ready)
4. **Additional notification channels**: Add to `email.py` or create new module
5. **Custom report format**: Modify `reporting.py` template

---

## Summary

This is a **production-ready media monitoring system** that:

1. **Monitors** multiple news sources for director mentions
2. **Filters** duplicates and false positives
3. **Classifies** articles by sentiment, severity, and category
4. **Generates** daily digest reports (HTML + PDF)
5. **Alerts** on high-severity items
6. **Provides** web UI for management and review

The architecture is **modular**, **scalable**, and **extensible**, making it easy to add new features or providers.



