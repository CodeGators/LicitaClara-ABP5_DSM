# UML do PostgreSQL — Licita Clara

Gerado a partir da metadata SQLAlchemy correspondente à revisão `0004_complementos`.

- [Abrir diagrama interativo](UML_BANCO.html): funciona localmente, sem internet. Use zoom, rolagem e busca; selecione uma tabela para destacar os vínculos e consultar todos os campos.
- [Imagem vetorial SVG](UML_BANCO.svg): visão geral que permite ampliar sem perder definição.
- [PlantUML completo](UML_BANCO.puml): diagrama de classes UML com estereótipo `table`, todos os campos, tipos e relacionamentos, editável em ferramentas compatíveis.

São **34 tabelas de aplicação e 64 FKs**, agrupadas em seis áreas para facilitar a leitura. A tabela interna `alembic_version` não faz parte do domínio e foi omitida. As visões HTML/SVG apresentam campos principais nos cartões; o painel HTML e o PlantUML contêm todos os campos.

`PK` indica chave primária, `FK` indica chave estrangeira e `?` indica campo que aceita NULL. No SVG/HTML, a seta aponta da tabela filha para o pai referenciado. No PlantUML, os vínculos indicam um pai obrigatório (`1`) ou opcional (`0..1`) por registro filho, com multiplicidade inversa permissiva (`0..*`). FKs compostas são desenhadas como um vínculo, não como relações independentes para cada coluna. Restrições de unicidade e CHECK refinam essas associações; consulte o [dicionário do banco](../BANCO_DE_DADOS.md).

Tabelas com sufixo `_versoes` preservam snapshots por base. Documentos têm exatamente um alvo (processo ou contrato); proveniência também exige exatamente um dos alvos permitidos. As relações opcionais do diagrama não significam que todos esses campos possam ser preenchidos simultaneamente. Propostas têm cobertura restrita a itens homologados na fonte.

Para atualizar, execute na raiz do repositório:

```bash
uv run --locked --all-packages python docs/diagramas/gerar_uml_banco.py
```

O gerador importa apenas a metadata; não abre conexão nem modifica o banco. A organização dos grupos deve ser atualizada caso novas tabelas sejam adicionadas; uma verificação impede omissões silenciosas.
