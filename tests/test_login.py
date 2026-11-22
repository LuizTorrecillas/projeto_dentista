import sqlite3

import pytest

import autenticacao
import banco
from conftest import SENHA_TESTE


# ---------- Hash de senha ----------

def test_hash_usa_sal_e_nao_contem_a_senha():
    h1 = autenticacao.gerar_hash_senha("minha-senha-123")
    h2 = autenticacao.gerar_hash_senha("minha-senha-123")
    assert h1 != h2                       # sal diferente a cada vez
    assert "minha-senha-123" not in h1
    assert autenticacao.verificar_senha("minha-senha-123", h1)
    assert not autenticacao.verificar_senha("outra-senha", h1)


@pytest.mark.parametrize("hash_invalido", ["", "lixo", "md5$abc", "scrypt$1$2$3$zz$zz"])
def test_hash_malformado_e_recusado_sem_erro(hash_invalido):
    assert autenticacao.verificar_senha("qualquer", hash_invalido) is False


def test_nome_de_usuario_nao_diferencia_maiusculas(usuario):
    with pytest.raises(sqlite3.IntegrityError):
        banco.inserir_usuario("RECEPCAO", "x")


# ---------- Login pela API ----------

def test_login_correto(cliente, usuario):
    resposta = cliente.post("/login", json=usuario)
    assert resposta.status_code == 200
    assert resposta.json() == {"id": 1, "nome_usuario": "recepcao"}
    assert "senha_hash" not in resposta.text

    cookie = resposta.headers["set-cookie"].lower()
    assert "clinica_sessao=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie

    assert cliente.get("/me").json()["nome_usuario"] == "recepcao"


def test_login_aceita_maiusculas_no_usuario(cliente, usuario):
    assert cliente.post("/login", json={**usuario, "nome_usuario": "RECEPCAO"}).status_code == 200


@pytest.mark.parametrize("nome, senha", [
    ("recepcao", "senha-errada"),        # senha errada
    ("ninguem", SENHA_TESTE),            # usuário que não existe
])
def test_login_incorreto_tem_mensagem_generica(cliente, usuario, nome, senha):
    resposta = cliente.post("/login", json={"nome_usuario": nome, "senha": senha})
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Usuário ou senha inválidos."
    assert cliente.get("/me").status_code == 401


ROTAS_PROTEGIDAS = [
    ("GET", "/me"),
    ("GET", "/pacientes"),
    ("GET", "/pacientes/123"),
    ("POST", "/pacientes"),
    ("GET", "/dentistas"),
    ("GET", "/dentistas/CRO-1"),
    ("POST", "/dentistas"),
    ("GET", "/consultas?data=2030-01-01"),
    ("POST", "/consultas"),
    ("PATCH", "/consultas/1/cancelar"),
]


@pytest.mark.parametrize("metodo, rota", ROTAS_PROTEGIDAS)
def test_rotas_sem_sessao_devolvem_401(cliente, metodo, rota):
    assert cliente.request(metodo, rota, json={}).status_code == 401


def test_logout_encerra_a_sessao(cliente_logado):
    assert cliente_logado.get("/pacientes").status_code == 200
    assert cliente_logado.post("/logout").status_code == 200
    assert cliente_logado.get("/pacientes").status_code == 401


def test_cookie_adulterado_e_recusado(cliente, usuario):
    cliente.cookies.set("clinica_sessao", "eyJ1c3VhcmlvX2lkIjogMX0=.falso.assinatura")
    assert cliente.get("/me").status_code == 401


def test_bloqueio_apos_falhas_mesmo_com_senha_certa(cliente, usuario):
    for _ in range(5):
        assert cliente.post("/login", json={**usuario, "senha": "errada"}).status_code == 401
    resposta = cliente.post("/login", json=usuario)
    assert resposta.status_code == 429
    assert "Usuário ou senha" not in resposta.json()["detail"]


def test_pagina_inicial_redireciona_sem_sessao(cliente):
    resposta = cliente.get("/", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/login.html"


def test_pagina_inicial_abre_com_sessao(cliente_logado):
    resposta = cliente_logado.get("/", follow_redirects=False)
    assert resposta.status_code == 200
    assert "Agenda da Clínica" in resposta.text


@pytest.mark.parametrize("rota", ["/login.html", "/docs", "/style.css"])
def test_paginas_publicas(cliente, rota):
    assert cliente.get(rota).status_code == 200


# ---------- Limitador de tentativas (com relógio falso) ----------

def test_limitador_bloqueia_e_libera_depois_do_tempo():
    agora = [0.0]
    lim = autenticacao.LimitadorDeTentativas(max_falhas=3, janela=60, bloqueio=300,
                                             relogio=lambda: agora[0])
    lim.registrar_falha("u")
    lim.registrar_falha("u")
    assert not lim.esta_bloqueado("u")
    lim.registrar_falha("u")
    assert lim.esta_bloqueado("u")
    agora[0] = 299
    assert lim.esta_bloqueado("u")
    agora[0] = 301
    assert not lim.esta_bloqueado("u")


def test_limitador_esquece_falhas_fora_da_janela():
    agora = [0.0]
    lim = autenticacao.LimitadorDeTentativas(max_falhas=3, janela=60, bloqueio=300,
                                             relogio=lambda: agora[0])
    lim.registrar_falha("u")
    agora[0] = 100          # a primeira falha já saiu da janela de 60s
    lim.registrar_falha("u")
    lim.registrar_falha("u")
    assert not lim.esta_bloqueado("u")
