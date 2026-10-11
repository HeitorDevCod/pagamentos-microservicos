import pytest
from fastapi.testclient import TestClient

from app import database
from app.fila import FilaBanco
from app.main import criar_app
from app.worker import processar_pagamento, processar_pendentes


@pytest.fixture
def caminho_banco(tmp_path):
    return str(tmp_path / "teste.db")


@pytest.fixture
def client(caminho_banco):
    return TestClient(criar_app(caminho_banco))


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


def test_criar_pagamento_publica_mensagem_na_fila(client, caminho_banco):
    client.post("/pagamentos", json=novo_pagamento())

    assert FilaBanco(caminho_banco).pendentes() == [(1, {"pagamento_id": 1})]


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


def test_processar_pendentes_consome_a_fila_e_atualiza_pagamentos(client, caminho_banco):
    client.post("/pagamentos", json=novo_pagamento(valor="10.00"))
    client.post("/pagamentos", json=novo_pagamento(valor="2000.00"))

    assert processar_pendentes(caminho_banco) == 2
    assert client.get("/pagamentos/1").json()["status"] == "aprovado"
    assert client.get("/pagamentos/2").json()["status"] == "recusado"
    assert FilaBanco(caminho_banco).pendentes() == []


def test_processar_pendentes_sem_mensagens_nao_faz_nada(caminho_banco):
    database.criar_tabelas(caminho_banco)

    assert processar_pendentes(caminho_banco) == 0


def test_mesma_chave_e_mesmo_pedido_nao_cria_outro_pagamento(client, caminho_banco):
    cabecalhos = {"Idempotency-Key": "pedido-123"}

    primeira = client.post("/pagamentos", json=novo_pagamento(), headers=cabecalhos)
    segunda = client.post("/pagamentos", json=novo_pagamento(), headers=cabecalhos)

    assert primeira.status_code == 201
    assert segunda.status_code == 201
    assert segunda.json()["id"] == primeira.json()["id"]
    assert len(client.get("/pagamentos").json()) == 1
    assert len(FilaBanco(caminho_banco).pendentes()) == 1


def test_mesma_chave_com_dados_diferentes_retorna_409(client):
    cabecalhos = {"Idempotency-Key": "pedido-456"}
    client.post("/pagamentos", json=novo_pagamento(), headers=cabecalhos)

    resposta = client.post(
        "/pagamentos", json=novo_pagamento(valor="99.00"), headers=cabecalhos
    )

    assert resposta.status_code == 409
    assert len(client.get("/pagamentos").json()) == 1


def test_chaves_diferentes_criam_pagamentos_diferentes(client):
    client.post("/pagamentos", json=novo_pagamento(), headers={"Idempotency-Key": "a"})
    client.post("/pagamentos", json=novo_pagamento(), headers={"Idempotency-Key": "b"})

    assert len(client.get("/pagamentos").json()) == 2


def test_sem_chave_cada_requisicao_cria_um_pagamento(client):
    client.post("/pagamentos", json=novo_pagamento())
    client.post("/pagamentos", json=novo_pagamento())

    assert len(client.get("/pagamentos").json()) == 2
