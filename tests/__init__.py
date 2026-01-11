# This file must be named conftest.py and placed in the tests directory
# It runs BEFORE test collection, allowing us to mock modules early

import sys
from unittest.mock import MagicMock

# Mock audio hardware libraries BEFORE any test imports
# This prevents actual hardware access during test collection
_mock_sd = MagicMock()
_mock_sd.query_devices.return_value = []
_mock_sd.sleep = MagicMock()
_mock_sd.wait = MagicMock()
_mock_sd.rec = MagicMock()
_mock_sd.play = MagicMock()

sys.modules['sounddevice'] = _mock_sd
sys.modules['pydub'] = MagicMock()
sys.modules['pydub.AudioSegment'] = MagicMock()

# These mocks will be available to ALL tests now
