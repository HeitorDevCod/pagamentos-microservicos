from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class Metodo(str, Enum):
    pix = "pix"
    boleto = "boleto"
    cartao_credito = "cartao_credito"


class PagamentoCriar(BaseModel):
    descricao: str = Field(min_length=3, max_length=120)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    metodo: Metodo


class PagamentoResposta(BaseModel):
    id: int
    descricao: str
    valor: Decimal
    metodo: Metodo
    status: str
    criado_em: str
