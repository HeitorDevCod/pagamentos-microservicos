import json
from contextlib import closing

from app.database import conectar


class FilaBanco:
    """Fila simples guardada numa tabela do SQLite."""

    def __init__(self, caminho_banco):
        self.caminho = caminho_banco

    def publicar(self, mensagem):
        with closing(conectar(self.caminho)) as conn:
            conn.execute(
                "INSERT INTO fila (mensagem) VALUES (?)", (json.dumps(mensagem),)
            )
            conn.commit()

    def pendentes(self):
        with closing(conectar(self.caminho)) as conn:
            linhas = conn.execute(
                "SELECT id, mensagem FROM fila WHERE processada = 0 ORDER BY id"
            ).fetchall()
            return [(linha["id"], json.loads(linha["mensagem"])) for linha in linhas]

    def marcar_processada(self, mensagem_id):
        with closing(conectar(self.caminho)) as conn:
            conn.execute("UPDATE fila SET processada = 1 WHERE id = ?", (mensagem_id,))
            conn.commit()
