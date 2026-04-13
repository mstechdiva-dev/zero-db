"""pytest configuration for SchemaZero backend tests."""

import pytest


# Configure pytest-asyncio to use asyncio mode for async test functions.
# This avoids having to add @pytest.mark.asyncio to every async test.
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (handled by pytest-asyncio)"
    )
