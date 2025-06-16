from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token):
    """Get user from JWT token"""
    try:
        # Validate the token
        UntypedToken(token)
        
        # Decode the token to get user_id
        from rest_framework_simplejwt.tokens import AccessToken
        decoded_token = AccessToken(token)
        user_id = decoded_token['user_id']
        
        # Get the user
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()


class TokenAuthMiddleware:
    """
    Token authorization middleware for Django Channels WebSocket
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await self.app(scope, receive, send) 