"""
Unit tests for Voice Input
Tests speech-to-text processing, audio capture, and wake word detection
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from src.voice_input import VoiceInput, SimpleWakeWordDetector


@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice module"""
    with patch('src.voice_input.sd') as mock_sd:
        # Mock query_devices to return available devices
        mock_sd.query_devices.return_value = [
            {'name': 'Default Microphone', 'max_input_channels': 1}
        ]
        # Mock sleep
        mock_sd.sleep = Mock()
        # Mock wait
        mock_sd.wait = Mock()
        yield mock_sd


@pytest.fixture
def sample_audio_chunk():
    """Generate small sample audio data (reduced size to prevent memory issues)"""
    # Use small array: 1000 samples instead of 16000 to prevent memory leaks
    return np.zeros(1000, dtype=np.float32)


class TestVoiceInput:
    """Test voice input functionality"""
    
    def test_initialization(self, test_config, mock_sounddevice):
        """Test voice input initialization"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            assert voice_input.config == test_config
            assert voice_input.sample_rate == test_config.mic_sample_rate
            assert voice_input.channels == test_config.mic_channels
            assert voice_input.is_recording is False
            assert isinstance(voice_input.audio_buffer, list)
    
    def test_initialization_with_wake_word(self, test_config, mock_sounddevice):
        """Test initialization with wake word enabled"""
        test_config.enable_wake_word = True
        test_config.wake_word = "hey assistant"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector:
                voice_input = VoiceInput(test_config)
                
                mock_detector.assert_called_once()
                assert voice_input.wake_word_detector is not None
    
    def test_is_ready_success(self, test_config, mock_sounddevice):
        """Test is_ready when devices available"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            assert voice_input.is_ready() is True
            mock_sounddevice.query_devices.assert_called()
    
    def test_is_ready_failure(self, test_config):
        """Test is_ready when no devices available"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.sd') as mock_sd:
                mock_sd.query_devices.side_effect = Exception("No devices")
                
                voice_input = VoiceInput(test_config)
                assert voice_input.is_ready() is False
    
    def test_capture_audio_fixed_duration(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test audio capture with fixed duration"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Mock rec to return sample audio
            mock_sounddevice.rec.return_value = sample_audio_chunk.reshape(-1, 1)
            
            audio = voice_input.capture_audio(duration=1.0)
            
            mock_sounddevice.rec.assert_called_once()
            assert isinstance(audio, np.ndarray)
            assert len(audio) > 0
    
    @pytest.mark.asyncio
    async def test_capture_audio_async(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test async audio capture"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            mock_sounddevice.rec.return_value = sample_audio_chunk.reshape(-1, 1)
            
            audio = await voice_input.capture_audio_async(duration=1.0)
            
            assert isinstance(audio, np.ndarray)
            assert len(audio) > 0
    
    def test_transcribe_success(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test successful transcription"""
        with patch('src.voice_input.OpenAI') as mock_openai, patch('src.voice_input.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = "Hello world"
            
            voice_input = VoiceInput(test_config)
            text = voice_input.transcribe(sample_audio_chunk)
            
            assert text == "Hello world"
            mock_client.audio.transcriptions.create.assert_called_once()
    
    def test_transcribe_empty_audio(self, test_config, mock_sounddevice):
        """Test transcription with empty audio"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            empty_audio = np.array([])
            text = voice_input.transcribe(empty_audio)
            
            assert text == ""
    
    def test_transcribe_error_handling(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test transcription error handling"""
        with patch('openai.OpenAI') as mock_openai, patch('openai.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
            
            voice_input = VoiceInput(test_config)
            text = voice_input.transcribe(sample_audio_chunk)
            
            assert text == ""
    
    @pytest.mark.asyncio
    async def test_transcribe_async_success(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test async transcription"""
        with patch('src.voice_input.OpenAI'), patch('src.voice_input.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = "Async transcription"
            
            voice_input = VoiceInput(test_config)
            text = await voice_input.transcribe_async(sample_audio_chunk)
            
            assert text == "Async transcription"
    
    @pytest.mark.asyncio
    async def test_transcribe_async_empty(self, test_config, mock_sounddevice):
        """Test async transcription with empty audio"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            empty_audio = np.array([])
            text = await voice_input.transcribe_async(empty_audio)
            
            assert text == ""
    
    def test_numpy_to_wav(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test numpy array to WAV conversion"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            wav_bytes = voice_input._numpy_to_wav(sample_audio_chunk)
            
            assert isinstance(wav_bytes, bytes)
            assert len(wav_bytes) > 0
            assert wav_bytes[:4] == b'RIFF'
    
    def test_wait_for_wake_word_no_detector(self, test_config, mock_sounddevice):
        """Test wake word waiting with no detector"""
        test_config.enable_wake_word = False
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            result = voice_input.wait_for_wake_word()
            assert result is True
    
    def test_cleanup(self, test_config, mock_sounddevice):
        """Test cleanup"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            voice_input.audio_buffer = [1, 2, 3]
            
            voice_input.cleanup()
            
            assert len(voice_input.audio_buffer) == 0


class TestSimpleWakeWordDetector:
    """Test wake word detector"""
    
    def test_initialization(self):
        """Test wake word detector initialization"""
        detector = SimpleWakeWordDetector("hey assistant", sensitivity=0.7)
        
        assert detector.wake_word == "hey assistant"
        assert detector.sensitivity == 0.7
    
    def test_detect(self, sample_audio_chunk):
        """Test wake word detection"""
        detector = SimpleWakeWordDetector("test")
        
        result = detector.detect(sample_audio_chunk)
        assert result is False
    
    def test_cleanup(self):
        """Test cleanup"""
        detector = SimpleWakeWordDetector("test")
        detector.cleanup()



class TestVoiceInputEdgeCases:
    """Test edge cases and error paths"""
    
    def test_init_wake_word_detector_exception(self, test_config, mock_sounddevice):
        """Test wake word detector initialization failure"""
        test_config.enable_wake_word = True
        test_config.wake_word = "test wake word"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector', side_effect=Exception("Init failed")):
                voice_input = VoiceInput(test_config)
                
                # Should handle exception gracefully
                assert voice_input.wake_word_detector is None
    
    def test_is_ready_exception(self, test_config):
        """Test is_ready handles exceptions"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.sd.query_devices', side_effect=Exception("Device error")):
                voice_input = VoiceInput(test_config)
                
                assert voice_input.is_ready() is False
    
    def test_capture_audio_until_silence_via_none_duration(self, test_config, mock_sounddevice):
        """Test capture_audio with duration=None triggers _record_until_silence"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Mock _record_until_silence
            with patch.object(voice_input, '_record_until_silence', return_value=np.array([1, 2, 3])):
                audio = voice_input.capture_audio(duration=None)
                
                assert isinstance(audio, np.ndarray)
                assert len(audio) == 3
    
    def test_record_until_silence_implementation(self, test_config, mock_sounddevice):
        """Test _record_until_silence with mocked callback"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Create silent audio chunks
            silent_chunk = np.zeros((1024, 1), dtype=np.float32)
            callback_count = [0]  # Use list to allow modification in nested function
            stored_callback = [None]
            
            # Mock InputStream to store callback for later execution
            class MockInputStream:
                def __init__(self, callback, **kwargs):
                    stored_callback[0] = callback
                
                def __enter__(self):
                    return self
                
                def __exit__(self, *args):
                    pass
            
            # Mock sleep to trigger callbacks during the loop
            def mock_sleep(ms):
                if stored_callback[0] and callback_count[0] < 40:
                    # Trigger callback with silent audio
                    stored_callback[0](silent_chunk, 1024, None, None)
                    callback_count[0] += 1
            
            with patch('src.voice_input.sd.InputStream', MockInputStream):
                with patch('src.voice_input.sd.sleep', side_effect=mock_sleep):
                    audio = voice_input._record_until_silence()
                    
                    assert isinstance(audio, np.ndarray)
                    assert len(audio) > 0  # Should have captured some audio
    
    def test_record_until_silence_with_audio_warnings(self, test_config, mock_sounddevice):
        """Test _record_until_silence handles audio callback warnings"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            quiet_chunk = np.ones((1024, 1), dtype=np.float32) * 0.001
            callback_count = [0]
            stored_callback = [None]
            
            class MockInputStream:
                def __init__(self, callback, **kwargs):
                    stored_callback[0] = callback
                
                def __enter__(self):
                    return self
                
                def __exit__(self, *args):
                    pass
            
            # Mock sleep to trigger callbacks with warnings during the loop
            def mock_sleep(ms):
                if stored_callback[0] and callback_count[0] < 40:
                    # Trigger callback with status warning
                    stored_callback[0](quiet_chunk, 1024, None, "Input overflow")
                    callback_count[0] += 1
            
            with patch('src.voice_input.sd.InputStream', MockInputStream):
                with patch('src.voice_input.sd.sleep', side_effect=mock_sleep):
                    audio = voice_input._record_until_silence()
                    assert isinstance(audio, np.ndarray)
                    assert len(audio) > 0  # Should have captured audio despite warnings
