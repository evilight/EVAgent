"""
Authentication service for EVAgent RAG system.
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBasic, HTTPBearer, HTTPBasicCredentials
import logging

logger = logging.getLogger(__name__)

security = HTTPBasic()
bearer = HTTPBearer()


class AuthService:
    """Service for handling authentication and authorization."""
    
    def __init__(self, secret_key: str, default_username: str = "admin", default_password: str = "admin123"):
        self.secret_key = secret_key
        self.default_username = default_username
        self.default_password = default_password
        self.token_expire_hours = 24
        
        # Simple in-memory user store (can be enhanced with database)
        self.users = {
            default_username: default_password
        }
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """
        Authenticate user credentials.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if credentials are valid
        """
        return self.users.get(username) == password
    
    def create_access_token(self, username: str) -> str:
        """
        Create JWT access token.
        
        Args:
            username: Username to include in token
            
        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(hours=self.token_expire_hours)
        payload = {
            "sub": username,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return encoded_jwt
    
    def verify_token(self, token: str) -> str:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Username from token
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return username
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def add_user(self, username: str, password: str) -> bool:
        """
        Add a new user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if user added successfully
        """
        if username in self.users:
            return False
        self.users[username] = password
        return True
    
    def get_current_user(self, credentials: HTTPBasicCredentials = Security(security)) -> str:
        """
        Get current user from Basic Auth credentials.
        
        Args:
            credentials: Basic auth credentials
            
        Returns:
            Username
            
        Raises:
            HTTPException: If credentials are invalid
        """
        if not self.authenticate_user(credentials.username, credentials.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username
    
    def get_current_user_from_token(self, token: str = Security(bearer)) -> str:
        """
        Get current user from JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Username
            
        Raises:
            HTTPException: If token is invalid
        """
        return self.verify_token(token.credentials)


# Global auth service instance
auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global auth_service
    if auth_service is None:
        import os
        secret_key = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
        default_username = os.getenv("DEFAULT_USERNAME", "admin")
        default_password = os.getenv("DEFAULT_PASSWORD", "admin123")
        
        auth_service = AuthService(secret_key, default_username, default_password)
        logger.info(f"AuthService initialized with user: {default_username}")
    
    return auth_service


def get_current_user_basic() -> str:
    """Dependency for Basic Auth."""
    return get_auth_service().get_current_user()


def get_current_user_token(token: str = Security(bearer)) -> str:
    """Dependency for Token Auth."""
    return get_auth_service().get_current_user_from_token(token)
