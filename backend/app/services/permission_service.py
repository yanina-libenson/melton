"""Permission service for agent sharing and collaboration."""

import secrets
import string
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_permission import AgentPermission
from app.models.user import User


class PermissionService:
    """Service for managing agent permissions and sharing."""

    # Permission types
    PERMISSION_USE = "use"
    PERMISSION_ADMIN = "admin"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def grant_permission(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        granted_by: uuid.UUID,
        permission_type: str = PERMISSION_USE,
    ) -> AgentPermission:
        """
        Grant permission to a user for an agent.

        Args:
            agent_id: ID of the agent
            user_id: ID of the user to grant permission to
            granted_by: ID of the user granting permission (must be admin)
            permission_type: Type of permission ("use" or "admin")

        Returns:
            The created AgentPermission

        Raises:
            ValueError: If permission_type is invalid or user doesn't have admin rights
        """
        if permission_type not in (self.PERMISSION_USE, self.PERMISSION_ADMIN):
            raise ValueError(f"Invalid permission type: {permission_type}")

        # Check if granter has admin permission
        if not await self.is_admin(agent_id, granted_by):
            raise ValueError("Only admins can grant permissions")

        # Check if permission already exists
        existing = await self.get_permission(agent_id, user_id)
        if existing:
            # Update existing permission
            existing.permission_type = permission_type
            existing.granted_by = granted_by
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        # Create new permission
        permission = AgentPermission(
            agent_id=agent_id,
            user_id=user_id,
            granted_by=granted_by,
            permission_type=permission_type,
        )
        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)
        return permission

    async def revoke_permission(
        self, agent_id: uuid.UUID, user_id: uuid.UUID, revoked_by: uuid.UUID
    ) -> bool:
        """
        Revoke permission from a user for an agent.

        Args:
            agent_id: ID of the agent
            user_id: ID of the user to revoke permission from
            revoked_by: ID of the user revoking permission (must be admin)

        Returns:
            True if permission was revoked, False if it didn't exist

        Raises:
            ValueError: If user doesn't have admin rights or trying to remove last admin
        """
        # Check if revoker has admin permission
        if not await self.is_admin(agent_id, revoked_by):
            raise ValueError("Only admins can revoke permissions")

        # Get the permission to revoke
        permission = await self.get_permission(agent_id, user_id)
        if not permission:
            return False

        # Prevent removing the last admin
        if permission.permission_type == self.PERMISSION_ADMIN:
            admin_count = await self.count_admins(agent_id)
            if admin_count <= 1:
                raise ValueError("Cannot remove the last admin")

        await self.session.delete(permission)
        await self.session.commit()
        return True

    async def get_permission(
        self, agent_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentPermission | None:
        """Get permission for a user on an agent."""
        result = await self.session.execute(
            select(AgentPermission).where(
                and_(
                    AgentPermission.agent_id == agent_id,
                    AgentPermission.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def has_permission(
        self, agent_id: uuid.UUID, user_id: uuid.UUID, required_type: str | None = None
    ) -> bool:
        """
        Check if a user has permission to access an agent.

        Args:
            agent_id: ID of the agent
            user_id: ID of the user
            required_type: Required permission type ("use" or "admin"). If None, any permission is OK.

        Returns:
            True if user has the required permission
        """
        permission = await self.get_permission(agent_id, user_id)
        if not permission:
            return False

        if required_type is None:
            return True

        # Admin permission includes use permission
        if required_type == self.PERMISSION_USE:
            return permission.permission_type in (self.PERMISSION_USE, self.PERMISSION_ADMIN)

        return permission.permission_type == required_type

    async def is_admin(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if a user has admin permission on an agent."""
        return await self.has_permission(agent_id, user_id, self.PERMISSION_ADMIN)

    async def count_admins(self, agent_id: uuid.UUID) -> int:
        """Count the number of admins for an agent."""
        result = await self.session.execute(
            select(AgentPermission).where(
                and_(
                    AgentPermission.agent_id == agent_id,
                    AgentPermission.permission_type == self.PERMISSION_ADMIN,
                )
            )
        )
        return len(result.scalars().all())

    async def list_agent_users(self, agent_id: uuid.UUID) -> list[dict]:
        """
        List all users with permissions on an agent.

        Returns list of dicts with user info and permission details.
        """
        result = await self.session.execute(
            select(AgentPermission, User)
            .join(User, AgentPermission.user_id == User.id)
            .where(AgentPermission.agent_id == agent_id)
            .order_by(
                # Sort admins first, then by granted_at
                AgentPermission.permission_type.desc(),
                AgentPermission.granted_at.desc(),
            )
        )

        users = []
        for permission, user in result:
            users.append({
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "permission_type": permission.permission_type,
                "granted_at": permission.granted_at.isoformat(),
                "granted_by": str(permission.granted_by),
            })

        return users

    async def list_user_agents(self, user_id: uuid.UUID, permission_type: str | None = None) -> list[Agent]:
        """
        List all agents a user has access to.

        Args:
            user_id: ID of the user
            permission_type: Filter by permission type ("use" or "admin"). If None, return all.

        Returns:
            List of agents
        """
        from sqlalchemy.orm import selectinload
        from app.models.integration import Integration

        query = (
            select(Agent)
            .join(AgentPermission, Agent.id == AgentPermission.agent_id)
            .where(AgentPermission.user_id == user_id)
            .options(
                selectinload(Agent.integrations).selectinload(Integration.tools)
            )
        )

        if permission_type:
            query = query.where(AgentPermission.permission_type == permission_type)

        query = query.order_by(Agent.updated_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def generate_share_code(self, agent_id: uuid.UUID, generated_by: uuid.UUID) -> str:
        """
        Generate a unique share code for an agent.

        Args:
            agent_id: ID of the agent
            generated_by: ID of the user generating the code (must be admin)

        Returns:
            The generated share code

        Raises:
            ValueError: If user doesn't have admin rights or agent not found
        """
        # Check if user has admin permission
        if not await self.is_admin(agent_id, generated_by):
            raise ValueError("Only admins can generate share codes")

        # Get the agent
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")

        # Generate a unique share code
        while True:
            # Generate 8-character alphanumeric code
            share_code = ''.join(
                secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8)
            )

            # Check if code is unique
            result = await self.session.execute(
                select(Agent).where(Agent.share_code == share_code)
            )
            if not result.scalar_one_or_none():
                break

        # Update agent with share code and mark as shareable
        agent.share_code = share_code
        agent.is_shareable = True
        await self.session.commit()
        await self.session.refresh(agent)

        return share_code

    async def accept_share_code(
        self, share_code: str, user_id: uuid.UUID, permission_type: str = PERMISSION_USE
    ) -> Agent:
        """
        Accept a share code and grant user permission to the agent.

        Args:
            share_code: The share code
            user_id: ID of the user accepting the share
            permission_type: Type of permission to grant (default: "use")

        Returns:
            The agent

        Raises:
            ValueError: If share code is invalid or expired
        """
        # Find agent by share code
        result = await self.session.execute(
            select(Agent).where(
                and_(
                    Agent.share_code == share_code,
                    Agent.is_shareable == True,
                )
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Invalid or expired share code")

        # Check if user already has permission
        existing = await self.get_permission(agent.id, user_id)
        if existing:
            return agent

        # Grant permission (use agent owner as granter)
        permission = AgentPermission(
            agent_id=agent.id,
            user_id=user_id,
            granted_by=agent.user_id,
            permission_type=permission_type,
        )
        self.session.add(permission)
        await self.session.commit()

        return agent

    async def revoke_share_code(self, agent_id: uuid.UUID, revoked_by: uuid.UUID) -> bool:
        """
        Revoke the share code for an agent.

        Args:
            agent_id: ID of the agent
            revoked_by: ID of the user revoking the code (must be admin)

        Returns:
            True if code was revoked

        Raises:
            ValueError: If user doesn't have admin rights or agent not found
        """
        # Check if user has admin permission
        if not await self.is_admin(agent_id, revoked_by):
            raise ValueError("Only admins can revoke share codes")

        # Get the agent
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")

        # Clear share code
        agent.share_code = None
        agent.is_shareable = False
        await self.session.commit()

        return True
