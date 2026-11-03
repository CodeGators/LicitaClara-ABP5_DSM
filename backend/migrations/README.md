# Migrações

Revisões explícitas e imutáveis após compartilhamento. Executar os comandos a partir da raiz do repositório, com `MIGRATION_DATABASE_URL` configurada.

```bash
uv run --locked --package licita-backend python -m licita_backend.db.permissions bootstrap
uv run --locked --package licita-backend alembic -x role=licita_migrator upgrade head
uv run --locked --package licita-backend python -m licita_backend.db.permissions apply
uv run --locked --package licita-backend alembic -x role=licita_migrator check
```

A flag `-x role=licita_migrator` faz as tabelas pertencerem ao grupo de migração. O login administrativo deve poder assumir esse papel. A API não aplica migrações na inicialização.

- `0001_coleta`: coleta e bases.
- `0002_dominio`: identidades, snapshots, análises e auditoria.
- `0003_proveniencia`: unicidade da proveniência para retomadas idempotentes.
- `0004_complementos`: propostas por ID oficial, contratos com snapshots, vínculos, documentos e expansão da proveniência. O downgrade é bloqueado se houver proveniência dos novos domínios; deve ser validado em banco descartável.

Criar a próxima revisão com `revision --autogenerate`, revisar o SQL/constraints e validar em banco descartável antes de aplicar. A comparação Alembic verifica o schema modelado, não a correção semântica de um importador nem todas as permissões. Os testes usam PostgreSQL real, não SQLite.

Referências: [autogeração e check](https://alembic.sqlalchemy.org/en/latest/autogenerate.html), [privilégios PostgreSQL](https://www.postgresql.org/docs/17/ddl-priv.html).
