"""
Event bus for real-time pub/sub of agent execution events.
Uses asyncio.Queue for in-memory event streaming.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuditEvent:
    """Event structure for audit streaming."""

    event_type: str
    conversation_id: str
    agent_id: str
    agent_name: str | None
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event": self.event_type,
            "data": {
                "conversation_id": self.conversation_id,
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "timestamp": self.timestamp,
                **self.data,
            },
        }


class EventBus:
    """
    In-memory pub/sub event bus for streaming audit events.

    Note: This is a single-instance solution. For multi-instance deployment,
    you would need Redis pub/sub or similar.
    """

    def __init__(self):
        # Map of subscriber_id -> (queue, agent_ids set)
        self._subscribers: dict[str, tuple[asyncio.Queue[AuditEvent], set[str]]] = {}

    async def subscribe(self, agent_ids: set[str]) -> tuple[str, asyncio.Queue[AuditEvent]]:
        """
        Subscribe to events for the given agent IDs.

        Args:
            agent_ids: Set of agent IDs the subscriber can access

        Returns:
            Tuple of (subscriber_id, queue)
        """
        subscriber_id = str(uuid.uuid4())
        queue: asyncio.Queue[AuditEvent] = asyncio.Queue()
        self._subscribers[subscriber_id] = (queue, agent_ids)
        return subscriber_id, queue

    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove a subscriber."""
        if subscriber_id in self._subscribers:
            del self._subscribers[subscriber_id]

    async def publish(self, event: AuditEvent) -> None:
        """
        Publish an event to all subscribers who have access to the event's agent.

        Events are only sent to subscribers who have the event's agent_id
        in their accessible agent_ids set.
        """
        for subscriber_id, (queue, agent_ids) in list(self._subscribers.items()):
            # Only publish if subscriber has access to this agent
            if event.agent_id in agent_ids:
                try:
                    # Use put_nowait to avoid blocking
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # If queue is full, skip this event for this subscriber
                    pass

    def create_event(
        self,
        event_type: str,
        conversation_id: str,
        agent_id: str,
        agent_name: str | None = None,
        **data: Any,
    ) -> AuditEvent:
        """Helper to create an AuditEvent with current timestamp."""
        return AuditEvent(
            event_type=event_type,
            conversation_id=str(conversation_id),
            agent_id=str(agent_id),
            agent_name=agent_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            data=data,
        )


# Global event bus instance
event_bus = EventBus()
