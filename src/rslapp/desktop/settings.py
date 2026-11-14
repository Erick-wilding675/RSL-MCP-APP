"""Configuração persistente do app desktop em arquivo JSON fora da pasta de dados."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import MutableMapping
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


# D-026, FR-18, NFR-03: Estrutura de configuração do app desktop com mascaramento de chaves no repr
@dataclass
class DesktopSettings:
    """Guarda os valores configurados no app desktop, mascarando chaves em __repr__."""

    values: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.values, dict):
            self.values = {}
            return
        self.values = {
            k: v
            for k, v in self.values.items()
            if k in ALLOWED_VARS and isinstance(v, str)
        }

    def __repr__(self) -> str:
        masked = {
            k: ("***" if k in KEY_VARS else v)
            for k, v in self.values.items()
            if k in ALLOWED_VARS
        }
        return f"DesktopSettings(values={masked!r})"


# D-026, FR-18, NFR-03: Carrega desktop.json sem levantar exceção em arquivo ausente ou corrompido
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
    return DesktopSettings(values=cleaned)


# D-026, FR-18, NFR-03: Grava desktop.json atomicamente, sem chaves desconhecidas nem valores vazios
def save_settings(settings: DesktopSettings) -> Path:
    """Grava as configurações válidas e não vazias em desktop.json com permissão 0o600 fora do Windows."""
    path = settings_path()
    raw_values = settings.values if isinstance(settings.values, dict) else {}
    cleaned: dict[str, str] = {}
    for key in ALLOWED_VARS:
        val = raw_values.get(key)
        if isinstance(val, str) and val.strip():
            cleaned[key] = val.strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n"
    atomic_write_replace(path, content)
    if sys.platform != "win32":
        os.chmod(path, 0o600)
    return path


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
        environ[key] = val.strip()
        applied.append(key)
    return applied
