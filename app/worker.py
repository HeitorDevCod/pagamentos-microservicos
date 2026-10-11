import os

from app import database
from app.fila import FilaRabbitMQ

LIMITE_CENTAVOS = 100_000  # R$ 1.000,00, limite simulado por transação


def decidir_status(valor_centavos):
    return "aprovado" if valor_centavos <= LIMITE_CENTAVOS else "recusado"


def processar_pagamento(caminho_banco, pagamento_id):
    """Processa um pagamento pendente. Se já foi processado, não faz nada."""
    pagamento = database.buscar_pagamento(caminho_banco, pagamento_id)
    if pagamento is None or pagamento["status"] != "pendente":
        return None

    novo_status = decidir_status(pagamento["valor_centavos"])
    database.atualizar_status(caminho_banco, pagamento_id, novo_status)
    return novo_status


def processar_mensagem(caminho_banco, mensagem):
    if "pagamento_id" not in mensagem:
        raise ValueError(f"mensagem sem o campo 'pagamento_id': {mensagem}")
    processar_pagamento(caminho_banco, mensagem["pagamento_id"])


def marcar_falha(caminho_banco, mensagem, erro):
    pagamento_id = mensagem.get("pagamento_id")
    if pagamento_id is not None:
        database.atualizar_status(caminho_banco, pagamento_id, "erro")


def executar(caminho_banco, fila=None):
    database.criar_tabelas(caminho_banco)
    fila = fila or FilaRabbitMQ()
    print("Worker conectado à fila de pagamentos.")
    fila.consumir(
        lambda mensagem: processar_mensagem(caminho_banco, mensagem),
        lambda mensagem, erro: marcar_falha(caminho_banco, mensagem, erro),
    )


if __name__ == "__main__":
    executar(os.getenv("DATABASE_URL", "pagamentos.db"))
