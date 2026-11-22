from enum import Enum
from datetime import datetime, timedelta
from banco import inserir_consulta, buscar_consultas_por_data, cancelar_consulta
from banco import buscar_paciente_por_id, buscar_dentista_por_id  


class EstadoConsulta(Enum):
    AGENDADA = "Agendada"
    CANCELADA = "Cancelada"
    REALIZADA = "Realizada"


class Paciente:
    def __init__(self, nome, cpf, telefone, id=None):
        self._id = id
        self._nome = nome.title()
        self._cpf = cpf
        self._telefone = telefone
        self._alergias = []

    @property
    def id(self):
        return self._id
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
    def __init__(self, nome, cro, especialidade, id=None):
        self._id = id
        self._nome = nome.title()
        self._cro = cro
        self._especialidade = especialidade

    @property
    def id(self):
        return self._id
    @property
    def nome(self):
        return self._nome
    @property
    def cro(self):
        return self._cro
    @property
    def especialidade(self):
        return self._especialidade

    def esta_disponivel(self, data_hora, agenda, duracao_minutos=30):
        fim = data_hora + timedelta(minutes=duracao_minutos)
        for consulta in agenda.consultas:
            if (
                consulta.dentista == self
                and consulta.estado != EstadoConsulta.CANCELADA
                and consulta.data_hora < fim
                and consulta.data_hora_fim > data_hora
            ):
                return False
        return True


class Consulta:
    def __init__(self, data_hora, motivo, paciente, dentista, id=None,
                 estado=EstadoConsulta.AGENDADA, duracao_minutos=30):
        self._id = id
        self._data_hora = data_hora
        self._motivo = motivo
        self._paciente = paciente
        self._dentista = dentista
        self._estado = estado
        self._duracao_minutos = duracao_minutos

    @property
    def id(self):
        return self._id
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
    @property
    def duracao_minutos(self):
        return self._duracao_minutos
    @property
    def data_hora_fim(self):
        return self._data_hora + timedelta(minutes=self._duracao_minutos)

    def cancelar(self):
        self._estado = EstadoConsulta.CANCELADA

    def realizar(self):
        self._estado = EstadoConsulta.REALIZADA



class Agenda:
    DURACAO_MIN = 10
    DURACAO_MAX = 240

    def agendar(self, data_hora, motivo, paciente, dentista, duracao_minutos=30):
        from banco import inserir_consulta

        if not (self.DURACAO_MIN <= duracao_minutos <= self.DURACAO_MAX):
            raise ValueError(
                f"A duração deve estar entre {self.DURACAO_MIN} e {self.DURACAO_MAX} minutos."
            )

        if data_hora < datetime.now():
            raise ValueError("Não é possível agendar em uma data/hora passada.")

        consulta_id = inserir_consulta(
            data_hora.strftime("%Y-%m-%d %H:%M:%S"),
            motivo,
            paciente.id,
            dentista.id,
            duracao_minutos
        )
        return Consulta(data_hora, motivo, paciente, dentista, id=consulta_id,
                        duracao_minutos=duracao_minutos)

    def consultas_do_dia(self, data):
        from banco import buscar_consultas_por_data
        from repositorio import consulta_para_objeto

        linhas = buscar_consultas_por_data(data.strftime("%Y-%m-%d"))
        return [consulta_para_objeto(linha) for linha in linhas]

    def cancelar(self, consulta_id):
        from banco import cancelar_consulta
        cancelar_consulta(consulta_id)