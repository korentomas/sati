"""Supabase authentication integration."""

from typing import Dict, Optional
from supabase import create_client, Client
from gotrue import User
from app.core.config import settings
from app.core.logging import logger


class SupabaseAuth:
    """Handle Supabase authentication."""

    def __init__(self):
        """Initialize Supabase client."""
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError("Supabase configuration is missing")

        self.client: Client = create_client(
            settings.supabase_url, settings.supabase_anon_key
        )

        # Use service role key if available for admin operations
        if (
            settings.supabase_service_role_key
            and settings.supabase_service_role_key != "your-service-role-key-here"
        ):
            try:
                self.admin_client: Client = create_client(
                    settings.supabase_url, settings.supabase_service_role_key
                )
            except Exception as e:
                logger.warning(f"Could not create admin client: {e}")
                self.admin_client = self.client
        else:
            self.admin_client = self.client

    async def verify_token(self, token: str) -> Optional[User]:
        """
        Verify a Supabase JWT token and return the user.

        Args:
            token: JWT token from the frontend

        Returns:
            User object if valid, None otherwise
        """
        try:
            # Get user from token
            response = self.client.auth.get_user(token)
            if response.user:
                logger.info(f"Token verified for user: {response.user.email}")
                return response.user
            return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None

    async def verify_token_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID (for backend-issued tokens).

        Args:
            user_id: User's Supabase ID

        Returns:
            User object if found
        """
        try:
            # This is a workaround - ideally use admin client
            # For now, return basic user info
            return None
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user by email using admin client.

        Args:
            email: User's email

        Returns:
            User data if found
        """
        try:
            # This requires service role key
            response = self.admin_client.auth.admin.list_users()
            for user in response:
                if user.email == email:
                    return {
                        "id": user.id,
                        "email": user.email,
                        "created_at": user.created_at,
                        "confirmed_at": user.confirmed_at,
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    async def create_user(self, email: str, password: str) -> Optional[User]:
        """
        Create a new user in Supabase (for backend-initiated registration).

        Args:
            email: User's email
            password: User's password

        Returns:
            User object if created successfully
        """
        try:
            response = self.admin_client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,  # Auto-confirm for backend creation
                }
            )
            return response.user
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None


# Singleton instance
supabase_auth = SupabaseAuth()
