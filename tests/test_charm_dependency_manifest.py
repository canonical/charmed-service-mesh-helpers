"""Tests for the manifest system.

This module contains tests for the manifest system components:
- CharmManifestEntry
- ManifestSource
- CharmManifest
- charm_manifest fixture
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from charmed_service_mesh_helpers.testing.charm_dependency_management import (
    CharmManifest,
    CharmManifestEntry,
    ManifestSource,
)


@pytest.fixture
def temp_manifest_file() -> Path:
    """Create a temporary manifest file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "charm-a": {
                    "channel": "latest/edge",
                    "trust": True,
                },
                "charm-b": {
                    "channel": "1.0/stable",
                    "revision": 42,
                    "entity_url": "custom/url",
                    "resources": {
                        "some-image-name": "some-image-url"
                    }
                },
            },
            f,
        )
    yield Path(f.name)
    os.unlink(f.name)


@pytest.fixture
def temp_manifest_file_2() -> Path:
    """Create a second temporary manifest file for testing merging."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "charm-a": {
                    "channel": "2.0/edge",  # Override channel
                    "revision": 100,  # Add revision
                    "trust": True,  # Explicitly set trust to preserve it
                },
                "charm-c": {  # New charm
                    "channel": "latest/stable",
                },
            },
            f,
        )
    yield Path(f.name)
    os.unlink(f.name)


@pytest.mark.parametrize(
    "channel, entity_url, revision, trust, resources",
    [
        # Test with all fields
        ("latest/edge", "custom/url", 42, True, {"some-image-name": "some-image-url", "another-resource": "another-url"}),
        # Test with minimal fields
        ("latest/edge", "default/url", None, None, None),
    ],
)
def test_charm_manifest_entry_creation(channel, entity_url, revision, trust, resources):
    """Test creating CharmManifestEntry objects."""
    entry = CharmManifestEntry(
        channel=channel,
        entity_url=entity_url,
        revision=revision,
        trust=trust,
        resources=resources,
    )
    assert entry.channel == channel
    assert entry.entity_url == entity_url
    assert entry.revision == revision
    assert entry.trust is trust
    assert entry.resources == resources


def test_manifest_source_local_file(temp_manifest_file: Path):
    """Test loading a manifest from a local file."""
    source = ManifestSource(str(temp_manifest_file))
    data = source.load()

    assert isinstance(data, dict)
    assert "charm-a" in data
    assert "charm-b" in data
    assert data["charm-a"]["channel"] == "latest/edge"
    assert data["charm-b"]["channel"] == "1.0/stable"


def test_manifest_source_url(httpserver):
    """Test loading a manifest from a URL."""
    manifest_data = {
        "charm-a": {
            "channel": "latest/edge",
            "trust": True,
        }
    }
    httpserver.expect_request("/manifest.yaml").respond_with_json(manifest_data)

    source = ManifestSource(httpserver.url_for("/manifest.yaml"))
    data = source.load()

    assert isinstance(data, dict)
    assert "charm-a" in data
    assert data["charm-a"]["channel"] == "latest/edge"


def test_manifest_source_invalid_file():
    """Test handling of invalid local file."""
    with pytest.raises(ValueError, match="Failed to load manifest"):
        source = ManifestSource("nonexistent.yaml")
        source.load()


def test_manifest_source_valid_url_invalid_content(httpserver):
    """Test handling of invalid URL."""
    httpserver.expect_request("/invalid.yaml").respond_with_data(
        "invalid yaml content", status=200
    )

    with pytest.raises(ValueError, match="Failed to load manifest"):
        source = ManifestSource(httpserver.url_for("/invalid.yaml"))
        source.load()


def test_manifest_source_invalid_url(httpserver):
    """Test handling of invalid URL."""
    httpserver.expect_request("invalid.com").respond_with_data(
        "", status=404
    )

    with pytest.raises(ValueError, match="Failed to load manifest"):
        source = ManifestSource(httpserver.url_for("invalid.com"))
        source.load()


def test_charm_manifest_single_source(temp_manifest_file: Path):
    """Test loading a manifest from a single source."""
    manifest = CharmManifest([str(temp_manifest_file)])

    # Test charm-a
    config = manifest.get_charm_config("charm-a")
    assert config.channel == "latest/edge"
    assert config.entity_url == "charm-a"  # Default value
    assert config.trust is True
    assert config.revision is None

    # Test charm-b
    config = manifest.get_charm_config("charm-b")
    assert config.channel == "1.0/stable"
    assert config.entity_url == "custom/url"  # Custom value
    assert config.revision == 42
    assert config.trust is None


def test_charm_manifest_multiple_sources(temp_manifest_file: Path, temp_manifest_file_2: Path):
    """Test loading and merging multiple manifest sources."""
    manifest = CharmManifest([str(temp_manifest_file), str(temp_manifest_file_2)])

    # Test charm-a (overridden)
    config = manifest.get_charm_config("charm-a")
    assert config.channel == "2.0/edge"  # Overridden
    assert config.entity_url == "charm-a"  # Default value
    assert config.revision == 100  # Added
    assert config.trust is True  # Preserved

    # Test charm-b (unchanged)
    config = manifest.get_charm_config("charm-b")
    assert config.channel == "1.0/stable"
    assert config.entity_url == "custom/url"
    assert config.revision == 42
    assert config.trust is None

    # Test charm-c (new)
    config = manifest.get_charm_config("charm-c")
    assert config.channel == "latest/stable"
    assert config.entity_url == "charm-c"  # Default value
    assert config.revision is None
    assert config.trust is None


def test_charm_manifest_missing_charm(temp_manifest_file: Path):
    """Test handling of requests for non-existent charms."""
    manifest = CharmManifest([str(temp_manifest_file)])

    with pytest.raises(KeyError, match="Charm nonexistent not found in manifest"):
        manifest.get_charm_config("nonexistent")


def test_charm_manifest_invalid_source():
    """Test handling of invalid manifest sources."""
    with pytest.raises(ValueError, match="Failed to load manifest"):
        CharmManifest(["nonexistent.yaml"])
