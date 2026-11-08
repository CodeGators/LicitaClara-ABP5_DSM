# Instalar e reproduzir o Licita Clara na equipe

O GitHub contém código e configuração, mas não contém CSVs, modelos treinados,
banco populado ou senhas. Os dois scripts abaixo constroem uma instalação local
com os mesmos arquivos de entrada. Não precisam receber o `.env` de outra pessoa.

Use Linux ou WSL2 com Docker disponível. O pipeline usa locks Unix e processos
Python. Dependências: Git, Python 3.12, uv 0.13.2, Node.js 20.19+ da linha 20,
npm e Docker Compose. Reserve espaço para os ZIPs, Parquet, banco e modelos;
os 312 MB de ZIPs não representam o tamanho final do processamento. Para esse
pacote, recomendamos reservar 30 GB livres, incluindo arquivos temporários.

## 1. Clonar e instalar

```bash
git clone https://github.com/CodeGators/LicitaClara-ABP5_DSM.git
cd LicitaClara-ABP5_DSM
cp .env.example .env
uv sync --locked --all-packages --extra validation
npm ci --prefix Frontend-licita-clara
```

Todos os próximos comandos são executados na **raiz do repositório**, onde estão
`pyproject.toml` e `.env`. Em instalação nova, o exemplo funciona localmente.
Não substitua um `.env` existente se o banco já tiver sido inicializado.

## 2. Criar PostgreSQL e aplicar o esquema

```bash
docker compose --env-file .env -f infra/compose.yaml up -d --wait
uv run --locked --all-packages --extra validation python -m licita_backend.db.permissions bootstrap
uv run --locked --all-packages --extra validation alembic -x role=licita_migrator upgrade head
uv run --locked --all-packages --extra validation python -m licita_backend.db.permissions apply
uv run --locked --all-packages --extra validation python -m licita_backend.db.permissions local-logins
```

O último comando gera as conexões locais da API, coleta e processamento no seu
`.env`. Isso não cria login de usuários da aplicação. Coleta e processamento
devem apontar para o mesmo banco e armazenamento. Não use `down -v`: ele apaga
o volume do PostgreSQL.

## 3. Receber os arquivos de dados

Receba de quem mantém os dados o pacote `dados_equipe.tar`. Ele contém somente
os ZIPs originais, organizados em `entrada_equipe/AAAA-MM/`. Na raiz do projeto:

```bash
mkdir -p data
tar -xf /caminho/para/dados_equipe.tar -C data
uv run --locked --all-packages --extra validation python scripts/popular_banco.py --conferir
```

A conferência verifica nomes, tamanhos e SHA-256 contra
[`config/equipe/dados.json`](../config/equipe/dados.json). Esse manifesto lista os
14 ZIPs da base usada no treinamento por unidades V2; **não é um download**.
Arquivos extras na pasta não entram no processamento. Os originais permanecem
intactos. Se faltar um arquivo ou houver divergência, receba a cópia correta.

Também é possível montar manualmente `data/entrada_equipe/AAAA-MM/` com esses
ZIPs. Para outra pasta, use `--dados /caminho/entrada_equipe`. Para outro conjunto
de entradas, prepare um manifesto no mesmo formato e passe `--manifesto`; isso
muda o experimento e os resultados, e precisa respeitar a política temporal.

## 4. Popular o banco

```bash
uv run --locked --all-packages --extra validation python scripts/popular_banco.py
```

Esse script:

1. Confere os 14 arquivos e as conexões.
2. Organiza os CSVs, cataloga produtos/unidades e prepara as partições temporais.
3. Registra no armazenamento e no banco os ZIPs do período operacional.
4. Importa os itens operacionais dos grupos preparados e grava `data/equipe/estado.json`.

Não treina modelos. Os itens já podem ser consultados, mas ainda não têm Scores
publicados nessa instalação. A preparação pode demorar; a saída informa a etapa
em execução. Ela usa o mesmo pipeline de organização e agrupamento do projeto.

A política agrupada atual usa histórico de julho a dezembro de 2025 para treino,
julho/agosto de 2026 para avaliação e setembro de 2026 para aplicação. O pacote
inclui os arquivos efetivamente disponíveis; não pressupõe todos os meses/anos
citados nos exemplos antigos da documentação.

Numa instalação nova, o banco será reconstruído a partir desses ZIPs. Não é uma
restauração idêntica do banco de Rodrigo: enriquecimentos coletados posteriormente
por API, bases históricas e itens preservados de bases anteriores não são
recriados pelos CSVs. Assim, UUIDs, cobertura e totais podem diferir da máquina
original. Para uma cópia exata do estado atual, é necessário também um backup do
banco e dos objetos referenciados. O treino usa os mesmos ZIPs e regras.

## 5. Treinar, analisar e publicar

```bash
uv run --locked --all-packages --extra validation python scripts/treinar_e_analisar.py
```

O script executa Isolation Forest e Autoencoder, confere os modelos e realiza
inferência sobre a base criada no passo anterior. Ao terminar, publica a execução
**experimental** para o frontend. Não publica modelos ou Scores na internet.
Itens sem grupo/modelo elegível continuam sem Score, com os motivos disponíveis.

Exemplo de progresso:

```text
Treinamento [############-------------] 50.0% | 89/178 grupos | faltam 50.0% | ...
```

A porcentagem conta grupos **concluídos**, atualizados ao final de cada lote.
Enquanto um lote está em execução, o percentual pode permanecer parado; no
terminal o tempo decorrido é atualizado periodicamente. O tempo restante só é
estimado após a primeira conclusão e pode variar. O 100% é do treinamento;
a inferência e a publicação são as etapas seguintes, indicadas separadamente.
As contagens acima são ilustrativas, não uma garantia de grupos elegíveis.

Para economizar memória:

```bash
uv run --locked --all-packages --extra validation python scripts/treinar_e_analisar.py --processos 1
```

O padrão são dois processos; o máximo são três. O corte de resultados atual é
`2026-10-31`, alterável por `--resultado-ate AAAA-MM-DD` sem mudar o treino.

### Interrupção e retomada

Repita o mesmo comando com os mesmos dados e a mesma pasta de saída. Etapas e
lotes completos são conferidos por hash e reutilizados; um lote interrompido
pode precisar recomeçar. Isso não duplica itens, modelos ou publicações iguais.
Os dois scripts compartilham um lock para impedir execução simultânea na mesma
pasta. O segundo exige que o primeiro tenha terminado corretamente.

Use `--saida data/outro_experimento` em **ambos** os scripts para uma execução
separada. Não copie uma pasta gerada de outra máquina esperando reutilizar seus
caminhos absolutos; os scripts são destinados à reconstrução local.

Saídas úteis em `data/equipe/`:

- `estado.json`: base importada e preparação usada.
- `treino.json`: grupos, modelos e diretórios de treinamento.
- `inferencia.json`: execução e resultados da inferência.
- `publicacao.json`: confirmação da análise experimental ativa.
- `revisoes/`: arquivos de revisão; não são pareceres preenchidos automaticamente.

Mantenha essa pasta e `data/objects/` para continuar trabalhando depois.
Os scripts não alteram migrações, não mudam senhas e não apagam bases anteriores.
Se aparecer falha, confira a etapa indicada, as dependências, `.env`, banco,
migrações e espaço em disco; corrija e repita o comando.

## 6. Iniciar a aplicação

Terminal 1, na raiz:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2, também na raiz:

```bash
npm run dev --prefix Frontend-licita-clara
```

Abra http://localhost:5173. API: http://127.0.0.1:8000/docs.
O Vite usa o proxy para a API na porta 8000; não é preciso copiar o `.env` do
frontend se usar esse padrão.

Confira `/api/v1/base/status`, abra Itens Sinalizados e um item com análise.
Sem Score não significa item regular. Anomalia estatística não comprova
irregularidade e os modelos não fornecem probabilidade de fraude.

## Quem mantém os dados: gerar o pacote para o grupo

Com os 14 ZIPs em `data/entrada_equipe/`, execute:

```bash
uv run --locked --all-packages --extra validation python scripts/popular_banco.py --empacotar data/entrega/dados_equipe.tar
```

Isso confere os hashes e gera o TAR e seu arquivo `.sha256`, sem acessar o banco
ou treinar. Compartilhe os dois arquivos por um meio de transferência da equipe.
O TAR contém somente ZIPs listados no manifesto: não inclui `.env`, banco,
modelos, dependências ou documentos locais. Esses arquivos permanecem fora do Git.
