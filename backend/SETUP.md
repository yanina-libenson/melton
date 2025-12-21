# Dr. Melton Backend - Complete Setup Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Poetry (Python package manager)

### 1. Install Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Navigate to Backend Directory
```bash
cd backend
```

### 3. Install Dependencies
```bash
poetry install
```

This will install all required packages including:
- FastAPI, SQLAlchemy, Alembic
- Anthropic, OpenAI, Google Generative AI SDKs
- LangFuse for observability
- All testing and linting tools

### 4. Start Infrastructure Services
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Redis (port 6379)

### 5. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
# Optional - users can provide their own API keys per agent
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

# Optional - for observability
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
```

### 6. Create Database Schema
```bash
poetry run alembic upgrade head
```

### 7. Start Development Server
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Access the API
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Running Tests

### Run All Tests
```bash
poetry run pytest
```

### Run with Coverage
```bash
poetry run pytest --cov=app --cov-report=html
```

### Run Specific Test File
```bash
poetry run pytest tests/unit/test_agent_service.py -v
```

## 🔍 Code Quality

### Linting
```bash
poetry run ruff check .
```

### Auto-fix Linting Issues
```bash
poetry run ruff check --fix .
```

### Formatting
```bash
poetry run black .
```

### Type Checking
```bash
poetry run mypy app
```

### Run All Quality Checks
```bash
poetry run ruff check . && poetry run black --check . && poetry run mypy app
```

## 📊 Database Management

### Create a New Migration
```bash
poetry run alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
poetry run alembic upgrade head
```

### Rollback One Migration
```bash
poetry run alembic downgrade -1
```

### View Migration History
```bash
poetry run alembic history
```

## 🔧 Development Workflow

### 1. Start Development Environment
```bash
# Terminal 1: Infrastructure
docker-compose up

# Terminal 2: Backend Server
poetry run uvicorn app.main:app --reload
```

### 2. Make Code Changes
- Follow coding principles in `/CODING_PRINCIPLES.md`
- Keep methods 10-20 lines
- Keep classes under 200 lines
- Use human-readable names

### 3. Test Your Changes
```bash
poetry run pytest tests/unit/test_your_feature.py
```

### 4. Check Code Quality
```bash
poetry run ruff check . --fix
poetry run black .
poetry run mypy app
```

### 5. Commit Changes
```bash
git add .
git commit -m "feat: add new feature"
```

## 📚 API Usage Examples

### Create an Agent
```bash
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support Agent",
    "instructions": "You are a helpful customer support agent.",
    "status": "draft",
    "model_config": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }'
```

### List Agents
```bash
curl -X GET "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer your-jwt-token"
```

### Test Agent in Playground (WebSocket)
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/playground/{agent_id}');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'user_message',
    content: 'Hello, how can you help me?',
    conversation_id: null  // or existing conversation_id
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
};
```

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker ps

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)
```

### Migration Issues
```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
poetry run alembic upgrade head
```

### Poetry Issues
```bash
# Clear cache
poetry cache clear pypi --all

# Reinstall dependencies
rm -rf .venv
poetry install
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/              # API endpoints
│   │   ├── agents.py        # Agent CRUD
│   │   └── playground.py    # WebSocket playground
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── agent_service.py
│   │   ├── conversation_service.py
│   │   └── execution_service.py
│   ├── llm/                 # LLM provider abstraction
│   │   ├── base_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   ├── google_provider.py
│   │   └── factory.py
│   ├── tools/               # Tool system
│   │   ├── base_tool.py
│   │   ├── registry.py
│   │   └── api_tool.py
│   ├── utils/               # Utilities
│   │   ├── encryption.py
│   │   ├── observability.py
│   │   └── openapi_parser.py
│   ├── config.py            # Settings
│   ├── database.py          # DB setup
│   ├── dependencies.py      # Dependency injection
│   └── main.py              # FastAPI app
├── tests/                   # Tests
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── alembic/                 # Migrations
├── docker-compose.yml       # Local infrastructure
├── pyproject.toml           # Dependencies
└── README.md
```

## 🎯 Next Steps

1. **Test the API**: Use the interactive docs at `/docs`
2. **Create an agent**: Use the Agent CRUD endpoints
3. **Add tools**: Implement custom API tools
4. **Test playground**: Connect via WebSocket and chat
5. **Deploy to Render**: Follow deployment guide (coming soon)

## 📞 Support

- Check the main README.md for architecture details
- Review CODING_PRINCIPLES.md for code standards
- See the implementation plan at `/Users/yani/.claude/plans/tranquil-plotting-tulip.md`
