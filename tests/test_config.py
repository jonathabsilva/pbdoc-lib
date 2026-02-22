from pbdoc_lib.config import PBDocConfig


def test_login_url():
    config = PBDocConfig(base_url="https://example.com", login_path="/login")
    assert config.login_url == "https://example.com/login"


def test_headless_default_true():
    assert PBDocConfig().headless is True


def test_headless_can_be_disabled_in_config():
    assert PBDocConfig(headless=False).headless is False
