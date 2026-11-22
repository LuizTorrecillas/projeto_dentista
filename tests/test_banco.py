"""Testes direto nas camadas de banco e domínio (sem passar pela API)."""
import sqlite3
import threading
from datetime import datetime, timedelta

import pytest

import banco
from clinica import Agenda
from repositorio import obter_dentista_por_cro, obter_paciente_por_cpf


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
    banco.inserir_paciente("Ana", "1", "61")
    banco.inserir_dentista("Carlos", "C1", "Clínico")
    return obter_paciente_por_cpf("1"), obter_dentista_por_cro("C1")


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
