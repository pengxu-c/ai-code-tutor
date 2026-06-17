import importlib

import config


def test_gradio_share_defaults_false(monkeypatch):
    monkeypatch.delenv("GRADIO_SHARE", raising=False)
    reloaded = importlib.reload(config)
    assert reloaded.GRADIO_SHARE is False


def test_gradio_share_truthy_values(monkeypatch):
    for value in ["true", "1", "yes", "on"]:
        monkeypatch.setenv("GRADIO_SHARE", value)
        reloaded = importlib.reload(config)
        assert reloaded.GRADIO_SHARE is True
