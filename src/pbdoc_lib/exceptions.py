class PBDocAutomationError(Exception):
    """Erro base da biblioteca."""


class LoginError(PBDocAutomationError):
    """Falha ao autenticar no PBDoc."""
