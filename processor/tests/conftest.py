import pytest


@pytest.fixture
def sample_bar():
    return {
        "bar_index": 100,
        "timestamp": "2024-01-01T00:00:00Z",
        "open": 100.0,
        "high": 101.0,
        "low": 99.5,
        "close": 100.5,
        "volume": 1000,
    }
