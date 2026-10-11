import sqlite3
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS pagamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    metodo TEXT NOT NULL,
    status TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    chave_idempotencia TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS fila (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mensagem TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendente',
    tentativas INTEGER NOT NULL DEFAULT 0,
    ultimo_erro TEXT
);
"""


def conectar(caminho):
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas(caminho):
    with closing(conectar(caminho)) as conn:
        conn.executescript(SCHEMA)


def inserir_pagamento(caminho, descricao, valor_centavos, metodo, status, chave_idempotencia=None):
    with closing(conectar(caminho)) as conn:
        cursor = conn.execute(
            "INSERT INTO pagamentos (descricao, valor_centavos, metodo, status, chave_idempotencia) "
            "VALUES (?, ?, ?, ?, ?)",
            (descricao, valor_centavos, metodo, status, chave_idempotencia),
        )
        conn.commit()
        return cursor.lastrowid


def buscar_pagamento_por_chave(caminho, chave_idempotencia):
    with closing(conectar(caminho)) as conn:
        linha = conn.execute(
            "SELECT * FROM pagamentos WHERE chave_idempotencia = ?", (chave_idempotencia,)
        ).fetchone()
        return dict(linha) if linha else None


def buscar_pagamento(caminho, pagamento_id):
    with closing(conectar(caminho)) as conn:
        linha = conn.execute(
            "SELECT * FROM pagamentos WHERE id = ?", (pagamento_id,)
        ).fetchone()
        return dict(linha) if linha else None


def atualizar_status(caminho, pagamento_id, status):
    with closing(conectar(caminho)) as conn:
        conn.execute(
            "UPDATE pagamentos SET status = ? WHERE id = ?", (status, pagamento_id)
        )
        conn.commit()


def listar_pagamentos(caminho):
    with closing(conectar(caminho)) as conn:
        linhas = conn.execute("SELECT * FROM pagamentos ORDER BY id").fetchall()
        return [dict(linha) for linha in linhas]
