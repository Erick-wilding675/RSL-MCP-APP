"""Configuração persistente do app desktop em arquivo JSON fora da pasta de dados."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path

from rslapp.store._atomic import atomic_write_replace

# D-026, FR-18, NFR-03: Variáveis de chave de API e demais configurações aceitas pelo app desktop
KEY_VARS: tuple[str, ...] = (
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "NCBI_API_KEY",
    "SCOPUS_API_KEY",
    "SCOPUS_INSTTOKEN",
    "WOS_STARTER_API_KEY",
)

OTHER_VARS: tuple[str, ...] = (
    "RSL_CONTACT_EMAIL",
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
)

ALLOWED_VARS: tuple[str, ...] = KEY_VARS + OTHER_VARS

_SYSTEM_ENV_VARS: frozenset[str] = frozenset()
_APPLIED_BY_APP_VALUES: dict[str, str] = {}


# D-026, FR-18, NFR-03: Captura no início do processo quais variáveis já vieram do ambiente do sistema
def capture_system_env_vars(
    environ: Mapping[str, str] = os.environ,
) -> frozenset[str]:
    """Registra quais variáveis de ALLOWED_VARS já vieram definidas no ambiente do sistema antes de apply_to_environ."""
    global _SYSTEM_ENV_VARS
    captured = frozenset(
        key
        for key in ALLOWED_VARS
        if isinstance(val := environ.get(key), str) and val.strip()
    )
    if environ is os.environ:
        _APPLIED_BY_APP_VALUES.clear()
        _SYSTEM_ENV_VARS = captured
    return captured


# D-026, FR-18, NFR-03: Consulta quais variáveis pertencem ao ambiente do sistema e não devem ser sobrescritas
def get_system_env_vars(
    environ: Mapping[str, str] = os.environ,
) -> frozenset[str]:
    """Devolve o frozenset de variáveis de ALLOWED_VARS definidas pelo ambiente do sistema."""
    if environ is not os.environ:
        return frozenset(
            key
            for key in ALLOWED_VARS
            if isinstance(val := environ.get(key), str) and val.strip()
        )
    active_sys_vars: set[str] = set()
    for key in ALLOWED_VARS:
        raw = environ.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        cleaned = raw.strip()
        if key in _SYSTEM_ENV_VARS or _APPLIED_BY_APP_VALUES.get(key) != cleaned:
            active_sys_vars.add(key)
    return frozenset(active_sys_vars)


# D-026, FR-18, NFR-03: Atualiza ou remove variável no ambiente do processo respeitando as variáveis do sistema
def set_app_env_var(
    key: str,
    value: str,
    environ: MutableMapping[str, str] = os.environ,
) -> bool:
    """Define uma variável configurada na tela no environ do processo, exceto se veio do sistema."""
    if key not in ALLOWED_VARS or key in get_system_env_vars(environ):
        return False
    cleaned = value.strip()
    if not cleaned:
        return False
    environ[key] = cleaned
    if environ is os.environ:
        _APPLIED_BY_APP_VALUES[key] = cleaned
    return True


def remove_app_env_var(
    key: str,
    environ: MutableMapping[str, str] = os.environ,
) -> bool:
    """Remove do environ uma variável apagada na tela, exceto se veio do sistema."""
    if key not in ALLOWED_VARS or key in get_system_env_vars(environ):
        return False
    environ.pop(key, None)
    if environ is os.environ:
        _APPLIED_BY_APP_VALUES.pop(key, None)
    return True


# D-026, FR-18: Resolve o caminho do arquivo de configuração do app conforme o sistema ou RSL_DESKTOP_CONFIG
def settings_path() -> Path:
    """Devolve o caminho de desktop.json conforme RSL_DESKTOP_CONFIG ou o sistema operacional."""
    custom = os.environ.get("RSL_DESKTOP_CONFIG")
    if custom and custom.strip():
        return Path(custom.strip()).expanduser()

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata and appdata.strip():
            base = Path(appdata.strip()).expanduser()
        else:
            base = Path.home() / "AppData" / "Roaming"
        return base / "RSL.app" / "desktop.json"

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg and xdg.strip():
        base = Path(xdg.strip()).expanduser()
    else:
        base = Path.home() / ".config"
    return base / "rslapp" / "desktop.json"


# D-026, D-031, FR-18, NFR-03: Estrutura de configuração do app desktop com mascaramento de chaves no repr
@dataclass
class DesktopSettings:
    """Guarda os valores configurados no app desktop, mascarando chaves em __repr__."""

    values: dict[str, str] = field(default_factory=dict)
    theme: str = "auto"

    def __post_init__(self) -> None:
        if not isinstance(self.values, dict):
            self.values = {}
        else:
            self.values = {
                k: v
                for k, v in self.values.items()
                if k in ALLOWED_VARS and isinstance(v, str)
            }
        if self.theme not in ("auto", "light", "dark"):
            self.theme = "auto"

    def __repr__(self) -> str:
        masked = {
            k: ("***" if k in KEY_VARS else v)
            for k, v in self.values.items()
            if k in ALLOWED_VARS
        }
        return f"DesktopSettings(values={masked!r}, theme={self.theme!r})"


# D-026, D-031, FR-18, NFR-03: Carrega desktop.json sem levantar exceção em arquivo ausente ou corrompido
def load_settings() -> DesktopSettings:
    """Lê o arquivo de configuração do app desktop, ignorando chaves desconhecidas ou valores inválidos."""
    path = settings_path()
    if not path.is_file():
        return DesktopSettings()
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, ValueError, TypeError):
        return DesktopSettings()

    if not isinstance(data, dict):
        return DesktopSettings()

    cleaned: dict[str, str] = {}
    for key in ALLOWED_VARS:
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            cleaned[key] = val.strip()

    raw_theme = data.get("theme")
    theme = raw_theme if raw_theme in ("auto", "light", "dark") else "auto"
    return DesktopSettings(values=cleaned, theme=theme)


# D-026, D-031, FR-18, NFR-03: Grava desktop.json atomicamente, sem chaves desconhecidas nem valores vazios
def save_settings(settings: DesktopSettings) -> Path:
    """Grava as configurações válidas e não vazias em desktop.json com permissão 0o600 fora do Windows."""
    path = settings_path()
    raw_values = settings.values if isinstance(settings.values, dict) else {}
    cleaned: dict[str, str] = {}
    for key in ALLOWED_VARS:
        val = raw_values.get(key)
        if isinstance(val, str) and val.strip():
            cleaned[key] = val.strip()

    theme = getattr(settings, "theme", "auto")
    if theme in ("auto", "light", "dark"):
        cleaned["theme"] = theme

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n"
    atomic_write_replace(path, content)
    if sys.platform != "win32":
        os.chmod(path, 0o600)
    return path


# D-031: Leitura e alteração do tema preservando as demais configurações intactas
def get_theme() -> str:
    """Devolve o tema configurado ('auto', 'light' ou 'dark'), padrão 'auto'."""
    return load_settings().theme


def set_theme(theme: str) -> str:
    """Atualiza o tema no arquivo desktop.json mantendo as demais configurações intactas."""
    cfg = load_settings()
    normalized = theme if theme in ("auto", "light", "dark") else "auto"
    cfg.theme = normalized
    save_settings(cfg)
    return normalized


# D-026, FR-18, NFR-03: Aplica configurações no ambiente do processo sem sobrescrever variáveis já definidas
def apply_to_environ(
    settings: DesktopSettings,
    environ: MutableMapping[str, str] = os.environ,
) -> list[str]:
    """Define no environ apenas variáveis com valor não vazio que ainda não estejam definidas no ambiente."""
    applied: list[str] = []
    raw_values = settings.values if isinstance(settings.values, dict) else {}
    for key in ALLOWED_VARS:
        val = raw_values.get(key)
        if not isinstance(val, str) or not val.strip():
            continue
        existing = environ.get(key)
        if existing is not None and existing.strip():
            continue
        cleaned = val.strip()
        environ[key] = cleaned
        if environ is os.environ:
            _APPLIED_BY_APP_VALUES[key] = cleaned
        applied.append(key)
    return applied
