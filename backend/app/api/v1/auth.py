"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.dependencies import CurrentUser
from app.schemas.auth import (
    SubdomainCheckResponse,
    SubdomainClaim,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_database_session)]
) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """
    Register a new user.

    Args:
        user_data: User registration data
        auth_service: Auth service dependency

    Returns:
        JWT token for the newly created user

    Raises:
        HTTPException: If email is already registered
    """
    try:
        user = await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )
        # Create token using user.id as both user_id and organization_id
        token = AuthService.create_access_token(user.id, user.id)
        return TokenResponse(access_token=token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """
    Login and receive a JWT token.

    Args:
        credentials: User login credentials
        auth_service: Auth service dependency

    Returns:
        JWT token for authentication

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        user, token = await auth_service.login(
            email=credentials.email,
            password=credentials.password,
        )
        return TokenResponse(access_token=token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user
        auth_service: Auth service dependency

    Returns:
        User information

    Raises:
        HTTPException: If user not found
    """
    user = await auth_service.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


@router.post("/subdomain/claim", response_model=UserResponse)
async def claim_subdomain(
    subdomain_data: SubdomainClaim,
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """
    Claim a subdomain for the current user.

    Args:
        subdomain_data: Subdomain to claim
        current_user: Current authenticated user
        auth_service: Auth service dependency

    Returns:
        Updated user information

    Raises:
        HTTPException: If subdomain is invalid or already taken
    """
    try:
        user = await auth_service.claim_subdomain(
            user_id=current_user["user_id"],
            subdomain=subdomain_data.subdomain,
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/subdomain/check/{subdomain}", response_model=SubdomainCheckResponse)
async def check_subdomain_availability(
    subdomain: str,
    auth_service: AuthServiceDep,
) -> SubdomainCheckResponse:
    """
    Check if a subdomain is available.

    Args:
        subdomain: Subdomain to check
        auth_service: Auth service dependency

    Returns:
        Availability information
    """
    available = await auth_service.check_subdomain_availability(subdomain)

    if not available:
        # Determine reason
        if not AuthService.validate_subdomain(subdomain):
            reason = "Invalid subdomain format"
        elif subdomain in {"www", "api", "app", "admin", "mail"}:
            reason = "Subdomain is reserved"
        else:
            reason = "Subdomain is already taken"
    else:
        reason = None

    return SubdomainCheckResponse(
        subdomain=subdomain,
        available=available,
        reason=reason,
    )
