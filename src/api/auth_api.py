"""
Authentication API Endpoints
Registration, login, logout, password reset, profile management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from src.database import get_db
from src.auth import (
    create_user, authenticate_user, create_user_session,
    get_current_user, refresh_access_token, revoke_session,
    revoke_all_sessions, create_password_reset_token,
    verify_password_reset_token, reset_password,
    create_email_verification_token, verify_email_token
)
from src.models import User
from src.subscription_service import get_usage_limits

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()

# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        """
        Strong password enforcement:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter  
        - At least one number
        - At least one special character
        """
        errors = []
        
        if len(v) < 8:
            errors.append('at least 8 characters')
        if not any(c.isupper() for c in v):
            errors.append('at least one uppercase letter')
        if not any(c.islower() for c in v):
            errors.append('at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            errors.append('at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            errors.append('at least one special character (!@#$%^&*...)')
        
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 1 hour

class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    company: Optional[str]
    is_active: bool
    email_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProfileResponse(UserResponse):
    subscription: dict
    usage_limits: dict

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        """Strong password enforcement for password reset"""
        errors = []
        
        if len(v) < 8:
            errors.append('at least 8 characters')
        if not any(c.isupper() for c in v):
            errors.append('at least one uppercase letter')
        if not any(c.islower() for c in v):
            errors.append('at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            errors.append('at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            errors.append('at least one special character')
        
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    session_id: str

# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    Creates user + trial subscription automatically
    """
    try:
        # Create user (includes trial subscription)
        user = create_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            company=request.company
        )
        
        # Create session and tokens
        session = create_user_session(
            db=db,
            user=user,
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent")
        )
        
        # Send verification email (implement later)
        # verification_token = create_email_verification_token(user.user_id)
        # send_verification_email(user.email, verification_token)
        
        return TokenResponse(
            access_token=session.token,
            refresh_token=session.refresh_token
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with email and password
    Returns access token and refresh token
    """
    # Authenticate user
    user = authenticate_user(db, request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create session
    session = create_user_session(
        db=db,
        user=user,
        ip_address=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("user-agent")
    )
    
    return TokenResponse(
        access_token=session.token,
        refresh_token=session.refresh_token
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    new_access_token = refresh_access_token(db, request.refresh_token)
    
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token  # Keep same refresh token
    )

@router.post("/logout")
async def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout (revoke session)"""
    success = revoke_session(db, request.session_id, current_user.user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {"message": "Logged out successfully"}

@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout from all devices (revoke all sessions)"""
    revoke_all_sessions(db, current_user.user_id)
    
    return {"message": "Logged out from all devices"}

# ============================================================================
# Profile Management
# ============================================================================


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile and subscription info - FIXED"""
    # Get subscription
    from src.models import Subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    subscription_data = {
        "status": subscription.status.value if subscription else None,
        "plan": subscription.plan.value if subscription else None,
        "trial_end": subscription.trial_end.isoformat() if subscription and subscription.trial_end else None,
        "days_remaining": subscription.days_until_expiry() if subscription else 0
    }
    
    usage_limits = get_usage_limits(subscription) if subscription else {}
    
    # FIXED: Return with correct field names matching ProfileResponse
    return ProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        company=current_user.company,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        subscription=subscription_data,
        usage_limits=usage_limits
    )

@router.patch("/me")
async def update_profile(
    full_name: Optional[str] = None,
    company: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if full_name is not None:
        current_user.full_name = full_name
    
    if company is not None:
        current_user.company = company
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Profile updated successfully"}

# ============================================================================
# Password Management
# ============================================================================

@router.post("/password-reset-request")
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset
    Sends email with reset token (implement email sending)
    """
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    
    # Always return success (don't reveal if email exists)
    if user:
        token = create_password_reset_token(request.email)
        
        # Send email (implement later)
        # send_password_reset_email(user.email, token)
        # Token masked for security - only showing prefix
        print(f"[PASSWORD RESET] Token issued for {user.email}: {token[:8]}...***MASKED***")
    
    return {
        "message": "If the email exists, a password reset link has been sent"
    }

@router.post("/password-reset-confirm")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    # Verify token
    email = verify_password_reset_token(request.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Reset password
    success = reset_password(db, email, request.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Password reset successfully"}

# ============================================================================
# Email Verification
# ============================================================================

@router.post("/send-verification-email")
async def send_verification_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send email verification link"""
    if current_user.email_verified:
        return {"message": "Email already verified"}
    
    token = create_email_verification_token(current_user.user_id)
    
    # Send email (implement later)
    # send_verification_email_to_user(current_user.email, token)
    # Token masked for security - only showing prefix
    print(f"[EMAIL VERIFY] Token issued for {current_user.email}: {token[:8]}...***MASKED***")
    
    return {"message": "Verification email sent"}

@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify email with token"""
    success = verify_email_token(db, token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    return {"message": "Email verified successfully"}

# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    
    users = db.query(User).offset(offset).limit(limit).all()
    total = db.query(User).count()
    
    return {
        "users": [UserResponse.from_orm(user) for user in users],
        "total": total,
        "limit": limit,
        "offset": offset
    }
    
# ============================================================================
# Database Endpoints
# ============================================================================
@router.get("/health/database")
async def health_database(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        user_count = db.query(User).count()
        subscription_count = db.query(Subscription).count()
        
        return {
            "status": "healthy",  # Make sure this is "healthy"
            "connection": "active",
            "statistics": {
                "users": user_count,
                "subscriptions": subscription_count
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }