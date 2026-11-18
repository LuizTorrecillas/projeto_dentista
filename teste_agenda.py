from datetime import datetime, timedelta
from clinica import Agenda
from repositorio import obter_paciente_por_cpf, obter_dentista_por_cro
from banco import inserir_paciente, inserir_dentista

# --- garantir que paciente e dentista existem (ou reaproveitar se já existirem) ---
try:
    id_paciente = inserir_paciente("Ana Souza", "11122233344", "61977776666")
except Exception:
    pass
paciente = obter_paciente_por_cpf("11122233344")

try:
    id_dentista = inserir_dentista("Carlos Lima", "CRO-DF-55555", "Clínico Geral")
except Exception:
    pass
dentista = obter_dentista_por_cro("CRO-DF-55555")

print("Paciente:", paciente.nome, "| id:", paciente.id)
print("Dentista:", dentista.nome, "| id:", dentista.id)

# --- testar Agenda ---
agenda = Agenda()

data_hora = datetime.now() + timedelta(days=1)  # amanhã, no mesmo horário atual

consulta = agenda.agendar(data_hora, "Avaliação inicial", paciente, dentista)
print("Consulta agendada, id:", consulta.id, "| estado:", consulta.estado)

# tentar agendar no MESMO horário, mesmo dentista → deve dar erro
try:
    agenda.agendar(data_hora, "Outra consulta", paciente, dentista)
except ValueError as erro:
    print("Erro esperado:", erro)

# listar consultas do dia
consultas_do_dia = agenda.consultas_do_dia(data_hora.date())
for c in consultas_do_dia:
    print("Consulta do dia:", c.id, c.data_hora, c.motivo, c.estado, "| paciente:", c.paciente.nome, "| dentista:", c.dentista.nome)

# cancelar
agenda.cancelar(consulta.id)
print("Consulta cancelada.")    