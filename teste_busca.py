"""Testes provisórios do item 2 (serão convertidos para pytest no item 4).
Usam um banco temporário: o clinica.db real NÃO é tocado."""
import os, sqlite3, tempfile

import banco
_caminho = os.path.join(tempfile.mkdtemp(), "teste.db")
_original = sqlite3.connect
banco.sqlite3 = type("S", (), {"connect": staticmethod(lambda _: _original(_caminho)),
                                "IntegrityError": sqlite3.IntegrityError})
banco.criar_tabelas()

from banco import inserir_paciente, inserir_dentista, normalizar_texto
from repositorio import obter_pacientes, obter_dentistas

assert normalizar_texto("JOÃO Ávila Çé") == "joao avila ce"

for nome, cpf in [("João Silva", "1"), ("Joana Souza", "2"), ("Ângela Lima", "3"),
                  ("Bruno 50% Off", "4"), ("Zélia Costa", "5")]:
    inserir_paciente(nome, cpf, "61")
inserir_dentista("Mário Gonçalves", "CRO-1", "Ortodontia")
inserir_dentista("Ana Paula", "CRO-2", "Endodontia")

def nomes(lista): return [p.nome for p in lista]

assert nomes(obter_pacientes("joao")) == ["João Silva"], "sem acento acha com acento"
assert nomes(obter_pacientes("JOÃO")) == ["João Silva"], "maiúsculas e acento"
assert nomes(obter_pacientes("jo")) == ["Joana Souza", "João Silva"], "trecho + ordem"
assert nomes(obter_pacientes("angela")) == ["Ângela Lima"]
assert nomes(obter_pacientes("  silva ")) == ["João Silva"], "espaços nas pontas"
assert nomes(obter_pacientes("xyz")) == []
assert nomes(obter_pacientes("%")) == ["Bruno 50% Off"], "% não é curinga"
assert nomes(obter_pacientes("_")) == [], "_ não é curinga"
# sem busca: todos, em ordem alfabética ignorando acentos (Â fica junto do A)
assert nomes(obter_pacientes()) == ["Ângela Lima", "Bruno 50% Off", "Joana Souza",
                                    "João Silva", "Zélia Costa"], nomes(obter_pacientes())
assert len(obter_pacientes(limite=2)) == 2, "limite"
assert [d.cro for d in obter_dentistas("goncalves")] == ["CRO-1"]
assert [d.nome for d in obter_dentistas()] == ["Ana Paula", "Mário Gonçalves"]
print("TODOS OS TESTES DE BUSCA PASSARAM")
