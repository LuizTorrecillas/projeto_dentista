from banco import inserir_paciente, inserir_dentista
from banco import inserir_consulta, buscar_consultas_por_data, cancelar_consulta

id_paciente = inserir_paciente("Maria Silva", "99988877766", "61988887777")
id_dentista = inserir_dentista("João Pereira", "CRO-DF-99999", "Ortodontia")

id_consulta = inserir_consulta("2026-11-20 14:30:00", "Limpeza", id_paciente, id_dentista)
print("Consulta inserida com id:", id_consulta)

# tentar marcar outra consulta no MESMO horário, com o MESMO dentista → deve dar erro
try:
    inserir_consulta("2026-11-20 14:30:00", "Canal", id_paciente, id_dentista)
except ValueError as erro:
    print("Erro esperado:", erro)

consultas = buscar_consultas_por_data("2026-11-20")
print("Consultas do dia:", consultas)