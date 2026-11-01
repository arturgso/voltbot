# VoltBot ⚡

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

As abas no topo organizam execução e cadastros. Use **Adicionar** para abrir os
formulários de cadastro; contatos também podem ser editados em um modal.
Cada instalação pode ter uma **Senha para abrir o PDF**, informada ao adicionar
ou editar a instalação. Quando cadastrada, ela acompanha os dados dessa instalação
na mensagem da fatura e na prévia da simulação. O campo é opcional; deixe-o vazio
ao editar para remover a senha. O modo de envio somente do código de barras
continua enviando apenas os dígitos.
Na execução, **Simular envio** mostra uma prévia por destinatário sem enviar
mensagens (a consulta IMAP e o download de PDFs ainda podem ocorrer). As opções
de reenvio de códigos de barras ficam em **Opções avançadas**. Selecione um item
do histórico para ver seu resultado e expandir os logs.

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
