# Quick Start Guide - Dr. Melton Agent Builder

Get up and running with Dr. Melton in under 5 minutes!

## Prerequisites

Before you start, make sure you have:
- ✅ **Docker Desktop** installed and running
- ✅ **Python 3.11+** installed
- ✅ **Node.js 18+** installed
- ✅ **Poetry** installed (`curl -sSL https://install.python-poetry.org | python3 -`)

## Quick Start (Automated)

### Option 1: Use Start Scripts (Recommended)

**Terminal 1 - Start Backend:**
```bash
cd backend
./start.sh
```

This will automatically:
- ✅ Check Docker is running
- ✅ Start PostgreSQL and Redis
- ✅ Run database migrations
- ✅ Start backend API server at http://localhost:8000

**Terminal 2 - Start Frontend:**
```bash
cd frontend
./start.sh
```

This will automatically:
- ✅ Check backend is running
- ✅ Install npm dependencies
- ✅ Start frontend at http://localhost:3000

**That's it!** Open http://localhost:3000/agents in your browser.

---

## Manual Start (Step-by-Step)

### Backend Setup

**1. Install Dependencies**
```bash
cd backend
poetry install
```

**2. Configure Environment**
```bash
# .env file is already created with defaults
# (Optional) Add your LLM API keys:
# - ANTHROPIC_API_KEY=sk-ant-your-key
# - OPENAI_API_KEY=sk-your-key
# - GOOGLE_API_KEY=AIzaSy-your-key
```

**3. Start Docker Services**
```bash
docker-compose up -d
```

**4. Run Database Migrations**
```bash
poetry run alembic upgrade head
```

**5. Start Backend Server**
```bash
poetry run uvicorn app.main:app --reload
```

Backend running at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

### Frontend Setup

**1. Install Dependencies**
```bash
cd frontend
npm install
```

**2. Configure Environment**
```bash
# Create .env.local (or use existing)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

**3. Start Frontend Server**
```bash
npm run dev
```

Frontend running at:
- App: http://localhost:3000
- Agents: http://localhost:3000/agents

---

## Verify Installation

### 1. Check Backend Health

**Via Browser:**
Open http://localhost:8000 - Should see API info

**Via curl:**
```bash
curl http://localhost:8000
```

Expected response:
```json
{
  "name": "Dr. Melton Agent Builder API",
  "version": "0.1.0",
  "status": "operational"
}
```

---

### 2. Check API Documentation

Open http://localhost:8000/docs - Should see Swagger UI with all endpoints

---

### 3. Check Frontend

Open http://localhost:3000/agents - Should see the agents page (empty or with agents)

---

## Create Your First Agent

### Via Frontend UI (Easy)

1. Navigate to http://localhost:3000/agents
2. Click "New Agent" button
3. Fill in:
   - **Name:** "My First Agent"
   - **Instructions:** "You are a helpful assistant who answers questions clearly and concisely."
4. Click "Save"
5. Agent created! Click on it to open the detail page
6. Click "Test" tab to try the playground

---

### Via API (Advanced)

**Create an agent:**
```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Agent",
    "instructions": "You are a helpful test agent.",
    "status": "draft",
    "model_config": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250929",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }'
```

**Response:**
```json
{
  "id": "uuid-here",
  "name": "Test Agent",
  "status": "draft",
  ...
}
```

**Save the agent ID!** You'll need it for testing the playground.

---

## Test the Playground

### Via Frontend (Easy)

1. Open an agent's detail page
2. Click "Test" tab
3. Type a message: "Hello! Can you help me?"
4. Press Enter or click "Send"
5. Watch the response stream in real-time!

---

### Via WebSocket (Advanced)

**Using wscat:**
```bash
# Install wscat
npm install -g wscat

# Connect to playground
wscat -c "ws://localhost:8000/api/v1/playground/YOUR_AGENT_ID"

# Send a message
{"type": "user_message", "content": "Hello!"}

# Watch streaming response
```

**Expected events:**
```json
{"type": "agent_loaded", "agent_id": "..."}
{"type": "conversation_started", "conversation_id": "..."}
{"type": "content_delta", "delta": "Hello"}
{"type": "content_delta", "delta": "!"}
...
{"type": "message_complete", "message_id": "..."}
```

---

## Common Issues

### "Docker is not running"
**Solution:** Start Docker Desktop and wait for it to fully start.

### "Port 8000 already in use"
**Solution:**
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
poetry run uvicorn app.main:app --reload --port 8001
```

### "Port 3000 already in use"
**Solution:**
```bash
# Kill process using port 3000
lsof -ti:3000 | xargs kill -9

# Or Next.js will automatically suggest port 3001
```

### "Database connection error"
**Solution:**
```bash
# Check Docker services are running
docker-compose ps

# Restart services
docker-compose restart

# Check logs
docker-compose logs postgres
```

### "Module not found" errors
**Backend:**
```bash
cd backend
poetry install
```

**Frontend:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## Next Steps

Now that everything is running:

### 1. Add LLM API Keys (Optional but Recommended)

Edit `backend/.env` and add your API keys:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=AIzaSy-your-key-here
```

Restart backend to apply changes.

### 2. Explore the Platform

- ✅ Create multiple agents with different personalities
- ✅ Test agents in the playground
- ✅ Try different model configurations
- ✅ Explore the API documentation at http://localhost:8000/docs

### 3. Add Custom Tools (Phase 1 Ready)

The backend is ready for custom API tools! Check out:
- `/backend/app/tools/api_tool.py` - Custom API tool implementation
- `/backend/app/utils/openapi_parser.py` - OpenAPI discovery
- API endpoints for tool management (coming soon in UI)

### 4. Read the Documentation

- **TESTING_GUIDE.md** - Comprehensive testing instructions
- **IMPLEMENTATION_SUMMARY.md** - Full architecture overview
- **BREAKING_CHANGES.md** - Recent bug fixes
- **backend/SETUP.md** - Detailed backend setup

---

## Stop Services

### Stop Frontend
Press `Ctrl+C` in the frontend terminal

### Stop Backend
Press `Ctrl+C` in the backend terminal

### Stop Docker Services
```bash
cd backend
docker-compose down

# To also remove data volumes:
docker-compose down -v
```

---

## Development Workflow

### Backend Development
```bash
cd backend

# Run tests
poetry run pytest

# Run linting
poetry run ruff check .

# Format code
poetry run black .

# Type check
poetry run mypy .

# Create new migration
poetry run alembic revision -m "description"
```

### Frontend Development
```bash
cd frontend

# Run type check
npm run type-check

# Run linting
npm run lint

# Format code
npm run format

# Build for production
npm run build
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Next.js + React)                         │
│  http://localhost:3000                              │
│  - Agents List & Detail Pages                       │
│  - Real-time Playground (WebSocket)                 │
│  - SWR Data Fetching & Caching                      │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP/WebSocket
                  ↓
┌─────────────────────────────────────────────────────┐
│  Backend API (FastAPI)                              │
│  http://localhost:8000                              │
│  - Agent CRUD Endpoints                             │
│  - WebSocket Playground                             │
│  - Multi-Provider LLM Support                       │
│  - Tool Execution Engine                            │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ↓                   ↓
┌─────────────────┐  ┌──────────────────┐
│  PostgreSQL     │  │  Redis           │
│  (Database)     │  │  (Cache/Queue)   │
│  localhost:5432 │  │  localhost:6379  │
└─────────────────┘  └──────────────────┘
```

---

## API Endpoints Summary

### Agents
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents` - List agents
- `GET /api/v1/agents/:id` - Get agent
- `PATCH /api/v1/agents/:id` - Update agent
- `DELETE /api/v1/agents/:id` - Delete agent

### Playground
- `WS /api/v1/playground/:id` - WebSocket testing

### Future (Phase 2+)
- Tool management endpoints
- Integration endpoints
- Deployment endpoints

---

## Tech Stack

**Backend:**
- FastAPI 0.115+ (async web framework)
- PostgreSQL 16+ (database)
- SQLAlchemy 2.0 (ORM)
- Anthropic, OpenAI, Google (LLM providers)
- LangFuse (observability)
- Redis (cache/queue)

**Frontend:**
- Next.js 16.1 (React framework)
- React 19.2 (UI library)
- TypeScript 5 (type safety)
- Tailwind CSS 4 (styling)
- SWR 2.3 (data fetching)

**Infrastructure:**
- Docker Compose (local development)
- Alembic (database migrations)
- Poetry (Python dependencies)
- npm (Node.js dependencies)

---

## Support

**Documentation:**
- Full Testing Guide: `/TESTING_GUIDE.md`
- Implementation Summary: `/IMPLEMENTATION_SUMMARY.md`
- Breaking Changes: `/BREAKING_CHANGES.md`
- Backend Setup: `/backend/SETUP.md`

**Issues?**
Check Docker logs: `docker-compose logs -f`
Check backend logs: Look in the terminal running the backend
Check browser console: F12 in browser

---

**Congratulations!** 🎉

You now have a fully functional AI agent builder platform running locally!

**Happy Building!** 🚀
