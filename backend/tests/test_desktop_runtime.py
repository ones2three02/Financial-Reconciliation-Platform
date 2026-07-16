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


def test_windows_desktop_data_dir_uses_appdata(tmp_path):
    assert run.desktop_data_dir(
        system="Windows",
        environment={"APPDATA": str(tmp_path)},
        home=tmp_path / "home",
    ) == tmp_path / "Financial-Reconciliation-Platform"


def test_desktop_logger_writes_rotating_log_without_secret(tmp_path):
    logger = run.configure_desktop_logging(tmp_path)
    logger.info("桌面后端启动 port=%s", 43123)
    for handler in logger.handlers:
        handler.flush()
    content = (tmp_path / "logs" / "desktop-backend.log").read_text(encoding="utf-8")
    assert "port=43123" in content
    assert "FRP_DESKTOP_TOKEN" not in content
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
