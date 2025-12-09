# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm interfaces for Service Mesh."""

from .gateway_metadata import (
    GatewayMetadata,
    GatewayMetadataProvider,
    GatewayMetadataRequirer,
)

__all__ = [
    "GatewayMetadata",
    "GatewayMetadataProvider",
    "GatewayMetadataRequirer",
]
