"""Testes provisórios do item 1 (serão convertidos para pytest no item 4).
Usam um banco temporário: o clinica.db real NÃO é tocado."""
import os, sqlite3, tempfile, threading
from datetime import datetime, timedelta

import banco
_dir = tempfile.mkdtemp()
_caminho = os.path.join(_dir, "teste.db")
banco.criar_conexao.__globals__["sqlite3"] = sqlite3
_original = sqlite3.connect
banco.sqlite3 = type("S", (), {"connect": staticmethod(lambda _: _original(_caminho, timeout=10)),
                                "IntegrityError": sqlite3.IntegrityError})
banco.criar_tabelas()

from clinica import Agenda
from banco import ConflitoDeHorarioError, inserir_paciente, inserir_dentista
from repositorio import obter_paciente_por_cpf, obter_dentista_por_cro

inserir_paciente("Ana", "1", "1"); inserir_dentista("Carlos", "C1", "x")
pac, den = obter_paciente_por_cpf("1"), obter_dentista_por_cro("C1")
ag = Agenda()
base = (datetime.now() + timedelta(days=2)).replace(hour=14, minute=0, second=0, microsecond=0)
def t(h, m): return base.replace(hour=h, minute=m)

base_c = ag.agendar(t(14, 0), "base", pac, den, 60)
def conflita(inicio, dur):
    try: ag.agendar(inicio, "x", pac, den, dur); return False
    except ConflitoDeHorarioError: return True

assert conflita(t(14, 30), 30), "14:30/30 deveria conflitar"
assert conflita(t(13, 30), 60), "13:30/60 deveria conflitar"
assert conflita(t(14, 0), 30), "mesmo horário deveria conflitar"
assert not conflita(t(13, 30), 30), "13:30/30 deveria passar"
assert not conflita(t(15, 0), 30), "15:00/30 (colada) deveria passar"
ag.cancelar(base_c.id)
assert not conflita(t(14, 15), 30), "cancelada não deve bloquear"
assert {c.id: c.duracao_minutos for c in ag.consultas_do_dia(base.date())}[base_c.id] == 60
try: ag.agendar(t(18, 0), "x", pac, den, 5); raise SystemExit("duração 5 deveria falhar")
except ValueError: pass

# concorrência: 8 threads tentando o mesmo intervalo -> só 1 pode vencer
res = []
def tenta():
    try: ag.agendar(t(17, 0), "c", pac, den, 30); res.append("ok")
    except ConflitoDeHorarioError: res.append("conflito")
ths = [threading.Thread(target=tenta) for _ in range(8)]
[x.start() for x in ths]; [x.join() for x in ths]
assert res.count("ok") == 1, res
print("TODOS OS TESTES PASSARAM", res.count("conflito"), "conflitos na corrida")
