"""
Logging Configuration
Structured logging with JSON support and Prometheus metrics
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Set up structured logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # JSON formatter for structured logging
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={'level': 'severity', 'timestamp': '@timestamp'}
    )
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger
    """
    return logging.getLogger(name)


def setup_monitoring(port: int = 9090):
    """
    Set up Prometheus metrics monitoring
    
    Args:
        port: Port for Prometheus metrics endpoint
    """
    try:
        from prometheus_client import start_http_server, Counter, Histogram, Gauge
        
        # Start Prometheus HTTP server
        start_http_server(port)
        
        # Define metrics
        global voice_input_latency, nlu_processing_time, context_memory_usage
        global active_conversations, error_rate
        
        voice_input_latency = Histogram(
            'voice_input_latency_seconds',
            'Latency of voice input processing',
            buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        )
        
        nlu_processing_time = Histogram(
            'nlu_processing_time_seconds',
            'Time to process NLU request',
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        context_memory_usage = Gauge(
            'context_memory_usage_bytes',
            'Memory used by context manager'
        )
        
        active_conversations = Gauge(
            'active_conversations_total',
            'Number of active conversations'
        )
        
        error_rate = Counter(
            'error_rate_total',
            'Total number of errors',
            ['error_type']
        )
        
        logger = get_logger(__name__)
        logger.info(f"Prometheus metrics server started on port {port}")
        
    except ImportError:
        logger = get_logger(__name__)
        logger.warning("prometheus_client not installed, monitoring disabled")


class LoggingContext:
    """Context manager for structured logging with additional fields"""
    
    def __init__(self, logger: logging.Logger, **kwargs):
        self.logger = logger
        self.extra = kwargs
    
    def __enter__(self):
        # Add context to logger
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Log exception if occurred
        if exc_type:
            self.logger.error(
                f"Exception in context: {exc_val}",
                extra=self.extra,
                exc_info=True
            )
        return False
