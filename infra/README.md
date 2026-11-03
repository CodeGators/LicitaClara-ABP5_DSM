# Infraestrutura local

O Compose desta etapa executa somente PostgreSQL. A API roda no Python local; hospedagem, Dockerfiles de aplicação e publicação serão feitos nas etapas seguintes.

Da raiz do repositório, com `.env` configurado:

```bash
docker compose --env-file .env -f infra/compose.yaml up -d --wait
docker compose --env-file .env -f infra/compose.yaml ps
docker compose --env-file .env -f infra/compose.yaml stop
```

O serviço usa porta `127.0.0.1:55432` por padrão e volume nomeado persistente. A porta é configurável por `POSTGRES_PORT`; atualizar também as URLs do banco se a alterar. Não interfere no container `postgres-aula`.

`stop` preserva o volume. Evitar `down -v`, que remove os dados. `POSTGRES_USER`, senha e banco só inicializam o volume na primeira execução; mudanças posteriores no `.env` não alteram automaticamente usuários/senhas já criados.

O usuário do Compose é administrador local. Grupos de banco e logins locais separados foram criados na etapa 03; as tabelas pertencem ao papel NOLOGIN `licita_migrator`. A URL da API usa o login restrito, enquanto `MIGRATION_DATABASE_URL` é administrativa. Ver a sequência de instalação no README do backend. Nenhuma nuvem foi provisionada.

Para futura hospedagem, os candidatos continuam Supabase (PostgreSQL), R2 (objetos), Render (API) e GitHub Actions (coleta). Limites, contas e custos precisam ser revalidados no provisionamento.

A imagem PostgreSQL 17 Alpine está fixada pelo digest tanto no Compose quanto na CI. Atualizações da imagem devem trocar o digest e executar os testes de integração.
