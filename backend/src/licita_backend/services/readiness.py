import logging

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("licita.database")


def database_is_ready(engine: Engine, request_id: str) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as error:
        logger.warning(
            "database_unavailable",
            extra={"request_id": request_id, "error_type": type(error).__name__},
        )
        return False
