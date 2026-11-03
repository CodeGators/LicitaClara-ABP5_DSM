"""Provisionamento explícito de grupos NOLOGIN e grants; exige administrador do banco."""

import argparse

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, create_engine, text

from licita_backend.models import Base

ROLES = ("licita_api", "licita_collector", "licita_processing", "licita_migrator")


def ident(value: str) -> str:
    # Identificadores do schema são configuração administrativa, nunca entrada HTTP.
    return '"' + value.replace('"', '""') + '"'


def bootstrap_roles(connection: Connection, schema: str = "public") -> None:
    for role in ROLES:
        if not connection.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
        ):
            connection.exec_driver_sql(
                f"CREATE ROLE {ident(role)} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"
            )
    connection.exec_driver_sql(f"REVOKE CREATE ON SCHEMA {ident(schema)} FROM PUBLIC")
    connection.exec_driver_sql(
        f"GRANT USAGE ON SCHEMA {ident(schema)} TO " + ", ".join(map(ident, ROLES))
    )
    connection.exec_driver_sql(f"GRANT CREATE ON SCHEMA {ident(schema)} TO licita_migrator")


def apply_permissions(connection: Connection, schema: str = "public") -> None:
    for table in Base.metadata.sorted_tables:
        qualified = f"{ident(schema)}.{ident(table.name)}"
        connection.exec_driver_sql(
            f"REVOKE ALL ON TABLE {qualified} FROM licita_api, licita_collector, licita_processing"
        )
        connection.exec_driver_sql(
            f"GRANT SELECT ON TABLE {qualified} TO licita_api, licita_processing"
        )
        domain = table.info["domain"]
        if domain == "coleta":
            connection.exec_driver_sql(
                f"GRANT SELECT, INSERT ON TABLE {qualified} TO licita_collector"
            )
        if table.name == "execucoes_coleta":
            connection.exec_driver_sql(
                "GRANT UPDATE (status, iniciado_em, concluido_em, erro) "
                f"ON {qualified} TO licita_collector"
            )
        if domain in (
            "importacao",
            "base",
            "cadastro",
            "identidade",
            "dados",
            "analise",
            "publicacao",
        ):
            connection.exec_driver_sql(f"GRANT INSERT ON TABLE {qualified} TO licita_processing")
        if table.name == "importacoes":
            connection.exec_driver_sql(
                "GRANT UPDATE (status, aceitos, rejeitados, diagnostico, concluido_em) "
                f"ON {qualified} TO licita_processing"
            )
        if table.name == "versoes_base":
            connection.exec_driver_sql(f"GRANT UPDATE (status) ON {qualified} TO licita_processing")
        if table.name == "execucoes_analise":
            connection.exec_driver_sql(
                f"GRANT UPDATE (status, concluido_em, erro) ON {qualified} TO licita_processing"
            )
        if table.name == "publicacoes_analise":
            connection.exec_driver_sql(f"GRANT UPDATE (ativa) ON {qualified} TO licita_processing")
        if table.name in ("usuarios", "revisoes", "relatorios"):
            connection.exec_driver_sql(f"GRANT INSERT ON TABLE {qualified} TO licita_api")
        if table.name == "usuarios":
            connection.exec_driver_sql(f"GRANT UPDATE (nome) ON {qualified} TO licita_api")
        if table.name == "relatorios":
            connection.exec_driver_sql(
                "GRANT UPDATE (status, snapshot, chave_objeto, sha256, erro, concluido_em) "
                f"ON {qualified} TO licita_processing"
            )


def provision_local_logins(connection, url):
    """Credenciais locais geradas uma vez; não reutilizar este comando para provisionar nuvem."""
    import secrets
    from pathlib import Path

    from dotenv import dotenv_values
    from psycopg import sql
    from sqlalchemy.engine import make_url

    if url.host not in ("127.0.0.1", "localhost"):
        raise ValueError("Criação automática de logins restrita ao PostgreSQL local")
    path = Path(".env")
    if not path.exists():
        raise ValueError("Configure .env antes de criar os logins locais")
    environment = dotenv_values(path)
    urls = {}
    for key, login, role in [
        ("DATABASE_URL", "licita_api_local", "licita_api"),
        ("COLLECTOR_DATABASE_URL", "licita_collector_local", "licita_collector"),
        ("PROCESSING_DATABASE_URL", "licita_processing_local", "licita_processing"),
    ]:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname=:login"), {"login": login}
        )
        if exists:
            stored = environment.get(key)
            if not stored or make_url(stored).username != login:
                raise ValueError("Login local existente sem credencial correspondente no .env")
            urls[key] = stored
        else:
            password = secrets.token_urlsafe(32)
            with connection.connection.driver_connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
                    ).format(sql.Identifier(login), sql.Literal(password))
                )
            urls[key] = url.set(username=login, password=password).render_as_string(
                hide_password=False
            )
        connection.exec_driver_sql(f"GRANT {ident(role)} TO {ident(login)}")
    return urls


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    migration_database_url: SecretStr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["bootstrap", "apply", "local-logins"])
    parser.add_argument("--schema", default="public")
    args = parser.parse_args()
    engine = create_engine(
        AdminSettings().migration_database_url.get_secret_value(), hide_parameters=True
    )
    try:
        with engine.begin() as connection:
            if args.operation == "bootstrap":
                bootstrap_roles(connection, args.schema)
            elif args.operation == "apply":
                apply_permissions(connection, args.schema)
            else:
                urls = provision_local_logins(connection, engine.url)
        if args.operation == "local-logins":
            from pathlib import Path

            from dotenv import set_key

            for name, url in urls.items():
                set_key(".env", name, url, quote_mode="never")
            Path(".env").chmod(0o600)
    finally:
        engine.dispose()
    print("Provisionamento concluído. Credenciais locais, quando geradas, ficam apenas no .env.")


if __name__ == "__main__":
    main()
