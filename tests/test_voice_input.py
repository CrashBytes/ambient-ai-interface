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
    # Use smaller array: 1000 samples instead of 16000 to prevent memory leaks
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
            # Mock transcription response
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # Mock the transcription create method to return a string directly
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
            
            # Mock the async transcription create method to return a string directly
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
            # WAV header starts with 'RIFF'
            assert wav_bytes[:4] == b'RIFF'
    
    def test_wait_for_wake_word_no_detector(self, test_config, mock_sounddevice):
        """Test wake word waiting with no detector"""
        test_config.enable_wake_word = False
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Should return True immediately if no detector
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
        
        # Simple detector always returns False in placeholder
        result = detector.detect(sample_audio_chunk)
        assert result is False
    
    def test_cleanup(self):
        """Test cleanup"""
        detector = SimpleWakeWordDetector("test")
        # Should not raise exception
        detector.cleanup()
    def test_init_wake_word_detector_exception(self, test_config, mock_sounddevice):
        """Test wake word detector initialization with exception"""
        test_config.enable_wake_word = True
        test_config.wake_word = "hey assistant"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector:
                # Simulate exception during initialization
                mock_detector.side_effect = Exception("Detector initialization failed")
                
                voice_input = VoiceInput(test_config)
                
                # Should handle exception gracefully
                assert voice_input.wake_word_detector is None
    
    def test_capture_audio_until_silence(self, test_config, mock_sounddevice):
        """Test audio capture until silence is detected"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Mock the _record_until_silence method
            with patch.object(voice_input, '_record_until_silence') as mock_record:
                mock_record.return_value = np.zeros(16000, dtype=np.float32)
                
                audio = voice_input.capture_audio(duration=None)
                
                mock_record.assert_called_once()
                assert isinstance(audio, np.ndarray)
    
    def test_record_until_silence(self, test_config, mock_sounddevice):
        """Test _record_until_silence implementation"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Create mock audio data (silent)
            silent_chunk = np.zeros((1024, 1), dtype=np.float32)
            
            # Mock InputStream to simulate recording
            mock_stream = MagicMock()
            
            with patch('src.voice_input.sd.InputStream') as mock_input_stream:
                # Simulate stream that provides silent audio chunks
                mock_input_stream.return_value.__enter__.return_value = mock_stream
                
                # Mock the audio_callback to be called a few times
                callback_calls = []
                def side_effect(*args, **kwargs):
                    # Simulate callback being invoked
                    callback = kwargs.get('callback') if 'callback' in kwargs else args[0] if args else None
                    if callback and len(callback_calls) < 5:
                        callback_calls.append(1)
                        # Call the callback with silent audio
                        callback(silent_chunk, 1024, None, None)
                
                mock_input_stream.side_effect = side_effect
                
                # Call the method
                audio = voice_input._record_until_silence()
                
                # Should return some audio data
                assert isinstance(audio, np.ndarray)
    
    def test_wait_for_wake_word_with_detector_detected(self, test_config, mock_sounddevice):
        """Test wait_for_wake_word when wake word is detected"""
        test_config.enable_wake_word = True
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector
                
                voice_input = VoiceInput(test_config)
                
                # Mock capture_audio
                with patch.object(voice_input, 'capture_audio') as mock_capture:
                    mock_capture.return_value = np.zeros(16000, dtype=np.float32)
                    
                    # Simulate wake word detected on first try
                    mock_detector.detect.return_value = True
                    
                    result = voice_input.wait_for_wake_word()
                    
                    assert result is True
                    mock_detector.detect.assert_called_once()
    
    def test_wait_for_wake_word_with_timeout(self, test_config, mock_sounddevice):
        """Test wait_for_wake_word with timeout"""
        test_config.enable_wake_word = True
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector
                
                voice_input = VoiceInput(test_config)
                
                # Mock capture_audio and event loop
                with patch.object(voice_input, 'capture_audio') as mock_capture:
                    mock_capture.return_value = np.zeros(16000, dtype=np.float32)
                    
                    # Never detect wake word
                    mock_detector.detect.return_value = False
                    
                    # Mock asyncio event loop to simulate timeout
                    with patch('asyncio.get_event_loop') as mock_loop:
                        mock_loop_instance = Mock()
                        mock_loop.return_value = mock_loop_instance
                        # Simulate time passing
                        mock_loop_instance.time.side_effect = [0, 0, 5.0, 10.0]
                        
                        result = voice_input.wait_for_wake_word(timeout=5.0)
                        
                        assert result is False
    
    @pytest.mark.asyncio
    async def test_wait_for_wake_word_async(self, test_config, mock_sounddevice):
        """Test async wait_for_wake_word"""
        test_config.enable_wake_word = False
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            result = await voice_input.wait_for_wake_word_async()
            
            # Should return True when no detector
            assert result is True
    
    def test_cleanup_with_wake_word_detector(self, test_config, mock_sounddevice):
        """Test cleanup with wake word detector"""
        test_config.enable_wake_word = True
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector
                
                voice_input = VoiceInput(test_config)
                voice_input.audio_buffer = [1, 2, 3]
                
                voice_input.cleanup()
                
                assert len(voice_input.audio_buffer) == 0
                mock_detector.cleanup.assert_called_once()
    
    def test_transcribe_async_error_handling(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test async transcription error handling"""
        with patch('src.voice_input.OpenAI'), patch('src.voice_input.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
            
            voice_input = VoiceInput(test_config)
            
            # Should return empty string on error
            import asyncio
            text = asyncio.run(voice_input.transcribe_async(sample_audio_chunk))
            
            assert text == ""


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
        
        # Simple detector always returns False in placeholder
        result = detector.detect(sample_audio_chunk)
        assert result is False
    
    def test_cleanup(self):
        """Test cleanup"""
        detector = SimpleWakeWordDetector("test")
        # Should not raise exception
        detector.cleanup()
    def test_init_wake_word_detector_exception(self, test_config, mock_sounddevice):
        """Test wake word detector initialization failure"""
        test_config.enable_wake_word = True
        test_config.wake_word = "test wake word"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector', side_effect=Exception("Init failed")):
                voice_input = VoiceInput(test_config)
                
                # Should handle exception gracefully
                assert voice_input.wake_word_detector is None
    
    def test_capture_audio_until_silence(self, test_config, mock_sounddevice):
        """Test audio capture until silence detected"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Mock _record_until_silence
            with patch.object(voice_input, '_record_until_silence', return_value=np.array([1, 2, 3])):
                audio = voice_input.capture_audio(duration=None)
                
                assert isinstance(audio, np.ndarray)
                assert len(audio) == 3
    
    def test_record_until_silence(self, test_config, mock_sounddevice):
        """Test recording until silence is detected"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            # Create mock audio chunks (loud then quiet)
            loud_chunk = np.ones((1024, 1), dtype=np.float32) * 0.5
            quiet_chunk = np.ones((1024, 1), dtype=np.float32) * 0.001
            
            # Mock InputStream to simulate audio recording
            call_count = [0]
            chunks = []
            
            class MockInputStream:
                def __init__(self, callback, **kwargs):
                    self.callback = callback
                    # Simulate a few loud chunks then quiet chunks
                    for i in range(3):
                        chunks.append(loud_chunk.copy())
                        self.callback(loud_chunk, 1024, None, None)
                    for i in range(10):  # Enough to trigger silence detection
                        chunks.append(quiet_chunk.copy())
                        self.callback(quiet_chunk, 1024, None, None)
                
                def __enter__(self):
                    return self
                
                def __exit__(self, *args):
                    pass
            
            with patch('src.voice_input.sd.InputStream', MockInputStream):
                with patch('src.voice_input.sd.sleep'):
                    audio = voice_input._record_until_silence()
                    
                    assert isinstance(audio, np.ndarray)
                    assert len(audio) > 0
    
    def test_record_until_silence_with_warning(self, test_config, mock_sounddevice):
        """Test recording with audio callback warning"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            quiet_chunk = np.ones((1024, 1), dtype=np.float32) * 0.001
            
            class MockInputStream:
                def __init__(self, callback, **kwargs):
                    self.callback = callback
                    # Trigger callback with status warning
                    for i in range(10):
                        self.callback(quiet_chunk, 1024, None, "Input overflow")
                
                def __enter__(self):
                    return self
                
                def __exit__(self, *args):
                    pass
            
            with patch('src.voice_input.sd.InputStream', MockInputStream):
                with patch('src.voice_input.sd.sleep'):
                    audio = voice_input._record_until_silence()
                    assert isinstance(audio, np.ndarray)
    
    def test_wait_for_wake_word_detected(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test wake word detection success"""
        test_config.enable_wake_word = True
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector
                mock_detector.detect.return_value = True
                
                voice_input = VoiceInput(test_config)
                
                # Mock capture_audio to return sample data
                with patch.object(voice_input, 'capture_audio', return_value=sample_audio_chunk):
                    result = voice_input.wait_for_wake_word(timeout=5.0)
                    
                    assert result is True
                    mock_detector.detect.assert_called()
    
    def test_wait_for_wake_word_timeout(self, test_config, mock_sounddevice, sample_audio_chunk):
        """Test wake word detection timeout"""
        test_config.enable_wake_word = True
        
        with patch('src.voice_input.OpenAI'), patch('src.voice_input.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector
                mock_detector.detect.return_value = False  # Never detected
                
                voice_input = VoiceInput(test_config)
                
                # Mock time and capture_audio with enough iterations to prevent StopIteration
                with patch('asyncio.get_event_loop') as mock_loop:
                    # Provide enough time values to cover multiple loop iterations
                    time_values = [0.0] + [i * 0.5 for i in range(1, 20)]  # 0.0, 0.5, 1.0, 1.5, ... 9.5
                    mock_loop.return_value.time.side_effect = time_values
                    
                    with patch.object(voice_input, 'capture_audio', return_value=sample_audio_chunk):
                        result = voice_input.wait_for_wake_word(timeout=5.0)
                        
                        assert result is False
                        # Verify capture_audio was called multiple times before timeout
                        assert voice_input.capture_audio.call_count > 0
    
    @pytest.mark.asyncio
    async def test_wait_for_wake_word_async(self, test_config, mock_sounddevice):
        """Test async wake word waiting"""
        test_config.enable_wake_word = False
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_input = VoiceInput(test_config)
            
            result = await voice_input.wait_for_wake_word_async()
            assert result is True
    
    def test_cleanup_with_wake_word_detector(self, test_config, mock_sounddevice):
        """Test cleanup with wake word detector"""
        test_config.enable_wake_word = True
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_input.SimpleWakeWordDetector') as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector
                
                voice_input = VoiceInput(test_config)
                voice_input.audio_buffer = [1, 2, 3]
                
                voice_input.cleanup()
                
                assert len(voice_input.audio_buffer) == 0
                mock_detector.cleanup.assert_called_once()
