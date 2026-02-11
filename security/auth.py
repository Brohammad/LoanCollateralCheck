"""
Authentication and Authorization System

Implements:
- API Key authentication
- JWT token authentication
- Role-based access control (RBAC)
- OAuth2 password flow
- Token refresh mechanism
- API key management
"""

import secrets
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from functools import wraps
import logging

from fastapi import HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = secrets.token_urlsafe(32)  # Should be from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class User(BaseModel):
    """User model"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    roles: List[str] = []
    api_keys: List[str] = []


class TokenData(BaseModel):
    """JWT token data"""
    username: Optional[str] = None
    roles: List[str] = []
    exp: Optional[datetime] = None


class Token(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class APIKeyAuth:
    """
    API Key Authentication
    
    Supports:
    - API key generation
    - Key validation
    - Key revocation
    - Rate limiting per key
    """
    
    def __init__(self):
        """Initialize API key authentication"""
        # In-memory storage (should use database in production)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.key_to_user: Dict[str, str] = {}
    
    def generate_api_key(self, username: str, description: str = "") -> str:
        """
        Generate new API key
        
        Args:
            username: Username to associate with key
            description: Optional description of key purpose
            
        Returns:
            Generated API key
        """
        # Generate secure random key
        api_key = f"sk_{secrets.token_urlsafe(32)}"
        
        # Hash key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Store key metadata
        self.api_keys[key_hash] = {
            "username": username,
            "description": description,
            "created_at": datetime.utcnow(),
            "last_used": None,
            "active": True,
            "usage_count": 0
        }
        
        # Map for quick lookup
        self.key_to_user[key_hash] = username
        
        logger.info(f"Generated API key for user: {username}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[str]:
        """
        Validate API key and return username
        
        Args:
            api_key: API key to validate
            
        Returns:
            Username if valid, None otherwise
        """
        if not api_key:
            return None
        
        # Hash provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Check if key exists and is active
        if key_hash not in self.api_keys:
            return None
        
        key_data = self.api_keys[key_hash]
        
        if not key_data["active"]:
            logger.warning(f"Inactive API key used: {key_hash[:16]}...")
            return None
        
        # Update usage statistics
        key_data["last_used"] = datetime.utcnow()
        key_data["usage_count"] += 1
        
        return key_data["username"]
    
    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke API key
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if revoked, False if not found
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self.api_keys:
            self.api_keys[key_hash]["active"] = False
            logger.info(f"Revoked API key: {key_hash[:16]}...")
            return True
        
        return False
    
    def list_user_keys(self, username: str) -> List[Dict[str, Any]]:
        """
        List all API keys for a user
        
        Args:
            username: Username to list keys for
            
        Returns:
            List of key metadata
        """
        keys = []
        for key_hash, data in self.api_keys.items():
            if data["username"] == username:
                keys.append({
                    "key_prefix": key_hash[:16],
                    "description": data["description"],
                    "created_at": data["created_at"],
                    "last_used": data["last_used"],
                    "active": data["active"],
                    "usage_count": data["usage_count"]
                })
        return keys


class JWTAuth:
    """
    JWT Token Authentication
    
    Supports:
    - Access token generation
    - Refresh token generation
    - Token validation
    - Token refresh
    """
    
    def __init__(self, secret_key: str = SECRET_KEY):
        """Initialize JWT authentication"""
        self.secret_key = secret_key
        self.algorithm = ALGORITHM
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token
        
        Args:
            data: Data to encode in token
            expires_delta: Token expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token
        
        Args:
            data: Data to encode in token
            expires_delta: Token expiration time
            
        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (access/refresh)
            
        Returns:
            Decoded token data if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
                return None
            
            username: str = payload.get("sub")
            roles: List[str] = payload.get("roles", [])
            exp_timestamp = payload.get("exp")
            
            if username is None:
                return None
            
            exp = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None
            
            return TokenData(username=username, roles=roles, exp=exp)
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Create new access token from refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token if refresh token is valid
        """
        token_data = self.verify_token(refresh_token, token_type="refresh")
        
        if not token_data:
            return None
        
        # Create new access token
        access_token = self.create_access_token(
            data={"sub": token_data.username, "roles": token_data.roles}
        )
        
        return access_token


class AuthManager:
    """
    Main authentication manager
    
    Combines API key and JWT authentication
    """
    
    def __init__(self):
        """Initialize authentication manager"""
        self.api_key_auth = APIKeyAuth()
        self.jwt_auth = JWTAuth()
        
        # User database (should use real database in production)
        self.users: Dict[str, User] = {}
        self.passwords: Dict[str, str] = {}
    
    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        roles: List[str] = None
    ) -> User:
        """
        Create new user
        
        Args:
            username: Unique username
            password: User password
            email: User email
            full_name: User full name
            roles: User roles
            
        Returns:
            Created user
        """
        if username in self.users:
            raise ValueError(f"User {username} already exists")
        
        # Hash password
        password_hash = pwd_context.hash(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            roles=roles or ["user"]
        )
        
        self.users[username] = user
        self.passwords[username] = password_hash
        
        logger.info(f"Created user: {username}")
        return user
    
    def verify_password(self, username: str, password: str) -> bool:
        """
        Verify user password
        
        Args:
            username: Username
            password: Password to verify
            
        Returns:
            True if password is correct
        """
        if username not in self.passwords:
            return False
        
        return pwd_context.verify(password, self.passwords[username])
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User if authenticated, None otherwise
        """
        if not self.verify_password(username, password):
            return None
        
        user = self.users.get(username)
        
        if user and user.disabled:
            return None
        
        return user
    
    def login(self, username: str, password: str) -> Optional[Token]:
        """
        User login
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Token if authenticated
        """
        user = self.authenticate_user(username, password)
        
        if not user:
            return None
        
        # Create tokens
        access_token = self.jwt_auth.create_access_token(
            data={"sub": user.username, "roles": user.roles}
        )
        
        refresh_token = self.jwt_auth.create_refresh_token(
            data={"sub": user.username, "roles": user.roles}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )


# Global auth manager
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get global auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


async def get_current_user_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[User]:
    """
    Get current user from API key
    
    FastAPI dependency for API key authentication
    """
    if not api_key:
        return None
    
    auth_manager = get_auth_manager()
    username = auth_manager.api_key_auth.validate_api_key(api_key)
    
    if not username:
        return None
    
    user = auth_manager.users.get(username)
    return user


async def get_current_user_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[User]:
    """
    Get current user from JWT token
    
    FastAPI dependency for JWT authentication
    """
    if not credentials:
        return None
    
    auth_manager = get_auth_manager()
    token_data = auth_manager.jwt_auth.verify_token(credentials.credentials)
    
    if not token_data:
        return None
    
    user = auth_manager.users.get(token_data.username)
    return user


async def get_current_user(
    user_from_api_key: Optional[User] = Depends(get_current_user_api_key),
    user_from_jwt: Optional[User] = Depends(get_current_user_jwt)
) -> User:
    """
    Get current user from either API key or JWT
    
    FastAPI dependency for authentication
    """
    user = user_from_api_key or user_from_jwt
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


def require_roles(required_roles: List[str]):
    """
    Decorator to require specific roles
    
    Args:
        required_roles: List of required roles
    
    Usage:
        @require_roles(["admin", "moderator"])
        async def admin_endpoint(user: User = Depends(get_current_user)):
            pass
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return user
    
    return role_checker


def require_api_key(func):
    """
    Decorator to require API key authentication
    
    Usage:
        @require_api_key
        async def protected_endpoint(user: User):
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user = await get_current_user_api_key()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key"
            )
        return await func(*args, user=user, **kwargs)
    
    return wrapper
