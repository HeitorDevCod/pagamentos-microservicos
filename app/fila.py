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
                "SELECT id, mensagem FROM fila WHERE status = 'pendente' ORDER BY id"
            ).fetchall()
            return [(linha["id"], json.loads(linha["mensagem"])) for linha in linhas]

    def falhas(self):
        with closing(conectar(self.caminho)) as conn:
            linhas = conn.execute(
                "SELECT id, mensagem, tentativas, ultimo_erro FROM fila WHERE status = 'falhou' ORDER BY id"
            ).fetchall()
            return [dict(linha) for linha in linhas]

    def marcar_processada(self, mensagem_id):
        with closing(conectar(self.caminho)) as conn:
            conn.execute("UPDATE fila SET status = 'processada' WHERE id = ?", (mensagem_id,))
            conn.commit()

    def registrar_falha(self, mensagem_id, erro, max_tentativas):
        """Conta a falha. Depois de max_tentativas, a mensagem vai para 'falhou'. Devolve o novo status."""
        with closing(conectar(self.caminho)) as conn:
            conn.execute(
                "UPDATE fila SET tentativas = tentativas + 1, ultimo_erro = ? WHERE id = ?",
                (erro, mensagem_id),
            )
            tentativas = conn.execute(
                "SELECT tentativas FROM fila WHERE id = ?", (mensagem_id,)
            ).fetchone()["tentativas"]
            novo_status = "falhou" if tentativas >= max_tentativas else "pendente"
            conn.execute("UPDATE fila SET status = ? WHERE id = ?", (novo_status, mensagem_id))
            conn.commit()
            return novo_status
