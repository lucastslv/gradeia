import os

from matricula.ai.config import Settings, load_environment


def test_defaults(monkeypatch) -> None:
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env(load_env_file=False)

    assert settings.model == "deepseek-flash"
    assert settings.base_url == "https://api.deepseek.com"
    assert settings.configured is False


def test_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "chave")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    settings = Settings.from_env(load_env_file=False)

    assert settings.configured is True
    assert settings.model == "deepseek-v4-pro"


def test_loads_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=do-arquivo\n")

    load_environment(env_file)

    assert os.environ.get("DEEPSEEK_API_KEY") == "do-arquivo"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
