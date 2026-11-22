"""Erros de regra de negócio do sistema.

Ficam num módulo próprio porque são usados por várias camadas: o banco levanta
(ConflitoDeHorarioError), o domínio e o repositório também, e a API converte
cada um no código HTTP certo. Nenhum deles depende de FastAPI nem de SQLite.
"""


class ConflitoDeHorarioError(ValueError):
    """O dentista já tem consulta (não cancelada) que se sobrepõe ao intervalo pedido."""


class RegistroDuplicadoError(Exception):
    """Já existe paciente com esse CPF ou dentista com esse CRO."""


class ConsultaNaoEncontradaError(LookupError):
    pass


class ConsultaJaCanceladaError(Exception):
    pass
