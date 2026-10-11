import os
import time

from app import database
from app.fila import FilaBanco

LIMITE_CENTAVOS = 100_000  # R$ 1.000,00, limite simulado por transação
MAX_TENTATIVAS = 3


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


def processar_pendentes(caminho_banco):
    """Processa as mensagens pendentes da fila. Devolve quantas foram lidas."""
    fila = FilaBanco(caminho_banco)
    mensagens = fila.pendentes()
    for mensagem_id, mensagem in mensagens:
        try:
            processar_pagamento(caminho_banco, mensagem["pagamento_id"])
        except Exception as erro:
            status = fila.registrar_falha(mensagem_id, str(erro), MAX_TENTATIVAS)
            if status == "falhou":
                pagamento_id = mensagem.get("pagamento_id")
                if pagamento_id is not None:
                    database.atualizar_status(caminho_banco, pagamento_id, "erro")
            continue
        fila.marcar_processada(mensagem_id)
    return len(mensagens)


def executar(caminho_banco, intervalo=2.0):
    database.criar_tabelas(caminho_banco)
    print(f"Worker iniciado. Verificando a fila a cada {intervalo} segundos.")
    while True:
        processar_pendentes(caminho_banco)
        time.sleep(intervalo)


if __name__ == "__main__":
    executar(os.getenv("DATABASE_PATH", "pagamentos.db"))
