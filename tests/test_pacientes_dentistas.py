import pytest


# ---------- Cadastro ----------

def test_criar_paciente_devolve_201_com_nome_padronizado(cliente_logado):
    resposta = cliente_logado.post(
        "/pacientes", json={"nome": "  joão   da silva ", "cpf": "111.222.333-44", "telefone": "61"})
    assert resposta.status_code == 201
    # A resposta mostra o que foi SALVO: nome padronizado e CPF só com dígitos
    assert resposta.json()["nome"] == "João Da Silva"
    assert resposta.json()["cpf"] == "11122233344"
    assert cliente_logado.get("/pacientes/11122233344").json()["nome"] == "João Da Silva"


def test_paciente_com_cpf_duplicado_devolve_409(cliente_logado, paciente):
    resposta = cliente_logado.post("/pacientes", json={**paciente, "nome": "Outra Pessoa"})
    assert resposta.status_code == 409


def test_buscar_paciente_por_cpf(cliente_logado, paciente):
    resposta = cliente_logado.get(f"/pacientes/{paciente['cpf']}")
    assert resposta.status_code == 200
    assert resposta.json()["cpf"] == paciente["cpf"]


def test_paciente_inexistente_devolve_404(cliente_logado):
    assert cliente_logado.get("/pacientes/00000000000").status_code == 404


def test_criar_dentista_devolve_201(cliente_logado):
    resposta = cliente_logado.post(
        "/dentistas", json={"nome": "ana lima", "cro": "CRO-1", "especialidade": "Endodontia"})
    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Ana Lima"


def test_dentista_com_cro_duplicado_devolve_409(cliente_logado, dentista):
    assert cliente_logado.post("/dentistas", json=dentista).status_code == 409


def test_dentista_inexistente_devolve_404(cliente_logado):
    assert cliente_logado.get("/dentistas/CRO-NAO-EXISTE").status_code == 404


def test_campo_obrigatorio_faltando_devolve_422(cliente_logado):
    assert cliente_logado.post("/pacientes", json={"nome": "Sem CPF"}).status_code == 422


# ---------- Busca por nome ----------

@pytest.fixture
def varios_pacientes(cliente_logado):
    for i, nome in enumerate(["João Silva", "Joana Souza", "Ângela Lima",
                              "Bruno 50% Off", "Zélia Costa"]):
        cpf = f"{i:011d}"
        resposta = cliente_logado.post("/pacientes", json={"nome": nome, "cpf": cpf, "telefone": "61"})
        assert resposta.status_code == 201


def nomes(resposta):
    assert resposta.status_code == 200
    return [p["nome"] for p in resposta.json()]


@pytest.mark.parametrize("busca", ["joao", "JOÃO", "João", "  joão  ", "silva"])
def test_busca_ignora_acentos_maiusculas_e_espacos(cliente_logado, varios_pacientes, busca):
    assert nomes(cliente_logado.get("/pacientes", params={"busca": busca})) == ["João Silva"]


def test_busca_sem_acento_acha_nome_com_acento_no_inicio(cliente_logado, varios_pacientes):
    assert nomes(cliente_logado.get("/pacientes", params={"busca": "angela"})) == ["Ângela Lima"]


def test_busca_por_trecho_vem_em_ordem_alfabetica(cliente_logado, varios_pacientes):
    assert nomes(cliente_logado.get("/pacientes", params={"busca": "jo"})) == [
        "Joana Souza", "João Silva"]


def test_sem_busca_lista_todos_em_ordem_ignorando_acentos(cliente_logado, varios_pacientes):
    assert nomes(cliente_logado.get("/pacientes")) == [
        "Ângela Lima", "Bruno 50% Off", "Joana Souza", "João Silva", "Zélia Costa"]


def test_busca_sem_resultado_devolve_lista_vazia(cliente_logado, varios_pacientes):
    assert nomes(cliente_logado.get("/pacientes", params={"busca": "xyz"})) == []


def test_porcentagem_e_sublinhado_nao_sao_curingas(cliente_logado, varios_pacientes):
    assert nomes(cliente_logado.get("/pacientes", params={"busca": "%"})) == ["Bruno 50% Off"]
    assert nomes(cliente_logado.get("/pacientes", params={"busca": "_"})) == []


def test_limite_de_resultados(cliente_logado, varios_pacientes):
    assert len(nomes(cliente_logado.get("/pacientes", params={"limite": 2}))) == 2


@pytest.mark.parametrize("limite", [0, 51])
def test_limite_fora_da_faixa_devolve_422(cliente_logado, limite):
    assert cliente_logado.get("/pacientes", params={"limite": limite}).status_code == 422


def test_busca_de_dentista_sem_acento(cliente_logado):
    cliente_logado.post("/dentistas", json={"nome": "Mário Gonçalves", "cro": "C1",
                                            "especialidade": "Ortodontia"})
    resposta = cliente_logado.get("/dentistas", params={"busca": "goncalves"})
    assert [d["cro"] for d in resposta.json()] == ["C1"]


def test_cadastro_novo_aparece_na_busca(cliente_logado, varios_pacientes):
    cliente_logado.post("/pacientes", json={"nome": "Érica Nova", "cpf": "99999999999", "telefone": "61"})
    assert nomes(cliente_logado.get("/pacientes", params={"busca": "erica"})) == ["Érica Nova"]


# ---------- Padronização de CPF e CRO ----------

@pytest.mark.parametrize("cpf_repetido", ["111.222.333-44", " 11122233344 ", "111 222 333 44"])
def test_mesmo_cpf_escrito_de_outro_jeito_e_duplicado(cliente_logado, paciente, cpf_repetido):
    resposta = cliente_logado.post("/pacientes", json={**paciente, "cpf": cpf_repetido})
    assert resposta.status_code == 409


@pytest.mark.parametrize("cpf_invalido", ["", "123", "1112223334", "111222333445", "abc"])
def test_cpf_sem_11_digitos_devolve_422_com_mensagem(cliente_logado, cpf_invalido):
    resposta = cliente_logado.post("/pacientes",
                                   json={"nome": "X", "cpf": cpf_invalido, "telefone": "61"})
    assert resposta.status_code == 422
    assert "11 dígitos" in resposta.json()["detail"][0]["msg"]


def test_buscar_por_cpf_com_pontuacao(cliente_logado, paciente):
    assert cliente_logado.get("/pacientes/111.222.333-44").status_code == 200


def test_cro_em_minusculas_e_o_mesmo_dentista(cliente_logado, dentista):
    repetido = {**dentista, "cro": "  cro-df-1234 "}
    assert cliente_logado.post("/dentistas", json=repetido).status_code == 409
    assert cliente_logado.get("/dentistas/cro-df-1234").json()["cro"] == "CRO-DF-1234"


@pytest.mark.parametrize("campo", ["nome", "telefone"])
def test_campo_so_com_espacos_devolve_422(cliente_logado, paciente, campo):
    dados = {"nome": "Ana", "cpf": "55566677788", "telefone": "61", campo: "   "}
    assert cliente_logado.post("/pacientes", json=dados).status_code == 422
