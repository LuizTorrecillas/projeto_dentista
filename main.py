import sqlite3
from datetime import date, datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from banco import (
    criar_tabelas, inserir_paciente, inserir_dentista,
    buscar_consulta_por_id, ConflitoDeHorarioError,
)
from clinica import Agenda
from repositorio import (
    obter_paciente_por_cpf, obter_dentista_por_cro, consulta_para_objeto,
)

criar_tabelas()
app = FastAPI(title="Sistema de Agendamento - Clínica Odontológica")
agenda = Agenda()


# ---------- Schemas (formato dos dados que entram/saem) ----------

class PacienteIn(BaseModel):
    nome: str
    cpf: str
    telefone: str

class DentistaIn(BaseModel):
    nome: str
    cro: str
    especialidade: str

class ConsultaIn(BaseModel):
    data_hora: datetime
    motivo: str
    paciente_cpf: str
    dentista_cro: str
    duracao_minutos: int = Field(default=30, ge=10, le=240)


def consulta_para_dict(c):
    return {
        "id": c.id,
        "data_hora": c.data_hora,
        "data_hora_fim": c.data_hora_fim,
        "duracao_minutos": c.duracao_minutos,
        "motivo": c.motivo,
        "estado": c.estado.value,
        "paciente": c.paciente.nome,
        "dentista": c.dentista.nome,
    }


# ---------- Pacientes ----------

@app.post("/pacientes", status_code=201)
def criar_paciente(dados: PacienteIn):
    try:
        novo_id = inserir_paciente(dados.nome.title(), dados.cpf, dados.telefone)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Já existe um paciente com esse CPF.")
    return {"id": novo_id, **dados.model_dump()}

@app.get("/pacientes/{cpf}")
def obter_paciente(cpf: str):
    paciente = obter_paciente_por_cpf(cpf)
    if paciente is None:
        raise HTTPException(404, "Paciente não encontrado.")
    return {"id": paciente.id, "nome": paciente.nome,
            "cpf": paciente.cpf, "telefone": paciente.telefone}


# ---------- Dentistas ----------

@app.post("/dentistas", status_code=201)
def criar_dentista(dados: DentistaIn):
    try:
        novo_id = inserir_dentista(dados.nome.title(), dados.cro, dados.especialidade)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Já existe um dentista com esse CRO.")
    return {"id": novo_id, **dados.model_dump()}

@app.get("/dentistas/{cro}")
def obter_dentista(cro: str):
    dentista = obter_dentista_por_cro(cro)
    if dentista is None:
        raise HTTPException(404, "Dentista não encontrado.")
    return {"id": dentista.id, "nome": dentista.nome,
            "cro": dentista.cro, "especialidade": dentista.especialidade}


# ---------- Consultas ----------

@app.post("/consultas", status_code=201)
def agendar_consulta(dados: ConsultaIn):
    paciente = obter_paciente_por_cpf(dados.paciente_cpf)
    if paciente is None:
        raise HTTPException(404, "Paciente não encontrado.")
    dentista = obter_dentista_por_cro(dados.dentista_cro)
    if dentista is None:
        raise HTTPException(404, "Dentista não encontrado.")

    try:
        consulta = agenda.agendar(
            dados.data_hora, dados.motivo, paciente, dentista, dados.duracao_minutos
        )
    except ConflitoDeHorarioError as erro:
        raise HTTPException(409, str(erro))
    except ValueError as erro:          # data no passado
        raise HTTPException(400, str(erro))
    return consulta_para_dict(consulta)

@app.get("/consultas")
def listar_consultas(data: date):
    return [consulta_para_dict(c) for c in agenda.consultas_do_dia(data)]

@app.patch("/consultas/{consulta_id}/cancelar")
def cancelar_consulta(consulta_id: int):
    if buscar_consulta_por_id(consulta_id) is None:
        raise HTTPException(404, "Consulta não encontrada.")
    agenda.cancelar(consulta_id)
    return consulta_para_dict(consulta_para_objeto(buscar_consulta_por_id(consulta_id)))


from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="static", html=True), name="static")