from selenium.webdriver.common.by import By

from pbdoc_lib.services.extract_pbdoc_process_info import extract_pbdoc_process_info


class FakeElement:
    def __init__(self, text=""):
        self.text = text

    def find_elements(self, *_args, **_kwargs):
        return []

    def get_attribute(self, *_args, **_kwargs):
        return None


class FakeDriver:
    title = "Processo"

    def find_elements(self, by, value):
        if by == By.XPATH and value == "//*[@id='page']/div[2]/div/h3":
            return [FakeElement("1ª Via (Arquivo) - Em andamento")]
        return []


def test_extracts_situacao_from_process_header_xpath():
    data = extract_pbdoc_process_info(FakeDriver())

    assert data["situacao"] == "1ª Via (Arquivo) - Em andamento"
