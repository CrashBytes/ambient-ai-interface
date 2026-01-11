"""
Unit tests for Config class
Tests configuration loading, validation, and defaults
"""

import os
import pytest
from src.utils.config import Config


class TestConfig:
    """Test configuration management"""
    
    def test_config_defaults(self):
        """Test default configuration values"""
        # Clear environment to get true defaults
        os.environ.clear()
        os.environ["OPENAI_API_KEY"] = "test-key"
        
        config = Config()
        
        assert config.openai_model == "gpt-4-turbo-preview"
        assert config.mic_sample_rate == 16000
        assert config.tts_voice == "alloy"
        assert config.max_context_length == 10
        assert config.enable_wake_word is True  # Default is true
        assert config.log_level == "INFO"
    
    def test_config_from_env_vars(self):
        """Test loading configuration from environment variables"""
        os.environ["OPENAI_MODEL"] = "gpt-4"
        os.environ["MIC_SAMPLE_RATE"] = "48000"
        os.environ["TTS_VOICE"] = "nova"
        os.environ["MAX_CONTEXT_LENGTH"] = "20"
        
        config = Config()
        
        assert config.openai_model == "gpt-4"
        assert config.mic_sample_rate == 48000
        assert config.tts_voice == "nova"
        assert config.max_context_length == 20
    
    def test_config_boolean_parsing(self):
        """Test boolean environment variable parsing"""
        # Test true values
        os.environ["ENABLE_WAKE_WORD"] = "true"
        config1 = Config()
        assert config1.enable_wake_word is True
        
        # Test false values
        os.environ["ENABLE_WAKE_WORD"] = "false"
        config2 = Config()
        assert config2.enable_wake_word is False
        
        # Test case insensitivity
        os.environ["ENABLE_WAKE_WORD"] = "TRUE"
        config3 = Config()
        assert config3.enable_wake_word is True
    
    def test_config_numeric_parsing(self):
        """Test numeric environment variable parsing"""
        os.environ["MIC_SAMPLE_RATE"] = "44100"
        os.environ["SILENCE_DURATION"] = "3.5"
        os.environ["TTS_SPEED"] = "1.25"
        
        config = Config()
        
        assert config.mic_sample_rate == 44100
        assert config.silence_duration == 3.5
        assert config.tts_speed == 1.25
    
    def test_config_list_parsing(self):
        """Test list environment variable parsing"""
        os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8000,https://example.com"
        
        config = Config()
        
        assert len(config.allowed_origins) == 3
        assert "http://localhost:3000" in config.allowed_origins
        assert "https://example.com" in config.allowed_origins
    
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        config = Config()
        config.openai_api_key = "valid-key"
        config.mic_sample_rate = 16000
        config.tts_speed = 1.0
        config.nlu_temperature = 0.7
        
        assert config.validate() is True
    
    def test_config_validation_missing_api_key(self):
        """Test validation fails with missing API key"""
        os.environ["OPENAI_API_KEY"] = ""
        
        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            Config()
    
    def test_config_validation_invalid_sample_rate(self):
        """Test validation fails with invalid sample rate"""
        os.environ["MIC_SAMPLE_RATE"] = "5000"  # Too low
        
        with pytest.raises(ValueError, match="MIC_SAMPLE_RATE must be between"):
            Config()
        
        os.environ["MIC_SAMPLE_RATE"] = "50000"  # Too high
        
        with pytest.raises(ValueError, match="MIC_SAMPLE_RATE must be between"):
            Config()
    
    def test_config_validation_invalid_tts_speed(self):
        """Test validation fails with invalid TTS speed"""
        os.environ["TTS_SPEED"] = "0.1"  # Too low
        
        with pytest.raises(ValueError, match="TTS_SPEED must be between"):
            Config()
        
        os.environ["TTS_SPEED"] = "5.0"  # Too high
        
        with pytest.raises(ValueError, match="TTS_SPEED must be between"):
            Config()
    
    def test_config_validation_invalid_temperature(self):
        """Test validation fails with invalid NLU temperature"""
        os.environ["NLU_TEMPERATURE"] = "-0.5"  # Too low
        
        with pytest.raises(ValueError, match="NLU_TEMPERATURE must be between"):
            Config()
        
        os.environ["NLU_TEMPERATURE"] = "3.0"  # Too high
        
        with pytest.raises(ValueError, match="NLU_TEMPERATURE must be between"):
            Config()
    
    def test_config_all_audio_fields(self):
        """Test all audio configuration fields"""
        os.environ["MIC_SAMPLE_RATE"] = "48000"
        os.environ["MIC_CHUNK_SIZE"] = "2048"
        os.environ["MIC_CHANNELS"] = "2"
        os.environ["SILENCE_THRESHOLD"] = "1000"
        os.environ["SILENCE_DURATION"] = "1.5"
        
        config = Config()
        
        assert config.mic_sample_rate == 48000
        assert config.mic_chunk_size == 2048
        assert config.mic_channels == 2
        assert config.silence_threshold == 1000
        assert config.silence_duration == 1.5
    
    def test_config_all_security_fields(self):
        """Test all security configuration fields"""
        os.environ["ENABLE_ENCRYPTION"] = "true"
        os.environ["ENCRYPTION_KEY"] = "test-encryption-key"
        os.environ["LOG_USER_QUERIES"] = "false"
        os.environ["AUTO_DELETE_CONTEXT_DAYS"] = "7"
        
        config = Config()
        
        assert config.enable_encryption is True
        assert config.encryption_key == "test-encryption-key"
        assert config.log_user_queries is False
        assert config.auto_delete_context_days == 7
    
    def test_config_monitoring_fields(self):
        """Test monitoring and logging configuration"""
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["ENABLE_PROMETHEUS"] = "true"
        os.environ["PROMETHEUS_PORT"] = "9091"
        os.environ["ENABLE_HEALTH_CHECK"] = "false"
        os.environ["HEALTH_CHECK_PORT"] = "8081"
        
        config = Config()
        
        assert config.log_level == "DEBUG"
        assert config.enable_prometheus is True
        assert config.prometheus_port == 9091
        assert config.enable_health_check is False
        assert config.health_check_port == 8081
    
    def test_config_feature_flags(self):
        """Test feature flag configuration"""
        os.environ["ENABLE_CONVERSATION_ANALYTICS"] = "true"
        os.environ["ENABLE_VOICE_CLONING"] = "false"
        os.environ["ENABLE_REAL_TIME_TRANSLATION"] = "true"
        
        config = Config()
        
        assert config.enable_conversation_analytics is True
        assert config.enable_voice_cloning is False
        assert config.enable_real_time_translation is True
    
    def test_config_development_settings(self):
        """Test development configuration settings"""
        os.environ["DEBUG_MODE"] = "true"
        os.environ["ENABLE_MOCK_SENSORS"] = "true"
        os.environ["SAVE_AUDIO_FILES"] = "true"
        os.environ["AUDIO_SAVE_PATH"] = "/tmp/audio/"
        
        config = Config()
        
        assert config.debug_mode is True
        assert config.enable_mock_sensors is True
        assert config.save_audio_files is True
        assert config.audio_save_path == "/tmp/audio/"
    
    def test_config_cloud_deployment(self):
        """Test cloud deployment configuration"""
        os.environ["DEPLOYMENT_ENV"] = "production"
        os.environ["CLOUD_PROVIDER"] = "aws"
        
        config = Config()
        
        assert config.deployment_env == "production"
        assert config.cloud_provider == "aws"
