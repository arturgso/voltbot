# VoltBot ⚡

Automatiza a consulta de faturas da Enel recebidas por e-mail e seu envio pelo
WhatsApp via Evolution API. Uma interface web reúne instalações, destinatários,
contas de e-mail e histórico de execuções, reduzindo o trabalho de encaminhar
manualmente faturas de várias unidades consumidoras.

## Funcionalidades

- Consulta várias contas IMAP e busca faturas por dia ou mês completo.
- Extrai instalação, valor e código de barras do corpo do e-mail, além do PDF anexado.
- Agrupa instalações pelo telefone do destinatário e envia apresentação inicial,
  resumo das faturas, códigos de barras em mensagens separadas e PDFs.
- Mantém controle de faturas processadas e de apresentações já enviadas.
- Permite cadastrar instalações, contatos e senha de abertura do PDF; quando
  informada, a senha acompanha a mensagem da fatura.
- Oferece simulação com prévia por destinatário, histórico, logs e diagnóstico
  de falhas IMAP na interface.
- Executa consultas semanais automáticas pelo servidor web, com próxima execução
  persistida e contagem regressiva na interface.
- Permite reenviar somente os códigos de barras, sem reenviar o texto e o PDF.

A leitura atual procura mensagens na `INBOX` com o assunto
`Enel - Conta por email`. Para reconhecer uma fatura, o parser precisa encontrar
`INSTALAÇÃO/UC` e um anexo PDF. Valor e código de barras são extraídos quando
presentes no corpo do e-mail; não há OCR ou leitura do conteúdo do PDF.

## Tecnologias e arquitetura

| Tecnologia | Responsabilidade |
| --- | --- |
| Python 3.14+, uv e Pydantic Settings | Aplicação, dependências e configuração |
| FastAPI e Uvicorn | API HTTP, interface estática e tarefas em background |
| React 19, TypeScript, Mantine 8 e Vite 6 | Interface web e compilação do frontend |
| SQLite | Instalações, contatos, contas, histórico e agendamento |
| IMAP e Evolution API | Consulta de e-mails e envio pelo WhatsApp |
| Docker Compose | Aplicação e serviços da Evolution API |
| pytest e GitHub Actions | Testes e CI/CD em runner self-hosted |

O fluxo principal é: consulta IMAP → extração da fatura → armazenamento do PDF
→ associação aos contatos → agrupamento por telefone → envio pela Evolution API.
O estado de envio fica em JSON, separado do banco SQLite. O estado é atualizado
após os envios correspondentes retornarem sucesso pela API; não representa
confirmação de leitura ou entrega ao aparelho do destinatário.

```text
src/voltbot/
  main.py             CLI e orquestração dos ciclos
  imap_client.py      Consulta às contas de e-mail
  parsers.py          Extração dos dados e anexos
  domain.py           Objetos de domínio e normalização de telefones
  evolution.py        Agrupamento, mensagens e transporte HTTP
  db.py, contacts.py  Persistência SQLite e consulta de contatos
  state.py            Controle de faturas e apresentações enviadas
  storage.py          Armazenamento dos PDFs
  scheduler.py        Agendamento semanal persistente
  config.py           Configuração por ambiente e .env
  web.py              API, tarefas em background e servidor web
  static/             Frontend compilado
frontend/src/         Código-fonte da interface
scripts/ci/           Deploy local
.github/workflows/   Pipeline de CI/CD
tests/                Testes automatizados
```

## Pré-requisitos

Para executar localmente:

- Python **3.14 ou superior** e [uv](https://docs.astral.sh/uv/).
- Uma conta com acesso IMAP às faturas; use senha de aplicativo se o provedor exigir.
- Evolution API acessível, com chave de API e instância WhatsApp pareada para envios.

Para usar o Compose, instale Docker Engine com Buildx e Docker Compose v2,
com acesso ao daemon pelo usuário que executa os comandos. O Compose fornece
Evolution API 2.3.7, PostgreSQL 15 e Redis 7. PostgreSQL e Redis atendem à Evolution;
o VoltBot continua usando SQLite.

Node.js e npm são necessários para desenvolver ou recompilar o frontend. O CI
usa **Node.js 24**. A execução do bundle já versionado não exige Node.js.

## Instalação e configuração

```bash
git clone https://github.com/arturgso/voltbot.git
cd voltbot
cp .env.example .env
```

Edite o `.env` antes de iniciar a aplicação. Nunca versione esse arquivo nem
credenciais, telefones ou faturas reais.

### Variáveis de ambiente

Os valores abaixo descrevem o `.env.example`. As configurações da aplicação são
lidas do ambiente ou do `.env` no diretório de execução.

| Variável | Uso e valor de referência |
| --- | --- |
| `IMAP_HOST` | Servidor IMAP; `imap.gmail.com` no exemplo |
| `IMAP_USER` | Usuário da conta inicial; obrigatório na configuração |
| `IMAP_PASS` | Senha da conta inicial; obrigatória na configuração |
| `EVOLUTION_API_URL` | URL acessível pelo backend; veja as opções de execução abaixo |
| `EVOLUTION_API_KEY` | Chave necessária para os envios e para iniciar a Evolution no Compose |
| `EVOLUTION_INSTANCE` | Nome da instância WhatsApp previamente criada e pareada |
| `DB_PATH` | SQLite local; `data/voltbot.db` |
| `DOWNLOADS_DIR` | Diretório local dos PDFs; `downloads` |
| `STATE_PATH` | Estado local de envio; `state.json` |
| `WEB_HOST` | Bind do servidor local; `127.0.0.1` |
| `WEB_PORT` | Porta do servidor local; `8000` |
| `BIND_IP` | Bind das portas publicadas pelo Compose; `127.0.0.1` |
| `POSTGRES_USER` | Usuário PostgreSQL da Evolution; `evolution` no exemplo |
| `POSTGRES_PASSWORD` | Senha PostgreSQL da Evolution; substitua o valor de exemplo |
| `POSTGRES_DB` | Banco PostgreSQL da Evolution; `evolution` no exemplo |

Quando a tabela de contas está vazia, a conta IMAP do `.env` é cadastrada como
**Principal**. Depois, gerencie as contas pela aba **E-mails**. Alterar o `.env`
não sobrescreve uma conta já cadastrada. Se nenhuma conta cadastrada estiver
ativa, a consulta usa a conta do `.env` como fallback.

### Execução local

Configure `EVOLUTION_API_URL` para o endereço real da Evolution. O exemplo usa
`http://127.0.0.1:8080`; se a Evolution vier do Compose deste projeto, use
`http://127.0.0.1:7800`.

```bash
uv sync --locked
uv run voltbot-web
```

Acesse [http://127.0.0.1:8000](http://127.0.0.1:8000).
O servidor também aceita `--host` e `--port`, que prevalecem sobre o `.env`.
O endpoint `/health` verifica a resposta do servidor, sem testar IMAP ou Evolution.
A documentação da API fica em `/docs`.

### Execução com Docker Compose

No `.env`, ajuste `EVOLUTION_API_URL=http://127.0.0.1:7800` para a URL publicada
pela Evolution. O Compose configura o backend para acessá-la internamente por
`http://evolution-api:8080`.

```bash
docker compose pull evolution-api voltbot-web
docker compose up -d evolution-api voltbot-web
docker compose ps
```

- Interface: [http://127.0.0.1:7801](http://127.0.0.1:7801).
- Evolution API: [http://127.0.0.1:7800](http://127.0.0.1:7800).

Crie e pareie a instância na Evolution API antes de realizar envios. O VoltBot
não faz esse pareamento pela interface. O Compose inicia PostgreSQL e Redis como
dependências; o worker CLI fica no perfil opcional `app`.

O Compose da raiz usa `ghcr.io/arturgso/voltbot:latest` tanto para o servidor web
quanto para o worker opcional. Não é necessário compilar o projeto localmente.
Para atualizar apenas o servidor web, preservando os dados:

```bash
docker compose pull voltbot-web
docker compose up -d --no-deps voltbot-web
```

Se o pacote exigir autenticação, faça login no `ghcr.io` com uma credencial
autorizada a ler a imagem antes do pull.

Para construir uma imagem de desenvolvimento, o `Dockerfile` usa o frontend já
compilado em `src/voltbot/static/`. Compile-o antes de executar
`docker build -t voltbot:local .`; o CI faz essa compilação automaticamente.

## Uso e agendamento

Na interface, cadastre as unidades em **Instalações e contatos** e associe seus
destinatários. Preserve os zeros à esquerda dos códigos de instalação. A senha
opcional do PDF é incluída na mensagem, sem alterar ou descriptografar o arquivo.

Em **Execuções**, escolha hoje, uma data ou um mês. A opção **Simular** mostra as
mensagens previstas sem enviá-las nem gravar o estado de envio. A simulação ainda
consulta IMAP e pode salvar PDFs. Os modos de código de barras ficam em
**Opções avançadas**. Limpar o histórico remove execuções e logs, preservando o
estado de envio e o agendamento.

O agendador do servidor web funciona da seguinte forma:

- A primeira execução ocorre sete dias após a inicialização do agendamento.
- Cada ciclo consulta os sete dias anteriores e o dia atual, com sobreposição
  para reduzir a perda de e-mails recebidos após a consulta anterior.
- A próxima data fica no SQLite e sobrevive a reinícios e limpeza do histórico.
- Ao voltar de um período desligado, executa uma única tarefa pendente; não
  recupera automaticamente períodos anteriores à janela consultada.
- Execuções manuais não adiam o agendamento. Tarefas web compartilham um bloqueio
  para evitar processamento simultâneo dentro do processo.
- Falhas ficam no histórico; uma execução semanal com erro não é repetida
  imediatamente, e a próxima permanece no horário semanal seguinte.

Mantenha uma única instância de processamento para o mesmo banco e estado.
Não execute o loop CLI em paralelo ao servidor web. O agendador faz envios reais
quando vence o prazo e requer que o servidor esteja em funcionamento.

### CLI

```bash
uv run voltbot --help
# Simular um dia; ainda consulta IMAP e pode salvar PDFs
uv run voltbot --date 2026-10-01 --once --dry-run
# Simular um mês; --month sempre executa um único ciclo
uv run voltbot --month 2026-10 --dry-run
```

Remova `--dry-run` para enviar efetivamente. `--once` limita a um ciclo, mas não
impede envios. Sem `--once` ou `--month`, a CLI inicia um ciclo imediatamente e
repete a consulta a cada `604800` segundos; `--interval-seconds` altera esse
intervalo. O loop consulta o dia atual, ou a data de `--date`, e não a janela
semanal usada pelo servidor web. Não existe variável `POLL_INTERVAL_SECONDS`.

`--barcode-only` envia somente os códigos das faturas já processadas no período.
Com `--barcode-all`, inclui também faturas ainda não processadas. Esse modo não
salva PDFs nem atualiza o estado de envio; novas execuções podem reenviar códigos.

O comando `uv run voltbot-send-test --help` descreve o utilitário de envio direto
de texto ou PDF a números informados. Esse utilitário realiza envios reais.

## Desenvolvimento e testes

Com o backend na porta 8000, execute em outro terminal:

```bash
cd frontend
npm ci
npm run dev
```

Acesse [http://localhost:5173](http://localhost:5173). O Vite encaminha `/api`
para `http://127.0.0.1:8000`.

Validação do backend, a partir da raiz:

```bash
uv run pytest
```

Validação e compilação do frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

O build substitui `src/voltbot/static/`. Edite os arquivos em `frontend/src/` e
inclua os artefatos gerados na alteração. Os testes usam mocks e dados temporários,
sem exigir credenciais reais ou serviços IMAP/Evolution disponíveis.

## CI/CD e imagens

O workflow [CI/CD local](.github/workflows/ci-cd.yml) roda em pushes para `master`
e por acionamento manual. Não há gatilho para pull requests. Todos os passos
exigem um runner Linux x64 com a label `voltbot-local`; sem runner online, os jobs
aguardam, sem fallback para máquinas hospedadas pelo GitHub.

O pipeline executa pytest, typecheck e build do frontend. Em `master`, autentica-se
com `GITHUB_TOKEN` e publica pelo `docker/build-push-action`:

- `ghcr.io/arturgso/voltbot:latest`.
- `ghcr.io/arturgso/voltbot:<SHA completo do commit>`.

O token recebe `contents: read` e `packages: write`. O build usa o diretório
compilado no mesmo job. Não há cache remoto nem upload de artefatos do Actions;
o upload automático do registro de build está desativado.

A publicação no GHCR não atualiza a aplicação em execução. O Compose padrão
baixa a imagem publicada; use os comandos de atualização acima para aplicá-la.

### Runner e deploy da instalação atual

O runner `voltbot-phoenixa-local` está instalado em `~/.local/share/voltbot-runner`
e é gerenciado por um serviço systemd do usuário:

```bash
systemctl --user status voltbot-actions-runner
systemctl --user restart voltbot-actions-runner
journalctl --user -u voltbot-actions-runner -n 50
```

O computador precisa estar ligado, conectado e com acesso ao Docker. Para manter
o serviço ativo após logout, um administrador pode habilitar o linger:

```bash
sudo loginctl enable-linger "$USER"
```

Para o deploy, acione **Actions → CI/CD local → Run workflow**, selecione `master`
e marque **deploy**. Após validar e publicar, o script [deploy.sh](scripts/ci/deploy.sh)
reconstrói uma imagem local do checkout e atualiza somente `voltbot-web`, usando o
Compose e o `.env` em `/home/artur/Repo/voltbot`. Esse caminho está definido no
workflow e precisa ser adaptado em outra instalação.

O deploy preserva volumes e diretórios, exige Evolution/PostgreSQL/Redis já
iniciados e verifica `/health` dentro do contêiner. Ele não executa rollback
automático se essa verificação falhar. Ao reiniciar o servidor, uma tarefa semanal
pendente pode disparar envios. Sem marcar **deploy**, o pipeline apenas valida e
publica a imagem.

Pelas regras atuais, [runners self-hosted não consomem a franquia de computação](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
e o [armazenamento e a transferência de imagens no GHCR são gratuitos](https://docs.github.com/en/billing/concepts/product-billing/github-packages).
CPU, disco, rede e energia são do computador local. Reavalie essas condições caso
o GitHub altere sua política de preços.

## Persistência e segurança

A interface e a API não têm autenticação e destinam-se a uso local. Mantenha
`WEB_HOST` e `BIND_IP` em `127.0.0.1`, salvo se houver controle de acesso externo.
As credenciais IMAP e senhas de PDF são armazenadas no SQLite sem criptografia;
restrinja o acesso ao banco, aos backups e ao diretório da aplicação.

| Dado | Execução local com o `.env.example` | Docker Compose |
| --- | --- | --- |
| Cadastros, histórico e agenda | `data/voltbot.db` | Volume `enel_data`, em `/app/data/voltbot.db` |
| Estado de envio | `state.json` | `./state/state.json` |
| PDFs | `downloads/` | `./downloads/` |
| Dados da Evolution | Conforme instalação externa | Volumes `evolution_instances`, `evolution_postgres` e `evolution_redis` |

Preserve banco, PDFs, estado e volumes ao atualizar. Apagar o estado pode permitir
reenvios de faturas e apresentações. Não use `docker compose down -v` para atualizar
ou solucionar problemas de execução.
