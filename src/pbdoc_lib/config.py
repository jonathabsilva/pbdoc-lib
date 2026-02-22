from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PBDocSelectors:
    """Seletores configuráveis para facilitar manutenção sem quebrar integrações."""

    username_input: str = "input[name='username'], input[name='login'], input[type='text']"
    password_input: str = "input[name='password'], input[type='password']"
    submit_button: str = "button[type='submit'], input[type='submit']"


@dataclass(slots=True)
class PBDocConfig:
    """Configuração do cliente Selenium para o PBDoc."""

    base_url: str = "https://pbdoc.pb.gov.br"
    login_path: str = "/siga/public/app/login"
    headless: bool = True
    timeout_seconds: int = 20
    selectors: PBDocSelectors = field(default_factory=PBDocSelectors)

    @property
    def login_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.login_path}"
