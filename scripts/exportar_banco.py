"""Exporta o PostgreSQL local para uma cópia privada, sem modificar dados ou treinar modelos."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def export(destination):
    settings = dotenv_values(ROOT / ".env")
    user, database = settings.get("POSTGRES_USER"), settings.get("POSTGRES_DB")
    if not user or not database:
        raise ValueError("Configure POSTGRES_USER e POSTGRES_DB no .env local.")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = destination / f"licita-clara-{stamp}.dump"
    command = [
        "docker",
        "compose",
        "--env-file",
        str(ROOT / ".env"),
        "-f",
        str(ROOT / "infra/compose.yaml"),
        "exec",
        "-T",
        "postgres",
        "pg_dump",
        "-U",
        user,
        "-d",
        database,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
    ]
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.PIPE)
        if result.returncode:
            raise RuntimeError("Falha ao exportar. Confira se o PostgreSQL local está disponível.")
        digest = hashlib.sha256()
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        manifest = {
            "arquivo": target.name,
            "bytes": target.stat().st_size,
            "sha256": digest.hexdigest(),
            "criado_em_utc": stamp,
            "formato": "pg_dump_custom",
            "proprietarios_e_grants": "reconfigurar_no_destino",
        }
        metadata = target.with_suffix(".json")
        with os.fdopen(os.open(metadata, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
            json.dump(manifest, out, ensure_ascii=False, indent=2)
            out.write("\n")
        return target, manifest
    except Exception:
        target.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=ROOT / "data/deploy")
    args = parser.parse_args()
    try:
        target, manifest = export(args.saida)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Exportação não concluída: {error}")
        return 1
    print(f"Cópia criada: {target}")
    print(f"Tamanho: {manifest['bytes']} bytes | SHA-256: {manifest['sha256']}")
    print("Banco local preservado. A cópia não contém as senhas dos papéis PostgreSQL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
