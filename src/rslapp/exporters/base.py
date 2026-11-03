"""Interface base para exportadores e funções comuns de gravação."""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

from rslapp.core.errors import RSLError
from rslapp.store._atomic import atomic_write_replace


# D-002, FR-06: Interface comum dos exportadores de lista
class Exporter(abc.ABC):
    """Classe base abstrata para exportadores de listas do RSL.app."""

    format: str
    extension: str

    @abc.abstractmethod
    def render(self, list_data: dict[str, Any]) -> str:
        """Renderiza o conteúdo da lista no formato específico."""
        ...


# D-007, FR-06: Gravação atômica comum com UTF-8 e substituição de arquivo
def save_export_file(export_dir: Path | str, filename: str, content: str) -> Path:
    """Grava o conteúdo de forma atômica em export_dir/filename em UTF-8.

    Cria o diretório se não existir. Se a pasta não aceitar gravação,
    levanta RSLError com o código 'export_folder_not_writable'.
    """
    export_path = Path(export_dir)
    dest = export_path / filename
    try:
        export_path.mkdir(parents=True, exist_ok=True)
        atomic_write_replace(dest, content)
    except (PermissionError, OSError) as err:
        raise RSLError(
            "export_folder_not_writable",
            f"Pasta de exportação não aceita gravação: {export_path}",
        ) from err
    return dest
