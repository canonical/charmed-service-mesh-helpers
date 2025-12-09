# Gateway Metadata Interface

Interface for sharing Gateway workload metadata between charms.

## Provider Usage

The provider publishes metadata about the Gateway workload.

```python
from charmed_service_mesh_helpers.interfaces.gateway_metadata import (
    GatewayMetadataProvider,
    GatewayMetadata,
)

class IstioIngressCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.gateway_metadata_provider = GatewayMetadataProvider(
            self,
            relation_name="gateway-metadata",
        )

    def _publish_metadata(self):
        """Publish gateway metadata when ready."""
        metadata = GatewayMetadata(
            namespace=self.model.name,
            gateway_name=self.app.name,
            deployment_name=f"{self.app.name}-istio",
            service_account=f"{self.app.name}-istio",
        )
        self.gateway_metadata_provider.publish_metadata(metadata)
```

**Charmcraft.yaml:**
```yaml
provides:
  gateway-metadata:
    interface: gateway_metadata
```

## Requirer Usage

The requirer receives Gateway metadata from the provider.

```python
from charmed_service_mesh_helpers.interfaces.gateway_metadata import (
    GatewayMetadataRequirer,
)

class MyCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.gateway_metadata = GatewayMetadataRequirer(
            self,
            relation_name="gateway-metadata",
        )
        self.framework.observe(
            self.on["gateway-metadata"].relation_changed,
            self._on_gateway_metadata_changed
        )

    def _on_gateway_metadata_changed(self, event):
        if not self.gateway_metadata.is_ready:
            return

        metadata = self.gateway_metadata.get_metadata()
        if not metadata:
            return

        # Use metadata fields:
        # - metadata.namespace
        # - metadata.gateway_name
        # - metadata.deployment_name
        # - metadata.service_account

        # Example: Create Istio AuthorizationPolicy principal
        principal = f"cluster.local/ns/{metadata.namespace}/sa/{metadata.service_account}"
```

**Charmcraft.yaml:**
```yaml
requires:
  gateway-metadata:
    interface: gateway_metadata
```
