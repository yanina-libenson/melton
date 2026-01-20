"""Authentication service for creator users."""

import re
import uuid
from datetime import datetime, timedelta

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Reserved subdomains that cannot be claimed
RESERVED_SUBDOMAINS = {
    "www",
    "api",
    "app",
    "admin",
    "mail",
    "ftp",
    "blog",
    "dev",
    "staging",
    "prod",
    "production",
    "test",
    "testing",
}


class AuthService:
    """Service for handling user authentication and authorization."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(user_id: uuid.UUID, organization_id: uuid.UUID) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user_id: The user's ID
            organization_id: The user's organization ID

        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        payload = {
            "sub": str(user_id),
            "user_id": str(user_id),
            "organization_id": str(organization_id),
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def verify_token(token: str) -> dict[str, uuid.UUID]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Dictionary with user_id and organization_id

        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id = uuid.UUID(payload["user_id"])
            organization_id = uuid.UUID(payload["organization_id"])
            return {"user_id": user_id, "organization_id": organization_id}
        except (JWTError, KeyError, ValueError) as e:
            raise JWTError(f"Invalid token: {e}")

    async def register_user(
        self, email: str, password: str, full_name: str | None = None
    ) -> User:
        """
        Register a new user.

        Args:
            email: User's email address
            password: Plain text password
            full_name: Optional full name

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        result = await self.session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Create new user
        user = User(
            email=email,
            password_hash=self.hash_password(password),
            full_name=full_name,
            # Generate a default organization_id for now (will be used in JWT)
            # In a real system, this would be properly managed
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def login(self, email: str, password: str) -> tuple[User, str]:
        """
        Authenticate a user and return a JWT token.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            Tuple of (User object, JWT token string)

        Raises:
            ValueError: If credentials are invalid or user is inactive
        """
        # Find user by email
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("User account is inactive")

        # Verify password
        if not self.verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        # Create JWT token (using user_id as organization_id for now)
        token = self.create_access_token(user.id, user.id)
        return user, token

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get a user by their ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def claim_subdomain(self, user_id: uuid.UUID, subdomain: str) -> User:
        """
        Claim a subdomain for a user.

        Args:
            user_id: The user's ID
            subdomain: Desired subdomain

        Returns:
            Updated User object

        Raises:
            ValueError: If subdomain is invalid or already taken
        """
        # Validate subdomain format and availability
        if not self.validate_subdomain(subdomain):
            raise ValueError(
                "Invalid subdomain format. Must be 3-20 characters, lowercase letters, numbers, and hyphens only."
            )

        if subdomain in RESERVED_SUBDOMAINS:
            raise ValueError("This subdomain is reserved and cannot be used")

        # Check if subdomain is already taken
        result = await self.session.execute(
            select(User).where(User.subdomain == subdomain)
        )
        if result.scalar_one_or_none():
            raise ValueError("Subdomain already taken")

        # Get user and update subdomain
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        user.subdomain = subdomain
        user.updated_at = datetime.utcnow()
        await self.session.flush()
        return user

    @staticmethod
    def validate_subdomain(subdomain: str) -> bool:
        """
        Validate subdomain format.

        Rules:
        - 3-20 characters
        - Lowercase letters, numbers, and hyphens only
        - Cannot start or end with a hyphen
        - Cannot contain consecutive hyphens

        Args:
            subdomain: Subdomain to validate

        Returns:
            True if valid, False otherwise
        """
        if not subdomain or len(subdomain) < 3 or len(subdomain) > 20:
            return False

        # Pattern: lowercase letters/numbers, can contain hyphens but not at start/end or consecutively
        pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
        if not re.match(pattern, subdomain):
            return False

        # Check for consecutive hyphens
        if "--" in subdomain:
            return False

        return True

    async def check_subdomain_availability(self, subdomain: str) -> bool:
        """
        Check if a subdomain is available.

        Args:
            subdomain: Subdomain to check

        Returns:
            True if available, False if taken or reserved
        """
        if not self.validate_subdomain(subdomain):
            return False

        if subdomain in RESERVED_SUBDOMAINS:
            return False

        result = await self.session.execute(
            select(User).where(User.subdomain == subdomain)
        )
        return result.scalar_one_or_none() is None

    async def get_user_by_subdomain(self, subdomain: str) -> User | None:
        """Get a user by their subdomain."""
        result = await self.session.execute(
            select(User).where(User.subdomain == subdomain)
        )
        return result.scalar_one_or_none()
