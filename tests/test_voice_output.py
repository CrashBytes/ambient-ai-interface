"""
Unit tests for Voice Output
Tests text-to-speech synthesis, audio playback, and caching
"""

import pytest
import numpy as np
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock, mock_open

from src.voice_output import VoiceOutput


@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice module"""
    with patch('src.voice_output.sd') as mock_sd:
        # Mock query_devices
        mock_sd.query_devices.return_value = [
            {'name': 'Default Speaker', 'max_output_channels': 2}
        ]
        # Mock play and wait
        mock_sd.play = Mock()
        mock_sd.wait = Mock()
        yield mock_sd


@pytest.fixture
def mock_audio_segment():
    """Mock AudioSegment"""
    with patch('src.voice_output.AudioSegment') as mock_segment:
        # Create mock audio object with small data to prevent memory issues
        mock_audio = Mock()
        # Use small array: 1000 samples instead of 16000
        mock_audio.get_array_of_samples.return_value = np.zeros(1000, dtype=np.int16)
        mock_audio.sample_width = 2  # 16-bit
        mock_audio.channels = 1  # Mono
        mock_segment.from_mp3.return_value = mock_audio
        yield mock_segment


@pytest.fixture
def sample_mp3_bytes():
    """Generate small sample MP3 bytes (reduced size)"""
    # Use smaller fake data to prevent memory issues
    return b'fake_mp3_data' * 100  # Was 1000, now 100


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
            
            # Should not raise exception
            voice_output.speak("")
            voice_output.speak("   ")
            
            # Should not have called play
            mock_sounddevice.play.assert_not_called()
    
    def test_speak_success(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test successful speech generation and playback"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            # Mock TTS response
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
            
            # First call should generate speech
            voice_output.speak("Test phrase", use_cache=True)
            assert mock_client.audio.speech.create.call_count == 1
            
            # Second call should use cache
            voice_output.speak("Test phrase", use_cache=True)
            assert mock_client.audio.speech.create.call_count == 1  # Still 1
            
            # Cache should have the phrase
            assert len(voice_output.audio_cache) == 1
    
    def test_speak_error_handling(self, test_config, mock_sounddevice, mock_audio_segment):
        """Test speech error handling"""
        with patch('openai.OpenAI') as mock_openai, patch('openai.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.audio.speech.create.side_effect = Exception("API Error")
            
            voice_output = VoiceOutput(test_config)
            
            # Should not raise exception
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
            
            # Should not raise exception
            await voice_output.speak_async("")
    
    def test_play_chime_wake(self, test_config, mock_sounddevice):
        """Test playing wake chime"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            voice_output.play_chime("wake")
            
            mock_sounddevice.play.assert_called_once()
            # Check that audio data was generated
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
                mock_audio.sample_width = 2  # 16-bit
                mock_audio.channels = 1  # Mono
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
                # Stereo data (alternating left/right channels)
                mock_audio.get_array_of_samples.return_value = np.array([100, 200, 300, 400])
                mock_audio.sample_width = 2  # 16-bit
                mock_audio.channels = 2  # Stereo
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                # Stereo should be converted to mono
                assert len(audio_data) == 2  # 4 samples / 2 channels
    
    def test_clear_cache(self, test_config, mock_sounddevice):
        """Test clearing audio cache"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            # Add some items to cache
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
            
            # Should have called TTS for each phrase
            assert mock_client.audio.speech.create.call_count == 3
            # Cache should have all phrases
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
            
            assert key1 == key2  # Same text should have same key
            assert key1 != key3  # Different text should have different key
    
    def test_save_audio(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test saving audio to file"""
        test_config.audio_save_path = "/tmp/audio"
        
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            # Create a proper wave file mock
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
                # Verify wave file methods were called
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
    @pytest.mark.asyncio
    async def test_speak_async_with_cache_hit(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test async speak with cache hit"""
        test_config.enable_caching = True
        
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            # First call to populate cache
            await voice_output.speak_async("Cached phrase", use_cache=True)
            
            # Second call should hit cache
            mock_client.audio.speech.create.reset_mock()
            await voice_output.speak_async("Cached phrase", use_cache=True)
            
            # Should not have called TTS again
            mock_client.audio.speech.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_speak_async_with_caching_disabled(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test async speak with caching disabled"""
        test_config.enable_caching = False
        
        with patch('src.voice_output.OpenAI'), patch('src.voice_output.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            await voice_output.speak_async("Test", use_cache=True)
            
            # Cache should be empty (caching disabled)
            assert len(voice_output.audio_cache) == 0
    
    @pytest.mark.asyncio
    async def test_speak_async_error_handling(self, test_config, mock_sounddevice, mock_audio_segment):
        """Test async speak error handling"""
        with patch('src.voice_output.OpenAI'), patch('src.voice_output.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_client.audio.speech.create.side_effect = Exception("TTS API Error")
            
            voice_output = VoiceOutput(test_config)
            
            # Should not raise exception
            await voice_output.speak_async("Error test", use_cache=False)
    
    @pytest.mark.asyncio
    async def test_generate_speech_async_error(self, test_config, mock_sounddevice, mock_audio_segment):
        """Test _generate_speech_async error handling"""
        with patch('src.voice_output.OpenAI'), patch('src.voice_output.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_client.audio.speech.create.side_effect = Exception("API Error")
            
            voice_output = VoiceOutput(test_config)
            
            # Should raise exception
            with pytest.raises(Exception, match="API Error"):
                await voice_output._generate_speech_async("Test")
    
    def test_play_audio_error(self, test_config, mock_sounddevice):
        """Test _play_audio error handling"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            # Mock play to raise exception
            mock_sounddevice.play.side_effect = Exception("Playback error")
            
            audio_data = np.zeros(1000, dtype=np.float32)
            
            # Should raise exception
            with pytest.raises(Exception, match="Playback error"):
                voice_output._play_audio(audio_data)
    
    @pytest.mark.asyncio
    async def test_play_audio_async(self, test_config, mock_sounddevice):
        """Test async audio playback"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            audio_data = np.zeros(1000, dtype=np.float32)
            
            await voice_output._play_audio_async(audio_data)
            
            mock_sounddevice.play.assert_called_once()
    
    def test_play_chime_unknown_type(self, test_config, mock_sounddevice):
        """Test playing chime with unknown type (uses default)"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            # Unknown chime type should use default (wake)
            voice_output.play_chime("unknown_type")
            
            mock_sounddevice.play.assert_called_once()
            # Check that audio data was generated
            call_args = mock_sounddevice.play.call_args
            assert isinstance(call_args[0][0], np.ndarray)
    
    def test_preload_phrases_with_error(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test preload_phrases with one phrase failing"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            
            # First call succeeds, second fails, third succeeds
            mock_client.audio.speech.create.side_effect = [
                mock_response,
                Exception("TTS Error"),
                mock_response
            ]
            
            voice_output = VoiceOutput(test_config)
            
            phrases = ["Success 1", "Will Fail", "Success 2"]
            voice_output.preload_phrases(phrases)
            
            # Should have 2 phrases cached (1 failed)
            assert len(voice_output.audio_cache) == 2
    
    @pytest.mark.asyncio
    async def test_preload_phrases_async_error(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test async preload with error"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.audio.speech.create.side_effect = Exception("TTS Error")
            
            voice_output = VoiceOutput(test_config)
            
            await voice_output.preload_phrases_async(["Error phrase"])
            
            # Cache should be empty (all failed)
            assert len(voice_output.audio_cache) == 0
    
    def test_mp3_to_numpy_8bit(self, test_config, mock_sounddevice):
        """Test MP3 to numpy conversion - 8-bit audio"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                mock_audio.get_array_of_samples.return_value = np.array([100, 200, 50])
                mock_audio.sample_width = 1  # 8-bit
                mock_audio.channels = 1
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                # 8-bit should be normalized by 128
                assert len(audio_data) == 3
    
    def test_mp3_to_numpy_32bit(self, test_config, mock_sounddevice):
        """Test MP3 to numpy conversion - 32-bit audio"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                mock_audio.get_array_of_samples.return_value = np.array([1000000, 2000000])
                mock_audio.sample_width = 4  # 32-bit
                mock_audio.channels = 1
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                # 32-bit should be normalized by 2147483648
                assert len(audio_data) == 2
    def test_speak_caching_disabled(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test speech with caching disabled in config"""
        test_config.enable_caching = False
        
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            # First call should generate speech
            voice_output.speak("Test phrase", use_cache=True)
            assert mock_client.audio.speech.create.call_count == 1
            
            # Second call should also generate (caching disabled)
            voice_output.speak("Test phrase", use_cache=True)
            assert mock_client.audio.speech.create.call_count == 2  # Called again
            
            # Cache should be empty
            assert len(voice_output.audio_cache) == 0
    
    @pytest.mark.asyncio
    async def test_speak_async_caching_disabled(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test async speech with caching disabled"""
        test_config.enable_caching = False
        
        with patch('src.voice_output.OpenAI'), patch('src.voice_output.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3_bytes
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            await voice_output.speak_async("Test", use_cache=True)
            
            # Cache should be empty since caching disabled
            assert len(voice_output.audio_cache) == 0
    
    def test_play_audio_error(self, test_config, mock_sounddevice):
        """Test audio playback error handling"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            # Make play raise an exception
            mock_sounddevice.play.side_effect = Exception("Playback failed")
            
            audio_data = np.array([0.1, 0.2, 0.3])
            
            with pytest.raises(Exception, match="Playback failed"):
                voice_output._play_audio(audio_data)
    
    def test_preload_phrases_with_failure(self, test_config, mock_sounddevice, mock_audio_segment, sample_mp3_bytes):
        """Test preload phrases with some failures"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # Make first call succeed, second fail, third succeed
            mock_response_success = Mock()
            mock_response_success.content = sample_mp3_bytes
            
            mock_client.audio.speech.create.side_effect = [
                mock_response_success,  # Success
                Exception("TTS failed"),  # Failure
                mock_response_success,  # Success
            ]
            
            voice_output = VoiceOutput(test_config)
            
            phrases = ["Success 1", "Failure", "Success 2"]
            voice_output.preload_phrases(phrases)
            
            # Should have cached 2 successful phrases
            assert len(voice_output.audio_cache) == 2
    
    def test_mp3_to_numpy_8bit(self, test_config, mock_sounddevice):
        """Test MP3 conversion with 8-bit audio"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                mock_audio.get_array_of_samples.return_value = np.array([100, 200, 50], dtype=np.int8)
                mock_audio.sample_width = 1  # 8-bit
                mock_audio.channels = 1
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                assert len(audio_data) == 3
    
    def test_mp3_to_numpy_32bit(self, test_config, mock_sounddevice):
        """Test MP3 conversion with 32-bit audio"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                mock_audio.get_array_of_samples.return_value = np.array([1000, 2000, 3000], dtype=np.int32)
                mock_audio.sample_width = 4  # 32-bit
                mock_audio.channels = 1
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                assert len(audio_data) == 3
