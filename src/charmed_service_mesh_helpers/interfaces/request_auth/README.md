# Request Auth Interface

Interface for configuring JWT-based authentication via Istio RequestAuthentication.

Downstream applications (requirers) provide their JWT validation rules - issuer, JWKS URI, and claim-to-header mappings. The ingress charm (provider) reads these rules and creates corresponding Istio RequestAuthentication resources targeting the Gateway.

## Requirer Usage (Downstream Application)

The requirer publishes JWT rules to the ingress charm.

```python
from charmed_service_mesh_helpers.interfaces.request_auth import (
    RequestAuthRequirer,
    RequestAuthData,
    JWTRuleData,
    ClaimToHeaderData,
)

class MyCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.request_auth = RequestAuthRequirer(
            self,
            relation_name="request-auth",
        )
        self.framework.observe(
            self.on["request-auth"].relation_joined,
            self._on_request_auth_joined
        )

    def _on_request_auth_joined(self, _):
        claim_to_headers = [
            ClaimToHeaderData(header="x-user-email", claim="email"),
            # Duplicate header names are allowed - useful for mapping
            # mutually exclusive claims (e.g. email for user tokens,
            # client_id for M2M tokens) to the same header.
            ClaimToHeaderData(header="x-user-id", claim="email"),
            ClaimToHeaderData(header="x-user-id", claim="client_id"),
        ]

        jwt_rules = [
            JWTRuleData(
                issuer="https://my-idp.example.com",
                forward_original_token=True,
                claim_to_headers=claim_to_headers,
            ),
        ]

        self.request_auth.publish_data(
            RequestAuthData(jwt_rules=jwt_rules)
        )
```

**Charmcraft.yaml:**
```yaml
requires:
  request-auth:
    interface: request_auth
```

## Provider Usage (Ingress Charm)

The provider reads JWT rules from all related applications.

```python
from charmed_service_mesh_helpers.interfaces.request_auth import (
    RequestAuthProvider,
)

class IstioIngressCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.request_auth_provider = RequestAuthProvider(
            self,
            relation_name="request-auth",
        )
        self.framework.observe(
            self.on["request-auth"].relation_changed,
            self._on_request_auth_changed
        )
        self.framework.observe(
            self.on["request-auth"].relation_broken,
            self._on_request_auth_changed
        )

    def _on_request_auth_changed(self, _):
        if not self.request_auth_provider.is_ready:
            return

        # Dict mapping app name to its RequestAuthData
        all_data = self.request_auth_provider.get_data()

        for app_name, auth_data in all_data.items():
            for rule in auth_data.jwt_rules:
                # rule.issuer
                # rule.jwks_uri
                # rule.claim_to_headers  (list of ClaimToHeaderData)
                # rule.audiences
                # rule.forward_original_token
                # rule.from_headers
                pass
```

**Charmcraft.yaml:**
```yaml
provides:
  request-auth:
    interface: request_auth
    description: |
      Allows related applications to configure JWT-based authentication via
      Istio RequestAuthentication. Each related app provides its JWT rules
      (issuer, JWKS URI, claim-to-header mappings) and the ingress charm
      creates corresponding RequestAuthentication resources targeting the Gateway.
```
