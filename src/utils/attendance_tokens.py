"""
Thread-safe single-use token management for QR attendance
Prevents replay attacks using atomic check-and-delete pattern
"""

import threading
import secrets
import time
import logging

logger = logging.getLogger(__name__)


class TokenStore:
    """Thread-safe in-memory token storage with atomic operations"""
    
    def __init__(self):
        """Initialize token store with lock"""
        self._tokens = {}  # {token_string: {'user_id': int, 'expires_at': float}}
        self._lock = threading.Lock()  # Protects all token access
        logger.info("TokenStore initialized with threading.Lock protection")
    
    def generate_token(self, user_id: int, ttl_seconds: int = 120) -> str:
        """
        Generate single-use attendance token
        
        Args:
            user_id: Telegram user ID
            ttl_seconds: Token lifetime in seconds (default 120)
        
        Returns:
            Random 32-character hex token string
        """
        try:
            with self._lock:  # ACQUIRE LOCK
                # Cleanup expired tokens before generating new one
                self._cleanup_expired_tokens()
                
                # Generate random hex token
                token = secrets.token_hex(16)  # 32 characters
                expires_at = time.time() + ttl_seconds
                
                # Store token with expiry
                self._tokens[token] = {
                    'user_id': user_id,
                    'expires_at': expires_at
                }
                
                logger.debug(f"Token generated for user {user_id}: TTL {ttl_seconds}s")
                return token
            # RELEASE LOCK
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            raise
    
    def validate_and_consume_token(self, token: str) -> tuple[bool, int | str]:
        """
        Atomically validate and consume token (check-and-delete pattern)
        
        Prevents replay attacks by deleting token immediately after first validation.
        This operation is atomic - no race conditions possible.
        
        Args:
            token: Token string to validate
        
        Returns:
            tuple[bool, int | str]: (is_valid, user_id_or_reason)
            - (True, user_id) if valid
            - (False, 'TOKEN_NOT_FOUND') if not found
            - (False, 'TOKEN_EXPIRED') if expired
        """
        try:
            with self._lock:  # ACQUIRE LOCK - blocks until available
                # Step 1: Cleanup expired tokens (lazy cleanup)
                self._cleanup_expired_tokens()
                
                # Step 2: Check if token exists
                if token not in self._tokens:
                    logger.debug(f"Token validation failed: TOKEN_NOT_FOUND")
                    return False, 'TOKEN_NOT_FOUND'
                
                # Step 3: Check if expired
                token_data = self._tokens[token]
                current_time = time.time()
                
                if current_time > token_data['expires_at']:
                    user_id = token_data['user_id']
                    del self._tokens[token]  # Delete expired token
                    logger.debug(f"Token validation failed for user {user_id}: TOKEN_EXPIRED")
                    return False, 'TOKEN_EXPIRED'
                
                # Step 4: Token is valid - consume it immediately (atomic delete)
                user_id = token_data['user_id']
                del self._tokens[token]  # ATOMIC: Delete inside lock
                
                logger.info(f"Token validated and consumed for user {user_id}")
                return True, user_id
            # RELEASE LOCK - race condition impossible
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, 'SERVER_ERROR'
    
    def _cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens (called inside lock only)
        Lazy cleanup: only runs when generate or validate is called
        
        Returns:
            Number of tokens cleaned up
        """
        current_time = time.time()
        expired_tokens = [
            token for token, data in self._tokens.items()
            if current_time > data['expires_at']
        ]
        
        for token in expired_tokens:
            del self._tokens[token]
        
        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired tokens")
        
        return len(expired_tokens)
    
    def get_active_token_count(self) -> int:
        """Get count of active (non-expired) tokens (for monitoring)"""
        try:
            with self._lock:
                self._cleanup_expired_tokens()
                return len(self._tokens)
        except Exception as e:
            logger.error(f"Error getting token count: {e}")
            return -1


# Module-level singleton instance (shared across all Flask requests)
token_store = TokenStore()
