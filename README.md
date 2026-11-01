# VoltBot ⚡

## CI/CD local (GitHub Actions)

O workflow `.github/workflows/ci-cd.yml` executa pytest, typecheck e build do
frontend a cada push em `master`, ou manualmente em **Actions → CI/CD local**.
Após a validação em `master`, `docker/build-push-action` publica a imagem
`ghcr.io/arturgso/voltbot` com as tags `latest` e o SHA completo do commit.
O contexto local inclui o frontend compilado no mesmo job. A autenticação usa
o `GITHUB_TOKEN` temporário com permissão `packages: write`, sem PAT cadastrado.
Todos os passos usam exclusivamente o runner `voltbot-phoenixa-local`, com label
`voltbot-local`, instalado em `~/.local/share/voltbot-runner`.
Não executa código de pull requests externos neste computador.

O runner é um serviço systemd do usuário:

```bash
systemctl --user status voltbot-actions-runner
systemctl --user restart voltbot-actions-runner
journalctl --user -u voltbot-actions-runner -n 50
```

O computador precisa estar ligado, conectado e com o serviço ativo. Sem runner
online, os jobs aguardam; não migram para runners hospedados pelo GitHub.
Para manter o serviço após logout/reinício sem sessão aberta, um administrador
pode executar `sudo loginctl enable-linger artur`.

O deploy é manual: execute o workflow na branch `master` marcando **deploy**.
Após os testes, ele constrói a imagem local e atualiza somente `voltbot-web`,
usando o Compose e o `.env` em `/home/artur/Repo/voltbot`; preserva volumes,
downloads e estado. Requer acesso do usuário do runner ao Docker e os serviços
Evolution/PostgreSQL/Redis já iniciados. O agendador normal da aplicação volta
a funcionar com o servidor, podendo executar uma tarefa semanal pendente.
Sem marcar **deploy**, nenhum serviço de produção é iniciado ou alterado.

Pelas [regras atuais de cobrança](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
runners self-hosted são gratuitos e não descontam minutos incluídos no plano.
O workflow não usa cache remoto nem upload de artefatos do Actions. O armazenamento
e a transferência de imagens no GHCR são atualmente gratuitos, conforme a
[documentação do GitHub Packages](https://docs.github.com/en/billing/concepts/product-billing/github-packages).
CPU, disco, rede e energia são do computador local; mudanças futuras de preço
do GitHub devem ser reavaliadas.

Busca faturas da Enel por e-mail (IMAP) e envia via Evolution API (WhatsApp),
falando como o VoltBot.

## Configuração

```bash
cp .env.example .env
# edite o .env com os dados reais (IMAP + Evolution)
```

Instalações, contatos e contas de e-mail de origem são gerenciados pela
interface web (SQLite em `DB_PATH`, padrão `data/voltbot.db`).

## Interface web

```bash
uv run voltbot-web
# abre http://127.0.0.1:8000
```

A interface permite: acompanhar status e logs, executar on-demand (dia, data
ou mês inteiro, com dry-run), cadastrar contas de e-mail de origem e gerenciar
instalações e contatos. Sem autenticação — uso local (bind em `WEB_HOST`).

As abas **Execuções**, **Instalações e contatos** e **E-mails** organizam a interface.
A execução mais recente é selecionada ao carregar o histórico. Em instalações,
selecione uma unidade para ver seus contatos e adicionar destinatários a ela.
Use **Adicionar** para abrir os formulários; contatos também podem ser editados em um modal.
Cada instalação pode ter uma **Senha para abrir o PDF**, informada ao adicionar
ou editar a instalação. Quando cadastrada, ela acompanha os dados dessa instalação
na mensagem da fatura e na prévia da simulação. O campo é opcional; deixe-o vazio
ao editar para remover a senha. O modo de envio somente do código de barras
continua enviando apenas os dígitos.
Na execução, **Simular envio** mostra uma prévia por destinatário sem enviar
mensagens (a consulta IMAP e o download de PDFs ainda podem ocorrer). As opções
de reenvio de códigos de barras ficam em **Opções avançadas**. Selecione um item
do histórico para ver seu resultado e expandir os logs. As prévias ficam recolhidas
por destinatário; abra uma delas para conferir a mensagem, os PDFs e os códigos de barras.

Os logs identificam a conta de e-mail pelo nome cadastrado e mostram a quantidade
de e-mails encontrados. Falhas de login ou conexão IMAP exibem orientações em
português, sem registrar usuário, senha ou a resposta bruta do provedor. Uma falha
na consulta interrompe o ciclo antes do envio de mensagens.

O servidor web mantém o **agendamento semanal ativo**, com intervalo fixo de sete
dias, sem variável de ambiente. A primeira execução ocorre sete dias após a primeira
inicialização; a próxima data fica salva no SQLite, inclusive após reiniciar ou
limpar o histórico. A interface mostra a contagem regressiva e atualiza o status a
cada 15 segundos. O servidor precisa estar em funcionamento para executar.
Cada execução automática consulta os sete dias anteriores e o dia atual,
sobrepondo o dia da execução anterior para não perder e-mails recebidos depois
da consulta. A deduplicação existente evita reenvios. Após ficar desligado, faz uma única execução pendente ao voltar,
sem repetir todos os horários perdidos; períodos anteriores aos últimos sete dias
podem ser consultados manualmente. Execuções manuais continuam disponíveis e não
adiam a próxima execução automática. Se uma execução manual estiver em andamento,
a automática aguarda sua conclusão. Falhas são registradas no histórico e a próxima
tentativa automática permanece no próximo horário semanal.
**Limpar recentes** remove apenas as execuções exibidas e seus logs, preservando o
controle de faturas já enviadas e o agendamento.

## Frontend (desenvolvimento)

O frontend é Vite + React + Mantine em `frontend/`; o build vai para
`src/voltbot/static/`, servido pelo próprio backend.

```bash
cd frontend
npm install
npm run dev    # http://127.0.0.1:5173 (proxy /api -> :8000)
npm run build  # gera o bundle servido em produção
```
## Evolution API (Docker)

```bash
docker compose up -d evolution-api voltbot-web
# parear a instância via QR code; a interface sobe em http://127.0.0.1:8000
# rodada manual opcional (não mantenha outro worker em paralelo ao servidor web):
docker compose --profile app run --rm voltbot --once
```

## Local

```bash
uv sync
# CLI opcional: intervalo padrão fixo de sete dias; prefira o agendador web
uv run voltbot
# rodada única
uv run voltbot --once
```
