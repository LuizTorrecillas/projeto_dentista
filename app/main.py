"""API do sistema (FastAPI). Para rodar, a partir da raiz do projeto:

    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.dominio.clinica import Agenda, normalizar_cpf, normalizar_cro
from app.dominio.excecoes import (
    ConflitoDeHorarioError, ConsultaJaCanceladaError,
    ConsultaNaoEncontradaError, RegistroDuplicadoError,
)
from app.persistencia.banco import criar_tabelas
from app.persistencia.repositorio import (
    criar_dentista, criar_paciente, obter_dentista_por_cro,
    obter_dentistas, obter_paciente_por_cpf, obter_pacientes,
)
from app.seguranca import autenticacao

config.carregar_env()
PASTA_STATIC = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def ciclo_de_vida(app):
    # Roda quando o servidor sobe (e não quando o arquivo é importado). Assim os
    # testes conseguem importar o main sem tocar no banco real.
    criar_tabelas()
    yield


app = FastAPI(title="Sistema de Agendamento - Clínica Odontológica", lifespan=ciclo_de_vida)
agenda = Agenda()

# Sessão por cookie assinado: o navegador guarda {"usuario_id": 1}, junto com uma
# assinatura feita com a chave secreta. Se alguém alterar o cookie, a assinatura
# deixa de bater e a sessão é descartada. O cookie sai sempre com HttpOnly (o
# JavaScript da página não consegue lê-lo) e SameSite=Lax (outros sites não
# conseguem fazer POST/PATCH aqui usando o seu login).
app.add_middleware(
    SessionMiddleware,
    secret_key=config.chave_secreta(),
    session_cookie="clinica_sessao",
    max_age=config.duracao_sessao_segundos(),
    same_site="lax",
    https_only=config.cookie_seguro(),   # flag Secure
)


# ---------- Login ----------

def usuario_logado(request: Request):
    """Dependência: devolve o usuário da sessão ou responde 401."""
    usuario = autenticacao.obter_usuario(request.session.get("usuario_id"))
    if usuario is None:
        raise HTTPException(401, "Faça login para continuar.")
    return usuario


# Todas as rotas registradas em `api` exigem login (a dependência roda antes de cada uma).
api = APIRouter(dependencies=[Depends(usuario_logado)])


# ---------- Schemas (formato dos dados que entram/saem) ----------
# A validação de formato fica aqui, na entrada da API: dados ruins são recusados
# com 422 antes de chegar às regras de negócio.

class Entrada(BaseModel):
    # tira espaços do começo e do fim de todos os textos recebidos
    model_config = ConfigDict(str_strip_whitespace=True)


class PacienteIn(Entrada):
    nome: str = Field(min_length=1, max_length=120)
    cpf: str = Field(description="Com ou sem pontuação; é salvo só com os 11 dígitos")
    telefone: str = Field(min_length=1, max_length=30)

    @field_validator("cpf")
    @classmethod
    def padronizar_cpf(cls, valor):
        return normalizar_cpf(valor)


class DentistaIn(Entrada):
    nome: str = Field(min_length=1, max_length=120)
    cro: str = Field(min_length=1, max_length=30)
    especialidade: str = Field(min_length=1, max_length=80)

    @field_validator("cro")
    @classmethod
    def padronizar_cro(cls, valor):
        return normalizar_cro(valor)


class LoginIn(Entrada):
    nome_usuario: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=1, max_length=200)

    # a senha NÃO pode perder espaços: eles fazem parte dela
    model_config = ConfigDict(str_strip_whitespace=False)


class ConsultaIn(Entrada):
    data_hora: datetime
    motivo: str = Field(min_length=1, max_length=200)
    paciente_cpf: str
    dentista_cro: str = Field(min_length=1, max_length=30)
    duracao_minutos: int = Field(default=30, ge=Agenda.DURACAO_MIN, le=Agenda.DURACAO_MAX)

    @field_validator("paciente_cpf")
    @classmethod
    def padronizar_cpf(cls, valor):
        return normalizar_cpf(valor)

    @field_validator("dentista_cro")
    @classmethod
    def padronizar_cro(cls, valor):
        return normalizar_cro(valor)


def paciente_para_dict(p):
    return {"id": p.id, "nome": p.nome, "cpf": p.cpf, "telefone": p.telefone}

def dentista_para_dict(d):
    return {"id": d.id, "nome": d.nome, "cro": d.cro, "especialidade": d.especialidade}


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


# ---------- Sessão ----------

@app.post("/login")
def login(dados: LoginIn, request: Request):
    ip = request.client.host if request.client else "desconhecido"
    try:
        usuario = autenticacao.fazer_login(dados.nome_usuario, dados.senha, ip)
    except autenticacao.MuitasTentativasError:
        raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos e tente de novo.")
    if usuario is None:
        raise HTTPException(401, "Usuário ou senha inválidos.")
    request.session.clear()   # descarta qualquer sessão anterior antes de começar a nova
    request.session["usuario_id"] = usuario["id"]
    return usuario

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}

@app.get("/me")
def quem_sou_eu(usuario=Depends(usuario_logado)):
    return usuario


# ---------- Pacientes ----------

@api.post("/pacientes", status_code=201)
def cadastrar_paciente(dados: PacienteIn):
    try:
        paciente = criar_paciente(dados.nome, dados.cpf, dados.telefone)
    except RegistroDuplicadoError as erro:
        raise HTTPException(409, str(erro))
    return paciente_para_dict(paciente)

@api.get("/pacientes")
def listar_pacientes(
    busca: str = Query("", max_length=100),
    limite: int = Query(50, ge=1, le=50),
):
    return [paciente_para_dict(p) for p in obter_pacientes(busca, limite)]

@api.get("/pacientes/{cpf}")
def obter_paciente(cpf: str):
    try:
        paciente = obter_paciente_por_cpf(normalizar_cpf(cpf))
    except ValueError:          # nem tem formato de CPF: certamente não existe
        paciente = None
    if paciente is None:
        raise HTTPException(404, "Paciente não encontrado.")
    return paciente_para_dict(paciente)


# ---------- Dentistas ----------

@api.post("/dentistas", status_code=201)
def cadastrar_dentista(dados: DentistaIn):
    try:
        dentista = criar_dentista(dados.nome, dados.cro, dados.especialidade)
    except RegistroDuplicadoError as erro:
        raise HTTPException(409, str(erro))
    return dentista_para_dict(dentista)

@api.get("/dentistas")
def listar_dentistas(
    busca: str = Query("", max_length=100),
    limite: int = Query(50, ge=1, le=50),
):
    return [dentista_para_dict(d) for d in obter_dentistas(busca, limite)]

@api.get("/dentistas/{cro}")
def obter_dentista(cro: str):
    dentista = obter_dentista_por_cro(normalizar_cro(cro))
    if dentista is None:
        raise HTTPException(404, "Dentista não encontrado.")
    return dentista_para_dict(dentista)


# ---------- Consultas ----------

@api.post("/consultas", status_code=201)
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
    except ConflitoDeHorarioError as erro:   # precisa vir antes: também é um ValueError
        raise HTTPException(409, str(erro))
    except ValueError as erro:               # data no passado ou duração inválida
        raise HTTPException(400, str(erro))
    return consulta_para_dict(consulta)

@api.get("/consultas")
def listar_consultas(data: date):
    return [consulta_para_dict(c) for c in agenda.consultas_do_dia(data)]

@api.patch("/consultas/{consulta_id}/cancelar")
def cancelar_consulta(consulta_id: int):
    try:
        consulta = agenda.cancelar(consulta_id)
    except ConsultaNaoEncontradaError as erro:
        raise HTTPException(404, str(erro))
    except ConsultaJaCanceladaError as erro:
        raise HTTPException(409, str(erro))
    return consulta_para_dict(consulta)


# include_router copia as rotas de `api` para o app; por isso vem depois delas.
app.include_router(api)


# ---------- Páginas ----------

@app.get("/", include_in_schema=False)
def pagina_inicial(request: Request):
    # Sem sessão, vai direto para o login (em vez de abrir a agenda vazia e depois redirecionar)
    if autenticacao.obter_usuario(request.session.get("usuario_id")) is None:
        return RedirectResponse("/login.html", status_code=303)
    return FileResponse(PASTA_STATIC / "index.html")

# Os arquivos da pasta static/ (login.html, app.js, style.css...) são públicos;
# os DADOS só saem pelas rotas da API, que exigem login.
app.mount("/", StaticFiles(directory=PASTA_STATIC, html=True), name="static")