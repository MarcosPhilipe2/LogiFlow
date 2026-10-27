class RegraNegocioError(Exception):
    """Operação que viola uma regra do domínio. A API responde com 409 Conflict."""
