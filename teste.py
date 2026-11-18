from banco import inserir_dentista, buscar_dentista_por_cro, criar_tabelas, inserir_paciente, buscar_paciente_por_cpf

criar_tabelas()

# --- paciente (já testado antes) ---
# id_paciente = inserir_paciente("Maria Silva", "12345678900", "61999999999")
# paciente = buscar_paciente_por_cpf("12345678900")
# print("Paciente encontrado:", paciente)

# --- dentista ---
id_dentista = inserir_dentista("João Pereira", "CRO-DF-12345", "Ortodontia")
print("Dentista inserido com id:", id_dentista)

dentista = buscar_dentista_por_cro("CRO-DF-12345")
print("Dentista encontrado:", dentista)