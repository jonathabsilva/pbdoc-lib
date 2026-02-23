from pbdoc_lib.client import PBDocClient


class FakeDriver:
    title = "Processo"
    current_url = "https://pbdoc.pb.gov.br/sigaex/app/expediente/doc/finalizar"

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


class FakeElement:
    def __init__(self, text=""):
        self.text = text
        self.clicked = False
        self.typed = ""

    def click(self):
        self.clicked = True

    def clear(self):
        self.typed = ""

    def send_keys(self, value):
        self.typed += value


def test_create_new_process_returns_generated_sigla(monkeypatch):
    client = PBDocClient(driver=FakeDriver())

    elements = {
        "a.btn.btn-success.form-control[href*='expediente/doc/editar']": FakeElement(),
        "button#dropdownMenuButton": FakeElement(),
        "li.dropdown-item[data-value='780']": FakeElement(),
        "#formulario_exDocumentoDTO\\.lotacaoDestinatarioSel_sigla": FakeElement(),
        "#formulario_exDocumentoDTO\\.classificacaoSel_sigla": FakeElement(),
        "textarea#descrDocumento": FakeElement(),
        "button#btnGravar": FakeElement(),
        "a#finalizar": FakeElement(),
        "h2.sigla-documento": FakeElement("TMP-10252506\n#10252506"),
    }

    def fake_wait_until(locator_tuple):
        selector = locator_tuple[1]
        return elements[selector]

    monkeypatch.setattr(
        "pbdoc_lib.client.WebDriverWait",
        lambda *_args, **_kwargs: type("W", (), {"until": lambda self, cond: fake_wait_until(cond.locator)})(),
    )
    monkeypatch.setattr("pbdoc_lib.client.EC.element_to_be_clickable", lambda locator: type("Cond", (), {"locator": locator})())
    monkeypatch.setattr("pbdoc_lib.client.EC.presence_of_element_located", lambda locator: type("Cond", (), {"locator": locator})())

    response = client.create_new_process("Conteúdo de teste")

    assert response.ok is True
    assert response.data["process_number"] == "TMP-10252506"
    assert elements["#formulario_exDocumentoDTO\\.lotacaoDestinatarioSel_sigla"].typed == "CBM-CCG"
    assert elements["#formulario_exDocumentoDTO\\.classificacaoSel_sigla"].typed == "04.01.04.07"
    assert elements["textarea#descrDocumento"].typed == "Conteúdo de teste"
