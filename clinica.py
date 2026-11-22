"""Classes de domínio da clínica e as regras de negócio da agenda."""
import re
from datetime import datetime, timedelta
from enum import Enum

from banco import (
    buscar_consulta_por_id, buscar_consultas_por_data,
    cancelar_consulta, inserir_consulta,
)
from excecoes import ConsultaJaCanceladaError, ConsultaNaoEncontradaError

FORMATO_DATA_HORA = "%Y-%m-%d %H:%M:%S"   # como as datas são gravadas no banco


# ---------- Padronização de dados ----------
# Sem padronizar, "111.222.333-44", " 11122233344" e "11122233344" virariam três
# pacientes diferentes para o banco, embora sejam a mesma pessoa.

def normalizar_nome(nome):
    """Tira espaços sobrando e coloca iniciais maiúsculas: "  joão   silva " -> "João Silva"."""
    return " ".join(nome.split()).title()


def normalizar_cpf(cpf):
    """Mantém só os dígitos e exige 11. Levanta ValueError se não for um CPF."""
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) != 11:
        raise ValueError("O CPF deve ter 11 dígitos.")
    return digitos


def normalizar_cro(cro):
    """Tira espaços sobrando e deixa maiúsculo: " cro-df-123 " -> "CRO-DF-123"."""
    return " ".join(cro.split()).upper()


# ---------- Entidades ----------

class EstadoConsulta(Enum):
    AGENDADA = "Agendada"
    CANCELADA = "Cancelada"
    REALIZADA = "Realizada"


class Paciente:
    def __init__(self, nome, cpf, telefone, id=None):
        self._id = id
        self._nome = normalizar_nome(nome)
        self._cpf = cpf
        self._telefone = telefone

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


class Dentista:
    def __init__(self, nome, cro, especialidade, id=None):
        self._id = id
        self._nome = normalizar_nome(nome)
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


# ---------- Regras da agenda ----------

class Agenda:
    DURACAO_MIN = 10
    DURACAO_MAX = 240

    def agendar(self, data_hora, motivo, paciente, dentista, duracao_minutos=30):
        if not (self.DURACAO_MIN <= duracao_minutos <= self.DURACAO_MAX):
            raise ValueError(
                f"A duração deve estar entre {self.DURACAO_MIN} e {self.DURACAO_MAX} minutos."
            )

        # Data com fuso horário (ex.: "2027-01-10T14:00-03:00") vira horário local sem
        # fuso, que é como o banco guarda tudo. Sem isso, comparar com datetime.now()
        # (que não tem fuso) dava TypeError e a API respondia 500.
        if data_hora.tzinfo is not None:
            data_hora = data_hora.astimezone().replace(tzinfo=None)

        if data_hora < datetime.now():
            raise ValueError("Não é possível agendar em uma data/hora passada.")

        # A checagem de conflito acontece dentro de inserir_consulta, na mesma
        # transação do INSERT (levanta ConflitoDeHorarioError).
        consulta_id = inserir_consulta(
            data_hora.strftime(FORMATO_DATA_HORA),
            motivo,
            paciente.id,
            dentista.id,
            duracao_minutos
        )
        return Consulta(data_hora, motivo, paciente, dentista, id=consulta_id,
                        duracao_minutos=duracao_minutos)

    # Os imports de repositorio ficam dentro dos métodos porque repositorio.py
    # importa este arquivo; importar lá em cima criaria um import circular.

    def consultas_do_dia(self, data):
        from repositorio import consulta_para_objeto

        linhas = buscar_consultas_por_data(data.strftime("%Y-%m-%d"))
        return [consulta_para_objeto(linha) for linha in linhas]

    def buscar(self, consulta_id):
        from repositorio import consulta_para_objeto

        return consulta_para_objeto(buscar_consulta_por_id(consulta_id))

    def cancelar(self, consulta_id):
        """Cancela e devolve a consulta. A linha continua no banco (histórico)."""
        consulta = self.buscar(consulta_id)
        if consulta is None:
            raise ConsultaNaoEncontradaError("Consulta não encontrada.")
        # cancelar_consulta só altera se ainda estiver Agendada; se outra pessoa
        # cancelou no mesmo instante, ele devolve False e não cancelamos duas vezes.
        if consulta.estado != EstadoConsulta.AGENDADA or not cancelar_consulta(consulta_id):
            raise ConsultaJaCanceladaError("Esta consulta não está mais agendada.")
        return self.buscar(consulta_id)
