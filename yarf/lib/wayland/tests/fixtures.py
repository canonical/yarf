from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_pwc():
    with patch("pywayland.client") as mock:
        yield mock
