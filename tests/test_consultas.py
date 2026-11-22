from datetime import timedelta

import pytest


def agendar(cliente, paciente, dentista, inicio, duracao=None, motivo="Avaliação"):
    corpo = {"data_hora": inicio.isoformat(), "motivo": motivo,
             "paciente_cpf": paciente["cpf"], "dentista_cro": dentista["cro"]}
    if duracao is not None:
        corpo["duracao_minutos"] = duracao
    return cliente.post("/consultas", json=corpo)


def test_agendar_devolve_201_com_intervalo(cliente_logado, paciente, dentista, dia_futuro):
    resposta = agendar(cliente_logado, paciente, dentista, dia_futuro.replace(hour=14))
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["duracao_minutos"] == 30          # padrão
    assert corpo["data_hora_fim"].endswith("14:30:00")
    assert corpo["estado"] == "Agendada"
    assert corpo["paciente"] == "João Da Silva"


# Consulta base: 14:00 às 15:00. Cada caso tenta outra consulta com o MESMO dentista.
@pytest.mark.parametrize("hora, minuto, duracao, status_esperado", [
    (14, 30, 30, 409),   # começa no meio da base
    (13, 30, 60, 409),   # termina no meio da base (13:30-14:30)
    (14, 0, 30, 409),    # mesmo início
    (14, 15, 15, 409),   # totalmente dentro da base
    (13, 0, 180, 409),   # engloba a base inteira (13:00-16:00)
    (13, 30, 30, 201),   # termina exatamente às 14:00: colada, não conflita
    (15, 0, 30, 201),    # começa exatamente às 15:00: colada, não conflita
    (16, 0, 30, 201),    # bem depois
])
def test_conflito_de_horario_por_intervalo(cliente_logado, paciente, dentista, dia_futuro,
                                           hora, minuto, duracao, status_esperado):
    base = agendar(cliente_logado, paciente, dentista, dia_futuro.replace(hour=14), 60)
    assert base.status_code == 201

    tentativa = agendar(cliente_logado, paciente, dentista,
                        dia_futuro.replace(hour=hora, minute=minuto), duracao)
    assert tentativa.status_code == status_esperado, tentativa.json()


def test_outro_dentista_no_mesmo_horario_pode(cliente_logado, paciente, dentista, dia_futuro):
    outro = {"nome": "Outro", "cro": "CRO-2", "especialidade": "Clínico"}
    cliente_logado.post("/dentistas", json=outro)
    assert agendar(cliente_logado, paciente, dentista, dia_futuro.replace(hour=14), 60).status_code == 201
    assert agendar(cliente_logado, paciente, outro, dia_futuro.replace(hour=14), 60).status_code == 201


def test_cancelar_libera_o_horario_e_mantem_historico(cliente_logado, paciente, dentista, dia_futuro):
    inicio = dia_futuro.replace(hour=14)
    consulta_id = agendar(cliente_logado, paciente, dentista, inicio, 60).json()["id"]

    resposta = cliente_logado.patch(f"/consultas/{consulta_id}/cancelar")
    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "Cancelada"

    # mesmo horário de novo: a cancelada não bloqueia
    assert agendar(cliente_logado, paciente, dentista, inicio, 60).status_code == 201

    # a cancelada continua na lista do dia (histórico), junto com a nova
    estados = [c["estado"] for c in cliente_logado.get(
        "/consultas", params={"data": inicio.date().isoformat()}).json()]
    assert sorted(estados) == ["Agendada", "Cancelada"]


def test_cancelar_consulta_inexistente_devolve_404(cliente_logado):
    assert cliente_logado.patch("/consultas/9999/cancelar").status_code == 404


def test_data_no_passado_devolve_400(cliente_logado, paciente, dentista, dia_futuro):
    ontem = dia_futuro - timedelta(days=5)
    assert agendar(cliente_logado, paciente, dentista, ontem.replace(hour=14)).status_code == 400


def test_data_com_fuso_horario_nao_quebra(cliente_logado, paciente, dentista, dia_futuro):
    corpo = {"data_hora": dia_futuro.replace(hour=14).isoformat() + "-03:00", "motivo": "x",
             "paciente_cpf": paciente["cpf"], "dentista_cro": dentista["cro"]}
    assert cliente_logado.post("/consultas", json=corpo).status_code == 201


def test_paciente_inexistente_ao_agendar_devolve_404(cliente_logado, dentista, dia_futuro):
    fantasma = {"cpf": "00000000000"}
    assert agendar(cliente_logado, fantasma, dentista, dia_futuro.replace(hour=9)).status_code == 404


def test_dentista_inexistente_ao_agendar_devolve_404(cliente_logado, paciente, dia_futuro):
    fantasma = {"cro": "CRO-NAO-EXISTE"}
    assert agendar(cliente_logado, paciente, fantasma, dia_futuro.replace(hour=9)).status_code == 404


@pytest.mark.parametrize("duracao", [5, 9, 241, 600])
def test_duracao_fora_da_faixa_devolve_422(cliente_logado, paciente, dentista, dia_futuro, duracao):
    assert agendar(cliente_logado, paciente, dentista,
                   dia_futuro.replace(hour=9), duracao).status_code == 422


def test_listar_por_dia_traz_so_o_dia_em_ordem(cliente_logado, paciente, dentista, dia_futuro):
    agendar(cliente_logado, paciente, dentista, dia_futuro.replace(hour=16), motivo="tarde")
    agendar(cliente_logado, paciente, dentista, dia_futuro.replace(hour=9), motivo="manhã")
    agendar(cliente_logado, paciente, dentista,
            (dia_futuro + timedelta(days=1)).replace(hour=9), motivo="outro dia")

    resposta = cliente_logado.get("/consultas", params={"data": dia_futuro.date().isoformat()})
    assert resposta.status_code == 200
    assert [c["motivo"] for c in resposta.json()] == ["manhã", "tarde"]


def test_dia_sem_consultas_devolve_lista_vazia(cliente_logado, dia_futuro):
    resposta = cliente_logado.get("/consultas", params={"data": dia_futuro.date().isoformat()})
    assert resposta.json() == []
