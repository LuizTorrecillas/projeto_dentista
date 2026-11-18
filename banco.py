import sqlite3

def criar_conexao():
    conexao = sqlite3.connect("clinica.db")
    conexao.execute("PRAGMA foreign_keys = ON")  # ativa integridade referencial
    return conexao

def criar_tabelas():
    conexao = criar_conexao()
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
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
            FOREIGN KEY (dentista_id) REFERENCES dentistas(id)
        )
    """)

    conexao.commit()
    conexao.close()



#PACIENTE

def inserir_paciente(nome, cpf, telefone):
    conexao = criar_conexao()
    cursor = conexao.cursor()

    cursor.execute(
        "INSERT INTO pacientes (nome, cpf, telefone) VALUES (?, ?, ?)",
        (nome, cpf, telefone)
    )
    conexao.commit()
    paciente_id = cursor.lastrowid  #cursor.lastrowid da o id que acabou de ser gerado numa tabela com AUTOINCREMENT
    conexao.close()
    return paciente_id


def buscar_paciente_por_cpf(cpf):
    conexao = criar_conexao()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT * FROM pacientes WHERE cpf = ?", (cpf,)
    )
    resultado = cursor.fetchone()
    conexao.close()
    return resultado    


#DENTISTA

def inserir_dentista(nome, cro, especialidade):
    conexao = criar_conexao()
    cursor = conexao.cursor()

    cursor.execute(
        "INSERT INTO dentistas (nome, cro, especialidade) VALUES (?,?,?)", (nome, cro, especialidade)
    )
    conexao.commit()
    dentista_id = cursor.lastrowid
    conexao.close()
    return dentista_id


def buscar_dentista_por_cro(cro):
    conexao = criar_conexao()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT * FROM dentistas WHERE cro = ?", (cro,)
    )
    resultado = cursor.fetchone()
    conexao.close()
    return resultado