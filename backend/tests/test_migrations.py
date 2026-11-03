"""Migrações e invariantes verificadas em schema descartável de banco *_test."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from licita_backend.db.permissions import apply_permissions, bootstrap_roles, ident
from licita_backend.models import Base
from licita_backend.models import analysis as a
from licita_backend.models import audit as u
from licita_backend.models import collection as c
from licita_backend.models import complementary as k
from licita_backend.models import procurement as p
from sqlalchemy.exc import IntegrityError, ProgrammingError

pytestmark = pytest.mark.integration


def config(connection):
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.attributes["connection"] = connection
    return cfg


@pytest.fixture
def migrated(integration_engine):
    schema = f"test_migrations_{uuid4().hex}"
    with integration_engine.begin() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {ident(schema)}")
    engine = sa.create_engine(
        integration_engine.url,
        connect_args={"options": f"-c search_path={schema}"},
        hide_parameters=True,
    )
    try:
        with engine.connect() as connection:
            command.upgrade(config(connection), "head")
        yield engine, schema
    finally:
        engine.dispose()
        with integration_engine.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA {ident(schema)} CASCADE")


def insert(connection, table, **values):
    return connection.execute(table.insert().values(**values).returning(table.c.id)).scalar_one()


def base(connection, version):
    return insert(
        connection,
        c.versoes_base,
        versao=version,
        versao_transformador="test-v1",
        versao_codigo="test",
        chave_manifesto=version + "/manifest.json",
        sha256_manifesto="a" * 64,
        periodo_inicio=date(2026, 9, 1),
        periodo_fim=date(2026, 9, 30),
    )


def dataset(connection):
    base_id = base(connection, "v1")
    orgao = insert(
        connection, p.orgaos, fonte="comprasgov", chave_oficial="001", nome="Órgão teste"
    )
    processo = insert(connection, p.processos, fonte="comprasgov", chave_oficial="0001")
    snapshot = insert(
        connection,
        p.processos_versoes,
        base_id=base_id,
        processo_id=processo,
        orgao_id=orgao,
        orgao_nome="Órgão teste",
        codigo_unidade="000001",
        numero_compra="0001",
        ano=2026,
        objeto="Teste",
        situacao="homologada",
        valor_estimado=Decimal("10.12345678"),
    )
    return base_id, orgao, processo, snapshot


def item(connection, base_id, processo, snapshot, code):
    item_id = insert(connection, p.itens_processo, processo_id=processo, chave_oficial=code)
    return insert(
        connection,
        p.itens_versoes,
        base_id=base_id,
        item_id=item_id,
        processo_id=processo,
        processo_versao_id=snapshot,
        numero_item=code,
        descricao="Item de teste",
    )


def execution(connection, base_id):
    modelo = insert(
        connection,
        a.versoes_modelo,
        base_treino_id=base_id,
        algoritmo="isolation_forest",
        versao="v1",
        versao_codigo="test",
        chave_artefato="test/model",
        sha256_artefato="b" * 64,
    )
    execucao = insert(connection, a.execucoes_analise, base_id=base_id, versao_politica_score="v1")
    connection.execute(a.execucoes_modelos.insert().values(execucao_id=execucao, modelo_id=modelo))
    return execucao, modelo


def test_upgrade_from_previous_revision_preserves_data_and_matches_metadata(migrated):
    engine, _ = migrated
    with engine.connect() as connection:
        cfg = config(connection)
        command.downgrade(cfg, "0001_coleta")
        with connection.begin():
            identifier = insert(
                connection,
                c.execucoes_coleta,
                fonte="comprasgov",
                modulo="pncp",
                competencia_inicio=date(2026, 9, 1),
                competencia_fim=date(2026, 9, 1),
            )
        command.upgrade(cfg, "head")
        assert connection.scalar(sa.select(c.execucoes_coleta.c.id)) == identifier
        connection.rollback()
        command.check(cfg)
        command.downgrade(cfg, "base")
        assert not (set(sa.inspect(connection).get_table_names()) & set(Base.metadata.tables))
        connection.rollback()
        command.upgrade(cfg, "head")
        command.check(cfg)


def test_versions_preserve_money_and_allow_multiple_items_and_winners(migrated):
    engine, _ = migrated
    with engine.begin() as connection:
        base_id, orgao, processo, snapshot = dataset(connection)
        first = item(connection, base_id, processo, snapshot, "1")
        item(connection, base_id, processo, snapshot, "2")
        for number in range(2):
            fornecedor = insert(
                connection,
                p.fornecedores,
                fonte="comprasgov",
                tipo_identificacao="CNPJ",
                identificacao=f"000{number}",
                nome="Teste",
            )
            insert(
                connection,
                p.resultados_itens,
                base_id=base_id,
                item_versao_id=first,
                fornecedor_id=fornecedor,
                fornecedor_nome="Teste",
                sequencial_resultado=number,
                chave_origem=str(number),
                situacao="homologado",
                valor_unitario_homologado=Decimal("1.00000001"),
            )
        new_base = base(connection, "v2")
        insert(
            connection,
            p.processos_versoes,
            base_id=new_base,
            processo_id=processo,
            orgao_id=orgao,
            orgao_nome="Órgão corrigido",
            codigo_unidade="000001",
            numero_compra="0001",
            ano=2026,
            objeto="Descrição corrigida",
            situacao="homologada",
            valor_estimado=Decimal("20"),
        )
        old_value = connection.scalar(
            sa.select(p.processos_versoes.c.valor_estimado).where(
                p.processos_versoes.c.id == snapshot
            )
        )
        assert old_value == Decimal("10.12345678")
        assert connection.scalar(sa.select(sa.func.count()).select_from(p.resultados_itens)) == 2


def test_duplicate_file_content_is_rejected_but_correction_is_preserved(migrated):
    engine, _ = migrated
    values = dict(
        fonte="comprasgov",
        modulo="pncp",
        competencia=date(2026, 9, 1),
        url_origem="https://example.test/file",
        url_final="https://example.test/file",
        tamanho_bytes=100,
    )
    with engine.begin() as connection:
        insert(connection, c.arquivos_coletados, **values, sha256="a" * 64, chave_objeto="v1/file")
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                c.arquivos_coletados,
                **values,
                sha256="a" * 64,
                chave_objeto="duplicate/file",
            )
        insert(connection, c.arquivos_coletados, **values, sha256="b" * 64, chave_objeto="v2/file")
        assert connection.scalar(sa.select(sa.func.count()).select_from(c.arquivos_coletados)) == 2


def test_analysis_rejects_mixed_bases_invalid_target_and_duplicate_process_score(migrated):
    engine, _ = migrated
    with engine.begin() as connection:
        base_id, _, processo, snapshot = dataset(connection)
        item_id = item(connection, base_id, processo, snapshot, "1")
        execucao, modelo = execution(connection, base_id)
        values = dict(
            base_id=base_id,
            execucao_id=execucao,
            modelo_id=modelo,
            processo_versao_id=snapshot,
            tipo_alvo="processo",
            score_bruto=Decimal("-0.5"),
            score_normalizado=Decimal("92"),
            versao_normalizacao="v1",
        )
        insert(connection, a.resultados_modelo, **values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, a.resultados_modelo, **values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, a.resultados_modelo, **dict(values, item_versao_id=item_id))
        other = base(connection, "other")
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, a.resultados_modelo, **dict(values, base_id=other))
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                a.avaliacoes_processo,
                base_id=base_id,
                execucao_id=execucao,
                processo_versao_id=snapshot,
                prioridade="nao_analisado",
                score=0,
                motivo_indisponibilidade="sem cobertura",
            )


def test_provenance_requires_source_import_in_same_base_and_exactly_one_target(migrated):
    engine, _ = migrated
    with engine.begin() as connection:
        base_id, _, _, snapshot = dataset(connection)
        arquivo = insert(
            connection,
            c.arquivos_coletados,
            fonte="comprasgov",
            modulo="pncp",
            competencia=date(2026, 9, 1),
            url_origem="https://example.test",
            url_final="https://example.test",
            sha256="a" * 64,
            tamanho_bytes=100,
            chave_objeto="raw/file",
        )
        imported = insert(connection, c.importacoes, arquivo_id=arquivo, versao_importador="v1")
        values = dict(
            base_id=base_id,
            importacao_id=imported,
            membro_arquivo="compra.csv",
            numero_linha=2,
            processo_versao_id=snapshot,
        )
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, p.proveniencias_registros, **values)
        connection.execute(
            c.base_importacoes.insert().values(base_id=base_id, importacao_id=imported)
        )
        insert(connection, p.proveniencias_registros, **values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, p.proveniencias_registros, **values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, p.proveniencias_registros, **dict(values, processo_versao_id=None))


def test_permissions_limit_writes_and_keep_reviews_append_only(migrated):
    engine, schema = migrated
    with engine.begin() as connection:
        bootstrap_roles(connection, schema)
        apply_permissions(connection, schema)
        base_id, _, _, snapshot = dataset(connection)
        execucao, _ = execution(connection, base_id)
        insert(
            connection,
            a.avaliacoes_processo,
            base_id=base_id,
            execucao_id=execucao,
            processo_versao_id=snapshot,
            prioridade="alta",
            score=92,
        )
        usuario = insert(
            connection, u.usuarios, issuer="https://issuer.test", subject="test", nome="Teste"
        )
        connection.exec_driver_sql("SET LOCAL ROLE licita_api")
        insert(
            connection,
            u.revisoes,
            usuario_id=usuario,
            processo_versao_id=snapshot,
            execucao_id=execucao,
            status="em_analise",
            observacao="Primeira revisão",
        )
        with pytest.raises(ProgrammingError), connection.begin_nested():
            connection.execute(p.processos_versoes.update().values(valor_estimado=0))
        with pytest.raises(ProgrammingError), connection.begin_nested():
            connection.execute(u.revisoes.update().values(observacao="apagada"))
        connection.exec_driver_sql("RESET ROLE")
        connection.exec_driver_sql("SET LOCAL ROLE licita_collector")
        insert(
            connection,
            c.execucoes_coleta,
            fonte="comprasgov",
            modulo="pncp",
            competencia_inicio=date(2026, 9, 1),
            competencia_fim=date(2026, 9, 1),
        )
        with pytest.raises(ProgrammingError), connection.begin_nested():
            connection.execute(p.processos.select())
        connection.exec_driver_sql("RESET ROLE")
        connection.exec_driver_sql("SET LOCAL ROLE licita_processing")
        with pytest.raises(ProgrammingError), connection.begin_nested():
            connection.execute(p.processos_versoes.update().values(valor_estimado=0))


def test_single_active_publication_and_report_base_consistency(migrated):
    engine, _ = migrated
    with engine.begin() as connection:
        base_id, _, _, _ = dataset(connection)
        execucao, _ = execution(connection, base_id)
        second = insert(
            connection, a.execucoes_analise, base_id=base_id, versao_politica_score="v2"
        )
        first_publication = insert(
            connection, a.publicacoes_analise, nome="painel", base_id=base_id, execucao_id=execucao
        )
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                a.publicacoes_analise,
                nome="painel",
                base_id=base_id,
                execucao_id=second,
            )
        connection.execute(
            a.publicacoes_analise.update()
            .where(a.publicacoes_analise.c.id == first_publication)
            .values(ativa=False)
        )
        insert(
            connection, a.publicacoes_analise, nome="painel", base_id=base_id, execucao_id=second
        )
        usuario = insert(connection, u.usuarios, issuer="test", subject="test", nome="Teste")
        other = base(connection, "different")
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                u.relatorios,
                usuario_id=usuario,
                base_id=other,
                execucao_id=execucao,
                titulo="Não pode misturar versões",
                formato="pdf",
            )


def test_runtime_login_cannot_escalate_to_migration_role(migrated):
    import secrets

    from psycopg import sql

    engine, schema = migrated
    login = f"test_runtime_{uuid4().hex}"
    password = secrets.token_urlsafe(24)
    with engine.begin() as connection:
        bootstrap_roles(connection, schema)
        apply_permissions(connection, schema)
        with connection.connection.driver_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(login), sql.Literal(password)
                )
            )
        connection.exec_driver_sql(f"GRANT licita_api TO {ident(login)}")
    restricted = sa.create_engine(
        engine.url.set(username=login, password=password),
        connect_args={"options": f"-c search_path={schema}"},
        hide_parameters=True,
    )
    try:
        with restricted.begin() as connection:
            assert connection.scalar(sa.text("SELECT current_user")) == login
            assert connection.scalar(sa.select(sa.func.count()).select_from(p.processos)) == 0
            with pytest.raises(ProgrammingError), connection.begin_nested():
                connection.exec_driver_sql("SET ROLE licita_migrator")
            with pytest.raises(ProgrammingError), connection.begin_nested():
                connection.exec_driver_sql("CREATE TABLE forbidden (id integer)")
    finally:
        restricted.dispose()
        with engine.begin() as connection:
            connection.exec_driver_sql(f"DROP ROLE {ident(login)}")


def contract(connection, base_id, key="contract-1"):
    identifier = insert(connection, k.contratos, fonte="comprasgov", chave_oficial=key)
    return insert(
        connection,
        k.contratos_versoes,
        base_id=base_id,
        contrato_id=identifier,
        numero_contrato="00001/2026",
        valor_global=Decimal("100.00000001"),
    )


def test_proposals_keep_official_ids_and_reject_wrong_process_or_base(migrated):
    engine, _ = migrated
    with engine.begin() as connection:
        base_id, orgao, processo, snapshot = dataset(connection)
        item_id = item(connection, base_id, processo, snapshot, "1")
        values = dict(
            base_id=base_id,
            processo_versao_id=snapshot,
            item_versao_id=item_id,
            fonte="comprasgov",
            identificacao_participante="00000000000100",
            valor_proposta=Decimal("0.12345678"),
        )
        for key in ["proposal-1", "proposal-2"]:
            insert(connection, k.participacoes, chave_origem=key, **values)
        assert connection.scalar(sa.select(sa.func.count()).select_from(k.participacoes)) == 2
        assert connection.scalar(sa.select(k.participacoes.c.valor_proposta).limit(1)) == Decimal(
            "0.12345678"
        )
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, k.participacoes, chave_origem="proposal-1", **values)
        other = insert(connection, p.processos, fonte="comprasgov", chave_oficial="other")
        other_snapshot = insert(
            connection,
            p.processos_versoes,
            base_id=base_id,
            processo_id=other,
            orgao_id=orgao,
            orgao_nome="Other",
            codigo_unidade="000001",
            numero_compra="2",
            ano=2026,
            objeto="Other",
            situacao="homologada",
        )
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                k.participacoes,
                chave_origem="bad-process",
                **dict(values, processo_versao_id=other_snapshot),
            )
        other_base = base(connection, "v2")
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                k.participacoes,
                chave_origem="bad-base",
                **dict(values, base_id=other_base),
            )


def test_contract_links_documents_and_snapshots_preserve_integrity(migrated):
    engine, _ = migrated
    with engine.begin() as connection:
        base_id, _, _, snapshot = dataset(connection)
        first, second = contract(connection, base_id), contract(connection, base_id, "contract-2")
        for target in [first, second]:
            insert(
                connection,
                k.contratos_processos,
                base_id=base_id,
                contrato_versao_id=target,
                processo_versao_id=snapshot,
                tipo_chave_vinculo="idCompra",
                chave_vinculo="official-purchase",
            )
        values = dict(
            base_id=base_id,
            fonte="pncp",
            chave_origem="org/compras/2026/1/1",
            sequencial_documento=1,
            url_origem="https://pncp.gov.br/test",
        )
        document = insert(connection, k.documentos, processo_versao_id=snapshot, **values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, k.documentos, processo_versao_id=snapshot, **values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(connection, k.documentos, **dict(values, chave_origem="no-parent"))
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                k.documentos,
                processo_versao_id=snapshot,
                contrato_versao_id=first,
                **dict(values, chave_origem="two-parents"),
            )
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                k.documentos,
                processo_versao_id=snapshot,
                sha256="a" * 64,
                **dict(values, chave_origem="incomplete-object"),
            )
        other_base = base(connection, "v2")
        with pytest.raises(IntegrityError), connection.begin_nested():
            insert(
                connection,
                k.documentos,
                contrato_versao_id=first,
                **dict(values, base_id=other_base, chave_origem="wrong-base"),
            )
        identity = connection.scalar(
            sa.select(k.contratos_versoes.c.contrato_id).where(k.contratos_versoes.c.id == first)
        )
        insert(
            connection,
            k.contratos_versoes,
            base_id=other_base,
            contrato_id=identity,
            numero_contrato="00001/2026",
            valor_global=Decimal("200"),
        )
        assert connection.scalar(
            sa.select(k.contratos_versoes.c.valor_global).where(k.contratos_versoes.c.id == first)
        ) == Decimal("100.00000001")
        assert (
            connection.scalar(
                sa.select(k.documentos.c.chave_objeto).where(k.documentos.c.id == document)
            )
            is None
        )


def test_extended_provenance_and_safe_downgrade(migrated):
    engine, _ = migrated
    with engine.begin() as connection:
        base_id, _, processo, snapshot = dataset(connection)
        item_id = item(connection, base_id, processo, snapshot, "1")
        participation = insert(
            connection,
            k.participacoes,
            base_id=base_id,
            processo_versao_id=snapshot,
            item_versao_id=item_id,
            fonte="comprasgov",
            chave_origem="p1",
        )
        version = contract(connection, base_id)
        link = insert(
            connection,
            k.contratos_processos,
            base_id=base_id,
            contrato_versao_id=version,
            processo_versao_id=snapshot,
            tipo_chave_vinculo="numeroControlePncpCompra",
            chave_vinculo="official-pncp",
        )
        document = insert(
            connection,
            k.documentos,
            base_id=base_id,
            contrato_versao_id=version,
            fonte="pncp",
            chave_origem="contract/doc/1",
            sequencial_documento=1,
            url_origem="https://pncp.gov.br/test",
        )
        file_id = insert(
            connection,
            c.arquivos_coletados,
            fonte="comprasgov",
            modulo="propostas",
            competencia=date(2026, 9, 1),
            url_origem="https://example.test",
            url_final="https://example.test",
            sha256="a" * 64,
            tamanho_bytes=10,
            chave_objeto="raw/proposals",
        )
        imported = insert(connection, c.importacoes, arquivo_id=file_id, versao_importador="v1")
        connection.execute(
            c.base_importacoes.insert().values(base_id=base_id, importacao_id=imported)
        )
        for column, target in [
            ("participacao_id", participation),
            ("contrato_versao_id", version),
            ("contrato_processo_id", link),
            ("documento_id", document),
        ]:
            values = dict(
                base_id=base_id,
                importacao_id=imported,
                membro_arquivo="records.json",
                numero_linha=1,
                **{column: target},
            )
            insert(connection, p.proveniencias_registros, **values)
            with pytest.raises(IntegrityError), connection.begin_nested():
                insert(connection, p.proveniencias_registros, **values)
            with pytest.raises(IntegrityError), connection.begin_nested():
                insert(connection, p.proveniencias_registros, processo_versao_id=snapshot, **values)
    with engine.connect() as connection:
        with pytest.raises(RuntimeError, match="Downgrade bloqueado"):
            command.downgrade(config(connection), "0003_proveniencia")
        connection.rollback()
        assert connection.scalar(sa.select(sa.func.count()).select_from(k.participacoes)) == 1


def test_complementary_runtime_permissions(migrated):
    engine, schema = migrated
    with engine.begin() as connection:
        bootstrap_roles(connection, schema)
        apply_permissions(connection, schema)
        connection.exec_driver_sql("SET LOCAL ROLE licita_processing")
        insert(connection, k.contratos, fonte="comprasgov", chave_oficial="runtime")
        for table in [
            k.participacoes,
            k.contratos,
            k.contratos_versoes,
            k.contratos_processos,
            k.documentos,
        ]:
            with pytest.raises(ProgrammingError), connection.begin_nested():
                connection.execute(table.delete())
        connection.exec_driver_sql("RESET ROLE")
        connection.exec_driver_sql("SET LOCAL ROLE licita_api")
        for table in [
            k.participacoes,
            k.contratos,
            k.contratos_versoes,
            k.contratos_processos,
            k.documentos,
        ]:
            connection.execute(table.select())
            with pytest.raises(ProgrammingError), connection.begin_nested():
                connection.execute(table.update().values(id=uuid4()))
        connection.exec_driver_sql("RESET ROLE")
        connection.exec_driver_sql("SET LOCAL ROLE licita_collector")
        with pytest.raises(ProgrammingError), connection.begin_nested():
            connection.execute(k.participacoes.select())


def test_upgrade_0003_preserves_existing_provenance_and_collection(migrated):
    engine, _ = migrated
    with engine.connect() as connection:
        cfg = config(connection)
        command.downgrade(cfg, "0003_proveniencia")
        with connection.begin():
            base_id, _, _, snapshot = dataset(connection)
            file_id = insert(
                connection,
                c.arquivos_coletados,
                fonte="comprasgov",
                modulo="pncp/compra",
                competencia=date(2026, 9, 1),
                url_origem="https://example.test",
                url_final="https://example.test",
                sha256="b" * 64,
                tamanho_bytes=100,
                chave_objeto="raw/existing",
            )
            imported = insert(connection, c.importacoes, arquivo_id=file_id, versao_importador="v1")
            connection.execute(
                c.base_importacoes.insert().values(base_id=base_id, importacao_id=imported)
            )
            evidence = insert(
                connection,
                p.proveniencias_registros,
                base_id=base_id,
                importacao_id=imported,
                membro_arquivo="compra.csv",
                numero_linha=2,
                processo_versao_id=snapshot,
            )
        command.upgrade(cfg, "head")
        assert connection.scalar(sa.select(p.proveniencias_registros.c.id)) == evidence
        assert connection.scalar(sa.select(c.arquivos_coletados.c.id)) == file_id
        expression = connection.scalar(
            sa.text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid='proveniencias_registros'::regclass "
                "AND conname='ck_proveniencias_registros_um_alvo'"
            )
        )
        assert "participacao_id" in expression and "documento_id" in expression
        connection.rollback()
        command.check(cfg)
