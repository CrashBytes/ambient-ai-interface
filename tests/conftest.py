"""
Pytest configuration and fixtures for ambient-ai-interface tests
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import pytest
import numpy as np

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set test environment variables before importing modules
os.environ.setdefault("OPENAI_API_KEY", "test-key-12345")
os.environ.setdefault("DEBUG_MODE", "true")
os.environ.setdefault("ENABLE_WAKE_WORD", "false")
os.environ.setdefault("LOG_USER_QUERIES", "false")


@pytest.fixture
def test_config():
    """Create a test configuration"""
    from src.utils.config import Config
    
    config = Config()
    config.openai_api_key = "test-key-12345"
    config.debug_mode = True
    config.enable_wake_word = False
    config.log_user_queries = False
    config.enable_persistent_memory = False
    
    return config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    with patch('openai.OpenAI') as mock_client:
        client_instance = Mock()
        mock_client.return_value = client_instance
        
        # Mock chat completion
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        client_instance.chat.completions.create.return_value = mock_response
        
        # Mock audio transcription
        mock_transcription = Mock()
        mock_transcription.text = "test transcription"
        client_instance.audio.transcriptions.create.return_value = mock_transcription
        
        # Mock TTS
        mock_tts_response = Mock()
        mock_tts_response.content = b"mock audio data"
        client_instance.audio.speech.create.return_value = mock_tts_response
        
        yield client_instance


@pytest.fixture
def mock_async_openai_client():
    """Mock AsyncOpenAI client"""
    with patch('openai.AsyncOpenAI') as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        
        # Mock async chat completion
        async def mock_create(*args, **kwargs):
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Async test response"))]
            return mock_response
        
        client_instance.chat.completions.create = AsyncMock(side_effect=mock_create)
        
        yield client_instance


@pytest.fixture
def mock_audio_input():
    """Mock audio input"""
    with patch('sounddevice.InputStream'):
        yield


@pytest.fixture
def mock_audio_output():
    """Mock audio output"""
    with patch('sounddevice.play'):
        yield


@pytest.fixture
def mock_pyaudio():
    """Mock PyAudio"""
    with patch('pyaudio.PyAudio') as mock_pa:
        pa_instance = Mock()
        mock_pa.return_value = pa_instance
        
        stream = Mock()
        stream.read.return_value = b'\x00' * 1024
        pa_instance.open.return_value = stream
        
        yield pa_instance


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path"""
    db_file = tmp_path / "test_context.db"
    return str(db_file)


@pytest.fixture
def sample_audio_data():
    """Sample audio data for testing"""
    import numpy as np
    # Generate 1 second of silence at 16kHz
    duration = 1.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    return np.zeros(samples, dtype=np.float32)


@pytest.fixture
def sample_context_messages():
    """Sample conversation context"""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you?"},
        {"role": "user", "content": "What's the weather?"},
    ]


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment before each test"""
    # Store original env vars
    original_env = os.environ.copy()
    
    yield
    
    # Restore original env vars
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.Redis') as mock_client:
        redis_instance = Mock()
        mock_client.return_value = redis_instance
        
        # Mock Redis operations
        redis_instance.get.return_value = None
        redis_instance.set.return_value = True
        redis_instance.delete.return_value = True
        redis_instance.exists.return_value = False
        
        yield redis_instance


@pytest.fixture
def mock_sqlalchemy_engine():
    """Mock SQLAlchemy engine"""
    with patch('sqlalchemy.create_engine') as mock_engine:
        engine_instance = Mock()
        mock_engine.return_value = engine_instance
        yield engine_instance
