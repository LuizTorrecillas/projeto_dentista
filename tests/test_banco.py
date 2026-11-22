"""Testes direto nas camadas de banco e domínio (sem passar pela API)."""
import sqlite3
import threading
from datetime import datetime, timedelta

import pytest

from app.dominio.clinica import (
    Agenda, EstadoConsulta, normalizar_cpf, normalizar_cro, normalizar_nome,
)
from app.dominio.excecoes import (
    ConsultaJaCanceladaError, ConsultaNaoEncontradaError, RegistroDuplicadoError,
)
from app.persistencia import banco
from app.persistencia.repositorio import (
    criar_paciente, obter_dentista_por_cro, obter_paciente_por_cpf,
)


def test_normalizar_texto():
    assert banco.normalizar_texto("JOÃO Ávila Çé") == "joao avila ce"
    assert banco.normalizar_texto(None) == ""


def test_migracao_adiciona_duracao_em_banco_antigo(tmp_path, monkeypatch):
    caminho = tmp_path / "antigo.db"
    # Tabela de consultas como era antes do item 1 (sem duracao_minutos)
    conexao = sqlite3.connect(caminho)
    conexao.execute("""CREATE TABLE consultas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT NOT NULL, motivo TEXT,
        estado TEXT NOT NULL DEFAULT 'Agendada', paciente_id INTEGER NOT NULL,
        dentista_id INTEGER NOT NULL)""")
    conexao.execute("INSERT INTO consultas (data_hora, motivo, paciente_id, dentista_id) "
                    "VALUES ('2026-01-01 10:00:00', 'antiga', 1, 1)")
    conexao.commit()
    conexao.close()

    monkeypatch.setenv("CLINICA_DB", str(caminho))
    banco.criar_tabelas()
    banco.criar_tabelas()   # rodar de novo não pode dar erro

    conexao = sqlite3.connect(caminho)
    colunas = [linha[1] for linha in conexao.execute("PRAGMA table_info(consultas)")]
    assert colunas[-1] == "duracao_minutos"
    assert conexao.execute("SELECT duracao_minutos FROM consultas").fetchone() == (30,)
    conexao.close()


@pytest.fixture
def paciente_e_dentista():
    banco.inserir_paciente("Ana", "11122233344", "61")
    banco.inserir_dentista("Carlos", "C1", "Clínico")
    return obter_paciente_por_cpf("11122233344"), obter_dentista_por_cro("C1")


def test_agendamentos_simultaneos_so_um_vence(paciente_e_dentista):
    """Várias threads tentando o mesmo horário: o BEGIN IMMEDIATE garante só 1 sucesso."""
    paciente, dentista = paciente_e_dentista
    inicio = (datetime.now() + timedelta(days=2)).replace(hour=17, minute=0, second=0, microsecond=0)
    resultados = []

    def tentar():
        try:
            Agenda().agendar(inicio, "corrida", paciente, dentista, 30)
            resultados.append("ok")
        except banco.ConflitoDeHorarioError:
            resultados.append("conflito")

    threads = [threading.Thread(target=tentar) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert resultados.count("ok") == 1
    assert resultados.count("conflito") == 7


def test_conflito_e_um_value_error(paciente_e_dentista):
    """A API depende disso: ConflitoDeHorarioError é tratado antes do ValueError genérico."""
    assert issubclass(banco.ConflitoDeHorarioError, ValueError)


@pytest.mark.parametrize("duracao", [0, 9, 241])
def test_agenda_recusa_duracao_invalida(paciente_e_dentista, duracao):
    paciente, dentista = paciente_e_dentista
    with pytest.raises(ValueError):
        Agenda().agendar(datetime.now() + timedelta(days=1), "x", paciente, dentista, duracao)


def test_consulta_carregada_do_banco_tem_duracao_e_fim(paciente_e_dentista):
    paciente, dentista = paciente_e_dentista
    inicio = (datetime.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    Agenda().agendar(inicio, "x", paciente, dentista, 45)
    [consulta] = Agenda().consultas_do_dia(inicio.date())
    assert consulta.duracao_minutos == 45
    assert consulta.data_hora_fim == inicio + timedelta(minutes=45)


def test_normalizadores():
    assert normalizar_nome("  maria   das  dores ") == "Maria Das Dores"
    assert normalizar_cpf("111.222.333-44") == "11122233344"
    assert normalizar_cro(" cro-df  123 ") == "CRO-DF 123"
    with pytest.raises(ValueError):
        normalizar_cpf("123")


def test_repositorio_cria_paciente_padronizado_e_detecta_duplicado():
    paciente = criar_paciente("  ana   lima ", "11122233344", "61")
    assert paciente.id is not None
    assert paciente.nome == "Ana Lima"
    with pytest.raises(RegistroDuplicadoError):
        criar_paciente("Outra", "11122233344", "61")


def test_agenda_cancelar(paciente_e_dentista):
    paciente, dentista = paciente_e_dentista
    agenda = Agenda()
    inicio = (datetime.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    consulta = agenda.agendar(inicio, "x", paciente, dentista)

    cancelada = agenda.cancelar(consulta.id)
    assert cancelada.estado == EstadoConsulta.CANCELADA
    with pytest.raises(ConsultaJaCanceladaError):
        agenda.cancelar(consulta.id)
    with pytest.raises(ConsultaNaoEncontradaError):
        agenda.cancelar(9999)


def test_api_nao_acessa_o_banco_diretamente():
    """Arquitetura: o main.py só usa o banco para criar as tabelas na inicialização."""
    import ast
    from app import main
    arvore = ast.parse(open(main.__file__, encoding="utf-8").read())
    nomes_importados_do_banco = [
        alias.name
        for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and no.module == "app.persistencia.banco"
        for alias in no.names
    ]
    assert nomes_importados_do_banco == ["criar_tabelas"]
