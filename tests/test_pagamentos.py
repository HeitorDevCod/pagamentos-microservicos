import pytest
from fastapi.testclient import TestClient

from app.main import criar_app


@pytest.fixture
def client(tmp_path):
    app = criar_app(str(tmp_path / "teste.db"))
    return TestClient(app)


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
