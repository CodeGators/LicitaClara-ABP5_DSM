"""Instalação da equipe: integridade, retomada, registro local e publicação real."""

import csv
import io
import json
import tarfile
from argparse import Namespace
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from licita_collector.config import Settings as CollectorSettings
from licita_collector.repository import Repository as CollectorRepository
from licita_ml import team
from licita_ml.diagnostics import checksum
from licita_ml.grouped import training
from licita_shared.storage.local import LocalObjectStorage
from test_grouped_inference import grouped_case as grouped_case
from test_grouped_inference import trained_groups as trained_groups
from test_grouped_temporal import grouped_source as grouped_source
from test_organized import sources as raw_sources
from test_organized import write


def manifest(folder, output):
    rows = [
        {"arquivo": folder.name + "/" + p.name, "sha256": checksum(p), "bytes": p.stat().st_size}
        for p in sorted(folder.glob("*.zip"))
    ]
    output.write_text(json.dumps({"versao": 1, "arquivos": rows}))
    return output


def test_inputs_missing_corrupt_and_traversal_are_rejected(tmp_path):
    folder, _ = raw_sources.__wrapped__(tmp_path)
    spec = manifest(folder, tmp_path / "inputs.json")
    assert len(team.inputs(tmp_path, spec)) == 4
    target = next(folder.glob("*.zip"))
    target.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="divergente"):
        team.inputs(tmp_path, spec)
    target.unlink()
    with pytest.raises(ValueError, match="Falta"):
        team.inputs(tmp_path, spec)
    spec.write_text(json.dumps({"versao": 1, "arquivos": [{"arquivo": "../outside"}]}))
    with pytest.raises(ValueError, match="fora"):
        team.inputs(tmp_path, spec)


def test_check_does_not_create_database_or_prepare_models(tmp_path, monkeypatch, capsys):
    folder, _ = raw_sources.__wrapped__(tmp_path)
    spec = manifest(folder, tmp_path / "inputs.json")
    monkeypatch.setattr(team, "database", lambda *_: pytest.fail("Não acessar banco"))
    team.populate(Namespace(dados=tmp_path, manifesto=spec, conferir=True))
    assert "4 ZIPs conferidos" in capsys.readouterr().out


def test_state_lock_releases_after_failure(tmp_path):
    with team.locked(tmp_path):
        with pytest.raises(ValueError, match="Já existe"):
            with team.locked(tmp_path):
                pass
    with pytest.raises(RuntimeError):
        with team.locked(tmp_path):
            raise RuntimeError("interrupção")
    with team.locked(tmp_path):
        pass


def test_progress_counts_only_completed_groups():
    stream = io.StringIO()
    with team.Progress(stream) as bar:
        bar.update(0, 20)
        assert "0.0%" in stream.getvalue() and "calculando" in stream.getvalue()
        bar.update(5, 20)
        assert "25.0%" in stream.getvalue() and "5/20 grupos" in stream.getvalue()
        bar.update(20, 20)
    assert "100.0%" in stream.getvalue()


@pytest.mark.integration
def test_local_registration_replays_without_duplicating_files(database, tmp_path):
    _, engine = database
    folder, _ = raw_sources.__wrapped__(tmp_path)
    cfg = CollectorSettings(
        _env_file=None,
        collector_database_url="postgresql+psycopg://test:test@localhost/test_test",
    )
    objects = LocalObjectStorage(tmp_path / "objects")
    repo = CollectorRepository(engine)
    paths = sorted(folder.glob("*.zip"))
    first = team.register(paths, cfg, repo, objects)
    assert team.register(paths, cfg, repo, objects) == first
    with engine.connect() as cn:
        assert cn.scalar(sa.select(sa.func.count()).select_from(repo.files)) == 4
        for row in cn.execute(sa.select(repo.files)).mappings():
            assert row["url_origem"].startswith("file://")
            with objects.open(row["chave_objeto"]) as stream:
                import hashlib

                assert hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"]
        for row in cn.execute(sa.select(repo.runs)).mappings():
            assert row["parametros"]["modo"] == "importacao_zip_local"


@pytest.mark.integration
def test_team_trains_then_infers_and_publishes_with_replay(
    grouped_case,
    trained_groups,
    settings,
    tmp_path,
    monkeypatch,
    capsys,
):
    repo, admin, _, base_id, _, _, _ = grouped_case
    original = training.checked(trained_groups)
    prep = Path(original["lotes"][0]["dataset"]).parent
    # Os modelos são de treino real da fixture. Reutilização evita refazer 90 ajustes.
    calls = []

    def fitted(source, output, reviews, workers, progress):
        assert source == prep and workers == 1
        calls.append("treinar")
        progress(original["grupos_treinados"], original["grupos_treinados"])
        return {"diretorio": str(trained_groups), "manifesto": original, "reutilizada": True}

    monkeypatch.setattr(training, "run", fitted)
    monkeypatch.setattr("licita_ml.config.Settings", lambda: settings)
    monkeypatch.setattr(team, "database", lambda *_: repo.engine)
    team.save(
        tmp_path / "estado.json",
        {
            "versao": 1,
            "preparacao": str(prep),
            "base_id": str(base_id),
            "preparacao_sha256": checksum(prep / "manifesto.json"),
        },
    )
    args = Namespace(saida=tmp_path, processos=1, resultado_ate=date(2026, 10, 31))
    team.train(args)
    result = json.loads((tmp_path / "inferencia.json").read_text())
    execution = UUID(result["execucao_id"])
    team.train(args)
    repeated = json.loads((tmp_path / "inferencia.json").read_text())
    assert repeated["execucao_id"] == str(execution) and repeated["reutilizada"]
    assert calls == ["treinar", "treinar"]
    from licita_backend.models import analysis as a

    with admin.connect() as cn:
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.resultados_modelo)) > 0
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.publicacoes_analise)) == 1
    assert "100.0%" in capsys.readouterr().out


@pytest.mark.integration
def test_population_rebuilds_from_zips_and_reuses_base(
    grouped_source,
    database,
    settings,
    tmp_path,
    monkeypatch,
):
    repo, admin = database
    base, _ = grouped_source
    origin = json.loads((base / "manifesto.json").read_text())
    folder = Path(origin["fontes"][0]["arquivo"]).parent
    # A fixture do catálogo usa cabeçalhos mínimos; completar o contrato do importador.
    from zipfile import ZipFile

    with ZipFile(folder / "material_2026_09.csv.zip") as archive:
        with archive.open(archive.namelist()[0]) as stream:
            material = list(csv.DictReader(io.TextIOWrapper(stream), delimiter=";"))
    for row in material:
        row.setdefault("nome_fornecedor", "Fornecedor teste")
        row.setdefault("forma", "SISRP")
    write(folder, "material", material)
    application = [r for r in material if r["data_compra"].startswith("2026-09")]
    write(
        folder,
        "compra",
        [
            {
                "id_compra": r["id_compra"],
                "codigo_orgao": "00001",
                "orgao_entidade_razao_social": "Órgão teste",
                "ano_compra_pncp": "2026",
                "numero_compra": "1",
                "objeto_compra": "Canetas",
                "data_atualizacao_pncp": "2026-09-03T12:00:00",
            }
            for r in application
        ],
    )
    write(
        folder,
        "compra_item",
        [
            {
                "id_compra": r["id_compra"],
                "id_compra_item": r["id_compra_item"],
                "numero_item_pncp": str(i + 1),
                "descricao_detalhada": r["descricao_detalhada_item"],
                "unidade_medida": "UNIDADE",
                "quantidade": r["quantidade"],
                "data_atualizacao_pncp": "2026-09-03T12:00:00",
            }
            for i, r in enumerate(application)
        ],
    )
    write(
        folder,
        "item_resultado",
        [
            {
                "id_compra": r["id_compra"],
                "id_compra_item": r["id_compra_item"],
                "sequencial_resultado": "1",
                "srk_item_resultado": str(i + 1),
                "ni_fornecedor": r["ni_fornecedor"],
                "nome_razao_social_fornecedor": r["nome_fornecedor"],
                "quantidade_homologada": r["quantidade"],
                "valor_unitario_homologado": r["preco_unitario"],
                "data_resultado_pncp": r["data_resultado"],
                "situacao_compra_item_resultado_id": "1",
                "situacao_compra_item_resultado_nome": "Informado",
                "data_atualizacao_pncp": "2026-09-03T12:00:00",
            }
            for i, r in enumerate(application)
        ],
    )
    spec = manifest(folder, tmp_path / "inputs.json")
    cfg = CollectorSettings(
        _env_file=None,
        collector_database_url=settings.processing_database_url,
        storage_root=settings.storage_root,
    )
    monkeypatch.setattr("licita_collector.config.Settings", lambda: cfg)
    monkeypatch.setattr("licita_ml.config.Settings", lambda: settings)
    monkeypatch.setattr(
        team,
        "database",
        lambda _s, attr: admin if attr == "collector_database_url" else repo.engine,
    )
    out = tmp_path / "team"
    out.mkdir()
    args = Namespace(dados=folder.parent, manifesto=spec, conferir=False, saida=out)
    team.populate(args)
    first = json.loads((out / "estado.json").read_text())
    assert UUID(first["base_id"])
    assert Path(first["preparacao"]).is_dir()
    team.populate(args)
    second = json.loads((out / "estado.json").read_text())
    assert first["base_id"] == second["base_id"]
    assert second["importacao"]["reutilizada"]


def test_grouped_training_progress_and_cached_replay(grouped_source, tmp_path):
    from licita_ml.grouped.temporal import prepare

    base, cat = grouped_source
    prep = prepare(base, cat, tmp_path / "prep", batch_size=1)
    events = []
    training.run(
        Path(prep["diretorio"]),
        tmp_path / "fit",
        tmp_path / "reviews",
        workers=1,
        progress=lambda done, total: events.append((done, total)),
    )
    assert events == [(0, 2), (1, 2), (2, 2)]
    events.clear()
    result = training.run(
        Path(prep["diretorio"]),
        tmp_path / "fit",
        tmp_path / "reviews",
        workers=1,
        progress=lambda done, total: events.append((done, total)),
    )
    assert result["reutilizada"] and events == [(2, 2)]


def test_bundle_contains_only_verified_zips(tmp_path):
    folder, _ = raw_sources.__wrapped__(tmp_path)
    spec = manifest(folder, tmp_path / "inputs.json")
    paths = team.inputs(tmp_path, spec)
    (tmp_path / ".env").write_text("DO_NOT_SHARE")
    target = tmp_path / "share.tar"
    team.bundle(paths, tmp_path, target)
    with tarfile.open(target) as archive:
        assert len(archive.getnames()) == 4
        assert all(name.startswith("entrada_equipe/2026-09/") for name in archive.getnames())
        assert all(name.endswith(".csv.zip") for name in archive.getnames())
    assert target.with_suffix(".tar.sha256").read_text().startswith(checksum(target))
