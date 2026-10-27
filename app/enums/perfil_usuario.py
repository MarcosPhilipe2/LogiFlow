from enum import Enum


class PerfilUsuario(str, Enum):
    ADMINISTRADOR = "Administrador"
    OPERACAO = "Operação"
    CONSULTA = "Consulta"
