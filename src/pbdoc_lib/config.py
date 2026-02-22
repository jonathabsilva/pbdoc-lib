from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlencode


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
    process_view_path: str = "/sigaex/app/expediente/doc/exibir"
    headless: bool = True
    timeout_seconds: int = 20
    selectors: PBDocSelectors = field(default_factory=PBDocSelectors)

    @property
    def login_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.login_path}"

    def process_view_url(self, process_number: str) -> str:
        params = urlencode({"sigla": process_number})
        return f"{self.base_url.rstrip('/')}{self.process_view_path}?{params}"
