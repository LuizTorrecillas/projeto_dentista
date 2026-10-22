from enum import Enum
from datetime import datetime


class EstadoConsulta(Enum):
    AGENDADA = "Agendada"
    CANCELADA = "Cancelada"
    REALIZADA = "Realizada"


class Paciente:
    def __init__(self, nome, cpf, telefone):
        self._nome = nome.title()
        self._cpf = cpf
        self._telefone = telefone
        self._alergias = []

    @property
    def nome(self):
        return self._nome
    @property
    def cpf(self):
        return self._cpf
    @property
    def telefone(self):
        return self._telefone
    @property
    def alergias(self):
        return self._alergias

    def adicionar_alergia(self, alergia):
        self._alergias.append(alergia)

    def historico_consultas(self, agenda):
        return [c for c in agenda.consultas if c.paciente == self]


class Dentista:
    def __init__(self, nome, cro, especialidade):
        self._nome = nome.title()
        self._cro = cro
        self._especialidade = especialidade

    @property
    def nome(self):
        return self._nome
    @property
    def cro(self):
        return self._cro
    @property
    def especialidade(self):
        return self._especialidade

    def esta_disponivel(self, data_hora, agenda):
        for consulta in agenda.consultas:
            if (
                consulta.dentista == self
                and consulta.data_hora == data_hora
                and consulta.estado != EstadoConsulta.CANCELADA
            ):
                return False
        return True


class Consulta:
    def __init__(self, data_hora: datetime, motivo, paciente: Paciente, dentista: Dentista):
        self._data_hora = data_hora
        self._motivo = motivo
        self._paciente = paciente
        self._dentista = dentista
        self._estado = EstadoConsulta.AGENDADA

    @property
    def data_hora(self):
        return self._data_hora
    @property
    def motivo(self):
        return self._motivo
    @property
    def paciente(self):
        return self._paciente
    @property
    def dentista(self):
        return self._dentista
    @property
    def estado(self):
        return self._estado

    def cancelar(self):
        self._estado = EstadoConsulta.CANCELADA

    def realizar(self):
        self._estado = EstadoConsulta.REALIZADA


class Agenda:
    def __init__(self):
        self._consultas = []

    @property
    def consultas(self):
        return self._consultas

    def agendar(self, data_hora, motivo, paciente, dentista):
        if not dentista.esta_disponivel(data_hora, self):
            raise ValueError(f"Dentista {dentista.nome} já tem consulta nesse horário.")
        if data_hora < datetime.now():
            raise ValueError("Não é possível agendar em uma data/hora passada.")

        consulta = Consulta(data_hora, motivo, paciente, dentista)
        self._consultas.append(consulta)
        return consulta

    def consultas_do_dia(self, data):
        return [c for c in self._consultas if c.data_hora.date() == data]