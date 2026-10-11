import pytest
from fastapi.testclient import TestClient

from app import database
from app.fila import FilaMemoria
from app.main import criar_app
from app.worker import processar_pagamento


@pytest.fixture
def caminho_banco(tmp_path):
    return str(tmp_path / "teste.db")


@pytest.fixture
def fila():
    return FilaMemoria()


@pytest.fixture
def client(caminho_banco, fila):
    return TestClient(criar_app(caminho_banco, fila=fila))


def novo_pagamento(**campos):
    dados = {"descricao": "Assinatura mensal", "valor": "49.90", "metodo": "pix"}
    dados.update(campos)
    return dados


def test_criar_pagamento_comeca_pendente(client):
    resposta = client.post("/pagamentos", json=novo_pagamento())

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["valor"] == "49.90"
    assert corpo["status"] == "pendente"
    assert corpo["metodo"] == "pix"


def test_criar_pagamento_publica_mensagem_na_fila(client, fila):
    client.post("/pagamentos", json=novo_pagamento())

    assert fila.mensagens == [{"pagamento_id": 1}]


def test_valor_zero_ou_negativo_e_recusado(client):
    assert client.post("/pagamentos", json=novo_pagamento(valor="0")).status_code == 422
    assert client.post("/pagamentos", json=novo_pagamento(valor="-5")).status_code == 422


def test_metodo_desconhecido_e_recusado(client):
    resposta = client.post("/pagamentos", json=novo_pagamento(metodo="dinheiro"))

    assert resposta.status_code == 422


def test_buscar_pagamento_existente(client):
    client.post("/pagamentos", json=novo_pagamento())

    resposta = client.get("/pagamentos/1")

    assert resposta.status_code == 200
    assert resposta.json()["descricao"] == "Assinatura mensal"


def test_buscar_pagamento_inexistente_retorna_404(client):
    resposta = client.get("/pagamentos/999")

    assert resposta.status_code == 404


def test_listar_pagamentos_na_ordem_de_criacao(client):
    client.post("/pagamentos", json=novo_pagamento(descricao="Primeiro"))
    client.post("/pagamentos", json=novo_pagamento(descricao="Segundo", metodo="boleto"))

    resposta = client.get("/pagamentos")

    assert [p["descricao"] for p in resposta.json()] == ["Primeiro", "Segundo"]


def test_worker_aprova_pagamento_dentro_do_limite(client, caminho_banco):
    client.post("/pagamentos", json=novo_pagamento(valor="1000.00"))

    assert processar_pagamento(caminho_banco, 1) == "aprovado"
    assert client.get("/pagamentos/1").json()["status"] == "aprovado"


def test_worker_recusa_pagamento_acima_do_limite(client, caminho_banco):
    client.post("/pagamentos", json=novo_pagamento(valor="1000.01"))

    assert processar_pagamento(caminho_banco, 1) == "recusado"
    assert client.get("/pagamentos/1").json()["status"] == "recusado"


def test_worker_nao_reprocessa_pagamento_ja_processado(client, caminho_banco):
    client.post("/pagamentos", json=novo_pagamento(valor="10.00"))
    processar_pagamento(caminho_banco, 1)

    assert processar_pagamento(caminho_banco, 1) is None
    assert client.get("/pagamentos/1").json()["status"] == "aprovado"


def test_worker_ignora_pagamento_inexistente(caminho_banco):
    database.criar_tabelas(caminho_banco)

    assert processar_pagamento(caminho_banco, 999) is None
