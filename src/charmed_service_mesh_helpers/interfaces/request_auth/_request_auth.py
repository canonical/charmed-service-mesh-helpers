# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Request authentication interface implementation."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ops import CharmBase
from ops.framework import Object
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ClaimToHeaderData(BaseModel):
    """Maps a JWT claim to a request header.

    Attributes:
        header: Target request header name
        claim: JWT claim name to extract
    """

    model_config = ConfigDict(frozen=True)

    header: str = Field(description="Target request header name")
    claim: str = Field(description="JWT claim name to extract")


class FromHeaderData(BaseModel):
    """Specifies a header location from which to extract a JWT.

    Attributes:
        name: Header name
        prefix: Prefix before the token value (e.g. "Bearer ")
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Header name")
    prefix: Optional[str] = None


class JWTRuleData(BaseModel):
    """A single JWT validation rule provided by the requiring app.

    Attributes:
        issuer: Issuer URL used to validate the token's iss claim
        jwks_uri: JWKS endpoint URL (defaults to OIDC discovery from issuer if omitted)
        audiences: List of allowed audience values
        forward_original_token: Whether to forward the original JWT to the downstream application
        claim_to_headers: List of claim-to-header mappings (duplicates allowed)
        from_headers: List of header locations from which to extract JWTs
    """

    model_config = ConfigDict(frozen=True)

    issuer: str = Field(description="Issuer URL for token validation")
    jwks_uri: Optional[str] = None
    audiences: Optional[List[str]] = None
    forward_original_token: Optional[bool] = None
    claim_to_headers: Optional[List[ClaimToHeaderData]] = None
    from_headers: Optional[List[FromHeaderData]] = None


class RequestAuthData(BaseModel):
    """Data sent by the requirer over the request-auth relation.

    Attributes:
        jwt_rules: List of JWT validation rules
    """

    model_config = ConfigDict(frozen=True)

    jwt_rules: List[JWTRuleData] = Field(description="List of JWT validation rules")


class RequestAuthProvider(Object):
    """Provider side of the request_auth interface.

    Used by the ingress charm to read JWT authentication rules from all related applications.
    """

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = "request-auth",
    ):
        """Initialize the RequestAuthProvider.

        Args:
            charm: The charm that owns this provider
            relation_name: Name of the relation (default: "request-auth")
        """
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    @property
    def is_ready(self) -> bool:
        """Check if any related application has provided request auth data.

        Returns:
            True if at least one requirer has published data, False otherwise
        """
        return bool(self.get_data())

    def get_data(self) -> Dict[str, RequestAuthData]:
        """Retrieve request auth data from all related applications.

        Returns:
            A dict mapping application name to its RequestAuthData
        """
        result: Dict[str, RequestAuthData] = {}
        relations = self._charm.model.relations.get(self._relation_name, [])

        for relation in relations:
            if not relation.app:
                continue

            data_json = relation.data[relation.app].get("request_auth_data")
            if not data_json:
                continue

            try:
                auth_data = RequestAuthData.model_validate_json(data_json)
                result[relation.app.name] = auth_data
            except Exception as e:
                logger.error(
                    f"Failed to parse request auth data from {relation.app.name}: {e}"
                )

        return result


class RequestAuthRequirer(Object):
    """Requirer side of the request_auth interface.

    Used by downstream applications to publish their JWT authentication rules
    to the ingress charm.
    """

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = "request-auth",
    ):
        """Initialize the RequestAuthRequirer.

        Args:
            charm: The charm that owns this requirer
            relation_name: Name of the relation (default: "request-auth")
        """
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish_data(self, data: RequestAuthData):
        """Publish request auth data to the provider.

        Args:
            data: The RequestAuthData to publish
        """
        if not self._charm.unit.is_leader():
            logger.debug("Not leader, skipping request auth data publication")
            return

        relations = self._charm.model.relations.get(self._relation_name, [])

        for relation in relations:
            relation.data[self._charm.app]["request_auth_data"] = data.model_dump_json()
