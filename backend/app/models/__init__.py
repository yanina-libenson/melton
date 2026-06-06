"""Database models.

Import every model here so that importing the package registers all mappers.
SQLAlchemy resolves string-based relationships (e.g. Agent -> "AgentPermission")
only against classes that have been imported; missing one breaks mapper
configuration wherever the full app isn't loaded (notably the test DB fixture).
"""

from app.models.agent import Agent
from app.models.agent_permission import AgentPermission
from app.models.conversation import Conversation
from app.models.deployment import Deployment
from app.models.encrypted_credential import EncryptedCredential
from app.models.execution_trace import ExecutionTrace
from app.models.integration import Integration
from app.models.llm_model import LLMModel
from app.models.message import Message
from app.models.tool import Tool
from app.models.user import User
from app.models.user_api_key import UserApiKey

__all__ = [
    "Agent",
    "AgentPermission",
    "Integration",
    "Tool",
    "EncryptedCredential",
    "Conversation",
    "Message",
    "Deployment",
    "ExecutionTrace",
    "LLMModel",
    "User",
    "UserApiKey",
]
