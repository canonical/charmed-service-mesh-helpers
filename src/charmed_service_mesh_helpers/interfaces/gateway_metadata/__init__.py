# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Gateway metadata interface."""

from ._gateway_metadata import (
    GatewayMetadata,
    GatewayMetadataProvider,
    GatewayMetadataRequirer,
)

__all__ = [
    "GatewayMetadata",
    "GatewayMetadataProvider",
    "GatewayMetadataRequirer",
]
