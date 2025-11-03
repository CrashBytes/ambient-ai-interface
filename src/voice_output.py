"""
Voice Output Module - Text-to-Speech Synthesis
Uses OpenAI TTS for natural-sounding speech output
"""

import asyncio
import io
from pathlib import Path
from typing import Optional

import sounddevice as sd
import numpy as np
from pydub import AudioSegment
from openai import OpenAI, AsyncOpenAI

from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class VoiceOutput:
    """
    Voice Output Handler
    
    Converts text to speech using OpenAI TTS API and plays audio
    through the system's default audio output device.
    """
    
    def __init__(self, config: Config):
        """
        Initialize voice output
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.sample_rate = config.mic_sample_rate  # Use same sample rate as input
        
        # Initialize OpenAI clients
        self.client = OpenAI(api_key=config.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=config.openai_api_key)
        
        # TTS configuration
        self.tts_model = config.tts_model
        self.tts_voice = config.tts_voice
        self.tts_speed = config.tts_speed
        
        # Audio cache for frequently used phrases
        self.audio_cache = {}
        
        # Playback queue for streaming
        self.playback_queue = asyncio.Queue()
        
        logger.info(f"Voice output initialized (voice: {self.tts_voice})")
    
    def is_ready(self) -> bool:
        """Check if voice output is ready"""
        try:
            devices = sd.query_devices()
            return len(devices) > 0
        except Exception:
            return False
    
    def speak(self, text: str, use_cache: bool = True) -> None:
        """
        Convert text to speech and play it
        
        Args:
            text: Text to speak
            use_cache: Whether to use cached audio for this text
        """
        if not text or text.strip() == "":
            return
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(text)
            if use_cache and cache_key in self.audio_cache:
                logger.info(f"Using cached audio for: {text[:50]}...")
                audio_data = self.audio_cache[cache_key]
            else:
                # Generate speech
                logger.info(f"Generating speech: {text[:50]}...")
                audio_data = self._generate_speech(text)
                
                # Cache if enabled
                if use_cache and self.config.enable_caching:
                    self.audio_cache[cache_key] = audio_data
            
            # Play audio
            self._play_audio(audio_data)
            
        except Exception as e:
            logger.error(f"Speech synthesis error: {e}", exc_info=True)
    
    async def speak_async(self, text: str, use_cache: bool = True) -> None:
        """Async version of speak"""
        if not text or text.strip() == "":
            return
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(text)
            if use_cache and cache_key in self.audio_cache:
                logger.info(f"Using cached audio for: {text[:50]}...")
                audio_data = self.audio_cache[cache_key]
            else:
                # Generate speech
                logger.info(f"Generating speech: {text[:50]}...")
                audio_data = await self._generate_speech_async(text)
                
                # Cache if enabled
                if use_cache and self.config.enable_caching:
                    self.audio_cache[cache_key] = audio_data
            
            # Play audio
            await self._play_audio_async(audio_data)
            
        except Exception as e:
            logger.error(f"Speech synthesis error: {e}", exc_info=True)
    
    def _generate_speech(self, text: str) -> np.ndarray:
        """Generate speech from text using OpenAI TTS"""
        try:
            # Call OpenAI TTS API
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                speed=self.tts_speed
            )
            
            # Get MP3 audio bytes
            audio_bytes = response.content
            
            # Convert to numpy array
            audio_data = self._mp3_to_numpy(audio_bytes)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}", exc_info=True)
            raise
    
    async def _generate_speech_async(self, text: str) -> np.ndarray:
        """Async version of _generate_speech"""
        try:
            # Call OpenAI TTS API
            response = await self.async_client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                speed=self.tts_speed
            )
            
            # Get MP3 audio bytes
            audio_bytes = response.content
            
            # Convert to numpy array
            audio_data = self._mp3_to_numpy(audio_bytes)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}", exc_info=True)
            raise
    
    def _mp3_to_numpy(self, mp3_bytes: bytes) -> np.ndarray:
        """Convert MP3 bytes to numpy array"""
        # Load MP3 with pydub
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        
        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples())
        
        # Normalize to float32 range [-1, 1]
        if audio.sample_width == 1:  # 8-bit
            samples = samples.astype(np.float32) / 128.0
        elif audio.sample_width == 2:  # 16-bit
            samples = samples.astype(np.float32) / 32768.0
        elif audio.sample_width == 4:  # 32-bit
            samples = samples.astype(np.float32) / 2147483648.0
        
        # Handle stereo to mono conversion if needed
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)
        
        return samples
    
    def _play_audio(self, audio_data: np.ndarray) -> None:
        """Play audio through default audio device"""
        try:
            logger.info("Playing audio...")
            
            # Play audio
            sd.play(audio_data, samplerate=self.sample_rate)
            sd.wait()  # Wait until audio finishes playing
            
            logger.info("Audio playback complete")
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}", exc_info=True)
            raise
    
    async def _play_audio_async(self, audio_data: np.ndarray) -> None:
        """Async version of _play_audio"""
        await asyncio.to_thread(self._play_audio, audio_data)
    
    def play_chime(self, chime_type: str = "wake") -> None:
        """
        Play a chime sound
        
        Args:
            chime_type: Type of chime ('wake', 'success', 'error')
        """
        # Generate simple tone
        duration = 0.2  # seconds
        frequency = {
            "wake": 880,  # A5
            "success": 1046,  # C6
            "error": 440  # A4
        }.get(chime_type, 880)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        tone = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Apply fade in/out
        fade_samples = int(0.01 * self.sample_rate)
        tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
        tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        self._play_audio(tone)
    
    async def play_chime_async(self, chime_type: str = "wake") -> None:
        """Async version of play_chime"""
        await asyncio.to_thread(self.play_chime, chime_type)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        # Use first 100 chars as key (enough to differentiate)
        return f"{self.tts_voice}:{text[:100]}"
    
    def clear_cache(self) -> None:
        """Clear audio cache"""
        logger.info(f"Clearing audio cache ({len(self.audio_cache)} items)")
        self.audio_cache.clear()
    
    def preload_phrases(self, phrases: list[str]) -> None:
        """
        Preload common phrases into cache
        
        Args:
            phrases: List of phrases to preload
        """
        logger.info(f"Preloading {len(phrases)} phrases...")
        
        for phrase in phrases:
            try:
                cache_key = self._get_cache_key(phrase)
                if cache_key not in self.audio_cache:
                    audio_data = self._generate_speech(phrase)
                    self.audio_cache[cache_key] = audio_data
            except Exception as e:
                logger.warning(f"Failed to preload phrase '{phrase[:30]}...': {e}")
        
        logger.info(f"Preloading complete ({len(self.audio_cache)} items cached)")
    
    async def preload_phrases_async(self, phrases: list[str]) -> None:
        """Async version of preload_phrases"""
        await asyncio.to_thread(self.preload_phrases, phrases)
    
    def save_audio(self, text: str, filename: str) -> Path:
        """
        Save generated audio to file
        
        Args:
            text: Text to convert to speech
            filename: Output filename (without extension)
            
        Returns:
            Path to saved file
        """
        audio_data = self._generate_speech(text)
        
        # Ensure output directory exists
        output_dir = Path(self.config.audio_save_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as WAV
        output_path = output_dir / f"{filename}.wav"
        
        # Convert to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Save
        import wave
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        logger.info(f"Audio saved to {output_path}")
        return output_path
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up voice output")
        self.clear_cache()
