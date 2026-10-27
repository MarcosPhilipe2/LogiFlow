from typing import Annotated

from pydantic import StringConstraints

# Números de pedido/carga: sem espaços nas pontas e sempre em maiúsculas.
Codigo = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=50)]

# O pattern é avaliado antes do to_upper, por isso aceita minúsculas.
UF = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{2}$")]


def rejeitar_nulo(valor):
    """Em atualizações parciais, omitir um campo mantém o valor atual; null só vale para campos opcionais."""
    if valor is None:
        raise ValueError("Este campo não pode ser nulo.")
    return valor
