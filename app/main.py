from decimal import Decimal

import sqlite3

from fastapi import FastAPI, Header, HTTPException

from app import database
from app.fila import FilaBanco
from app.schemas import PagamentoCriar, PagamentoResposta

STATUS_INICIAL = "pendente"


def mesmo_pedido(linha: dict, dados: PagamentoCriar) -> bool:
    return (
        linha["descricao"] == dados.descricao
        and linha["valor_centavos"] == int(dados.valor * 100)
        and linha["metodo"] == dados.metodo.value
    )


def criar_app(caminho_banco: str = "pagamentos.db", fila=None) -> FastAPI:
    database.criar_tabelas(caminho_banco)
    fila = fila or FilaBanco(caminho_banco)
    app = FastAPI(title="Pagamentos", version="0.2.0")

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
    def criar_pagamento(
        dados: PagamentoCriar,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        if idempotency_key:
            existente = database.buscar_pagamento_por_chave(caminho_banco, idempotency_key)
            if existente:
                if not mesmo_pedido(existente, dados):
                    raise HTTPException(
                        status_code=409,
                        detail="Essa Idempotency-Key já foi usada com outros dados",
                    )
                return para_resposta(existente)

        try:
            novo_id = database.inserir_pagamento(
                caminho_banco,
                dados.descricao,
                int(dados.valor * 100),
                dados.metodo.value,
                STATUS_INICIAL,
                idempotency_key,
            )
        except sqlite3.IntegrityError:
            # Outra requisição com a mesma chave foi gravada antes desta
            existente = database.buscar_pagamento_por_chave(caminho_banco, idempotency_key)
            if existente and mesmo_pedido(existente, dados):
                return para_resposta(existente)
            raise HTTPException(
                status_code=409,
                detail="Essa Idempotency-Key já foi usada com outros dados",
            )

        fila.publicar({"pagamento_id": novo_id})
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
