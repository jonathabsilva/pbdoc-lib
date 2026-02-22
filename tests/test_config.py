from pbdoc_lib.config import PBDocConfig


def test_login_url():
    config = PBDocConfig(base_url="https://example.com", login_path="/login")
    assert config.login_url == "https://example.com/login"
