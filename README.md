# Pagamentos Microserviços

API de pagamentos em Python, construída em etapas para estudar sistemas de backend orientados a eventos: registro de pagamentos, processamento assíncrono, idempotência e containers.

Este projeto está em desenvolvimento. Etapas concluídas:

1. API de registro e consulta de pagamentos.
2. Fila com RabbitMQ e worker que processa os pagamentos pendentes.

## Tecnologias

- Python 3.14
- FastAPI e Pydantic para a API e validação dos dados
- SQLite (biblioteca padrão) para armazenamento
- RabbitMQ (fila) com a biblioteca pika
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

A API publica uma mensagem na fila `pagamentos.pendentes` a cada pagamento criado. O worker consome essas mensagens e decide o status:

- valor até R$ 1.000,00: `aprovado`
- valor acima de R$ 1.000,00: `recusado`

O worker ignora pagamentos que já não estão `pendente`, então a mesma mensagem processada duas vezes não muda o resultado.

Para rodar, primeiro suba um RabbitMQ local, depois em outro terminal:

```bash
python -m app.worker
```

A conexão padrão é `amqp://guest:guest@localhost:5672/`. Para usar outra, defina a variável `RABBITMQ_URL`. O arquivo do banco é definido por `DATABASE_PATH` (padrão `pagamentos.db`).

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
tests/
  test_pagamentos.py
```

## Próximas etapas

1. Idempotência: o mesmo pedido enviado duas vezes não gera dois pagamentos.
2. Tratar falhas: retentativas e fila de mensagens com erro (dead-letter).
3. Banco PostgreSQL e Docker Compose para subir tudo com um comando.
