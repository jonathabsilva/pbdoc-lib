import re
from bs4 import BeautifulSoup


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def extract_pbdoc_process_info(html: str) -> dict:
    """
    Extrai informações do processo/documento na tela do PBdoc (/sigaex/app/expediente/doc/exibir?...).

    Retorna um dict com:
      - sigla, id_interno (#...), situacao (ex: "1ª Via (Arquivo) - Aguardando Andamento")
      - detalhes do "Documento Interno Produzido"
      - movimentacoes (Tempo/Lotação/Evento/Assunto + docs juntados)
      - vias (tabela de Vias, quando existir)
    """
    soup = BeautifulSoup(html, "lxml")

    out: dict = {
        "sigla": None,
        "id_interno": None,
        "situacao": None,
        "documento_interno": {},
        "movimentacoes": [],
        "vias": [],
    }

    # -----------------------------
    # 1) Sigla + ID interno (#10158099)
    # -----------------------------
    h2 = soup.select_one("h2.sigla-documento")
    if h2:
        # Ex: "CBM-OFN-2026/02317" aparece como texto principal
        # e o "#10158099" em um <small> com link /sigaex/app/documento/10158099
        text = _clean(h2.get_text(" ", strip=True))
        # pega a primeira "cara" de sigla do documento (antes do #)
        # fallback: usa title da página se precisar
        sigla_match = re.search(r"\b[A-Z]{2,}-[A-Z]{2,}-\d{4}/\d+\b", text)
        if sigla_match:
            out["sigla"] = sigla_match.group(0)

        a_id = h2.select_one("small a[href*='/sigaex/app/documento/']")
        if a_id:
            # texto do link é "#10158099"
            out["id_interno"] = _clean(a_id.get_text()).lstrip("#") or None

    if not out["sigla"]:
        title = soup.title.get_text(strip=True) if soup.title else ""
        # Ex: "PBdoc - CBM-OFN-2026/02317"
        m = re.search(r"\b[A-Z]{2,}-[A-Z]{2,}-\d{4}/\d+\b", title)
        if m:
            out["sigla"] = m.group(0)

    # -----------------------------
    # 2) Situação (ex: "1ª Via (Arquivo) - Aguardando Andamento")
    # -----------------------------
    # No seu HTML aparece como texto em card "Situação do Documento"
    # e também no topo como "1ª Via (Arquivo) - Aguardando Andamento"
    # Vamos procurar esse padrão no texto visível do body.
    body_text = _clean(soup.get_text(" ", strip=True))
    m_sit = re.search(r"\b\d+ª Via\s*\(Arquivo\)\s*-\s*[A-Za-zÀ-ÿ ]{3,}", body_text)
    if m_sit:
        out["situacao"] = _clean(m_sit.group(0))

    # -----------------------------
    # 3) "Documento Interno Produzido" (campos rotulados por <b>XXX:</b>)
    # -----------------------------
    # A seção possui vários <p> com <b>Rótulo:</b> Valor
    # Ex: Suporte/Data/De/Para/Cadastrante/Espécie/Modelo/Assunto/Tipo Documental
    doc_box = None
    for card in soup.select(".card-sidebar.card"):
        header = card.select_one(".card-header")
        if header and "Documento Interno Produzido" in header.get_text(strip=True):
            doc_box = card
            break

    if doc_box:
        for p in doc_box.select(".card-body p"):
            b = p.select_one("b")
            if not b:
                continue
            label = _clean(b.get_text()).rstrip(":").lower()
            # remove o <b> do texto para pegar só o valor
            b.extract()
            value = _clean(p.get_text(" ", strip=True))
            if value:
                out["documento_interno"][label] = value

        # Normaliza alguns nomes de chave para ficar mais previsível
        # (mantém também as originais em "documento_interno")
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

    # -----------------------------
    # 4) Movimentações (tabela Tempo/Lotação/Evento/Assunto)
    # -----------------------------
    mov_table = None
    for tbl in soup.select("table.table.table-sm.table-responsive-sm.table-striped"):
        heads = [th.get_text(strip=True).lower() for th in tbl.select("thead th")]
        if heads[:4] == ["tempo", "lotação", "evento", "assunto"]:
            mov_table = tbl
            break

    if mov_table:
        for tr in mov_table.select("tbody tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            tempo_td, lotacao_td, evento_td, assunto_td = tds[:4]

            item = {
                "classe": " ".join(tr.get("class", [])) or None,  # ex: "anotacao", "juntada"
                "tempo_relativo": _clean(tempo_td.get_text()),
                "tempo_absoluto": tempo_td.get("title"),  # ex: "18/02/26 12:22:16"
                "lotacao_sigla": _clean(lotacao_td.get_text()),
                "lotacao_nome": lotacao_td.get("title"),
                "evento": _clean(evento_td.get_text()),
                "assunto": _clean(assunto_td.get_text(" ", strip=True)),
                "documentos_juntados": [],
            }

            # Se for juntada, costuma ter link(s) do documento juntado no assunto
            for a in assunto_td.select("a[href*='/sigaex/app/expediente/doc/exibir']"):
                sigla_j = _clean(a.get_text())
                href = a.get("href")
                if sigla_j:
                    item["documentos_juntados"].append(
                        {
                            "sigla": sigla_j,
                            "href": href,
                        }
                    )

            # Tenta capturar "Descrição: ...." se existir no texto do assunto
            m_desc = re.search(r"Descrição:\s*(.+)$", item["assunto"])
            if m_desc:
                item["descricao_juntada"] = _clean(m_desc.group(1))
            else:
                item["descricao_juntada"] = None

            out["movimentacoes"].append(item)

    # -----------------------------
    # 5) Vias (tabela "Vias" na sidebar)
    # -----------------------------
    vias_box = None
    for card in soup.select(".card-sidebar.card"):
        header = card.select_one(".card-header")
        if header and header.get_text(" ", strip=True).strip().startswith("Vias"):
            vias_box = card
            break

    if vias_box:
        for tr in vias_box.select("table tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            # Na prática, as colunas relevantes são:
            # [0]=identificador (A / Geral), [1]=status, [2]=pessoa, [3]=lotação
            via = {
                "via": _clean(tds[0].get_text(" ", strip=True)),
                "status": _clean(tds[1].get_text(" ", strip=True)),
                "responsavel": _clean(tds[2].get_text(" ", strip=True)),
                "lotacao": _clean(tds[3].get_text(" ", strip=True)),
            }
            out["vias"].append(via)

    return out