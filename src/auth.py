"""
Authentication Service
Handles user registration, login, JWT tokens, and password management
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import secrets
import os

from src.models import User, Session as DBSession, Subscription
from src.database import get_db

# ============================================================================
# Configuration
# ============================================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing - use bcrypt with manual truncation to avoid passlib version issues
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token authentication
security = HTTPBearer()

# ============================================================================
# Password Management
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password for storage - manually handles bcrypt 72-byte limit"""
    import bcrypt
    # Truncate password to 72 bytes before hashing (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    import bcrypt
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

# ============================================================================
# JWT Token Management
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str) -> Optional[dict]:
    """Generic token verification helper"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            return None
            
        return payload
    except JWTError:
        return None
# ============================================================================
# User Authentication
# ============================================================================

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user by email and password"""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        return None
    
    return user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    Usage: def endpoint(current_user: User = Depends(get_current_user))
    """
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token, token_type="access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    return user

def get_current_active_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Subscription:
    """
    Dependency to get current user's active subscription
    Raises 403 if subscription is not active
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No subscription found"
        )
    
    if not subscription.is_active_subscription():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Subscription {subscription.status.value}. Please upgrade to continue."
        )
    
    return subscription

def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require superuser access
    Usage: def admin_endpoint(user: User = Depends(require_superuser))
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user

# ============================================================================
# Session Management
# ============================================================================

def create_user_session(
    db: Session,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> DBSession:
    """Create a new user session"""
    # Generate tokens
    access_token = create_access_token(data={"sub": user.user_id})
    refresh_token = create_refresh_token(data={"sub": user.user_id})
    
    # Create session record
    session = DBSession(
        session_id=secrets.token_urlsafe(32),
        user_id=user.user_id,
        token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=ip_address,
        user_agent=user_agent,
        last_activity=datetime.now(timezone.utc)
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

def refresh_access_token(db: Session, refresh_token: str) -> Optional[str]:
    """Refresh access token using refresh token"""
    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")
    
    if payload is None:
        return None
    
    user_id = payload.get("sub")
    
    # Check if session exists and is valid
    session = db.query(DBSession).filter(
        DBSession.refresh_token == refresh_token,
        DBSession.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not session:
        return None
    
    # Create new access token
    new_access_token = create_access_token(data={"sub": user_id})
    
    # Update session
    session.token = new_access_token
    session.last_activity = datetime.now(timezone.utc)
    db.commit()
    
    return new_access_token

def revoke_session(db: Session, session_id: str, user_id: str) -> bool:
    """Revoke a user session (logout)"""
    session = db.query(DBSession).filter(
        DBSession.session_id == session_id,
        DBSession.user_id == user_id
    ).first()
    
    if session:
        db.delete(session)
        db.commit()
        return True
    
    return False

def revoke_all_sessions(db: Session, user_id: str):
    """Revoke all sessions for a user (logout everywhere)"""
    db.query(DBSession).filter(DBSession.user_id == user_id).delete()
    db.commit()

def cleanup_expired_sessions(db: Session):
    """Remove expired sessions (run periodically)"""
    db.query(DBSession).filter(
        DBSession.expires_at < datetime.now(timezone.utc)
    ).delete()
    db.commit()

# ============================================================================
# User Registration
# ============================================================================

def create_user(
    db,
    email: str,
    password: str,
    full_name = None,
    company = None
):
    """Create a new user account"""
    from src.models import User
    import secrets
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate user ID
    user_id = f"usr_{secrets.token_urlsafe(16)}"
    
    # Create user
    user = User(
        user_id=user_id,
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        company=company,
        is_active=True,
        email_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Import here to avoid circular dependency
    from src.subscription_service import create_trial_subscription
    create_trial_subscription(db, user)
    
    return user

# ============================================================================
# Password Reset
# ============================================================================

def create_password_reset_token(email: str) -> str:
    """Create a password reset token (send via email)"""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {"sub": email, "exp": expire, "type": "password_reset"}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify password reset token and return email"""
    payload = verify_token(token, token_type="password_reset")
    if payload:
        return payload.get("sub")
    return None

def reset_password(db, token: str, new_password: str) -> bool:
    """Reset user password using verified token"""
    from src.models import User
    
    # Verify token and get email
    email = verify_password_reset_token(token)
    
    if not email:
        return False
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return False
    
    user.hashed_password = hash_password(new_password)
    db.commit()
    
    # Revoke all sessions for security
    revoke_all_sessions(db, user.user_id)
    
    return True

# ============================================================================
# Email Verification
# ============================================================================

def create_email_verification_token(user_id: str) -> str:
    """Create email verification token"""
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = {"sub": user_id, "exp": expire, "type": "email_verify"}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_email_token(db: Session, token: str) -> bool:
    """Verify email verification token"""
    payload = verify_token(token, token_type="email_verify")
    
    if not payload:
        return False
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        return False
    
    user.email_verified = True
    db.commit()
    
    return True

# ============================================================================
# Session Management
# ============================================================================

def revoke_all_sessions(db: Session, user_id: str):
    """Revoke all sessions for a specific user"""
    try:
        db.query(DBSession).filter(DBSession.user_id == user_id).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error revoking sessions: {e}")

def cleanup_expired_sessions(db: Session):
    """Remove expired sessions from the database (Used by main.py)"""
    try:
        now = datetime.now(timezone.utc)
        # Delete sessions where expires_at is in the past
        db.query(DBSession).filter(DBSession.expires_at < now).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up sessions: {e}")