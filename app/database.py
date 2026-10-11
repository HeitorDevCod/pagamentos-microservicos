import sqlite3
from contextlib import closing

try:
    import psycopg

    ERROS_DE_INTEGRIDADE = (sqlite3.IntegrityError, psycopg.IntegrityError)
except ImportError:
    ERROS_DE_INTEGRIDADE = (sqlite3.IntegrityError,)

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS pagamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    metodo TEXT NOT NULL,
    status TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    chave_idempotencia TEXT UNIQUE
);

"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS pagamentos (
    id SERIAL PRIMARY KEY,
    descricao TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    metodo TEXT NOT NULL,
    status TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),
    chave_idempotencia TEXT UNIQUE
);

"""


class ChaveDuplicada(Exception):
    """A chave de idempotência já existe no banco."""


def eh_postgres(caminho):
    return str(caminho).startswith(("postgresql://", "postgres://"))


class _Conexao:
    """Deixa SQLite e PostgreSQL usarem o mesmo código: troca '?' por '%s' quando for PostgreSQL."""

    def __init__(self, conn, postgres):
        self.conn = conn
        self.postgres = postgres

    def execute(self, sql, parametros=()):
        if self.postgres:
            sql = sql.replace("?", "%s")
        return self.conn.execute(sql, parametros)

    def executar_script(self, script):
        if self.postgres:
            self.conn.execute(script)
        else:
            self.conn.executescript(script)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def conectar(caminho):
    if eh_postgres(caminho):
        import psycopg
        from psycopg.rows import dict_row

        return _Conexao(psycopg.connect(caminho, row_factory=dict_row), postgres=True)

    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    return _Conexao(conn, postgres=False)


def criar_tabelas(caminho):
    schema = SCHEMA_POSTGRES if eh_postgres(caminho) else SCHEMA_SQLITE
    with closing(conectar(caminho)) as conn:
        conn.executar_script(schema)
        conn.commit()


def inserir_pagamento(caminho, descricao, valor_centavos, metodo, status, chave_idempotencia=None):
    sql = (
        "INSERT INTO pagamentos (descricao, valor_centavos, metodo, status, chave_idempotencia) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    parametros = (descricao, valor_centavos, metodo, status, chave_idempotencia)
    with closing(conectar(caminho)) as conn:
        try:
            if eh_postgres(caminho):
                novo_id = conn.execute(sql + " RETURNING id", parametros).fetchone()["id"]
            else:
                novo_id = conn.execute(sql, parametros).lastrowid
            conn.commit()
            return novo_id
        except ERROS_DE_INTEGRIDADE as erro:
            conn.rollback()
            raise ChaveDuplicada(str(erro)) from erro


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
