"""Converte as tuplas do banco em objetos do domínio (e cria registros novos)."""
import sqlite3
from datetime import datetime

from app.persistencia.banco import (
    buscar_paciente_por_id, buscar_paciente_por_cpf,
    buscar_dentista_por_id, buscar_dentista_por_cro,
    inserir_paciente, inserir_dentista,
    listar_pacientes, listar_dentistas,
)
from app.dominio.clinica import FORMATO_DATA_HORA, Consulta, Dentista, EstadoConsulta, Paciente
from app.dominio.excecoes import RegistroDuplicadoError


# ---------- Tupla -> objeto ----------

def paciente_para_objeto(linha):
    if linha is None:
        return None
    paciente_id, nome, cpf, telefone = linha
    return Paciente(nome=nome, cpf=cpf, telefone=telefone, id=paciente_id)


def dentista_para_objeto(linha):
    if linha is None:
        return None
    dentista_id, nome, cro, especialidade = linha
    return Dentista(nome=nome, cro=cro, especialidade=especialidade, id=dentista_id)


def consulta_para_objeto(linha):
    if linha is None:
        return None
    consulta_id, data_hora_str, motivo, estado_str, paciente_id, dentista_id, duracao_minutos = linha
    return Consulta(
        data_hora=datetime.strptime(data_hora_str, FORMATO_DATA_HORA),
        motivo=motivo,
        paciente=obter_paciente_por_id(paciente_id),
        dentista=obter_dentista_por_id(dentista_id),
        id=consulta_id,
        estado=EstadoConsulta(estado_str),
        duracao_minutos=duracao_minutos
    )


# ---------- Pacientes ----------

def criar_paciente(nome, cpf, telefone):
    """Cadastra e devolve o Paciente como ficou salvo (com o nome já padronizado)."""
    novo = Paciente(nome=nome, cpf=cpf, telefone=telefone)
    try:
        paciente_id = inserir_paciente(novo.nome, novo.cpf, novo.telefone)
    except sqlite3.IntegrityError:
        raise RegistroDuplicadoError("Já existe um paciente com esse CPF.")
    return obter_paciente_por_id(paciente_id)


def obter_paciente_por_id(paciente_id):
    return paciente_para_objeto(buscar_paciente_por_id(paciente_id))


def obter_paciente_por_cpf(cpf):
    return paciente_para_objeto(buscar_paciente_por_cpf(cpf))


def obter_pacientes(busca="", limite=50):
    return [paciente_para_objeto(linha) for linha in listar_pacientes(busca, limite)]


# ---------- Dentistas ----------

def criar_dentista(nome, cro, especialidade):
    """Cadastra e devolve o Dentista como ficou salvo (com o nome já padronizado)."""
    novo = Dentista(nome=nome, cro=cro, especialidade=especialidade)
    try:
        dentista_id = inserir_dentista(novo.nome, novo.cro, novo.especialidade)
    except sqlite3.IntegrityError:
        raise RegistroDuplicadoError("Já existe um dentista com esse CRO.")
    return obter_dentista_por_id(dentista_id)


def obter_dentista_por_id(dentista_id):
    return dentista_para_objeto(buscar_dentista_por_id(dentista_id))


def obter_dentista_por_cro(cro):
    return dentista_para_objeto(buscar_dentista_por_cro(cro))


def obter_dentistas(busca="", limite=50):
    return [dentista_para_objeto(linha) for linha in listar_dentistas(busca, limite)]
