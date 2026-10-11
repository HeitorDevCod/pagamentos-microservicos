from decimal import Decimal

from fastapi import FastAPI, HTTPException

from app import database
from app.schemas import PagamentoCriar, PagamentoResposta

STATUS_INICIAL = "pendente"


def criar_app(caminho_banco: str = "pagamentos.db") -> FastAPI:
    database.criar_tabelas(caminho_banco)
    app = FastAPI(title="Pagamentos", version="0.1.0")

    def para_resposta(linha: dict) -> PagamentoResposta:
        return PagamentoResposta(
            id=linha["id"],
            descricao=linha["descricao"],
            valor=Decimal(linha["valor_centavos"]).scaleb(-2),
            metodo=linha["metodo"],
            status=linha["status"],
            criado_em=linha["criado_em"],
        )

    @app.post("/pagamentos", status_code=201, response_model=PagamentoResposta)
    def criar_pagamento(dados: PagamentoCriar):
        novo_id = database.inserir_pagamento(
            caminho_banco,
            dados.descricao,
            int(dados.valor * 100),
            dados.metodo.value,
            STATUS_INICIAL,
        )
        return para_resposta(database.buscar_pagamento(caminho_banco, novo_id))

    @app.get("/pagamentos", response_model=list[PagamentoResposta])
    def listar_pagamentos():
        return [para_resposta(l) for l in database.listar_pagamentos(caminho_banco)]

    @app.get("/pagamentos/{pagamento_id}", response_model=PagamentoResposta)
    def buscar_pagamento(pagamento_id: int):
        linha = database.buscar_pagamento(caminho_banco, pagamento_id)
        if linha is None:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        return para_resposta(linha)

    return app
