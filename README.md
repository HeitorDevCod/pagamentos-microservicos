# Pagamentos Microserviços

API de pagamentos em Python, construída em etapas para estudar sistemas de backend orientados a eventos: registro de pagamentos, processamento assíncrono, idempotência e containers.

Este projeto está em desenvolvimento. Etapas concluídas:

1. API de registro e consulta de pagamentos.
2. Fila e worker que processam os pagamentos pendentes.
3. Idempotência: o mesmo pedido enviado duas vezes não cria dois pagamentos.

## Tecnologias

- Python 3.14
- FastAPI e Pydantic para a API e validação dos dados
- SQLite (biblioteca padrão) para armazenamento
- Fila guardada no próprio SQLite (sem broker externo)
- pytest e httpx para testes

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:criar_app --factory --reload
```

A documentação interativa fica em http://127.0.0.1:8000/docs.

## Processando pagamentos

A API grava uma mensagem na tabela `fila` a cada pagamento criado. O worker consulta essa tabela a cada 2 segundos, processa as mensagens pendentes e decide o status:

- valor até R$ 1.000,00: `aprovado`
- valor acima de R$ 1.000,00: `recusado`

O worker ignora pagamentos que já não estão `pendente`, então processar a mesma mensagem duas vezes não muda o resultado.

Para rodar, deixe a API no ar e, em outro terminal, o worker:

```bash
python -m app.worker
```

O arquivo do banco é definido por `DATABASE_PATH` (padrão `pagamentos.db`). Use o mesmo valor na API e no worker.

## Idempotência

Em caso de falha de rede, o cliente pode repetir o `POST` sem saber se o primeiro chegou. Para evitar cobranças duplicadas, envie o cabeçalho `Idempotency-Key` com um valor único para cada pedido:

```bash
curl -X POST http://127.0.0.1:8000/pagamentos -H "Content-Type: application/json" -H "Idempotency-Key: pedido-123" -d "{\"descricao\": \"Assinatura mensal\", \"valor\": \"49.90\", \"metodo\": \"pix\"}"
```

- Mesma chave e mesmos dados: a API devolve o pagamento que já existe, sem criar outro e sem publicar outra mensagem na fila.
- Mesma chave com dados diferentes: a API responde `409 Conflict`.
- Sem o cabeçalho: cada requisição cria um pagamento novo.

Se você já tinha um `pagamentos.db` de etapas anteriores, apague o arquivo, porque a tabela ganhou a coluna da chave.

## Testes

```bash
pytest
```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/pagamentos` | Registra um pagamento com status `pendente` |
| `GET` | `/pagamentos` | Lista todos os pagamentos |
| `GET` | `/pagamentos/{id}` | Consulta um pagamento pelo id |

Exemplo de corpo para `POST /pagamentos`:

```json
{
  "descricao": "Assinatura mensal",
  "valor": "49.90",
  "metodo": "pix"
}
```

Métodos aceitos: `pix`, `boleto` e `cartao_credito`. O valor precisa ser maior que zero e ter no máximo duas casas decimais.

## Estrutura

```
app/
  main.py        rotas e criação da aplicação
  schemas.py     modelos de entrada e saída (Pydantic)
  database.py    acesso ao SQLite
  fila.py        fila guardada numa tabela do SQLite
  worker.py      processa os pagamentos pendentes
tests/
  test_pagamentos.py
```

## Próximas etapas

1. Tratar falhas: tentativas repetidas quando o processamento dá erro.
2. Trocar a fila de SQLite por um broker de mensagens (RabbitMQ) e usar PostgreSQL com Docker Compose.
