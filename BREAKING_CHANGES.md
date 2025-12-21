# Breaking Changes and Bug Fixes

## Overview
This document describes the breaking changes and bug fixes applied to resolve import errors and reserved name conflicts in the backend.

## Changes Made

### 1. Fixed FastAPI Import Error
**File:** `/backend/app/database.py`

**Issue:** Incorrect import `from fastapi import Depend` should be `Depends`

**Fix:**
```python
# Before
from fastapi import Depend
DatabaseSession = Annotated[AsyncSession, Depend(get_database_session)]

# After
from fastapi import Depends
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
```

**Impact:** None - this was a typo that prevented imports.

---

### 2. Fixed SQLAlchemy Reserved Name: `metadata`
**Files:**
- `/backend/app/models/conversation.py`
- `/backend/app/models/message.py`

**Issue:** `metadata` is a reserved attribute name in SQLAlchemy's Declarative API. Using it as a column name causes:
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

**Fix:**
```python
# Before (Conversation model)
metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

# After
conversation_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

# Before (Message model)
metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

# After
message_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
```

**Impact:**
- **Database Schema Change Required**
- Column name changed from `metadata` to `conversation_metadata` and `message_metadata`
- Alembic migration needed to rename columns
- Any code accessing `conversation.metadata` or `message.metadata` must update to `conversation.conversation_metadata` or `message.message_metadata`

**Migration SQL:**
```sql
-- For conversations table
ALTER TABLE conversations RENAME COLUMN metadata TO conversation_metadata;

-- For messages table
ALTER TABLE messages RENAME COLUMN metadata TO message_metadata;
```

---

### 3. Fixed Pydantic Reserved Name: `model_config`
**File:** `/backend/app/schemas/agent.py`

**Issue:** `model_config` is a reserved name in Pydantic v2 for model configuration. Using it as a field name causes:
```
pydantic.errors.PydanticUserError: `model_config` cannot be used as a model field name.
```

**Fix:**
```python
# Before
class AgentCreate(BaseModel):
    name: str
    instructions: str
    status: Literal["active", "inactive", "draft"]
    model_config: ModelConfig  # ❌ Reserved name

# After
class AgentCreate(BaseModel):
    name: str
    instructions: str
    status: Literal["active", "inactive", "draft"]
    llm_config: ModelConfig = Field(..., alias="model_config")  # ✅ Internal name + alias

    model_config = {"populate_by_name": True}  # Allow both names in JSON
```

**Impact:**
- **API Contract Preserved**: JSON still uses `model_config` (via alias)
- Internal Pydantic attribute renamed to `llm_config`
- Updated `AgentCreate`, `AgentUpdate`, and `AgentResponse` schemas
- Updated `AgentService.create_agent()` to use `agent_data.llm_config`

**API Examples (No Change from Client Perspective):**
```json
{
  "name": "Customer Support",
  "instructions": "...",
  "status": "draft",
  "model_config": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250929",
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

---

### 4. Poetry Configuration
**File:** `/backend/pyproject.toml`

**Issue:** Poetry attempted to build a package but no package structure exists.

**Fix:**
```toml
[tool.poetry]
name = "melton-backend"
version = "0.1.0"
description = "Production Python API for Dr. Melton Agent Builder"
authors = ["Dr. Melton Team"]
readme = "README.md"
package-mode = false  # ← Added this line
```

**Impact:** None - allows `poetry install` to work without package structure.

---

## Testing the Fixes

### 1. Verify Backend Imports
```bash
cd backend
poetry run python -c "import app.main; print('✅ Backend imports successfully')"
```

**Expected Output:**
```
✅ Backend imports successfully
```

You may see a deprecation warning about `google.generativeai` - this is expected and can be addressed later.

---

### 2. Update Database Schema

**Create a new Alembic migration:**
```bash
cd backend
poetry run alembic revision -m "Rename metadata columns to avoid reserved names"
```

**Edit the generated migration file** to include:
```python
"""Rename metadata columns to avoid reserved names

Revision ID: xxx
"""

from alembic import op

def upgrade() -> None:
    # Rename metadata columns
    op.alter_column('conversations', 'metadata', new_column_name='conversation_metadata')
    op.alter_column('messages', 'metadata', new_column_name='message_metadata')

def downgrade() -> None:
    # Revert column names
    op.alter_column('conversations', 'conversation_metadata', new_column_name='metadata')
    op.alter_column('messages', 'message_metadata', new_column_name='metadata')
```

**Run the migration:**
```bash
poetry run alembic upgrade head
```

---

### 3. Start Services

**Start Docker services:**
```bash
cd backend
docker-compose up -d
```

**Verify services are running:**
```bash
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE    STATUS
melton-postgres     "docker-entrypoint.s…"   postgres   Up
melton-redis        "docker-entrypoint.s…"   redis      Up
```

---

### 4. Start Backend Server

**Option 1: Development mode with auto-reload**
```bash
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Option 2: Production mode**
```bash
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Verify server is running:**
```bash
curl http://localhost:8000/
```

Expected: JSON response with API info.

**Check API docs:**
Open http://localhost:8000/docs in browser - should see Swagger UI.

---

### 5. Test Agent CRUD

**Create an agent:**
```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Agent",
    "instructions": "You are a helpful test agent for development.",
    "status": "draft",
    "model_config": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250929",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }'
```

Expected: 201 Created with agent JSON (including `id`, `user_id`, `organization_id`, etc.)

**List agents:**
```bash
curl http://localhost:8000/api/v1/agents
```

Expected: Array of agents.

**Get specific agent:**
```bash
curl http://localhost:8000/api/v1/agents/{agent_id}
```

**Update agent:**
```bash
curl -X PATCH http://localhost:8000/api/v1/agents/{agent_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Test Agent",
    "status": "active"
  }'
```

**Delete agent:**
```bash
curl -X DELETE http://localhost:8000/api/v1/agents/{agent_id}
```

---

### 6. Test WebSocket Playground

**Using wscat:**
```bash
npm install -g wscat
wscat -c ws://localhost:8000/api/v1/playground/{agent_id}
```

**Send a message:**
```json
{"type": "user_message", "content": "Hello!"}
```

**Expected response events:**
```json
{"type": "agent_loaded", "agent_id": "..."}
{"type": "conversation_started", "conversation_id": "..."}
{"type": "content_delta", "delta": "Hello"}
{"type": "content_delta", "delta": "!"}
{"type": "message_complete", "message_id": "..."}
```

---

### 7. Test Frontend Integration

**Start frontend:**
```bash
cd frontend
npm run dev
```

**Navigate to:**
- http://localhost:3000/agents - Should load agents from API
- Create a new agent - Should call POST /api/v1/agents
- Click on an agent - Should load via GET /api/v1/agents/:id
- Try the Test tab - Should connect WebSocket and allow chatting

---

## Code Changes Required

### If You're Using `metadata` Fields Directly

**Before:**
```python
# In any service or business logic
conversation.metadata["key"] = "value"
message.metadata["timestamp"] = datetime.now()
```

**After:**
```python
# Update to new column names
conversation.conversation_metadata["key"] = "value"
message.message_metadata["timestamp"] = datetime.now()
```

---

### If You're Accessing `model_config` in Pydantic Schemas

**No changes needed in API clients** - the JSON field name remains `model_config`.

**Internal code changes:**
```python
# Before (in services)
agent_data.model_config.model_dump()

# After
agent_data.llm_config.model_dump()
```

---

## Rollback Instructions

If you need to rollback these changes:

### 1. Rollback Database Migration
```bash
poetry run alembic downgrade -1
```

### 2. Revert Code Changes
```bash
git revert <commit-hash>
```

### 3. Restore Original Column Names
The downgrade migration will automatically restore:
- `conversation_metadata` → `metadata`
- `message_metadata` → `metadata`

---

## Environment Setup

**Required environment variables** (`.env` file):
```bash
# Database
DATABASE_URL=postgresql+asyncpg://melton:melton@localhost:5432/melton

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-32-character-encryption-key

# LLM Providers (optional for testing)
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GOOGLE_API_KEY=AIzaSyxxx

# LangFuse (optional)
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# Debug
DEBUG=True
```

---

## Summary

✅ **Fixed 4 critical import/naming errors**
✅ **Preserved API contracts** (JSON field names unchanged)
✅ **Minimal code changes required** (mostly internal refactoring)
✅ **Database migration provided** for schema changes
✅ **Comprehensive testing instructions** included

The backend should now import successfully and be ready for testing!
