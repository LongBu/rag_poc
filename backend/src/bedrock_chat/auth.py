import re
from threading import Lock
from time import monotonic

import httpx
import jwt


UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")


def _identifier(value):
    return value.lower() if isinstance(value, str) and UUID.fullmatch(value) else ""


class OwnerAuth:
    def __init__(self, tenant_id, api_client_id, spa_client_id, owner_object_id):
        self.tenant_id = _identifier(tenant_id)
        self.api_client_id = _identifier(api_client_id)
        self.spa_client_id = _identifier(spa_client_id)
        self.owner_object_id = _identifier(owner_object_id)
        self.configured = bool(
            self.tenant_id and self.api_client_id and self.spa_client_id
            and self.owner_object_id and self.api_client_id != self.spa_client_id
        )
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        self.keys = None
        self.discovery_expires = 0
        self.discovery_lock = Lock()

    def _signing_keys(self):
        with self.discovery_lock:
            if self.keys is None or monotonic() >= self.discovery_expires:
                try:
                    response = httpx.get(
                        f"{self.issuer}/.well-known/openid-configuration",
                        timeout=2, follow_redirects=False,
                    )
                    response.raise_for_status()
                    metadata = response.json()
                    if not isinstance(metadata, dict) or metadata.get("issuer") != self.issuer:
                        raise ValueError
                    uri = metadata.get("jwks_uri")
                    if not isinstance(uri, str) or not re.fullmatch(
                        r"https://login\.microsoftonline\.com/(?:common|"
                        + re.escape(self.tenant_id) + r")/discovery/v2\.0/keys", uri
                    ):
                        raise ValueError
                except (httpx.HTTPError, ValueError):
                    raise jwt.PyJWKClientError("Signing metadata unavailable") from None
                self.keys = jwt.PyJWKClient(
                    uri, cache_keys=False, cache_jwk_set=True, lifespan=300,
                    timeout=2, cooldown_duration=30,
                )
                self.discovery_expires = monotonic() + 300
            return self.keys

    def __call__(self, authorization):
        if not self.configured:
            raise jwt.InvalidTokenError("Owner is not configured")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token or token != token.strip():
            raise jwt.InvalidTokenError("Bearer token required")
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str) or not header["kid"] or "crit" in header:
            raise jwt.InvalidTokenError("RS256 signing key required")
        try:
            key = self._signing_keys().get_signing_key_from_jwt(token)
            # Entra's issuer extension is retained in PyJWT's pinned JWK data.
            if key.algorithm_name != "RS256" or key._jwk_data.get("issuer") not in (
                self.issuer, "https://login.microsoftonline.com/{tenantid}/v2.0"
            ):
                raise jwt.InvalidTokenError("Signing key issuer is not allowed")
            claims = jwt.decode(
                token, key.key, algorithms=["RS256"], issuer=self.issuer,
                audience=self.api_client_id,
                options={
                    "strict_aud": True,
                    "require": ["exp", "iat", "nbf", "iss", "aud", "ver", "tid", "scp", "azp", "oid"],
                },
            )
        except (ValueError, TypeError, KeyError):
            raise jwt.InvalidTokenError("Invalid signing metadata or token") from None
        if (
            claims["ver"] != "2.0" or claims["tid"] != self.tenant_id
            or claims["azp"] != self.spa_client_id or claims["oid"] != self.owner_object_id
            or claims.get("idtyp") not in (None, "user")
            or not isinstance(claims["scp"], str) or "query" not in claims["scp"].split()
            or any(type(claims[field]) is not int for field in ("exp", "iat", "nbf"))
        ):
            raise jwt.InvalidTokenError("Owner delegated access token required")
