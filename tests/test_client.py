from pbdoc_lib.client import PBDocClient


class FakeElement:
    def __init__(self, text: str = "", headers=None, rows=None, cells=None):
        self.text = text
        self._headers = headers or []
        self._rows = rows or []
        self._cells = cells or []

    def find_elements(self, by, value):  # noqa: ARG002
        if "./th|./td" in value:
            return [FakeElement(text=c) for c in self._cells]
        if "th" in value:
            return [FakeElement(text=h) for h in self._headers]
        if "tr[td]" in value:
            return self._rows
        if "./td" in value:
            return [FakeElement(text=c) for c in self._cells]
        if "tr" in value:
            return self._rows
        return []


class FakeDriver:
    title = "Processo"
    page_source = "<html></html>"

    def __init__(self):
        self.url = None

    def get(self, url):
        self.url = url

    def find_element(self, by, value):  # noqa: ARG002
        return FakeElement(text="texto completo")

    def find_elements(self, by, value):  # noqa: ARG002
        if "local" in value.lower():
            return [FakeElement(text="Local Atual: SEÇÃO DE PROTOCOLO")]
        if value == "table":
            tramitacoes = FakeElement(
                headers=["Data", "Tramitação", "Destino"],
                rows=[FakeElement(cells=["01/01/2026", "Recebido", "Gabinete"])],
            )
            doc = FakeElement(rows=[FakeElement(cells=["Tipo", "Processo administrativo"])])
            return [tramitacoes, doc]
        return []


def test_consult_process_returns_structured_data(monkeypatch):
    client = PBDocClient(driver=FakeDriver())

    monkeypatch.setattr("pbdoc_lib.client.WebDriverWait", lambda *_args, **_kwargs: type("W", (), {"until": lambda self, cond: True})())

    response = client.consult_process("ABC123")

    assert response.ok is True
    assert response.data["process_number"] == "ABC123"
    assert "sigla=ABC123" in response.data["url"]
    assert response.data["local_atual"] == "Local Atual: SEÇÃO DE PROTOCOLO"
    assert response.data["tramitacoes"][0]["Tramitação"] == "Recebido"
    assert response.data["documento_atual"]["Tipo"] == "Processo administrativo"
