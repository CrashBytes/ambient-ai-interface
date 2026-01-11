"""
Unit tests for Voice Output
Tests text-to-speech synthesis, audio playback, and caching
"""

import pytest
import numpy as np
import io
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock, mock_open

# Mock pydub before importing voice_output (Python 3.14 compatibility)
sys.modules['pydub'] = MagicMock()
sys.modules['pydub.AudioSegment'] = MagicMock()

from src.voice_output import VoiceOutput


@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice module"""
    with patch('src.voice_output.sd') as mock_sd:
        mock_sd.query_devices.return_value = [
            {'name': 'Default Speaker', 'max_output_channels': 2}
        ]
        mock_sd.play = Mock()
        mock_sd.wait = Mock()
        yield mock_sd


@pytest.fixture
def mock_audio_segment():
    """Mock AudioSegment"""
    with patch('src.voice_output.AudioSegment') as mock_segment:
        mock_audio = Mock()
        mock_audio.get_array_of_samples.return_value = np.random.randint(
            -32768, 32767, 1000, dtype=np.int16  # Reduced from 16000 to 1000
        )
        mock_audio.sample_width = 2  # 16-bit
        mock_audio.channels = 1  # Mono
        mock_segment.from_mp3.return_value = mock_audio
        yield mock_segment


@pytest.fixture
def sample_mp3_bytes():
    """Generate small sample MP3 bytes"""
    return b'fake_mp3_data' * 100  # Reduced from 1000 to 100


class TestVoiceOutput:
    """Test voice output functionality"""
    
    def test_initialization(self, test_config, mock_sounddevice):
        """Test voice output initialization"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            assert voice_output.config == test_config
            assert voice_output.tts_model == test_config.tts_model
            assert voice_output.tts_voice == test_config.tts_voice
            assert voice_output.tts_speed == test_config.tts_speed
            assert isinstance(voice_output.audio_cache, dict)
    
    def test_is_ready_success(self, test_config, mock_sounddevice):
        """Test is_ready when devices available"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            assert voice_output.is_ready() is True
            mock_sounddevice.query_devices.assert_called()
    
    def test_is_ready_failure(self, test_config):
        """Test is_ready when no devices available"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.sd') as mock_sd:
                mock_sd.query_devices.side_effect = Exception("No devices")
                
                voice_output = VoiceOutput(test_config)
                assert voice_output.is_ready() is False
    
    def test_speak_empty_text(self, test_config, mock_sounddevice):
        """Test speak with empty text"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            voice_output.speak("")
            voice_output.speak("   ")
            
            mock_sounddevice.play.assert_not_called()
    
    def test_speak_success(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test successful speech generation and playback"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            voice_output.speak("Hello world", use_cache=False)
            
            mock_client.audio.speech.create.assert_called_once()
            mock_sounddevice.play.assert_called_once()
            mock_sounddevice.wait.assert_called_once()
    
    def test_speak_with_caching(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test speech with caching enabled"""
        test_config.enable_caching = True
        
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            voice_output.speak("Test phrase", use_cache=True)
            assert mock_client.audio.speech.create.call_count == 1
            
            voice_output.speak("Test phrase", use_cache=True)
            assert mock_client.audio.speech.create.call_count == 1
            
            assert len(voice_output.audio_cache) == 1
    
    def test_speak_error_handling(self, test_config, mock_sounddevice, mock_audio_segment):
        """Test speech error handling"""
        with patch('openai.OpenAI') as mock_openai, patch('openai.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.audio.speech.create.side_effect = Exception("API Error")
            
            voice_output = VoiceOutput(test_config)
            voice_output.speak("Test", use_cache=False)
    
    @pytest.mark.asyncio
    async def test_speak_async(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test async speech generation"""
        with patch('src.voice_output.OpenAI'), patch('src.voice_output.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            await voice_output.speak_async("Hello async", use_cache=False)
            
            mock_client.audio.speech.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_speak_async_empty(self, test_config, mock_sounddevice):
        """Test async speak with empty text"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            await voice_output.speak_async("")
    
    def test_play_chime_wake(self, test_config, mock_sounddevice):
        """Test playing wake chime"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            voice_output.play_chime("wake")
            
            mock_sounddevice.play.assert_called_once()
            call_args = mock_sounddevice.play.call_args
            assert isinstance(call_args[0][0], np.ndarray)
    
    def test_play_chime_success(self, test_config, mock_sounddevice):
        """Test playing success chime"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            voice_output.play_chime("success")
            mock_sounddevice.play.assert_called_once()
    
    def test_play_chime_error(self, test_config, mock_sounddevice):
        """Test playing error chime"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            voice_output.play_chime("error")
            mock_sounddevice.play.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_play_chime_async(self, test_config, mock_sounddevice):
        """Test async chime playback"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            await voice_output.play_chime_async("wake")
            mock_sounddevice.play.assert_called_once()
    
    def test_mp3_to_numpy_mono(self, test_config, mock_sounddevice):
        """Test MP3 to numpy conversion - mono"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                mock_audio.get_array_of_samples.return_value = np.array([100, 200, 300])
                mock_audio.sample_width = 2
                mock_audio.channels = 1
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                assert len(audio_data) == 3
    
    def test_mp3_to_numpy_stereo(self, test_config, mock_sounddevice):
        """Test MP3 to numpy conversion - stereo"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                mock_audio.get_array_of_samples.return_value = np.array([100, 200, 300, 400])
                mock_audio.sample_width = 2
                mock_audio.channels = 2
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                assert len(audio_data) == 2
    
    def test_clear_cache(self, test_config, mock_sounddevice):
        """Test clearing audio cache"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            voice_output.audio_cache['key1'] = np.array([1, 2, 3])
            voice_output.audio_cache['key2'] = np.array([4, 5, 6])
            
            assert len(voice_output.audio_cache) == 2
            
            voice_output.clear_cache()
            
            assert len(voice_output.audio_cache) == 0
    
    def test_preload_phrases(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test preloading phrases"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            phrases = ["Hello", "Goodbye", "Thank you"]
            voice_output.preload_phrases(phrases)
            
            assert mock_client.audio.speech.create.call_count == 3
            assert len(voice_output.audio_cache) == 3
    
    @pytest.mark.asyncio
    async def test_preload_phrases_async(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test async phrase preloading"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            await voice_output.preload_phrases_async(["Test"])
            
            assert len(voice_output.audio_cache) == 1
    
    def test_get_cache_key(self, test_config, mock_sounddevice):
        """Test cache key generation"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            key1 = voice_output._get_cache_key("Test phrase")
            key2 = voice_output._get_cache_key("Test phrase")
            key3 = voice_output._get_cache_key("Different phrase")
            
            assert key1 == key2
            assert key1 != key3
    
    def test_save_audio(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test saving audio to file"""
        test_config.audio_save_path = "/tmp/audio"
        
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            mock_wav_file = MagicMock()
            mock_wav_context = MagicMock()
            mock_wav_context.__enter__.return_value = mock_wav_file
            mock_wav_context.__exit__.return_value = None
            
            with patch('pathlib.Path.mkdir'), \
                 patch('wave.open', return_value=mock_wav_context):
                voice_output = VoiceOutput(test_config)
                
                output_path = voice_output.save_audio("Test text", "test_file")
                
                assert isinstance(output_path, Path)
                assert "test_file.wav" in str(output_path)
                mock_wav_file.setnchannels.assert_called_once_with(1)
                mock_wav_file.setsampwidth.assert_called_once_with(2)
                mock_wav_file.setframerate.assert_called_once()
                mock_wav_file.writeframes.assert_called_once()
    
    def test_cleanup(self, test_config, mock_sounddevice):
        """Test cleanup"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            voice_output.audio_cache['test'] = np.array([1, 2, 3])
            
            voice_output.cleanup()
            
            assert len(voice_output.audio_cache) == 0
