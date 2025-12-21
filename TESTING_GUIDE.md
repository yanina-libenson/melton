# Complete Testing Guide - Dr. Melton Agent Builder

## Overview
This guide provides step-by-step instructions for testing the complete Dr. Melton platform, from backend API to frontend integration.

## Prerequisites

### System Requirements
- Python 3.11+ (backend)
- Node.js 18+ (frontend)
- Docker & Docker Compose (database services)
- curl or httpie (API testing)
- wscat (WebSocket testing, optional)

### Environment Setup

**Create `.env` file in `/backend` directory:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://melton:melton@localhost:5432/melton

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=dev-secret-key-change-in-production
ENCRYPTION_KEY=dev-encryption-key-32-chars!!

# LLM Providers (add your real keys)
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=AIzaSy-your-key-here

# LangFuse (optional)
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# Debug
DEBUG=True
```

**Frontend environment** (`.env.local` in `/frontend` directory):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Phase 1: Backend Setup

### Step 1: Install Dependencies

```bash
cd backend
poetry install
```

**Verify installation:**
```bash
poetry run python -c "import app.main; print('✅ Backend imports successfully')"
```

Expected output:
```
✅ Backend imports successfully
```

---

### Step 2: Start Database Services

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
NAME              COMMAND                  SERVICE    STATUS
melton-postgres   "docker-entrypoint.s…"   postgres   Up
melton-redis      "docker-entrypoint.s…"   redis      Up
```

**Check PostgreSQL connection:**
```bash
docker exec melton-postgres psql -U melton -d melton -c "SELECT version();"
```

**Check Redis connection:**
```bash
docker exec melton-redis redis-cli ping
```
Expected: `PONG`

---

### Step 3: Run Database Migrations

```bash
poetry run alembic upgrade head
```

**Verify tables were created:**
```bash
docker exec melton-postgres psql -U melton -d melton -c "\dt"
```

Expected output should list 8 tables:
- `agents`
- `integrations`
- `tools`
- `encrypted_credentials`
- `conversations`
- `messages`
- `deployments`
- `execution_traces`

---

### Step 4: Start Backend Server

**Terminal 1 - Start backend:**
```bash
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify server is running:**
```bash
curl http://localhost:8000/
```

Expected: JSON response with API information.

**Access API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Phase 2: Backend API Testing

### Test 1: Health Check

```bash
curl http://localhost:8000/
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

### Test 2: Create Agent

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Support Agent",
    "instructions": "You are a helpful customer support agent. Be polite and professional.",
    "status": "draft",
    "model_config": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250929",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }'
```

Expected response:
```json
{
  "id": "uuid-here",
  "user_id": "uuid-here",
  "organization_id": "uuid-here",
  "name": "Test Support Agent",
  "instructions": "You are a helpful customer support agent...",
  "status": "draft",
  "model_config": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250929",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "created_at": "2025-12-20T...",
  "updated_at": "2025-12-20T...",
  "integrations": []
}
```

**Save the agent ID for next steps!**

---

### Test 3: List Agents

```bash
curl http://localhost:8000/api/v1/agents
```

Expected: Array of agents (should include the one you just created).

---

### Test 4: Get Single Agent

```bash
curl http://localhost:8000/api/v1/agents/{agent_id}
```

Replace `{agent_id}` with the ID from Test 2.

---

### Test 5: Update Agent

```bash
curl -X PATCH http://localhost:8000/api/v1/agents/{agent_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Support Agent",
    "status": "active"
  }'
```

Expected: Updated agent object with new name and status.

---

### Test 6: WebSocket Playground

**Option 1: Using wscat (recommended)**

Install wscat:
```bash
npm install -g wscat
```

Connect to playground:
```bash
wscat -c "ws://localhost:8000/api/v1/playground/{agent_id}"
```

Send a message:
```json
{"type": "user_message", "content": "Hello! Can you help me?"}
```

Expected response (streamed):
```json
{"type": "agent_loaded", "agent_id": "..."}
{"type": "conversation_started", "conversation_id": "..."}
{"type": "content_delta", "delta": "Hello"}
{"type": "content_delta", "delta": "!"}
{"type": "content_delta", "delta": " Of"}
{"type": "content_delta", "delta": " course"}
...
{"type": "message_complete", "message_id": "..."}
```

**Option 2: Using JavaScript in browser console**

Open browser console and run:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/playground/YOUR_AGENT_ID');

ws.onopen = () => {
  console.log('✅ Connected');
  ws.send(JSON.stringify({
    type: 'user_message',
    content: 'Hello!'
  }));
};

ws.onmessage = (event) => {
  console.log('📨', JSON.parse(event.data));
};

ws.onerror = (error) => {
  console.error('❌ Error:', error);
};
```

---

### Test 7: Delete Agent (Optional)

```bash
curl -X DELETE http://localhost:8000/api/v1/agents/{agent_id}
```

Expected: 204 No Content

---

## Phase 3: Frontend Testing

### Step 1: Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

### Step 2: Start Frontend Server

**Terminal 2 - Start frontend:**
```bash
cd frontend
npm run dev
```

Expected output:
```
  ▲ Next.js 16.1.0
  - Local:        http://localhost:3000
  - Network:      http://192.168.1.x:3000

 ✓ Starting...
 ✓ Ready in 2.3s
```

---

### Step 3: Test Agent List Page

**Navigate to:** http://localhost:3000/agents

**Verify:**
- ✅ Page loads without errors
- ✅ Loading state appears briefly
- ✅ Agents from backend API are displayed
- ✅ Agent count is correct
- ✅ Each agent card shows name, status, tool count, and last updated

**Check browser console:**
- No errors
- Network tab shows GET request to `http://localhost:8000/api/v1/agents`

---

### Step 4: Test Agent Creation

**Click "New Agent" button**

**Verify:**
- ✅ Navigate to `/agents/new`
- ✅ Form shows with empty fields
- ✅ Default instructions are pre-filled

**Fill out form:**
- Name: "Frontend Test Agent"
- Instructions: "You are a test agent created from the frontend interface."

**Click "Save"**

**Verify:**
- ✅ Success toast appears: "Agent created successfully"
- ✅ Redirects to `/agents` page
- ✅ New agent appears in the list

**Check browser console:**
- Network tab shows POST request to `http://localhost:8000/api/v1/agents`
- Request payload includes `model_config` with default values

---

### Step 5: Test Agent Detail Page

**Click on an existing agent**

**Verify:**
- ✅ Navigate to `/agents/{id}`
- ✅ Loading state appears briefly
- ✅ Agent name and instructions load from API
- ✅ "Configure" tab is active by default
- ✅ All fields are populated correctly

---

### Step 6: Test Agent Update

**On agent detail page:**
- Change name to "Updated from Frontend"
- Click "Save"

**Verify:**
- ✅ Success toast appears: "Agent updated successfully"
- ✅ Page doesn't redirect (stays on detail page)
- ✅ Changes persist when page is refreshed

**Check browser console:**
- Network tab shows PATCH request to `http://localhost:8000/api/v1/agents/{id}`

---

### Step 7: Test Playground Tab

**On agent detail page:**
- Click "Test" tab

**Verify:**
- ✅ Tab switches to playground view
- ✅ Welcome message appears in chat
- ✅ Input field is enabled
- ✅ Send button is visible

**Type a message and send:**
- Message: "Hello, can you help me?"

**Verify:**
- ✅ User message appears immediately in chat (blue bubble on right)
- ✅ Typing indicator appears (three animated dots)
- ✅ Agent response streams in character by character (gray bubble on left)
- ✅ Final message is complete and readable

**Check browser console:**
- WebSocket connection established: `ws://localhost:8000/api/v1/playground/{id}`
- Events logged: `agent_loaded`, `conversation_started`, `content_delta`, `message_complete`
- No connection errors

**Test multiple messages:**
- Send 2-3 more messages
- Verify conversation history builds up
- Verify scrolling works correctly

---

## Phase 4: Integration Testing

### Test Scenario 1: Complete Agent Lifecycle

1. **Create agent via frontend** ✓
2. **Verify in database:**
   ```bash
   docker exec melton-postgres psql -U melton -d melton -c \
     "SELECT name, status, model_config FROM agents ORDER BY created_at DESC LIMIT 1;"
   ```
3. **Update agent via frontend** ✓
4. **Test in playground** ✓
5. **Verify conversation is saved:**
   ```bash
   docker exec melton-postgres psql -U melton -d melton -c \
     "SELECT COUNT(*) FROM conversations;"
   ```
6. **Delete agent via API**
7. **Verify it disappears from frontend** (refresh `/agents` page)

---

### Test Scenario 2: Error Handling

**Test 1: Create agent with invalid data**
- Try creating agent with name < 1 character
- Verify: Client-side validation prevents submission

**Test 2: Create agent with instructions too short**
- Try creating agent with instructions < 20 characters
- Verify: Error toast appears

**Test 3: Disconnect backend**
- Stop backend server: `Ctrl+C` in Terminal 1
- Refresh frontend `/agents` page
- Verify: Error state shows with retry button
- Restart backend and click "Retry"
- Verify: Agents load successfully

**Test 4: WebSocket disconnect**
- Open playground
- Stop backend server
- Try sending a message
- Verify: Error toast appears: "Not connected"

---

### Test Scenario 3: Concurrent Users (Optional)

**Open two browser windows:**
1. Window A: http://localhost:3000/agents/{agent-id} - Playground tab
2. Window B: http://localhost:3000/agents/{same-agent-id} - Playground tab

**In Window A:** Send message "Hello from Window A"
**In Window B:** Send message "Hello from Window B"

**Verify:**
- Each window maintains its own WebSocket connection
- Messages don't interfere with each other
- Both conversations are saved separately in database

---

## Phase 5: Performance Testing

### Test Backend Performance

**Create 10 agents in parallel:**
```bash
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/agents \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"Load Test Agent $i\",
      \"instructions\": \"You are load test agent number $i.\",
      \"status\": \"draft\",
      \"model_config\": {
        \"provider\": \"anthropic\",
        \"model\": \"claude-sonnet-4-20250929\",
        \"temperature\": 0.7,
        \"max_tokens\": 4096
      }
    }" &
done
wait
```

**Verify:**
- All 10 agents created successfully
- Response times < 500ms
- No database errors in backend logs

---

### Test Frontend Performance

**Check page load time:**
1. Open Chrome DevTools → Performance tab
2. Record page load of `/agents`
3. Verify: Total load time < 2 seconds
4. Check Network tab: API call completes < 200ms

**Check memory leaks:**
1. Open Chrome DevTools → Memory tab
2. Take heap snapshot
3. Navigate between `/agents` and `/agents/{id}` 10 times
4. Take another heap snapshot
5. Compare: Memory usage shouldn't grow significantly

---

## Phase 6: Cleanup

### Stop Services

**Stop frontend:**
- Terminal 2: `Ctrl+C`

**Stop backend:**
- Terminal 1: `Ctrl+C`

**Stop Docker services:**
```bash
cd backend
docker-compose down
```

**Remove all data (optional):**
```bash
docker-compose down -v  # Removes volumes (deletes database data)
```

---

## Troubleshooting

### Backend won't start

**Check Python version:**
```bash
python --version  # Should be 3.11+
```

**Check dependencies:**
```bash
poetry install
```

**Check environment variables:**
```bash
cat .env  # Verify all required vars are set
```

---

### Database connection error

**Check Docker services:**
```bash
docker-compose ps
docker-compose logs postgres
```

**Verify DATABASE_URL:**
```
DATABASE_URL=postgresql+asyncpg://melton:melton@localhost:5432/melton
```

**Test connection:**
```bash
docker exec melton-postgres psql -U melton -d melton -c "SELECT 1;"
```

---

### Frontend can't connect to backend

**Check CORS settings:**
Backend should allow `http://localhost:3000` in CORS origins.

**Check API URL:**
```bash
cat .env.local  # Should have NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Check browser console:**
Look for CORS errors or network failures.

---

### WebSocket connection fails

**Check WebSocket URL:**
Should be `ws://localhost:8000` not `wss://` (no SSL in development).

**Check backend logs:**
Look for WebSocket connection errors.

**Test with wscat:**
```bash
wscat -c "ws://localhost:8000/api/v1/playground/{agent_id}"
```

---

## Success Criteria

✅ **Backend:**
- [x] All imports work without errors
- [x] Database migrations run successfully
- [x] All CRUD endpoints work (Create, Read, Update, Delete)
- [x] WebSocket playground accepts connections
- [x] LLM responses stream correctly
- [x] No errors in backend logs

✅ **Frontend:**
- [x] Agents list loads from API
- [x] Agent creation works
- [x] Agent updates persist
- [x] Playground WebSocket connects
- [x] Messages stream in real-time
- [x] Error states display correctly
- [x] No console errors

✅ **Integration:**
- [x] Frontend → Backend communication works
- [x] WebSocket streams work end-to-end
- [x] Database persistence works
- [x] Authentication placeholders in place
- [x] All Phase 1 requirements met

---

## Next Steps

After successful testing:

1. **Add LLM API Keys** - Configure real API keys for Anthropic, OpenAI, Google
2. **Test Custom API Tools** - Create integrations and test tool calling
3. **Implement Authentication** - Add JWT authentication for production
4. **Add Tool Configuration UI** - Build tool management pages
5. **Implement Deployment Channels** - Add Widget, WhatsApp, Email integrations
6. **Performance Optimization** - Add caching, rate limiting
7. **Production Deployment** - Deploy to Render or similar platform

---

## Documentation

- **Setup Guide:** `/backend/SETUP.md`
- **Breaking Changes:** `/BREAKING_CHANGES.md`
- **Frontend Integration:** `/FRONTEND_INTEGRATION.md`
- **API Documentation:** http://localhost:8000/docs (when backend is running)

---

## Support

If you encounter issues not covered in this guide:
1. Check backend logs: `poetry run uvicorn app.main:app --reload --log-level debug`
2. Check Docker logs: `docker-compose logs -f`
3. Review BREAKING_CHANGES.md for recent changes
4. Check GitHub issues for known problems

---

**Happy Testing! 🚀**
