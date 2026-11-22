import os
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from app import config
from app.dominio.excecoes import ConflitoDeHorarioError  # noqa: F401 (reexportado)

config.carregar_env()  # permite definir CLINICA_DB no .env



def caminho_banco():
    """Caminho do arquivo do banco: variável CLINICA_DB, ou dados/clinica.db no projeto.

    É lido a cada conexão (e não uma vez só), para que os testes possam apontar
    cada teste para um banco temporário diferente.
    Caminho relativo é resolvido a partir da pasta do projeto, e não da pasta
    onde o comando foi rodado: assim o cron ou um uvicorn iniciado em outro
    lugar não criam, sem querer, um clinica.db vazio em outra pasta.
    """
    caminho = Path(os.environ.get("CLINICA_DB") or config.PASTA_DADOS / "clinica.db")
    if not caminho.is_absolute():
        caminho = config.RAIZ_DO_PROJETO / caminho
    return str(caminho)


def normalizar_texto(texto):
    """Deixa o texto minúsculo e sem acentos: "João" -> "joao".

    NFD separa a letra do acento ("ã" vira "a" + "~"); depois descartamos
    os acentos soltos (categoria "Mn" do Unicode). casefold() é um lower()
    mais completo para comparações.
    """
    if texto is None:
        return ""
    decomposto = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return sem_acento.casefold()


def criar_conexao():
    caminho = caminho_banco()
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)  # cria dados/ se faltar
    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys = ON")  # ativa integridade referencial
    # Registra normalizar_texto como função SQL: assim dá para escrever
    # normalizar(nome) dentro de um SELECT (o LIKE do SQLite não ignora acentos).
    conexao.create_function("normalizar", 1, normalizar_texto, deterministic=True)
    return conexao


def criar_tabelas():
    conexao = criar_conexao()
    try:
        _criar_tabelas(conexao)
    finally:
        conexao.close()


def _criar_tabelas(conexao):
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            telefone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alergias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dentistas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cro TEXT UNIQUE NOT NULL,
            especialidade TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            motivo TEXT,
            estado TEXT NOT NULL DEFAULT 'Agendada',
            paciente_id INTEGER NOT NULL,
            dentista_id INTEGER NOT NULL,
            duracao_minutos INTEGER NOT NULL DEFAULT 30,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
            FOREIGN KEY (dentista_id) REFERENCES dentistas(id)
        )
    """)

    # COLLATE NOCASE: "Admin" e "admin" são o mesmo usuário (no UNIQUE e na busca).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_usuario TEXT UNIQUE NOT NULL COLLATE NOCASE,
            senha_hash TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
    """)

    # Migração: bancos criados antes do item 1 não têm a coluna duracao_minutos.
    # PRAGMA table_info devolve uma linha por coluna; o nome fica na posição 1.
    colunas = [linha[1] for linha in cursor.execute("PRAGMA table_info(consultas)")]
    if "duracao_minutos" not in colunas:
        cursor.execute(
            "ALTER TABLE consultas ADD COLUMN duracao_minutos INTEGER NOT NULL DEFAULT 30"
        )

    conexao.commit()


# ---------- Pacientes ----------
# As colunas são listadas por nome (e não SELECT *) para que a ordem da tupla
# não mude se um dia uma coluna nova for adicionada à tabela.

def inserir_paciente(nome, cpf, telefone):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO pacientes (nome, cpf, telefone) VALUES (?, ?, ?)",
            (nome, cpf, telefone)
        )
        conexao.commit()
        return cursor.lastrowid  # id gerado pelo AUTOINCREMENT
    finally:
        conexao.close()  # fecha mesmo se o INSERT falhar (ex.: CPF duplicado)


def buscar_paciente_por_cpf(cpf):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, nome, cpf, telefone FROM pacientes WHERE cpf = ?", (cpf,)
        )
        return cursor.fetchone()
    finally:
        conexao.close()


def buscar_paciente_por_id(paciente_id):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, nome, cpf, telefone FROM pacientes WHERE id = ?", (paciente_id,)
        )
        return cursor.fetchone()
    finally:
        conexao.close()


def listar_pacientes(busca="", limite=50):
    """Pacientes cujo nome contém `busca` (sem diferenciar maiúsculas nem acentos)."""
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        # instr(a, b) > 0 significa "b aparece dentro de a". Usamos instr em vez de
        # LIKE para que % e _ digitados pelo usuário não virem curingas.
        # Com busca vazia, instr devolve 1, ou seja, todos entram.
        cursor.execute(
            """
            SELECT id, nome, cpf, telefone FROM pacientes
            WHERE instr(normalizar(nome), ?) > 0
            ORDER BY normalizar(nome), id
            LIMIT ?
            """,
            (normalizar_texto(busca.strip()), limite)
        )
        return cursor.fetchall()
    finally:
        conexao.close()


# ---------- Dentistas ----------

def inserir_dentista(nome, cro, especialidade):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO dentistas (nome, cro, especialidade) VALUES (?, ?, ?)",
            (nome, cro, especialidade)
        )
        conexao.commit()
        return cursor.lastrowid
    finally:
        conexao.close()


def buscar_dentista_por_cro(cro):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, nome, cro, especialidade FROM dentistas WHERE cro = ?", (cro,)
        )
        return cursor.fetchone()
    finally:
        conexao.close()


def buscar_dentista_por_id(dentista_id):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, nome, cro, especialidade FROM dentistas WHERE id = ?", (dentista_id,)
        )
        return cursor.fetchone()
    finally:
        conexao.close()


def listar_dentistas(busca="", limite=50):
    """Dentistas cujo nome contém `busca` (sem diferenciar maiúsculas nem acentos)."""
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT id, nome, cro, especialidade FROM dentistas
            WHERE instr(normalizar(nome), ?) > 0
            ORDER BY normalizar(nome), id
            LIMIT ?
            """,
            (normalizar_texto(busca.strip()), limite)
        )
        return cursor.fetchall()
    finally:
        conexao.close()


# ---------- Usuários ----------

def inserir_usuario(nome_usuario, senha_hash):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO usuarios (nome_usuario, senha_hash, criado_em) VALUES (?, ?, ?)",
            (nome_usuario, senha_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conexao.commit()
        return cursor.lastrowid
    finally:
        conexao.close()


def buscar_usuario_por_nome(nome_usuario):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, nome_usuario, senha_hash, criado_em FROM usuarios WHERE nome_usuario = ?",
            (nome_usuario,)
        )
        return cursor.fetchone()
    finally:
        conexao.close()


def buscar_usuario_por_id(usuario_id):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, nome_usuario, senha_hash, criado_em FROM usuarios WHERE id = ?",
            (usuario_id,)
        )
        return cursor.fetchone()
    finally:
        conexao.close()


# ---------- Consultas ----------

_COLUNAS_CONSULTA = "id, data_hora, motivo, estado, paciente_id, dentista_id, duracao_minutos"

# Regra de sobreposição: [inicio, fim) novo conflita com um existente se
#   inicio_existente < fim_novo  E  fim_existente > inicio_novo
# O fim de cada consulta é calculado pelo SQLite: datetime(data_hora, '+N minutes').
# Como todas as datas têm o formato "AAAA-MM-DD HH:MM:SS", comparar texto = comparar datas.
_SQL_CONFLITO = """
    SELECT 1 FROM consultas
    WHERE dentista_id = ?
      AND estado != 'Cancelada'
      AND data_hora < datetime(?, ?)
      AND datetime(data_hora, '+' || duracao_minutos || ' minutes') > ?
    LIMIT 1
"""


def _existe_conflito(cursor, dentista_id, data_hora, duracao_minutos):
    cursor.execute(
        _SQL_CONFLITO,
        (dentista_id, data_hora, f"+{int(duracao_minutos)} minutes", data_hora)
    )
    return cursor.fetchone() is not None


def inserir_consulta(data_hora, motivo, paciente_id, dentista_id, duracao_minutos=30):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        # BEGIN IMMEDIATE trava o banco para escrita já agora. Assim, ninguém consegue
        # inserir entre a nossa checagem de conflito e o nosso INSERT (atomicidade).
        cursor.execute("BEGIN IMMEDIATE")
        try:
            if _existe_conflito(cursor, dentista_id, data_hora, duracao_minutos):
                raise ConflitoDeHorarioError("Dentista já possui consulta marcada nesse horário.")
            cursor.execute(
                """
                INSERT INTO consultas (data_hora, motivo, paciente_id, dentista_id, duracao_minutos)
                VALUES (?, ?, ?, ?, ?)
                """,
                (data_hora, motivo, paciente_id, dentista_id, duracao_minutos)
            )
            conexao.commit()
            return cursor.lastrowid
        except BaseException:
            conexao.rollback()
            raise
    finally:
        conexao.close()


def buscar_consulta_por_id(consulta_id):
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"SELECT {_COLUNAS_CONSULTA} FROM consultas WHERE id = ?", (consulta_id,)
        )
        return cursor.fetchone()
    finally:
        conexao.close()


def buscar_consultas_por_data(data):
    """Consultas de um dia (data no formato AAAA-MM-DD), em ordem de horário."""
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"SELECT {_COLUNAS_CONSULTA} FROM consultas "
            "WHERE data_hora LIKE ? ORDER BY data_hora, id",
            (f"{data}%",)
        )
        return cursor.fetchall()
    finally:
        conexao.close()


def cancelar_consulta(consulta_id):
    """Cancela só se ainda estiver Agendada. Devolve True se alguma linha mudou."""
    conexao = criar_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE consultas SET estado = 'Cancelada' WHERE id = ? AND estado = 'Agendada'",
            (consulta_id,)
        )
        conexao.commit()
        return cursor.rowcount > 0
    finally:
        conexao.close()
