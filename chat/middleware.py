from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
import urllib.parse


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Extract token from query parameters in the URL
        token_key = self.get_token_from_url(scope)
        print(token_key)
        # Resolve the user based on the token
        scope['user'] = await self.get_user_from_token(token_key) if token_key else AnonymousUser()

        return await self.inner(scope, receive, send)

    def get_token_from_url(self, scope):
        # Extract the query string from the URL in the scope
        query_string = scope.get('query_string', b'').decode()
        # Parse the query string to retrieve the token
        parsed_url = urllib.parse.parse_qs(query_string)
        # Token should be passed as a parameter named 'token'
        return parsed_url.get('token', [None])[0]

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        """
        Fetches the user associated with the provided token.
        """
        try:
            token = Token.objects.select_related('user').get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return AnonymousUser()
