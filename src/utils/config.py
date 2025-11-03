"""
Configuration Management
Loads and validates configuration from environment variables
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """
    Application Configuration
    
    Loads all configuration from environment variables with sensible defaults
    """
    
    # OpenAI Configuration
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"))
    openai_whisper_model: str = field(default_factory=lambda: os.getenv("OPENAI_WHISPER_MODEL", "whisper-1"))
    
    # Audio Configuration
    mic_sample_rate: int = field(default_factory=lambda: int(os.getenv("MIC_SAMPLE_RATE", "16000")))
    mic_chunk_size: int = field(default_factory=lambda: int(os.getenv("MIC_CHUNK_SIZE", "1024")))
    mic_channels: int = field(default_factory=lambda: int(os.getenv("MIC_CHANNELS", "1")))
    silence_threshold: int = field(default_factory=lambda: int(os.getenv("SILENCE_THRESHOLD", "500")))
    silence_duration: float = field(default_factory=lambda: float(os.getenv("SILENCE_DURATION", "2.0")))
    
    # Voice Output Configuration
    tts_model: str = field(default_factory=lambda: os.getenv("TTS_MODEL", "tts-1-hd"))
    tts_voice: str = field(default_factory=lambda: os.getenv("TTS_VOICE", "alloy"))
    tts_speed: float = field(default_factory=lambda: float(os.getenv("TTS_SPEED", "1.0")))
    
    # Context and Memory Configuration
    max_context_length: int = field(default_factory=lambda: int(os.getenv("MAX_CONTEXT_LENGTH", "10")))
    context_window_hours: int = field(default_factory=lambda: int(os.getenv("CONTEXT_WINDOW_HOURS", "24")))
    enable_persistent_memory: bool = field(default_factory=lambda: os.getenv("ENABLE_PERSISTENT_MEMORY", "true").lower() == "true")
    memory_db_path: str = field(default_factory=lambda: os.getenv("MEMORY_DB_PATH", "./data/context.db"))
    
    # Wake Word Configuration
    enable_wake_word: bool = field(default_factory=lambda: os.getenv("ENABLE_WAKE_WORD", "true").lower() == "true")
    wake_word: str = field(default_factory=lambda: os.getenv("WAKE_WORD", "hey assistant"))
    wake_word_sensitivity: float = field(default_factory=lambda: float(os.getenv("WAKE_WORD_SENSITIVITY", "0.5")))
    
    # Natural Language Understanding
    nlu_temperature: float = field(default_factory=lambda: float(os.getenv("NLU_TEMPERATURE", "0.7")))
    nlu_max_tokens: int = field(default_factory=lambda: int(os.getenv("NLU_MAX_TOKENS", "500")))
    nlu_system_prompt: Optional[str] = field(default_factory=lambda: os.getenv("NLU_SYSTEM_PROMPT"))
    
    # Sensor Integration
    enable_sensors: bool = field(default_factory=lambda: os.getenv("ENABLE_SENSORS", "false").lower() == "true")
    sensor_update_interval: int = field(default_factory=lambda: int(os.getenv("SENSOR_UPDATE_INTERVAL", "30")))
    temperature_sensor_pin: int = field(default_factory=lambda: int(os.getenv("TEMPERATURE_SENSOR_PIN", "4")))
    motion_sensor_pin: int = field(default_factory=lambda: int(os.getenv("MOTION_SENSOR_PIN", "17")))
    light_sensor_pin: int = field(default_factory=lambda: int(os.getenv("LIGHT_SENSOR_PIN", "27")))
    
    # Security and Privacy
    enable_encryption: bool = field(default_factory=lambda: os.getenv("ENABLE_ENCRYPTION", "true").lower() == "true")
    encryption_key: Optional[str] = field(default_factory=lambda: os.getenv("ENCRYPTION_KEY"))
    log_user_queries: bool = field(default_factory=lambda: os.getenv("LOG_USER_QUERIES", "false").lower() == "true")
    auto_delete_context_days: int = field(default_factory=lambda: int(os.getenv("AUTO_DELETE_CONTEXT_DAYS", "30")))
    
    # Monitoring and Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    enable_prometheus: bool = field(default_factory=lambda: os.getenv("ENABLE_PROMETHEUS", "false").lower() == "true")
    prometheus_port: int = field(default_factory=lambda: int(os.getenv("PROMETHEUS_PORT", "9090")))
    enable_health_check: bool = field(default_factory=lambda: os.getenv("ENABLE_HEALTH_CHECK", "true").lower() == "true")
    health_check_port: int = field(default_factory=lambda: int(os.getenv("HEALTH_CHECK_PORT", "8080")))
    
    # Performance Optimization
    enable_caching: bool = field(default_factory=lambda: os.getenv("ENABLE_CACHING", "true").lower() == "true")
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "300")))
    use_local_whisper: bool = field(default_factory=lambda: os.getenv("USE_LOCAL_WHISPER", "false").lower() == "true")
    local_whisper_model_size: str = field(default_factory=lambda: os.getenv("LOCAL_WHISPER_MODEL_SIZE", "base"))
    
    # Advanced Features
    enable_spatial_audio: bool = field(default_factory=lambda: os.getenv("ENABLE_SPATIAL_AUDIO", "false").lower() == "true")
    enable_emotion_detection: bool = field(default_factory=lambda: os.getenv("ENABLE_EMOTION_DETECTION", "false").lower() == "true")
    enable_multi_language: bool = field(default_factory=lambda: os.getenv("ENABLE_MULTI_LANGUAGE", "false").lower() == "true")
    default_language: str = field(default_factory=lambda: os.getenv("DEFAULT_LANGUAGE", "en"))
    
    # Development Settings
    debug_mode: bool = field(default_factory=lambda: os.getenv("DEBUG_MODE", "false").lower() == "true")
    enable_mock_sensors: bool = field(default_factory=lambda: os.getenv("ENABLE_MOCK_SENSORS", "false").lower() == "true")
    save_audio_files: bool = field(default_factory=lambda: os.getenv("SAVE_AUDIO_FILES", "false").lower() == "true")
    audio_save_path: str = field(default_factory=lambda: os.getenv("AUDIO_SAVE_PATH", "./data/audio/"))
    
    # API Configuration
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    api_workers: int = field(default_factory=lambda: int(os.getenv("API_WORKERS", "1")))
    enable_cors: bool = field(default_factory=lambda: os.getenv("ENABLE_CORS", "true").lower() == "true")
    allowed_origins: list = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","))
    
    # Database Configuration
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/ambient_ai.db"))
    
    # Cloud Deployment
    deployment_env: str = field(default_factory=lambda: os.getenv("DEPLOYMENT_ENV", "development"))
    cloud_provider: str = field(default_factory=lambda: os.getenv("CLOUD_PROVIDER", "none"))
    
    # Feature Flags
    enable_conversation_analytics: bool = field(default_factory=lambda: os.getenv("ENABLE_CONVERSATION_ANALYTICS", "false").lower() == "true")
    enable_voice_cloning: bool = field(default_factory=lambda: os.getenv("ENABLE_VOICE_CLONING", "false").lower() == "true")
    enable_real_time_translation: bool = field(default_factory=lambda: os.getenv("ENABLE_REAL_TIME_TRANSLATION", "false").lower() == "true")
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        # Check required fields
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        # Validate numeric ranges
        if self.mic_sample_rate < 8000 or self.mic_sample_rate > 48000:
            raise ValueError("MIC_SAMPLE_RATE must be between 8000 and 48000")
        
        if self.tts_speed < 0.25 or self.tts_speed > 4.0:
            raise ValueError("TTS_SPEED must be between 0.25 and 4.0")
        
        if self.nlu_temperature < 0 or self.nlu_temperature > 2.0:
            raise ValueError("NLU_TEMPERATURE must be between 0 and 2.0")
        
        return True
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()
