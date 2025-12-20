# Coding Principles for This Project

## Core Mission
Empower non-technical people to build powerful AI agents through exceptional UX.

## Code Standards

### 1. Clean, Readable Code
- Code should read like prose
- If you need a comment to explain what code does, rewrite the code
- Comments only for WHY, never for WHAT

### 2. Small & Simple
- **Methods**: Do one thing, 10-20 lines max
- **Classes**: Single responsibility, 100-200 lines max
- **Files**: Focused purpose, easy to understand at a glance

### 3. Human-Readable Names
- Variables: `agentConfiguration` not `config` or `ac`
- Methods: `saveAgentToDatabase()` not `save()` or `persist()`
- Classes: `AgentConfigurationForm` not `Form` or `ACF`
- Booleans: `isAgentActive` not `active` or `status`

### 4. Object-Oriented
- Encapsulate related logic
- Clear class boundaries
- Favor composition over inheritance
- No god objects

### 5. No Excessive Comments
```python
# BAD
# Get the user's agent
agent = db.query(Agent).filter(Agent.user_id == user.id).first()

# GOOD
def get_user_agent(user_id: str) -> Agent:
    return db.query(Agent).filter(Agent.user_id == user_id).first()
```

### 6. TypeScript/Python Best Practices
- Use types everywhere (no `any` in TS, proper type hints in Python)
- Destructure for clarity
- Early returns to reduce nesting
- Explicit is better than clever

## Examples

### Good Method Design
```typescript
// GOOD: Clear purpose, one responsibility, human-readable
async function saveAgentConfiguration(agentId: string, prompt: string, tools: Tool[]) {
  validatePrompt(prompt)
  validateTools(tools)

  const agent = await updateAgent(agentId, { prompt, tools })
  await logAgentUpdate(agent)

  return agent
}
```

```typescript
// BAD: Too much happening, unclear, poor naming
async function save(id: string, p: string, t: any[]) {
  // validate
  if (!p || p.length < 20) throw new Error("bad prompt")

  // update db
  const a = await db.agent.update({
    where: { id },
    data: { prompt: p, tools: t }
  })

  // log it
  console.log("updated", id)

  return a
}
```

### Good Class Design
```python
# GOOD: Single responsibility, clear methods
class AgentExecutor:
    def __init__(self, agent_config: AgentConfig):
        self.agent_config = agent_config
        self.graph = self._build_graph()

    def execute_conversation(self, user_message: str) -> AgentResponse:
        validated_message = self._validate_message(user_message)
        response = self._run_graph(validated_message)
        return self._format_response(response)

    def _build_graph(self) -> CompiledGraph:
        # Build LangGraph
        pass

    def _validate_message(self, message: str) -> str:
        # Validation logic
        pass
```

```python
# BAD: Does everything, unclear responsibility
class Agent:
    def __init__(self, config):
        self.config = config
        self.db = Database()
        self.graph = self.build_graph()

    def run(self, msg):
        # validate
        if not msg: return None

        # save to db
        self.db.save(msg)

        # run
        result = self.graph.invoke(msg)

        # format
        return {"response": result, "status": "ok"}
```

## UI/UX Principles

### 1. No Technical Jargon
- "System Prompt" → "Agent Instructions"
- "API Endpoint" → "Web Address" (or keep it if clear in context)
- "Parameters" → "Information needed"

### 2. Clear Error Messages
```
❌ BAD: "Validation error: field required"
✅ GOOD: "Agent name is required"

❌ BAD: "API returned 404"
✅ GOOD: "We couldn't find this web address. Please check the URL."
```

### 3. Obvious Actions
- Button text: "Save Agent" not "Submit" or "OK"
- Link text: "Test Your Agent" not "Click here"
- Form labels: "What should your agent say when greeting customers?"

### 4. Progressive Disclosure
- Show simple options first
- Advanced features behind "Advanced" toggle
- Don't overwhelm with all options at once

## Remember
Every line of code should make it easier for a non-technical person to build a powerful agent. If it's confusing to us, it will be impossible for them.
