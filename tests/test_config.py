"""Testes de pacote e configuração do RSL.app."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, fields
from importlib.metadata import entry_points, version
from pathlib import Path

import pytest

from rslapp import config

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "RSL_CONTACT_EMAIL",
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Limpa as seis variáveis de ambiente e isola a pasta home do usuário."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    fake_home = tmp_path / "fake_home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home


# D-001, D-008: Metadados do pacote Python e ponto de entrada rslapp para uvx
def test_d001_d008_pacote_e_entrypoint_instalados() -> None:
    import rslapp

    assert version("rslapp") == rslapp.__version__
    scripts = entry_points(group="console_scripts")
    rslapp_eps = [ep for ep in scripts if ep.name == "rslapp"]
    assert len(rslapp_eps) == 1
    assert rslapp_eps[0].value == "rslapp.server:main"


# FR-07, NFR-02: Sem variáveis de ambiente, usa padrões locais na pasta do usuário sem criar pastas
def test_fr07_nfr02_padroes_sem_variaveis_e_sem_criar_pastas(isolated_env: Path) -> None:
    cfg = config.load()

    assert cfg.data_dir == isolated_env / "RSL.app"
    assert cfg.export_dir == isolated_env / "RSL.app" / "exports"
    assert cfg.cache_days == 7
    assert cfg.contact_email is None
    assert cfg.openalex_key_configured is False
    assert cfg.semantic_scholar_key_configured is False
    assert not cfg.data_dir.exists()
    assert not cfg.export_dir.exists()


# FR-07, NFR-02: Com RSL_DATA_DIR definido e RSL_EXPORT_DIR ausente, export_dir acompanha data_dir
def test_fr07_nfr02_rsl_data_dir_muda_pasta_e_export_dir_segue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom_data = tmp_path / "meus_dados_rsl"
    monkeypatch.setenv("RSL_DATA_DIR", str(custom_data))

    cfg = config.load()

    assert cfg.data_dir == custom_data
    assert cfg.export_dir == custom_data / "exports"
    assert not cfg.data_dir.exists()
    assert not cfg.export_dir.exists()


# FR-07, NFR-02: RSL_DATA_DIR e RSL_EXPORT_DIR aceitam til (~) e releem o ambiente a cada chamada
def test_fr07_nfr02_expansao_de_til_e_releitura_sem_cache(
    monkeypatch: pytest.MonkeyPatch, isolated_env: Path
) -> None:
    monkeypatch.setenv("RSL_DATA_DIR", "~/dados_custom")
    monkeypatch.setenv("RSL_EXPORT_DIR", "~/exportacoes_custom")

    cfg1 = config.load()
    assert cfg1.data_dir == isolated_env / "dados_custom"
    assert cfg1.export_dir == isolated_env / "exportacoes_custom"

    monkeypatch.setenv("RSL_DATA_DIR", "~/outros_dados")
    monkeypatch.delenv("RSL_EXPORT_DIR")

    cfg2 = config.load()
    assert cfg2.data_dir == isolated_env / "outros_dados"
    assert cfg2.export_dir == isolated_env / "outros_dados" / "exports"


# FR-07: Configuração é imutável (dataclass frozen=True)
def test_fr07_config_imutavel() -> None:
    cfg = config.load()
    with pytest.raises(FrozenInstanceError):
        cfg.cache_days = 10  # type: ignore[misc]


# FR-07, NFR-03: Detecta presença das chaves como booleano; vazio ou só espaços conta como ausente
@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
def test_fr07_nfr03_chaves_vazias_ou_espacos_contam_como_nao_configuradas(
    monkeypatch: pytest.MonkeyPatch, empty_val: str
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", empty_val)
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", empty_val)
    monkeypatch.setenv("RSL_CONTACT_EMAIL", empty_val)

    cfg = config.load()

    assert cfg.openalex_key_configured is False
    assert cfg.semantic_scholar_key_configured is False
    assert cfg.contact_email is None


# FR-07, NFR-03: Cada chave de API controla exclusivamente o seu respectivo booleano
def test_fr07_nfr03_cada_chave_controla_apenas_seu_booleano(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123-oa")
    cfg_oa = config.load()
    assert cfg_oa.openalex_key_configured is True
    assert cfg_oa.semantic_scholar_key_configured is False

    monkeypatch.delenv("OPENALEX_API_KEY")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "fake-key-456-s2")
    cfg_s2 = config.load()
    assert cfg_s2.openalex_key_configured is False
    assert cfg_s2.semantic_scholar_key_configured is True


# NFR-03: repr, str, vars e asdict nunca expõem o valor das chaves nem o email de contato em repr/str
def test_nfr03_repr_e_str_nao_expoem_chaves_nem_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campos = {f.name: f.type for f in fields(config.Config)}
    assert set(campos.keys()) == {
        "data_dir",
        "export_dir",
        "cache_days",
        "contact_email",
        "openalex_key_configured",
        "semantic_scholar_key_configured",
    }
    assert campos["openalex_key_configured"] in (bool, "bool")
    assert campos["semantic_scholar_key_configured"] in (bool, "bool")

    fake_oa_key = "fake-key-123-openalex"
    fake_s2_key = "fake-key-456-s2"
    fake_email = "pesquisador@exemplo.org"

    monkeypatch.setenv("OPENALEX_API_KEY", fake_oa_key)
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", fake_s2_key)
    monkeypatch.setenv("RSL_CONTACT_EMAIL", fake_email)

    cfg = config.load()

    assert type(cfg.openalex_key_configured) is bool
    assert type(cfg.semantic_scholar_key_configured) is bool
    assert cfg.openalex_key_configured is True
    assert cfg.semantic_scholar_key_configured is True
    assert cfg.contact_email == fake_email

    texto_repr = repr(cfg)
    texto_str = str(cfg)
    dicionario_vars = str(vars(cfg))
    dicionario_asdict = str(asdict(cfg))

    for segredo in (fake_oa_key, fake_s2_key):
        assert segredo not in texto_repr
        assert segredo not in texto_str
        assert segredo not in dicionario_vars
        assert segredo not in dicionario_asdict

    assert fake_email not in texto_repr
    assert fake_email not in texto_str


# NFR-03: Erro ao validar RSL_CACHE_DAYS não expõe chaves configuradas nem o valor recebido
def test_nfr03_erro_cache_days_nao_expoe_chaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_oa_key = "fake-key-123-openalex"
    fake_s2_key = "fake-key-456-s2"
    valor_invalido = "invalido-789"

    monkeypatch.setenv("OPENALEX_API_KEY", fake_oa_key)
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", fake_s2_key)
    monkeypatch.setenv("RSL_CACHE_DAYS", valor_invalido)

    with pytest.raises(ValueError, match="RSL_CACHE_DAYS") as exc_info:
        config.load()

    mensagem_erro = str(exc_info.value)
    assert fake_oa_key not in mensagem_erro
    assert fake_s2_key not in mensagem_erro
    assert valor_invalido not in mensagem_erro
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


# FR-07: RSL_CACHE_DAYS aceita inteiro positivo e rejeita valores inválidos com o nome da variável
def test_fr07_rsl_cache_days_valido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RSL_CACHE_DAYS", "14")
    cfg = config.load()
    assert cfg.cache_days == 14


@pytest.mark.parametrize("invalid_days", ["0", "-1", "-30", "abc", "3.5", ""])
def test_fr07_rsl_cache_days_invalido_gera_value_error(
    monkeypatch: pytest.MonkeyPatch, invalid_days: str
) -> None:
    monkeypatch.setenv("RSL_CACHE_DAYS", invalid_days)
    with pytest.raises(ValueError, match="RSL_CACHE_DAYS"):
        config.load()
