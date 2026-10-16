# Orientações para agentes

## Contexto

VoltBot busca faturas da Enel por e-mail (IMAP), extrai os dados e PDFs e envia
mensagens pelo WhatsApp usando a Evolution API. A interface web permite gerenciar
instalações, contatos, contas de e-mail e execuções. Responda ao usuário em
português e mantenha os textos da interface nesse idioma.

## Estrutura

- `src/voltbot/main.py`: CLI e orquestração do processamento diário, mensal e de códigos de barras.
- `src/voltbot/imap_client.py` e `parsers.py`: busca de e-mails e extração de faturas.
- `src/voltbot/domain.py`: objetos de domínio.
- `src/voltbot/evolution.py`: mensagens, agrupamento por contato e integração com a Evolution API.
- `src/voltbot/db.py` e `contacts.py`: SQLite e consulta de instalações, contatos e contas.
- `src/voltbot/state.py` e `storage.py`: controle de envios e armazenamento dos PDFs.
- `src/voltbot/config.py`: configurações via Pydantic Settings e variáveis de ambiente.
- `src/voltbot/web.py`: FastAPI, endpoints `/api` e execução de tarefas em background.
- `frontend/src/`: React 19, TypeScript e Mantine 8, com Vite 6.
- `src/voltbot/static/`: bundle gerado pelo frontend e servido pelo backend.
- `tests/`: testes Python com pytest.
- `docker-compose.yml`: aplicação, Evolution API, PostgreSQL e Redis. O banco do VoltBot é SQLite; PostgreSQL e Redis atendem à Evolution API.

## Ambiente e comandos

Execute os comandos Python na raiz. O projeto requer Python >= 3.14 e usa `uv`;
preserve o `uv.lock` e atualize-o quando mudar as dependências Python.

```bash
uv sync
uv run pytest
uv run voltbot-web
```

O backend local usa `127.0.0.1:8000` por padrão. Para o frontend:

```bash
cd frontend
npm install
npm run dev
npm run typecheck
npm run build
```

O Vite usa a porta 5173 e encaminha `/api` para o backend na porta 8000.
`npm run build` substitui o conteúdo de `src/voltbot/static/`; faça alterações
visuais em `frontend/src/`, sem editar manualmente os bundles gerados.
No Docker Compose, as portas publicadas padrão são 7801 para a interface web
e 7800 para a Evolution API; confira as variáveis de bind antes de usar.

## Convenções de implementação

- Siga o estilo dos arquivos existentes: funções e módulos Python em `snake_case`, tipos explícitos nas interfaces e componentes React funcionais em TypeScript.
- Preserve a divisão entre extração de dados, regras de envio, persistência e transporte HTTP. Reutilize os componentes Mantine e o cliente `frontend/src/api.ts`.
- Mantenha frontend e backend alinhados ao alterar contratos de `/api`.
- Preserve instalações e códigos de barras como texto para não perder zeros à esquerda. Reutilize as funções existentes de normalização de telefones.
- Preserve a deduplicação de faturas, o controle de apresentação por contato e o agrupamento de instalações que compartilham o mesmo telefone.
- Marque uma fatura como processada somente após a entrega bem-sucedida, conforme as regras existentes. Não altere as chaves de estado sem considerar os dados já gravados.
- Preserve o envio separado do código de barras e o comportamento dos modos `--barcode-only` e `--barcode-all`.
- Ao alterar SQLite, mantenha compatibilidade com bancos existentes. Use queries parametrizadas e uma conexão própria para cada thread que escreve no banco.
- Atualize `README.md` e `.env.example` quando mudar configuração, comandos ou comportamento documentado. Não adicione ferramentas ou dependências sem necessidade para a tarefa.

## Validação

- Para mudanças Python, execute os testes pertinentes; use `uv run pytest` para alterações que afetem vários módulos ou o fluxo de entrega.
- Para mudanças no frontend, execute `npm run typecheck` e `npm run build` dentro de `frontend/` e confira o diff dos artefatos gerados.
- Cubra mudanças de comportamento com testes úteis, seguindo os exemplos existentes de clientes falsos, `monkeypatch` e diretórios temporários.
- Testes devem usar bancos, arquivos de estado e PDFs temporários e simular IMAP/Evolution, sem depender de serviços ou credenciais reais.
- Na entrega, informe o que mudou, quais verificações executou e qualquer impedimento de validação.

## Dados e efeitos externos

- Não exponha nem versione `.env`, credenciais IMAP, chaves da Evolution, senhas de contas, telefones ou conteúdo real de faturas. Use `.env.example` como referência de configuração.
- Preserve `data/`, `downloads/`, `state/` e `state.json`: contêm dados de execução e não são fixtures de teste. Não apague estado para forçar reenvios.
- Não execute o worker, `voltbot-send-test` ou endpoints que disparam envios reais sem autorização para esses efeitos. `--once` limita a execução a um ciclo, mas ainda pode enviar mensagens.
- `--dry-run` evita disparos de WhatsApp e gravação do estado de envio, mas ainda pode consultar IMAP e salvar PDFs; prefira mocks para validação automatizada.
- A interface web não tem autenticação e destina-se ao uso local. Preserve o bind local por padrão e não amplie sua exposição de rede incidentalmente.
- Preserve volumes Docker e dados existentes; não use `docker compose down -v` como etapa de desenvolvimento ou teste.
