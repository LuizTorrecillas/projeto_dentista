"""Configuração comum dos testes (o pytest carrega este arquivo sozinho).

Cada teste recebe um banco NOVO e vazio numa pasta temporária (tmp_path),
apontado pela variável CLINICA_DB. O clinica.db real nunca é usado.
"""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Isto roda ANTES de importar o main, porque ele lê essas variáveis ao ser importado.
# Atribuição direta (e não setdefault): vence o que estiver no seu .env.
os.environ["CLINICA_CHAVE_SECRETA"] = "chave-usada-somente-nos-testes-" + "x" * 32
os.environ["CLINICA_COOKIE_SECURE"] = "false"   # o TestClient usa http://
# Rede de segurança: mesmo um teste que esqueça a fixture cai num banco descartável.
os.environ["CLINICA_DB"] = str(Path(tempfile.mkdtemp()) / "nunca_usar.db")

from app.persistencia import banco  # noqa: E402
from app.seguranca import autenticacao  # noqa: E402

SENHA_TESTE = "senha-de-teste-123"


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    """Roda automaticamente em todo teste: banco novo + contadores de login zerados."""
    caminho = tmp_path / "teste.db"
    monkeypatch.setenv("CLINICA_DB", str(caminho))
    banco.criar_tabelas()
    monkeypatch.setattr(autenticacao, "limitador_por_usuario",
                        autenticacao.LimitadorDeTentativas(max_falhas=5))
    monkeypatch.setattr(autenticacao, "limitador_por_ip",
                        autenticacao.LimitadorDeTentativas(max_falhas=20))
    return caminho


@pytest.fixture
def usuario():
    banco.inserir_usuario("recepcao", autenticacao.gerar_hash_senha(SENHA_TESTE))
    return {"nome_usuario": "recepcao", "senha": SENHA_TESTE}


@pytest.fixture
def cliente():
    """Cliente HTTP de teste, SEM login. O `with` dispara o ciclo de vida do app."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def cliente_logado(cliente, usuario):
    resposta = cliente.post("/login", json=usuario)
    assert resposta.status_code == 200
    return cliente


@pytest.fixture
def paciente(cliente_logado):
    dados = {"nome": "joão da silva", "cpf": "11122233344", "telefone": "61999990000"}
    assert cliente_logado.post("/pacientes", json=dados).status_code == 201
    return dados


@pytest.fixture
def dentista(cliente_logado):
    dados = {"nome": "Carla Mendes", "cro": "CRO-DF-1234", "especialidade": "Ortodontia"}
    assert cliente_logado.post("/dentistas", json=dados).status_code == 201
    return dados


@pytest.fixture
def dia_futuro():
    """Uma data daqui a 3 dias, à meia-noite (para montar horários: dia_futuro.replace(hour=14))."""
    return (datetime.now() + timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
