from backend import run


def test_desktop_server_uses_requested_port_without_reloader():
    assert hasattr(run, "build_uvicorn_options"), "桌面 Uvicorn 启动参数尚未抽离"

    options = run.build_uvicorn_options(
        desktop=True,
        frozen=False,
        port=43123,
    )

    assert options == {
        "host": "127.0.0.1",
        "port": 43123,
        "reload": False,
    }


def test_web_development_server_keeps_reload_enabled():
    assert run.build_uvicorn_options(
        desktop=False,
        frozen=False,
        port=8000,
    )["reload"] is True
