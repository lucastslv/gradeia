from matricula.ai.config import Settings


def test_defaults(monkeypatch) -> None:
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    assert settings.model == "deepseek-flash"
    assert settings.base_url == "https://api.deepseek.com"
    assert settings.configured is False


def test_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "chave")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    settings = Settings.from_env()

    assert settings.configured is True
    assert settings.model == "deepseek-v4-pro"
