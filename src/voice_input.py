"""
Voice Input Module - Speech-to-Text Processing
Uses OpenAI Whisper for high-accuracy speech recognition
"""

import asyncio
import io
import wave
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
from openai import OpenAI, AsyncOpenAI

from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class VoiceInput:
    """
    Voice Input Handler
    
    Captures audio from microphone and converts speech to text using
    OpenAI Whisper or local Whisper model.
    """
    
    def __init__(self, config: Config):
        """
        Initialize voice input
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.sample_rate = config.mic_sample_rate
        self.chunk_size = config.mic_chunk_size
        self.channels = config.mic_channels
        self.silence_threshold = config.silence_threshold
        self.silence_duration = config.silence_duration
        
        # Initialize OpenAI clients
        self.client = OpenAI(api_key=config.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=config.openai_api_key)
        
        # Audio buffer
        self.audio_buffer = []
        self.is_recording = False
        
        # Wake word detection (if enabled)
        self.wake_word_detector = None
        if config.enable_wake_word:
            self._init_wake_word_detector()
        
        logger.info("Voice input initialized")
    
    def _init_wake_word_detector(self):
        """Initialize wake word detection model"""
        try:
            # Placeholder for wake word detection
            # In production, use Porcupine or Snowboy
            logger.info(f"Wake word detection enabled: '{self.config.wake_word}'")
            self.wake_word_detector = SimpleWakeWordDetector(
                self.config.wake_word,
                sensitivity=self.config.wake_word_sensitivity
            )
        except Exception as e:
            logger.error(f"Failed to initialize wake word detector: {e}")
            self.wake_word_detector = None
    
    def is_ready(self) -> bool:
        """Check if voice input is ready"""
        try:
            devices = sd.query_devices()
            return len(devices) > 0
        except Exception:
            return False
    
    def capture_audio(self, duration: Optional[float] = None) -> np.ndarray:
        """
        Capture audio from microphone
        
        Args:
            duration: Recording duration in seconds. If None, records until silence.
            
        Returns:
            Audio data as numpy array
        """
        logger.info("Starting audio capture...")
        
        if duration:
            # Fixed duration recording
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32'
            )
            sd.wait()
            return audio_data.flatten()
        else:
            # Record until silence
            return self._record_until_silence()
    
    async def capture_audio_async(self, duration: Optional[float] = None) -> np.ndarray:
        """Async version of capture_audio"""
        return await asyncio.to_thread(self.capture_audio, duration)
    
    def _record_until_silence(self) -> np.ndarray:
        """Record audio until silence is detected"""
        audio_chunks = []
        silence_chunks = 0
        silence_threshold_chunks = int(
            self.silence_duration * self.sample_rate / self.chunk_size
        )
        
        logger.info("Recording... (speak now)")
        
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            
            audio_chunks.append(indata.copy())
            
            # Check for silence
            volume = np.abs(indata).mean()
            if volume < self.silence_threshold / 32768.0:  # Normalize to float32 range
                nonlocal silence_chunks
                silence_chunks += 1
            else:
                silence_chunks = 0
        
        # Start recording
        with sd.InputStream(
            callback=audio_callback,
            channels=self.channels,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size
        ):
            # Wait for silence
            while silence_chunks < silence_threshold_chunks:
                sd.sleep(100)
        
        logger.info("Recording finished")
        
        # Concatenate chunks
        if not audio_chunks:
            return np.array([])
        
        audio_data = np.concatenate(audio_chunks)
        return audio_data.flatten()
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio to text using Whisper
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Transcribed text
        """
        if len(audio_data) == 0:
            return ""
        
        try:
            # Convert numpy array to WAV bytes
            wav_bytes = self._numpy_to_wav(audio_data)
            
            # Create file-like object
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"
            
            # Transcribe with Whisper
            logger.info("Transcribing audio...")
            transcript = self.client.audio.transcriptions.create(
                model=self.config.openai_whisper_model,
                file=audio_file,
                response_format="text"
            )
            
            text = transcript.strip()
            logger.info(f"Transcription: {text}")
            
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return ""
    
    async def transcribe_async(self, audio_data: np.ndarray) -> str:
        """Async version of transcribe"""
        if len(audio_data) == 0:
            return ""
        
        try:
            # Convert numpy array to WAV bytes
            wav_bytes = self._numpy_to_wav(audio_data)
            
            # Create file-like object
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"
            
            # Transcribe with Whisper
            logger.info("Transcribing audio...")
            transcript = await self.async_client.audio.transcriptions.create(
                model=self.config.openai_whisper_model,
                file=audio_file,
                response_format="text"
            )
            
            text = transcript.strip()
            logger.info(f"Transcription: {text}")
            
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return ""
    
    def _numpy_to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convert numpy array to WAV format bytes"""
        # Ensure audio is in correct format
        audio_data = audio_data.astype(np.float32)
        
        # Convert to 16-bit PCM
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        return wav_buffer.getvalue()
    
    def wait_for_wake_word(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for wake word detection
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if wake word detected, False if timeout
        """
        if not self.wake_word_detector:
            return True  # If no wake word detector, always return True
        
        logger.info(f"Listening for wake word: '{self.config.wake_word}'")
        
        start_time = asyncio.get_event_loop().time() if timeout else None
        
        while True:
            # Capture short audio chunk
            audio_chunk = self.capture_audio(duration=1.0)
            
            # Check for wake word
            if self.wake_word_detector.detect(audio_chunk):
                logger.info("Wake word detected!")
                return True
            
            # Check timeout
            if timeout and start_time:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    logger.info("Wake word detection timeout")
                    return False
    
    async def wait_for_wake_word_async(self, timeout: Optional[float] = None) -> bool:
        """Async version of wait_for_wake_word"""
        return await asyncio.to_thread(self.wait_for_wake_word, timeout)
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up voice input")
        self.audio_buffer.clear()
        if self.wake_word_detector:
            self.wake_word_detector.cleanup()


class SimpleWakeWordDetector:
    """
    Simple wake word detector
    
    In production, replace with Porcupine, Snowboy, or similar
    """
    
    def __init__(self, wake_word: str, sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        logger.info(f"Simple wake word detector initialized: '{wake_word}'")
    
    def detect(self, audio_data: np.ndarray) -> bool:
        """
        Detect wake word in audio
        
        This is a placeholder implementation.
        In production, use a proper wake word detection model.
        """
        # For demo purposes, always return False
        # In production, implement actual wake word detection
        return False
    
    def cleanup(self):
        """Clean up resources"""
        pass
