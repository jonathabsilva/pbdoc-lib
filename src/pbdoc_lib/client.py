from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import PBDocConfig
from .exceptions import LoginError
from .models import ApiLikeResponse

# ✅ NOVO: importa o extrator
from .services.extract_pbdoc_process_info import extract_pbdoc_process_info


class PBDocClient:
    """Cliente reutilizável para automação do PBDoc com interface semelhante a API."""

    def __init__(
        self,
        config: PBDocConfig | None = None,
        *,
        chrome_driver_path: str | None = None,
        driver: WebDriver | None = None,
    ) -> None:
        self.config = config or PBDocConfig()
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
        """
        Mantive como estava (ele ainda retorna html).
        Se você quiser também “higienizar” para não retornar html, eu ajusto.
        """
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

    def consult_process(self, process_number: str) -> ApiLikeResponse:
        """Consulta um processo no SIGA e retorna dados estruturados (sem salvar HTML)."""
        self.start()

        url = self.config.process_view_url(process_number)
        self.driver.get(url)

        # espera o body para garantir carregamento mínimo
        WebDriverWait(self.driver, self.config.timeout_seconds).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Extrai dados estruturados direto do DOM com Selenium
        parsed = extract_pbdoc_process_info(self.driver)

        # garante que a sigla consultada fique registrada
        parsed.setdefault("process_number", process_number)

        return ApiLikeResponse(
            ok=True,
            status_code=200,
            message="Consulta de processo realizada com sucesso.",
            data={
                "process_number": process_number,
                "url": url,
                "title": self.driver.title,
                "parsed": parsed,  # ✅ aqui vai o dicionário estruturado
            },
        )

    def create_new_process(self, description: str) -> ApiLikeResponse:
        """Cria e finaliza um novo processo administrativo genérico no PBDoc."""
        self.start()

        wait = WebDriverWait(self.driver, self.config.timeout_seconds)

        create_new_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-success.form-control[href*='expediente/doc/editar']"))
        )
        create_new_button.click()

        dropdown_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#dropdownMenuButton"))
        )
        dropdown_button.click()

        process_type_option = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li.dropdown-item[data-value='780']"))
        )
        process_type_option.click()

        lotacao_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, r"#formulario_exDocumentoDTO\.lotacaoDestinatarioSel_sigla"))
        )
        lotacao_input.clear()
        lotacao_input.send_keys("CBM-CCG")

        classificacao_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, r"#formulario_exDocumentoDTO\.classificacaoSel_sigla"))
        )
        classificacao_input.clear()
        classificacao_input.send_keys("04.01.04.07")

        description_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea#descrDocumento"))
        )
        description_input.clear()
        description_input.send_keys(description)

        save_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button#btnGravar")))
        save_button.click()

        finalize_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a#finalizar")))
        finalize_button.click()

        sigla_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h2.sigla-documento")))
        sigla_text = sigla_element.text.strip()
        process_number = re.search(r"\b[A-Z]+-\d+\b", sigla_text)

        return ApiLikeResponse(
            ok=True,
            status_code=200,
            message="Novo processo criado e finalizado com sucesso.",
            data={
                "process_number": process_number.group(0) if process_number else sigla_text,
                "url": self.driver.current_url,
                "title": self.driver.title,
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

    # ------------------------------------------------------------
    # Métodos antigos (mantidos por compatibilidade / uso futuro)
    # ------------------------------------------------------------
    def _extract_current_location(self) -> str | None:
        candidates = self.driver.find_elements(
            By.XPATH,
            "//*[contains(translate(normalize-space(.), 'LOCALIZAÇÃO', 'localização'), 'local') "
            "or contains(translate(normalize-space(.), 'ATUAL', 'atual'), 'local atual')]",
        )
        for item in candidates:
            text = item.text.strip()
            if text and len(text) > 3:
                return text
        return None

    def _extract_tramitations(self) -> list[dict[str, str]]:
        tramitacoes: list[dict[str, str]] = []
        tables = self.driver.find_elements(By.TAG_NAME, "table")

        for table in tables:
            headers = [
                h.text.strip()
                for h in table.find_elements(By.XPATH, ".//th")
                if h.text.strip()
            ]
            lower_headers = [h.lower() for h in headers]
            if not headers or not any("tramit" in h or "moviment" in h for h in lower_headers):
                continue

            for row in table.find_elements(By.XPATH, ".//tr[td]"):
                cells = [c.text.strip() for c in row.find_elements(By.XPATH, "./td")]
                if not any(cells):
                    continue
                if headers and len(headers) == len(cells):
                    tramitacoes.append(dict(zip(headers, cells, strict=False)))
                else:
                    tramitacoes.append({f"coluna_{i + 1}": v for i, v in enumerate(cells)})

        return tramitacoes

    def _extract_document_info(self) -> dict[str, str]:
        info: dict[str, str] = {}
        tables = self.driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            for row in table.find_elements(By.XPATH, ".//tr"):
                cells = row.find_elements(By.XPATH, "./th|./td")
                if len(cells) != 2:
                    continue
                key = cells[0].text.strip().rstrip(":")
                value = cells[1].text.strip()
                if key and value:
                    info[key] = value

        if info:
            return info

        labels = self.driver.find_elements(By.XPATH, "//label")
        for label in labels:
            key = label.text.strip().rstrip(":")
            if not key:
                continue
            value = self._read_nearby_value(label)
            if value:
                info[key] = value

        return info

    def _read_nearby_value(self, label: WebElement) -> str | None:
        neighbors = label.find_elements(
            By.XPATH,
            "./following-sibling::*[1] | ../following-sibling::*[1] | ../*[self::span or self::div]",
        )
        for node in neighbors:
            text = node.text.strip()
            if text:
                return text
        return None

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
