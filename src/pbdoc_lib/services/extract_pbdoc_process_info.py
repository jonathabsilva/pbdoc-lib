import re

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _first(elements: list[WebElement]) -> WebElement | None:
    return elements[0] if elements else None


def _is_plausible_situacao(text: str) -> bool:
    """
    Decide se um texto parece ser uma "situação" do processo.

    Aceita, por exemplo:
      - "1º Volume - Caixa de Entrada (Digital) [CCG]"
      - "1º Volume - Aguardando Andamento (Digital) [CCG]"
      - "1ª Via (Arquivo) - Aguardando Andamento"
      - "2ª Via (Digital) - Em tramitação"
      - etc.

    Não depende de palavras fixas como "Caixa de Entrada".
    """
    t = _clean(text)
    if not t:
        return False

    # Padrão "Xª Via (...) - <texto>"
    if re.search(r"\b\d+ª\s+Via\b", t, re.IGNORECASE) and " - " in t:
        return True

    # Padrão "Xº Volume - <texto>"
    if re.search(r"\b\d+º\s+Volume\b", t, re.IGNORECASE) and " - " in t:
        return True

    # Fallback: se contém "Via" ou "Volume" e tem um separador " - "
    if (" - " in t) and re.search(r"\b(via|volume)\b", t, re.IGNORECASE):
        return True

    return False


def _pick_best_situacao_from_text(lines: list[str]) -> Optional[str]:
    """
    Dado um conjunto de linhas/textos, escolhe a melhor candidata a 'situação'
    priorizando:
      1) "<n>ª Via ..." (mais específico)
      2) "<n>º Volume ..."
      3) qualquer coisa que passe no _is_plausible_situacao
    """
    cleaned = [_clean(x) for x in lines if _clean(x)]

    # 1) Via
    for t in cleaned:
        if re.search(r"\b\d+ª\s+Via\b", t, re.IGNORECASE) and " - " in t:
            return t

    # 2) Volume
    for t in cleaned:
        if re.search(r"\b\d+º\s+Volume\b", t, re.IGNORECASE) and " - " in t:
            return t

    # 3) Plausível
    for t in cleaned:
        if _is_plausible_situacao(t):
            return t

    return None


def extract_pbdoc_process_info(driver: WebDriver) -> dict:
    """
    Extrai informações do processo/documento na tela do PBdoc (/sigaex/app/expediente/doc/exibir?...).

    ATUALIZAÇÃO (situação robusta):
    - 'situacao' agora é extraída tentando, nesta ordem:
      1) <h3> que pareça situação (Via/Volume + " - ")
      2) Se não achar, procura no body por uma linha que pareça situação
         (ex.: "1ª Via (Arquivo) - Aguardando Andamento")

    Assim, o texto da situação pode mudar livremente ("Caixa de Entrada", "Aguardando Andamento", etc.).
    """
    out: dict = {
        "sigla": None,
        "id_interno": None,
        "situacao": None,
        "documento_interno": {},
        "movimentacoes": [],
        "vias": [],
    }

    # ----------------------------
    # Sigla / ID interno
    # ----------------------------
    h2 = _first(driver.find_elements(By.CSS_SELECTOR, "h2.sigla-documento"))
    if h2:
        text = _clean(h2.text)

        # Aceita 1+ prefixos (ex.: CBM-PRC-2026/00122)
        sigla_match = re.search(r"\b[A-Z]{2,}(?:-[A-Z]{2,})*-\d{4}/\d+\b", text)
        if sigla_match:
            out["sigla"] = sigla_match.group(0)

        a_id = _first(h2.find_elements(By.CSS_SELECTOR, "small a[href*='/sigaex/app/documento/']"))
        if a_id:
            out["id_interno"] = _clean(a_id.text).lstrip("#") or None

    if not out["sigla"]:
        m = re.search(r"\b[A-Z]{2,}(?:-[A-Z]{2,})*-\d{4}/\d+\b", _clean(driver.title))
        if m:
            out["sigla"] = m.group(0)

    # ----------------------------
    # Situação (robusta, sem depender do texto fixo)
    # ----------------------------
    # 1) tenta h3
    h3_texts = [_clean(h3.text) for h3 in driver.find_elements(By.TAG_NAME, "h3")]
    h3_texts = [t for t in h3_texts if t]
    out["situacao"] = _pick_best_situacao_from_text(h3_texts)

    # 2) fallback: procura no body por linhas candidatas
    if not out["situacao"]:
        body = _first(driver.find_elements(By.TAG_NAME, "body"))
        body_text = body.text if body else ""
        # Divide em linhas para aumentar chance de achar a "frase" inteira
        lines = [x.strip() for x in (body_text or "").splitlines() if x.strip()]

        # Filtra linhas plausíveis
        candidates = [ln for ln in lines if _is_plausible_situacao(ln)]
        out["situacao"] = _pick_best_situacao_from_text(candidates)

    # 3) fallback extra: regex direto no texto completo (caso não tenha quebras de linha úteis)
    if not out["situacao"]:
        body = _first(driver.find_elements(By.TAG_NAME, "body"))
        body_text = _clean(body.text) if body else ""

        # Captura "Nª Via ( ... ) - <qualquer coisa até fim da sentença>"
        m_via = re.search(r"\b\d+ª\s+Via\b.*?-\s*[^\n\r]{3,}", body_text, re.IGNORECASE)
        if m_via:
            out["situacao"] = _clean(m_via.group(0))
        else:
            m_vol = re.search(r"\b\d+º\s+Volume\b.*?-\s*[^\n\r]{3,}", body_text, re.IGNORECASE)
            if m_vol:
                out["situacao"] = _clean(m_vol.group(0))

    # ----------------------------
    # Documento Interno Produzido
    # ----------------------------
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

    # ----------------------------
    # Movimentações
    # ----------------------------
    mov_table = None
    for tbl in driver.find_elements(By.CSS_SELECTOR, "table.table.table-sm.table-responsive-sm.table-striped"):
        heads = [_clean(th.text).lower() for th in tbl.find_elements(By.CSS_SELECTOR, "thead th")]
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

    # ----------------------------
    # Vias
    # ----------------------------
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
