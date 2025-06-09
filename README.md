# charmed-service-mesh-helpers
A collection of helpers and shared code from the Service Mesh team.

The goal of this is a place to put **lightweight** shared code that's used in multiple Service Mesh charms.  Anything kept here should require very lightweight dependencies, typically the standard library or very common dependencies.

## Publishing to PyPI

To release a new version of this package to PyPI, you can create a Github release with the new version number (eg: 
0.1.2).  The release will trigger a workflow that builds the package and publishes it to PyPI.