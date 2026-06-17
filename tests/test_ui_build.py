import gradio as gr

import app


def test_build_ui_constructs_without_launch(monkeypatch):
    monkeypatch.setattr(gr.Blocks, "launch", lambda self, *args, **kwargs: None)
    app.build_ui()
