import logging
import json
import datetime
import traceback

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after log arguments are merged.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields but filter out keys that might be in record dict from basicConfig
        # For simplicity, we only add specifically passed extra if possible, 
        # but logging module merges them.
        # We can add thread/process info
        log_record["thread_id"] = record.thread
        log_record["process_id"] = record.process
        
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def configure_json_logging(logger_name="osp_server"):
    handler = logging.StreamHandler()
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(logger_name)
    if not logger.handlers:  # Avoid duplicate handlers
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Don't bubble up to root
    
    return logger
