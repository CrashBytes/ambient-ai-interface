"""
Additional tests for voice_output.py to improve coverage
Focuses on edge cases and uncovered code paths
"""

import pytest
import numpy as np
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock

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
            -32768, 32767, 1000, dtype=np.int16
        )
        mock_audio.sample_width = 2
        mock_audio.channels = 1
        mock_segment.from_mp3.return_value = mock_audio
        yield mock_segment


class TestVoiceOutputCoverage:
    """Additional tests to improve coverage"""
    
    def test_speak_with_cache_hit_and_play(self, test_config, mock_sounddevice, mock_audio_segment):
        """Test speak() using cached audio and actually playing it"""
        test_config.enable_caching = True
        sample_mp3 = b'fake_mp3_data' * 100
        
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            # First call - generate and cache
            voice_output.speak("Test phrase", use_cache=True)
            first_play_count = mock_sounddevice.play.call_count
            
            # Second call - use cache and play (lines 106-107)
            voice_output.speak("Test phrase", use_cache=True)
            
            # Should have called play twice (once for first, once for cached)
            assert mock_sounddevice.play.call_count == first_play_count + 1
            # But only generated speech once
            assert mock_client.audio.speech.create.call_count == 1
    
    @pytest.mark.asyncio
    async def test_speak_async_with_cache_hit_and_play(self, test_config, mock_sounddevice, mock_audio_segment):
        """Test speak_async() using cached audio (lines 120-121)"""
        test_config.enable_caching = True
        sample_mp3 = b'fake_mp3_data' * 100
        
        with patch('src.voice_output.OpenAI'), patch('src.voice_output.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3
            mock_client.audio.speech.create.return_value = mock_response
            
            voice_output = VoiceOutput(test_config)
            
            # First call - generate and cache
            await voice_output.speak_async("Test phrase", use_cache=True)
            first_play_count = mock_sounddevice.play.call_count
            
            # Second call - use cache and play (lines 120-121)
            await voice_output.speak_async("Test phrase", use_cache=True)
            
            # Should have called play twice
            assert mock_sounddevice.play.call_count == first_play_count + 1
            # But only generated speech once
            assert mock_client.audio.speech.create.call_count == 1
    
    def test_mp3_to_numpy_8bit(self, test_config, mock_sounddevice):
        """Test MP3 to numpy conversion with 8-bit audio (line 165)"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                # Use valid int8 range: -128 to 127
                mock_audio.get_array_of_samples.return_value = np.array([100, 120, -50], dtype=np.int8)
                mock_audio.sample_width = 1  # 8-bit
                mock_audio.channels = 1
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                assert audio_data.dtype == np.float32
    
    def test_mp3_to_numpy_32bit(self, test_config, mock_sounddevice):
        """Test MP3 to numpy conversion with 32-bit audio (line 167)"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            with patch('src.voice_output.AudioSegment') as mock_segment:
                mock_audio = Mock()
                mock_audio.get_array_of_samples.return_value = np.array(
                    [1000000, 2000000, 3000000], dtype=np.int32
                )
                mock_audio.sample_width = 4  # 32-bit
                mock_audio.channels = 1
                mock_segment.from_mp3.return_value = mock_audio
                
                voice_output = VoiceOutput(test_config)
                audio_data = voice_output._mp3_to_numpy(b'fake_mp3')
                
                assert isinstance(audio_data, np.ndarray)
                assert audio_data.dtype == np.float32
    
    def test_play_audio_exception(self, test_config, mock_sounddevice):
        """Test _play_audio exception handling (lines 179, 182-183)"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            # Mock sd.play to raise exception
            mock_sounddevice.play.side_effect = Exception("Playback device error")
            
            test_audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
            
            # Should raise the exception
            with pytest.raises(Exception) as exc_info:
                voice_output._play_audio(test_audio)
            
            assert "Playback device error" in str(exc_info.value)
    
    def test_play_chime_unknown_type(self, test_config, mock_sounddevice):
        """Test play_chime with unknown chime type (uses default)"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            voice_output = VoiceOutput(test_config)
            
            # Unknown chime type should use default frequency
            voice_output.play_chime("unknown_type")
            
            mock_sounddevice.play.assert_called_once()
            call_args = mock_sounddevice.play.call_args
            assert isinstance(call_args[0][0], np.ndarray)
    
    def test_preload_phrases_with_failures(self, test_config, mock_sounddevice, mock_audio_segment):
        """Test preload_phrases with some phrases failing (lines 264-265)"""
        sample_mp3 = b'fake_mp3_data' * 100
        
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.content = sample_mp3
            
            # First call succeeds, second fails, third succeeds
            mock_client.audio.speech.create.side_effect = [
                mock_response,
                Exception("API Error"),
                mock_response
            ]
            
            voice_output = VoiceOutput(test_config)
            
            phrases = ["Phrase 1", "Phrase 2", "Phrase 3"]
            voice_output.preload_phrases(phrases)
            
            # Should have attempted all 3
            assert mock_client.audio.speech.create.call_count == 3
            # Only 2 should be cached (1st and 3rd succeeded)
            assert len(voice_output.audio_cache) == 2
    
    def test_generate_speech_exception_propagation(self, test_config, mock_sounddevice):
        """Test that _generate_speech exceptions are properly raised"""
        with patch('src.voice_output.OpenAI') as mock_openai, patch('src.voice_output.AsyncOpenAI'):
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            voice_output = VoiceOutput(test_config)
            
            # Now set the side effect after VoiceOutput is created
            mock_client.audio.speech.create.side_effect = Exception("TTS API Error")
            
            with pytest.raises(Exception) as exc_info:
                voice_output._generate_speech("Test")
            
            assert "TTS API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_speech_async_exception_propagation(self, test_config, mock_sounddevice):
        """Test that _generate_speech_async exceptions are properly raised"""
        with patch('src.voice_output.OpenAI'), patch('src.voice_output.AsyncOpenAI') as mock_async_openai:
            mock_client = AsyncMock()
            mock_async_openai.return_value = mock_client
            
            voice_output = VoiceOutput(test_config)
            
            # Now set the side effect after VoiceOutput is created
            mock_client.audio.speech.create.side_effect = Exception("Async TTS API Error")
            
            with pytest.raises(Exception) as exc_info:
                await voice_output._generate_speech_async("Test")
            
            assert "Async TTS API Error" in str(exc_info.value)
