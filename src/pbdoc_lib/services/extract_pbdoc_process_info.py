import re

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _first(elements: list[WebElement]) -> WebElement | None:
    return elements[0] if elements else None


def extract_pbdoc_process_info(driver: WebDriver) -> dict:
    """
    Extrai informações do processo/documento na tela do PBdoc (/sigaex/app/expediente/doc/exibir?...)
    usando apenas Selenium.
    """
    out: dict = {
        "sigla": None,
        "id_interno": None,
        "situacao": None,
        "documento_interno": {},
        "movimentacoes": [],
        "vias": [],
    }

    h2 = _first(driver.find_elements(By.CSS_SELECTOR, "h2.sigla-documento"))
    if h2:
        text = _clean(h2.text)
        sigla_match = re.search(r"\b[A-Z]{2,}-[A-Z]{2,}-\d{4}/\d+\b", text)
        if sigla_match:
            out["sigla"] = sigla_match.group(0)

        a_id = _first(h2.find_elements(By.CSS_SELECTOR, "small a[href*='/sigaex/app/documento/']"))
        if a_id:
            out["id_interno"] = _clean(a_id.text).lstrip("#") or None

    if not out["sigla"]:
        m = re.search(r"\b[A-Z]{2,}-[A-Z]{2,}-\d{4}/\d+\b", _clean(driver.title))
        if m:
            out["sigla"] = m.group(0)

    body = _first(driver.find_elements(By.TAG_NAME, "body"))
    body_text = _clean(body.text) if body else ""
    m_sit = re.search(r"\b\d+ª Via\s*\(Arquivo\)\s*-\s*[A-Za-zÀ-ÿ ]{3,}", body_text)
    if m_sit:
        out["situacao"] = _clean(m_sit.group(0))

    doc_box = None
    for card in driver.find_elements(By.CSS_SELECTOR, ".card-sidebar.card"):
        header = _first(card.find_elements(By.CSS_SELECTOR, ".card-header"))
        if header and "Documento Interno Produzido" in _clean(header.text):
            doc_box = card
            break

    if doc_box:
        for p in doc_box.find_elements(By.CSS_SELECTOR, ".card-body p"):
            b = _first(p.find_elements(By.CSS_SELECTOR, "b"))
            if not b:
                continue
            label = _clean(b.text).rstrip(":").lower()
            full_text = _clean(p.text)
            value = _clean(full_text.replace(_clean(b.text), "", 1))
            if value:
                out["documento_interno"][label] = value

        normalized = {}
        mapping = {
            "suporte": "suporte",
            "data": "data",
            "de": "de",
            "para": "para",
            "cadastrante": "cadastrante",
            "espécie": "especie",
            "modelo": "modelo",
            "assunto": "assunto",
            "tipo documental": "tipo_documental",
        }
        for k, v in out["documento_interno"].items():
            if k in mapping:
                normalized[mapping[k]] = v
        out["documento_interno_normalizado"] = normalized

    mov_table = None
    for tbl in driver.find_elements(By.CSS_SELECTOR, "table.table.table-sm.table-responsive-sm.table-striped"):
        heads = [
            _clean(th.text).lower()
            for th in tbl.find_elements(By.CSS_SELECTOR, "thead th")
        ]
        if heads[:4] == ["tempo", "lotação", "evento", "assunto"]:
            mov_table = tbl
            break

    if mov_table:
        for tr in mov_table.find_elements(By.CSS_SELECTOR, "tbody tr"):
            tds = tr.find_elements(By.TAG_NAME, "td")
            if len(tds) < 4:
                continue

            tempo_td, lotacao_td, evento_td, assunto_td = tds[:4]
            item = {
                "classe": tr.get_attribute("class") or None,
                "tempo_relativo": _clean(tempo_td.text),
                "tempo_absoluto": tempo_td.get_attribute("title"),
                "lotacao_sigla": _clean(lotacao_td.text),
                "lotacao_nome": lotacao_td.get_attribute("title"),
                "evento": _clean(evento_td.text),
                "assunto": _clean(assunto_td.text),
                "documentos_juntados": [],
            }

            for a in assunto_td.find_elements(By.CSS_SELECTOR, "a[href*='/sigaex/app/expediente/doc/exibir']"):
                sigla_j = _clean(a.text)
                href = a.get_attribute("href")
                if sigla_j:
                    item["documentos_juntados"].append({"sigla": sigla_j, "href": href})

            m_desc = re.search(r"Descrição:\s*(.+)$", item["assunto"])
            item["descricao_juntada"] = _clean(m_desc.group(1)) if m_desc else None

            out["movimentacoes"].append(item)

    vias_box = None
    for card in driver.find_elements(By.CSS_SELECTOR, ".card-sidebar.card"):
        header = _first(card.find_elements(By.CSS_SELECTOR, ".card-header"))
        if header and _clean(header.text).startswith("Vias"):
            vias_box = card
            break

    if vias_box:
        for tr in vias_box.find_elements(By.CSS_SELECTOR, "table tr"):
            tds = tr.find_elements(By.TAG_NAME, "td")
            if len(tds) < 4:
                continue
            out["vias"].append(
                {
                    "via": _clean(tds[0].text),
                    "status": _clean(tds[1].text),
                    "responsavel": _clean(tds[2].text),
                    "lotacao": _clean(tds[3].text),
                }
            )

    return out
