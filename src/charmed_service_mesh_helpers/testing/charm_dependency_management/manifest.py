"""Manifest handling for charm dependencies in integration tests.

This module provides functionality to load and access charm dependencies defined
manifests in YAML format.  The manifest defines things like the charm channel,
whether it is a locally built charm, and can be loaded both from a local file or
a URL.
"""

import logging
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.request import urlopen

import pytest
import yaml

logger = logging.getLogger(__name__)


@dataclass
class CharmManifestEntry:
    """Configuration for a single charm from the manifest.

    These are designed to match the input names for pylibjuju's juju.deploy so it can be **expanded directly into the
    deploy call.
    """
    channel: str
    entity_url: str
    revision: Optional[int] = None
    trust: Optional[bool] = None


class ManifestSource:
    """Represents a manifest source, either a local file or URL."""

    def __init__(self, source: str):
        """Initialize a manifest source.

        Args:
            source: Path to a local file or URL
        """
        self.source = source
        self._is_url = self._is_url_source(source)

    @staticmethod
    def _is_url_source(source: str) -> bool:
        """Check if the source is a URL.

        Args:
            source: Source string to check

        Returns:
            True if the source is a URL, False otherwise
        """
        try:
            result = urllib.parse.urlparse(source)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def load(self) -> Dict:
        """Load the manifest data from the source.

        Returns:
            Dictionary containing the manifest data

        Raises:
            ValueError: If the source cannot be loaded or is invalid
        """
        try:
            if self._is_url:
                with urlopen(self.source) as response:
                    raw_data = yaml.safe_load(response.read().decode('utf-8'))
            else:
                with open(self.source) as f:
                    raw_data = yaml.safe_load(f)

            if not isinstance(raw_data, dict):
                raise ValueError(f"Manifest {self.source} must be a YAML dictionary")

            return raw_data
        except Exception as e:
            raise ValueError(f"Failed to load manifest from {self.source}: {e}")


class CharmManifest:
    """Manages access to charm dependency manifest data."""

    def __init__(self, manifest_sources: List[str]):
        """Initialize the manifest from one or more sources.

        Args:
            manifest_sources: List of manifest sources (local files or URLs).
                            Later sources take precedence over earlier ones for the same charm.
        """
        self._manifest_sources = [ManifestSource(s) for s in manifest_sources]
        self._data: Dict[str, CharmManifestEntry] = {}
        self._load_manifests()

    def _load_manifests(self):
        """Load and merge all manifest sources.

        Later manifest sources take precedence over earlier ones for the same charm.
        """
        for source in self._manifest_sources:
            try:
                charm_configs = source.load()
                for charm_name, config in charm_configs.items():
                    if not isinstance(config, dict):
                        raise ValueError(
                            f"Configuration for {charm_name} in {source.source} must be a dictionary"
                        )

                    # TODO: Not sure if this validation is needed.  Can we just rely on the CharmManifestEntry class's
                    #  validation?
                    # Validate required fields
                    if "channel" not in config:
                        raise ValueError(
                            f"Missing required 'channel' field for {charm_name} in {source.source}"
                        )

                    # Create or update manifest entry
                    self._data[charm_name] = CharmManifestEntry(
                        channel=config["channel"],
                        entity_url=config.get("entity_url", charm_name),  # Default to charm_name if not specified
                        revision=config.get("revision"),
                        trust=config.get("trust"),
                    )
            except Exception as e:
                logger.error(f"Error loading manifest {source.source}: {e}")
                raise

    def get_charm_config(self, charm_name: str) -> CharmManifestEntry:
        """Get the configuration for a specific charm.

        Args:
            charm_name: Name of the charm to get configuration for

        Returns:
            CharmManifestEntry containing the charm's configuration

        Raises:
            KeyError: If the charm is not found in the manifest
        """
        if charm_name not in self._data:
            raise KeyError(f"Charm {charm_name} not found in manifest")
        return self._data[charm_name]


@pytest.fixture(scope="session")
def charm_manifest(request) -> CharmManifest:
    """Fixture providing access to the charm dependency manifest.

    This fixture loads the manifest sources specified by the --dependency-manifest
    command line arguments and provides access to the charm configurations.
    Later manifest sources take precedence over earlier ones for the same charm.

    To use this fixture, you must add the `--dependency-manifest` option to your pytest command line parsing options,
    for example by adding this to your conftest.py:

        def pytest_addoption(parser):
            \"""Add the dependency-manifest option to pytest.

            To pass a manifesst when calling pytest, use:
                `pytest --dependency-manifest path/to/manifest.yaml --dependency-manifest http://url.to/manifest.yaml`
            \"""
            parser.addoption(
                "--dependency-manifest",
                action="append",  # Changed to append to support multiple files
                help="Path to a YAML manifest file or URL specifying charm dependencies. Can be specified multiple times.",
            )

    Returns:
        CharmManifest instance for accessing charm configurations

    Raises:
        ValueError: If no manifest sources are specified or cannot be loaded
    """
    # Developer note: This fixture is not tested directly in unit tests here.  If you edit it, manually test to confirm
    # it is working.
    manifest_sources = request.config.getoption("--dependency-manifest")
    if not manifest_sources:
        raise ValueError(
            "No dependency manifests specified. Use --dependency-manifest to specify one or more manifest sources."
        )

    return CharmManifest(manifest_sources)