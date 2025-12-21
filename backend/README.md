# Dr. Melton Backend API

Production Python API for the Dr. Melton Agent Builder platform.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Poetry

### Local Development Setup

1. **Start infrastructure services:**
   ```bash
   docker-compose up -d
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Setup environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations:**
   ```bash
   poetry run alembic upgrade head
   ```

5. **Start the development server:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

6. **Access the API:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── llm/             # LLM provider abstraction
│   ├── tools/           # Tool system
│   ├── channels/        # Deployment channels
│   ├── utils/           # Utilities
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   └── main.py          # FastAPI app
├── tests/               # Tests
├── alembic/             # Database migrations
└── docker-compose.yml   # Local development
```

## Development

### Running Tests
```bash
poetry run pytest
```

### Code Quality
```bash
# Linting
poetry run ruff check .

# Formatting
poetry run black .

# Type checking
poetry run mypy app
```

### Database Migrations
```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## API Documentation

Once the server is running, visit http://localhost:8000/docs for interactive API documentation.

## Architecture

See the [implementation plan](/Users/yani/.claude/plans/tranquil-plotting-tulip.md) for detailed architecture documentation.

## License

Proprietary
