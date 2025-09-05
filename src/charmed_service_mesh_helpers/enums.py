#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Shared enums used across service mesh charms."""
from enum import Enum


class Method(str, Enum):
    """HTTP method."""

    connect = "CONNECT"
    delete = "DELETE"
    get = "GET"
    head = "HEAD"
    options = "OPTIONS"
    patch = "PATCH"
    post = "POST"
    put = "PUT"
    trace = "TRACE"


class Action(str, Enum):
    """Action is a type that represents the action to take when a rule matches."""

    allow = "ALLOW"
    deny = "DENY"
    # These exist, but not sure if we've implemented everything to support them
    # audit = "AUDIT"
    # custom = "CUSTOM"
