from __future__ import annotations

from dataclasses import asdict
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import PBDocConfig
from .exceptions import LoginError
from .models import ApiLikeResponse


class PBDocClient:
    """Cliente reutilizável para automação do PBDoc com interface semelhante a API."""

    def __init__(
        self,
        config: PBDocConfig | None = None,
        *,
        headless: bool | None = None,
        chrome_driver_path: str | None = None,
        driver: WebDriver | None = None,
    ) -> None:
        self.config = config or PBDocConfig()
        if headless is not None:
            self.config.headless = headless
        self._chrome_driver_path = chrome_driver_path
        self._driver = driver

    def __enter__(self) -> "PBDocClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            raise RuntimeError("WebDriver não iniciado. Use start() ou contexto with.")
        return self._driver

    def start(self) -> None:
        if self._driver is not None:
            return
        self._driver = self._build_driver()

    def close(self) -> None:
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    def set_headless(self, enabled: bool, *, restart_driver: bool = True) -> None:
        """Ativa/desativa headless dinamicamente.

        Se o driver já estiver iniciado e ``restart_driver=True``, reinicia o navegador
        para aplicar a nova configuração.
        """

        if self.config.headless == enabled:
            return

        self.config.headless = enabled
        if self._driver is not None and restart_driver:
            self.close()
            self.start()

    def login(self, username: str, password: str) -> ApiLikeResponse:
        self.start()
        self.driver.get(self.config.login_url)

        try:
            username_input = WebDriverWait(self.driver, self.config.timeout_seconds).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config.selectors.username_input))
            )
            password_input = self.driver.find_element(By.CSS_SELECTOR, self.config.selectors.password_input)
            submit_button = self.driver.find_element(By.CSS_SELECTOR, self.config.selectors.submit_button)

            username_input.clear()
            username_input.send_keys(username)
            password_input.clear()
            password_input.send_keys(password)
            submit_button.click()

            WebDriverWait(self.driver, self.config.timeout_seconds).until(
                lambda d: d.current_url != self.config.login_url
            )
        except TimeoutException as exc:
            raise LoginError("Timeout durante login no PBDoc.") from exc

        if self.config.login_path in self.driver.current_url:
            raise LoginError("Login falhou. Verifique credenciais ou mudanças no layout da página.")

        return ApiLikeResponse(
            ok=True,
            status_code=200,
            message="Login realizado com sucesso.",
            data={
                "current_url": self.driver.current_url,
                "cookies": self.driver.get_cookies(),
            },
        )

    def get_authenticated_page(self, path: str) -> ApiLikeResponse:
        self.start()
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        self.driver.get(url)
        return ApiLikeResponse(
            ok=True,
            status_code=200,
            message="Página carregada com sucesso.",
            data={
                "url": url,
                "title": self.driver.title,
                "html": self.driver.page_source,
            },
        )

    def run_step(self, name: str, func: Any, *args, **kwargs) -> ApiLikeResponse:
        """Executa etapa customizada de automação mantendo retorno padronizado."""
        self.start()
        result = func(self.driver, *args, **kwargs)
        return ApiLikeResponse(
            ok=True,
            status_code=200,
            message=f"Etapa '{name}' executada com sucesso.",
            data={"result": result},
        )

    def health(self) -> ApiLikeResponse:
        """Retorna estado do cliente para observabilidade em integrações externas."""
        return ApiLikeResponse(
            ok=True,
            status_code=200,
            message="Cliente pronto.",
            data={
                "started": self._driver is not None,
                "config": asdict(self.config),
            },
        )

    def _build_driver(self) -> WebDriver:
        options = ChromeOptions()
        if self.config.headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        if self._chrome_driver_path:
            service = ChromeService(executable_path=self._chrome_driver_path)
            return webdriver.Chrome(service=service, options=options)

        return webdriver.Chrome(options=options)
