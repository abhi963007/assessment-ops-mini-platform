import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional

# Context variable to hold per-request metadata
request_context: ContextVar[dict] = ContextVar('request_context', default={})


def get_request_id() -> str:
    """Get current request ID from context, or generate one."""
    ctx = request_context.get()
    return ctx.get('request_id', str(uuid.uuid4()))


class StructuredFormatter(logging.Formatter):
    """
    Monolog-style structured JSON log formatter.
    Every log line includes: timestamp, level, message, channel, context, extra.
    """

    def format(self, record: logging.LogRecord) -> str:
        ctx = request_context.get()

        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'channel': getattr(record, 'channel', 'app'),
            'context': {
                'request_id': ctx.get('request_id'),
                'attempt_id': getattr(record, 'attempt_id', None),
                'student_id': getattr(record, 'student_id', None),
                **{k: v for k, v in ctx.items() if k != 'request_id'},
            },
            'extra': {
                'ip': ctx.get('ip'),
                'user_agent': ctx.get('user_agent'),
                'query_params': ctx.get('query_params'),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                **getattr(record, 'extra_data', {}),
            },
        }

        # Remove None values for cleaner output
        log_entry['context'] = {
            k: v for k, v in log_entry['context'].items() if v is not None
        }
        log_entry['extra'] = {
            k: v for k, v in log_entry['extra'].items() if v is not None
        }

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = 'INFO') -> logging.Logger:
    """Configure and return the application logger with structured JSON output."""
    logger = logging.getLogger('assessment')
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

    return logger


def get_logger(channel: str = 'app') -> logging.LoggerAdapter:
    """Get a logger adapter with a specific channel."""
    logger = logging.getLogger('assessment')
    return ChannelAdapter(logger, channel=channel)


class ChannelAdapter(logging.LoggerAdapter):
    """Logger adapter that injects channel into log records."""

    def __init__(self, logger: logging.Logger, channel: str = 'app'):
        super().__init__(logger, {})
        self.channel = channel

    def process(self, msg, kwargs):
        # Inject channel into the record
        extra = kwargs.get('extra', {})
        extra['channel'] = self.channel
        kwargs['extra'] = extra
        return msg, kwargs

    def log_with_data(
        self,
        level: int,
        msg: str,
        attempt_id: Optional[str] = None,
        student_id: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ):
        """Log with additional structured data."""
        extra = {'channel': self.channel}
        if attempt_id:
            extra['attempt_id'] = str(attempt_id)
        if student_id:
            extra['student_id'] = str(student_id)
        if extra_data:
            extra['extra_data'] = extra_data
        self.logger.log(level, msg, extra=extra)
