#!/usr/bin/env python3
"""
Logging and error handling module for Quokka regression testing web generator.
Provides comprehensive logging, error handling, and validation utilities.
"""

import os
import sys
import logging
import traceback
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
from datetime import datetime
import json


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration for the web generator.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        log_format: Optional custom log format string
        
    Returns:
        Configured logger instance
    """
    # Default format if not provided
    if log_format is None:
        log_format = '[%(asctime)s] [%(levelname)8s] [%(name)s:%(lineno)d] %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get logger for web generator
    logger = logging.getLogger('web_generator')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Could not create log file {log_file}: {e}")
    
    return logger


def get_logger(name: str = 'web_generator') -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_exception(func: Callable) -> Callable:
    """
    Decorator to log exceptions in functions.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with exception logging
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {str(e)}")
            logger.debug(f"Traceback:\n{traceback.format_exc()}")
            raise
    return wrapper


def safe_execution(
    func: Callable,
    default_return: Any = None,
    error_message: Optional[str] = None,
    reraise: bool = False
) -> Callable:
    """
    Decorator for safe function execution with error recovery.
    
    Args:
        func: Function to wrap
        default_return: Value to return on error
        error_message: Custom error message
        reraise: Whether to re-raise the exception after logging
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if error_message:
                logger.error(f"{error_message}: {str(e)}")
            else:
                logger.error(f"Error in {func.__name__}: {str(e)}")
            
            logger.debug(f"Traceback:\n{traceback.format_exc()}")
            
            if reraise:
                raise
            return default_return
    return wrapper


class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass


class FileOperationError(Exception):
    """Custom exception for file operation errors."""
    pass


def validate_directory(path: str, create: bool = False) -> bool:
    """
    Validate that a directory exists and is accessible.
    
    Args:
        path: Directory path to validate
        create: Whether to create the directory if it doesn't exist
        
    Returns:
        True if directory is valid
        
    Raises:
        FileOperationError: If directory is invalid or cannot be created
    """
    logger = get_logger()
    
    if not path:
        raise FileOperationError("Directory path cannot be empty")
    
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise FileOperationError(f"Path exists but is not a directory: {path}")
        if not os.access(path, os.R_OK):
            raise FileOperationError(f"Directory is not readable: {path}")
        logger.debug(f"Directory validated: {path}")
        return True
    
    if create:
        try:
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created directory: {path}")
            return True
        except Exception as e:
            raise FileOperationError(f"Could not create directory {path}: {e}")
    
    raise FileOperationError(f"Directory does not exist: {path}")


def validate_file(path: str, must_exist: bool = True) -> bool:
    """
    Validate that a file path is valid.
    
    Args:
        path: File path to validate
        must_exist: Whether the file must exist
        
    Returns:
        True if file is valid
        
    Raises:
        FileOperationError: If file is invalid
    """
    logger = get_logger()
    
    if not path:
        raise FileOperationError("File path cannot be empty")
    
    if must_exist:
        if not os.path.exists(path):
            raise FileOperationError(f"File does not exist: {path}")
        if not os.path.isfile(path):
            raise FileOperationError(f"Path exists but is not a file: {path}")
        if not os.access(path, os.R_OK):
            raise FileOperationError(f"File is not readable: {path}")
    else:
        # Just check if parent directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            raise FileOperationError(f"Parent directory does not exist: {parent_dir}")
    
    logger.debug(f"File validated: {path}")
    return True


def validate_timestamp(timestamp: str) -> bool:
    """
    Validate that a timestamp string is in the correct format.
    
    Args:
        timestamp: Timestamp string to validate (format: YYYYMMDDHHMMSS)
        
    Returns:
        True if timestamp is valid
        
    Raises:
        DataValidationError: If timestamp is invalid
    """
    if not timestamp:
        raise DataValidationError("Timestamp cannot be empty")
    
    if not timestamp.isdigit():
        raise DataValidationError(f"Timestamp must contain only digits: {timestamp}")
    
    if len(timestamp) != 14:
        raise DataValidationError(f"Timestamp must be 14 digits (YYYYMMDDHHMMSS): {timestamp}")
    
    try:
        datetime.strptime(timestamp, "%Y%m%d%H%M%S")
    except ValueError as e:
        raise DataValidationError(f"Invalid timestamp format: {timestamp} - {e}")
    
    return True


def validate_performance_data(data: Dict[str, Any]) -> bool:
    """
    Validate performance data structure.
    
    Args:
        data: Performance data dictionary to validate
        
    Returns:
        True if data is valid
        
    Raises:
        DataValidationError: If data is invalid
    """
    required_fields = ['test_name', 'cores', 'gpus_per_task']
    
    for field in required_fields:
        if field not in data:
            raise DataValidationError(f"Missing required field: {field}")
    
    # Validate numeric fields
    if not isinstance(data.get('cores'), (int, float)) or data['cores'] <= 0:
        raise DataValidationError(f"Invalid cores value: {data.get('cores')}")
    
    if not isinstance(data.get('gpus_per_task'), (int, float)) or data['gpus_per_task'] < 0:
        raise DataValidationError(f"Invalid gpus_per_task value: {data.get('gpus_per_task')}")
    
    # Validate optional numeric fields if present
    if 'zone_updates_per_sec_per_gpu' in data:
        value = data['zone_updates_per_sec_per_gpu']
        if value != 'N/A' and not isinstance(value, (int, float)):
            raise DataValidationError(f"Invalid zone_updates_per_sec_per_gpu value: {value}")
    
    return True


def safe_write_file(path: str, content: str, backup: bool = True) -> bool:
    """
    Safely write content to a file with optional backup.
    
    Args:
        path: File path to write to
        content: Content to write
        backup: Whether to create a backup of existing file
        
    Returns:
        True if write was successful
        
    Raises:
        FileOperationError: If write fails
    """
    logger = get_logger()
    
    try:
        # Validate path
        validate_file(path, must_exist=False)
        
        # Create backup if file exists
        if backup and os.path.exists(path):
            backup_path = f"{path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                with open(path, 'r') as f:
                    backup_content = f.read()
                with open(backup_path, 'w') as f:
                    f.write(backup_content)
                logger.debug(f"Created backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
        
        # Write content
        with open(path, 'w') as f:
            f.write(content)
        
        logger.debug(f"Successfully wrote file: {path}")
        return True
        
    except Exception as e:
        raise FileOperationError(f"Failed to write file {path}: {e}")


def safe_read_file(path: str, default: Optional[str] = None) -> Optional[str]:
    """
    Safely read content from a file.
    
    Args:
        path: File path to read from
        default: Default value if read fails
        
    Returns:
        File content or default value
    """
    logger = get_logger()
    
    try:
        validate_file(path, must_exist=True)
        with open(path, 'r') as f:
            content = f.read()
        logger.debug(f"Successfully read file: {path}")
        return content
    except Exception as e:
        logger.warning(f"Could not read file {path}: {e}")
        return default


class ErrorRecovery:
    """Context manager for error recovery with rollback capability."""
    
    def __init__(self, description: str = "operation"):
        """
        Initialize error recovery context.
        
        Args:
            description: Description of the operation
        """
        self.description = description
        self.logger = get_logger()
        self.rollback_actions = []
        self.success = False
    
    def add_rollback(self, action: Callable, *args, **kwargs):
        """
        Add a rollback action to execute on failure.
        
        Args:
            action: Function to call for rollback
            *args: Positional arguments for the action
            **kwargs: Keyword arguments for the action
        """
        self.rollback_actions.append((action, args, kwargs))
    
    def __enter__(self):
        """Enter the context."""
        self.logger.debug(f"Starting {self.description}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context and handle any errors.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if exc_type is None:
            self.success = True
            self.logger.debug(f"Completed {self.description} successfully")
        else:
            self.logger.error(f"Failed {self.description}: {exc_val}")
            self.logger.debug(f"Traceback:\n{traceback.format_exception(exc_type, exc_val, exc_tb)}")
            
            # Execute rollback actions
            for action, args, kwargs in reversed(self.rollback_actions):
                try:
                    action(*args, **kwargs)
                    self.logger.debug(f"Executed rollback: {action.__name__}")
                except Exception as e:
                    self.logger.warning(f"Rollback failed for {action.__name__}: {e}")
        
        # Don't suppress the exception
        return False


def log_performance_metrics(metrics: Dict[str, Any]):
    """
    Log performance metrics in a structured format.
    
    Args:
        metrics: Dictionary of performance metrics
    """
    logger = get_logger()
    
    try:
        # Format metrics as JSON for structured logging
        metrics_json = json.dumps(metrics, indent=2)
        logger.info(f"Performance metrics:\n{metrics_json}")
    except Exception as e:
        logger.warning(f"Could not log performance metrics: {e}")


def create_error_page(error_message: str, details: Optional[str] = None) -> str:
    """
    Create an HTML error page for display.
    
    Args:
        error_message: Main error message
        details: Optional detailed error information
        
    Returns:
        HTML content for error page
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Quokka Regression Testing</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .error-container {{
            max-width: 800px;
            margin: 50px auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #dc3545;
        }}
        h1 {{
            color: #dc3545;
            margin-top: 0;
        }}
        .error-message {{
            font-size: 1.1em;
            color: #333;
            margin: 20px 0;
        }}
        .error-details {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
            color: #666;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 20px;
        }}
        a {{
            color: #007bff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>⚠️ Error Generating Page</h1>
        <div class="error-message">{error_message}</div>
    """
    
    if details:
        html += f"""
        <div class="error-details">{details}</div>
        """
    
    html += f"""
        <div class="timestamp">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        <p><a href="../index.html">← Back to Index</a></p>
    </div>
</body>
</html>"""
    
    return html