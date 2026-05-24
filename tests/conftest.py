"""Pytest fixtures shared across tests.

`enable_custom_integrations` is the standard hook that makes HA's test
harness treat `custom_components/heatsync/` as a real integration during
the test run.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable the custom_components dir for every test."""
    yield
