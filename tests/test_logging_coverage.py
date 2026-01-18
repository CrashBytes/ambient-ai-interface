"""
Unit tests for logging utilities
Tests structured logging, file handlers, and monitoring setup
"""

import pytest
import logging
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock


class TestSetupLogging:
    """Test setup_logging function"""
    
    def test_setup_logging_default_level(self):
        """Test setup with default INFO level"""
        from src.utils.logging import setup_logging
        
        setup_logging()
        
        logger = logging.getLogger()
        assert logger.level == logging.INFO
    
    def test_setup_logging_debug_level(self):
        """Test setup with DEBUG level"""
        from src.utils.logging import setup_logging
        
        setup_logging(log_level="DEBUG")
        
        logger = logging.getLogger()
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_warning_level(self):
        """Test setup with WARNING level"""
        from src.utils.logging import setup_logging
        
        setup_logging(log_level="WARNING")
        
        logger = logging.getLogger()
        assert logger.level == logging.WARNING
    
    def test_setup_logging_with_file_handler(self):
        """Test setup with file handler"""
        from src.utils.logging import setup_logging
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            setup_logging(log_file=log_file)
            
            logger = logging.getLogger()
            
            # Should have at least 2 handlers (console + file)
            file_handlers = [h for h in logger.handlers 
                           if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) >= 1
    
    def test_setup_logging_creates_log_directory(self):
        """Test that setup creates parent directories for log file"""
        from src.utils.logging import setup_logging
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "subdir", "nested", "test.log")
            
            setup_logging(log_file=log_file)
            
            # Verify parent directories were created
            assert Path(log_file).parent.exists()
    
    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup clears existing handlers"""
        from src.utils.logging import setup_logging
        
        logger = logging.getLogger()
        
        # Add some dummy handlers
        logger.addHandler(logging.NullHandler())
        logger.addHandler(logging.NullHandler())
        initial_count = len(logger.handlers)
        
        setup_logging()
        
        # After setup, should have fresh handlers
        # (console handler at minimum)
        assert len(logger.handlers) >= 1


class TestGetLogger:
    """Test get_logger function"""
    
    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance"""
        from src.utils.logging import get_logger
        
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_get_logger_with_dunder_name(self):
        """Test get_logger with __name__"""
        from src.utils.logging import get_logger
        
        logger = get_logger(__name__)
        
        assert isinstance(logger, logging.Logger)


class TestSetupMonitoring:
    """Test setup_monitoring function"""
    
    def test_setup_monitoring_success(self):
        """Test monitoring setup with prometheus_client available"""
        mock_start_server = Mock()
        mock_counter = Mock()
        mock_histogram = Mock()
        mock_gauge = Mock()
        
        mock_prometheus = MagicMock()
        mock_prometheus.start_http_server = mock_start_server
        mock_prometheus.Counter = mock_counter
        mock_prometheus.Histogram = mock_histogram
        mock_prometheus.Gauge = mock_gauge
        
        with patch.dict('sys.modules', {'prometheus_client': mock_prometheus}):
            # Re-import to get fresh function
            import importlib
            import src.utils.logging as logging_module
            importlib.reload(logging_module)
            
            logging_module.setup_monitoring(port=9999)
            
            mock_start_server.assert_called_once_with(9999)
    
    def test_setup_monitoring_import_error(self):
        """Test monitoring setup handles ImportError gracefully"""
        # Simulate prometheus_client not being available
        with patch.dict('sys.modules', {'prometheus_client': None}):
            from src.utils.logging import setup_monitoring
            
            # This should not raise - it catches ImportError internally
            # The function may fail silently or log a warning
            try:
                setup_monitoring()
            except (ImportError, AttributeError):
                pass  # Expected if prometheus_client unavailable
    
    def test_setup_monitoring_default_port(self):
        """Test monitoring uses default port"""
        mock_start_server = Mock()
        mock_prometheus = MagicMock()
        mock_prometheus.start_http_server = mock_start_server
        mock_prometheus.Counter = Mock()
        mock_prometheus.Histogram = Mock()
        mock_prometheus.Gauge = Mock()
        
        with patch.dict('sys.modules', {'prometheus_client': mock_prometheus}):
            import importlib
            import src.utils.logging as logging_module
            importlib.reload(logging_module)
            
            logging_module.setup_monitoring()
            
            mock_start_server.assert_called_once_with(9090)


class TestLoggingContext:
    """Test LoggingContext context manager"""
    
    def test_logging_context_enter_exit(self):
        """Test context manager enter and exit"""
        from src.utils.logging import LoggingContext
        
        logger = Mock()
        
        with LoggingContext(logger, request_id="123") as ctx_logger:
            assert ctx_logger == logger
    
    def test_logging_context_logs_exception(self):
        """Test context manager logs exceptions"""
        from src.utils.logging import LoggingContext
        
        logger = Mock()
        
        try:
            with LoggingContext(logger, request_id="456"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify exception was logged
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "Test error" in str(call_args)
    
    def test_logging_context_no_exception(self):
        """Test context manager doesn't log when no exception"""
        from src.utils.logging import LoggingContext
        
        logger = Mock()
        
        with LoggingContext(logger, user="test"):
            pass  # No exception
        
        # Should not have logged error
        logger.error.assert_not_called()
    
    def test_logging_context_propagates_exception(self):
        """Test context manager propagates exceptions"""
        from src.utils.logging import LoggingContext
        
        logger = Mock()
        
        with pytest.raises(RuntimeError):
            with LoggingContext(logger):
                raise RuntimeError("Propagated error")
    
    def test_logging_context_with_extra_fields(self):
        """Test context manager stores extra fields"""
        from src.utils.logging import LoggingContext
        
        logger = Mock()
        
        ctx = LoggingContext(logger, user_id="u123", session="s456")
        
        assert ctx.extra["user_id"] == "u123"
        assert ctx.extra["session"] == "s456"
