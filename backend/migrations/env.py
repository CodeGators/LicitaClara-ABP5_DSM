"""Migrações explícitas; nunca acionadas pela inicialização da API."""

from alembic import context
from licita_backend.models import Base
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, pool, text

config = context.config
target_metadata = config.attributes.get("target_metadata", Base.metadata)


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    migration_database_url: SecretStr


def run(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url="postgresql+psycopg://",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run(config.attributes["connection"])
else:
    engine = create_engine(
        MigrationSettings().migration_database_url.get_secret_value(),
        poolclass=pool.NullPool,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c lock_timeout=5000 -c statement_timeout=60000",
        },
    )
    try:
        with engine.connect() as connection:
            role = context.get_x_argument(as_dictionary=True).get("role")
            if role is not None:
                if role != "licita_migrator":
                    raise ValueError("Papel de migração permitido: licita_migrator")
                connection.execute(text("SET ROLE licita_migrator"))
                connection.commit()
            run(connection)
    finally:
        engine.dispose()
