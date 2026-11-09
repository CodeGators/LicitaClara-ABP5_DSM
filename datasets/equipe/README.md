# CSVs de entrada da equipe

Esta pasta contém os 14 ZIPs originais usados pelo pipeline. São aproximadamente
312 MB e vêm junto com o clone do repositório. Não é necessário descompactar os
CSVs: os scripts leem diretamente os ZIPs.

| Conteúdo | Período |
| --- | --- |
| Material — 6 ZIPs | Julho a dezembro de 2025 |
| Itens e resultados — 2 ZIPs | Maio de 2026 |
| Material — 2 ZIPs | Julho e agosto de 2026 |
| Compra, itens, resultados e material — 4 ZIPs | Setembro de 2026 |

Nomes, tamanhos e SHA-256 estão em `config/equipe/dados.json`, na raiz do projeto.
Para conferir os arquivos, execute na raiz:

```bash
uv run --locked --all-packages --extra validation python scripts/popular_banco.py --conferir
```

A política atual usa histórico de julho a dezembro de 2025 para treino,
julho/agosto de 2026 para avaliação e setembro de 2026 para aplicação. Os arquivos
de maio complementam os dados disponíveis para conciliação. O recorte de cada
registro é determinado pelas regras do pipeline, não apenas pelo nome do ZIP.

Preserve estes originais. CSVs organizados, Parquet, modelos, relatórios gerados e
arquivos temporários continuam em `data/`, ignorada pelo Git. O passo a passo de
instalação está no README principal e em `scripts/README.md`.
