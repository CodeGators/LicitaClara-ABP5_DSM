"""Logs JSON sem query strings, corpos de requisição ou detalhes de conexão."""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "error_type"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    logger = logging.getLogger("licita")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
