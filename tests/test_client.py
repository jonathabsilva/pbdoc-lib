from pbdoc_lib.client import PBDocClient


class FakeDriver:
    title = "Processo"

    def __init__(self):
        self.url = None

    def get(self, url):
        self.url = url



def test_consult_process_returns_structured_data(monkeypatch):
    client = PBDocClient(driver=FakeDriver())

    monkeypatch.setattr(
        "pbdoc_lib.client.WebDriverWait",
        lambda *_args, **_kwargs: type("W", (), {"until": lambda self, cond: True})(),
    )
    monkeypatch.setattr(
        "pbdoc_lib.client.extract_pbdoc_process_info",
        lambda driver: {"sigla": "ABC123", "movimentacoes": []},
    )

    response = client.consult_process("ABC123")

    assert response.ok is True
    assert response.data["process_number"] == "ABC123"
    assert "sigla=ABC123" in response.data["url"]
    assert response.data["parsed"]["sigla"] == "ABC123"
