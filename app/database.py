import sqlite3
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS pagamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    metodo TEXT NOT NULL,
    status TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def conectar(caminho):
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas(caminho):
    with closing(conectar(caminho)) as conn:
        conn.executescript(SCHEMA)


def inserir_pagamento(caminho, descricao, valor_centavos, metodo, status):
    with closing(conectar(caminho)) as conn:
        cursor = conn.execute(
            "INSERT INTO pagamentos (descricao, valor_centavos, metodo, status) "
            "VALUES (?, ?, ?, ?)",
            (descricao, valor_centavos, metodo, status),
        )
        conn.commit()
        return cursor.lastrowid


def buscar_pagamento(caminho, pagamento_id):
    with closing(conectar(caminho)) as conn:
        linha = conn.execute(
            "SELECT * FROM pagamentos WHERE id = ?", (pagamento_id,)
        ).fetchone()
        return dict(linha) if linha else None


def listar_pagamentos(caminho):
    with closing(conectar(caminho)) as conn:
        linhas = conn.execute("SELECT * FROM pagamentos ORDER BY id").fetchall()
        return [dict(linha) for linha in linhas]
