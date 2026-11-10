import jwt


class OwnerAuth:
    def __init__(self, issuer, client_id, owner_sub):
        self.issuer = issuer
        self.client_id = client_id
        self.owner_sub = owner_sub
        self.keys = jwt.PyJWKClient(
            f"{issuer}/.well-known/jwks.json", lifespan=300, timeout=2
        ) if issuer else None

    def __call__(self, authorization):
        scheme, _, token = authorization.partition(" ")
        if not (self.issuer and self.client_id and self.owner_sub):
            raise jwt.InvalidTokenError("Owner is not configured")
        if scheme != "Bearer" or not token:
            raise jwt.InvalidTokenError("Bearer token required")
        key = self.keys.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, key.key, algorithms=["RS256"], issuer=self.issuer,
            options={
                "verify_aud": False,
                "require": ["exp", "iat", "sub", "iss", "token_use", "client_id", "scope"],
            },
        )
        if (
            claims["token_use"] != "access"
            or claims["client_id"] != self.client_id
            or claims["sub"] != self.owner_sub
            or not isinstance(claims["scope"], str)
            or "chat/query" not in claims["scope"].split()
        ):
            raise jwt.InvalidTokenError("Owner access token required")
