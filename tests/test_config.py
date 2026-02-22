from pbdoc_lib.config import PBDocConfig


def test_login_url():
    config = PBDocConfig(base_url="https://pbdoc.pb.gov.br", login_path="/login")
    assert config.login_url == "https://pbdoc.pb.gov.br/login"


def test_process_view_url():
    config = PBDocConfig(base_url="https://pbdoc.pb.gov.br")
    assert (
        config.process_view_url("123.456")
        == "https://pbdoc.pb.gov.br/sigaex/app/expediente/doc/exibir?sigla=123.456"
    )
