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


def executar(caminho_banco, fila=None):
    fila = fila or FilaRabbitMQ()

    def ao_receber(mensagem):
        processar_pagamento(caminho_banco, mensagem["pagamento_id"])

    fila.consumir(ao_receber)


if __name__ == "__main__":
    import os

    executar(os.getenv("DATABASE_PATH", "pagamentos.db"))
