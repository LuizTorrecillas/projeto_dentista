from banco import (
    buscar_paciente_por_id, buscar_paciente_por_cpf,
    buscar_dentista_por_id, buscar_dentista_por_cro,
)
from clinica import Paciente, Dentista, Consulta, EstadoConsulta
from datetime import datetime


def paciente_para_objeto(linha):
    if linha is None:
        return None
    id, nome, cpf, telefone = linha
    return Paciente(nome=nome, cpf=cpf, telefone=telefone, id=id)


def dentista_para_objeto(linha):
    if linha is None:
        return None
    id, nome, cro, especialidade = linha
    return Dentista(nome=nome, cro=cro, especialidade=especialidade, id=id)


def consulta_para_objeto(linha):
    if linha is None:
        return None
    id, data_hora_str, motivo, estado_str, paciente_id, dentista_id, duracao_minutos = linha
    return Consulta(
        data_hora=datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M:%S"),
        motivo=motivo,
        paciente=obter_paciente_por_id(paciente_id),
        dentista=obter_dentista_por_id(dentista_id),
        id=id,
        estado=EstadoConsulta(estado_str),
        duracao_minutos=duracao_minutos
    )

def obter_paciente_por_id(paciente_id):
    linha = buscar_paciente_por_id(paciente_id)
    return paciente_para_objeto(linha)


def obter_paciente_por_cpf(cpf):
    linha = buscar_paciente_por_cpf(cpf)
    return paciente_para_objeto(linha)


def obter_dentista_por_id(dentista_id):
    linha = buscar_dentista_por_id(dentista_id)
    return dentista_para_objeto(linha)


def obter_dentista_por_cro(cro):
    linha = buscar_dentista_por_cro(cro)
    return dentista_para_objeto(linha)

