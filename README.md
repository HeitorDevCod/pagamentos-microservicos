# Pagamentos Microserviços

API de pagamentos em Python, construída em etapas para estudar sistemas de backend orientados a eventos: registro de pagamentos, processamento assíncrono, idempotência e containers.

Este projeto está em desenvolvimento. A primeira etapa é a API de registro e consulta de pagamentos.

## Tecnologias

- Python 3.14
- FastAPI e Pydantic para a API e validação dos dados
- SQLite (biblioteca padrão) para armazenamento
- pytest e httpx para testes

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:criar_app --factory --reload
```

A documentação interativa fica em http://127.0.0.1:8000/docs.

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

1. Fila de mensagens (RabbitMQ) e um worker que processa os pagamentos pendentes.
2. Idempotência: o mesmo pedido enviado duas vezes não gera dois pagamentos.
3. Banco PostgreSQL e Docker Compose para subir tudo com um comando.
