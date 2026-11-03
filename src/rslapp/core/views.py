"""Visualizações de dados do miolo: paginação de listas e consulta ao log de buscas."""

from __future__ import annotations

from typing import Any

from rslapp.core.errors import RSLError
from rslapp.core.models import Work
from rslapp.core.search import _summarize_work
from rslapp.store import Store

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 25
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100
ALLOWED_DETAILS = frozenset({"summary", "full"})

DEFAULT_LOG_LIMIT = 20
MIN_LOG_LIMIT = 1
MAX_LOG_LIMIT = 200


def _item_to_work(item: Any) -> Work:
    if isinstance(item, Work):
        return item
    if isinstance(item, dict):
        return Work.from_dict(item)
    raise TypeError(f"Item da lista deve ser dict ou Work, recebido: {type(item).__name__}")


# FR-12, D-002: Leitura e paginação de lista salva por páginas com resumo ou detalhes completos
def get_list_view(
    store: Store,
    list_id: str,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    detail: str = "summary",
    max_page_size: int = MAX_PAGE_SIZE,
) -> dict[str, Any]:
    """Lê uma lista salva no armazenamento, valida parâmetros e devolve a página solicitada.

    Args:
        store: Armazenamento contendo as listas gravadas.
        list_id: Identificador da lista (formato 'l-NNNN').
        page: Número da página (a partir de 1).
        page_size: Quantidade de itens por página (entre 1 e max_page_size).
        detail: Nível de detalhe dos trabalhos ('summary' ou 'full').
        max_page_size: Limite superior para page_size (padrão 100).

    Returns:
        Dicionário com list_id, search_id, status, total, page, page_size, next_page e works.

    Raises:
        RSLError('invalid_input'): Parâmetros page, page_size ou detail fora do permitido.
        RSLError('list_not_found'): Lista inexistente ou identificador malformado.
    """
    if type(page) is not int or page < 1:
        raise RSLError("invalid_input", f"page deve ser um inteiro >= 1 (recebido: {page!r})")

    if type(page_size) is not int or page_size < MIN_PAGE_SIZE or page_size > max_page_size:
        raise RSLError(
            "invalid_input",
            f"page_size deve ser um inteiro entre {MIN_PAGE_SIZE} e {max_page_size} (recebido: {page_size!r})",
        )

    if not isinstance(detail, str) or detail not in ALLOWED_DETAILS:
        raise RSLError(
            "invalid_input",
            f"detail deve ser 'summary' ou 'full' (recebido: {detail!r})",
        )

    if not isinstance(list_id, str):
        raise RSLError("list_not_found", f"Lista não encontrada: {list_id!r}")

    try:
        list_data = store.get_list(list_id)
    except (FileNotFoundError, ValueError) as err:
        raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    raw_works: list[Any] = list_data.get("works") or []
    total = len(raw_works)

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    if start_idx >= total:
        page_items: list[Any] = []
        next_page: int | None = None
    else:
        page_items = raw_works[start_idx:end_idx]
        next_page = page + 1 if end_idx < total else None

    if detail == "summary":
        works = [_summarize_work(_item_to_work(item)) for item in page_items]
    else:
        works = [_item_to_work(item).to_dict() for item in page_items]

    return {
        "list_id": list_data.get("id", list_id),
        "search_id": list_data.get("search_id"),
        "status": list_data.get("status", "complete"),
        "total": total,
        "page": page,
        "page_size": page_size,
        "next_page": next_page,
        "works": works,
    }


# FR-05, FR-13, D-002: Leitura do log de buscas e caminho absoluto do log.md legível
def get_search_log_view(
    store: Store,
    search_id: str | None = None,
    limit: int = DEFAULT_LOG_LIMIT,
) -> dict[str, Any]:
    """Consulta as entradas gravadas do log de buscas e o caminho do log.md legível.

    Args:
        store: Armazenamento contendo as buscas e o log legível.
        search_id: Identificador opcional da busca ('s-NNNN'). Se informado, volta apenas ela.
        limit: Quantidade máxima de entradas recentes (entre 1 e 200).

    Returns:
        Dicionário com 'entries' e 'log_file' (caminho absoluto do log.md).

    Raises:
        RSLError('invalid_input'): limit fora do intervalo [1, 200] ou tipo inválido.
        RSLError('search_not_found'): search_id inexistente ou malformado.
    """
    if type(limit) is not int or limit < MIN_LOG_LIMIT or limit > MAX_LOG_LIMIT:
        raise RSLError(
            "invalid_input",
            f"limit deve ser um inteiro entre {MIN_LOG_LIMIT} e {MAX_LOG_LIMIT} (recebido: {limit!r})",
        )

    if search_id is not None:
        if not isinstance(search_id, str):
            raise RSLError("search_not_found", f"Busca não encontrada: {search_id!r}")
        try:
            search_data = store.get_search(search_id)
        except (FileNotFoundError, ValueError) as err:
            raise RSLError("search_not_found", f"Busca não encontrada: {search_id}") from err
        entries = [search_data]
    else:
        all_searches = store.list_searches()
        entries = all_searches[-limit:]

    log_file = str(store.log_path.resolve())

    return {
        "entries": entries,
        "log_file": log_file,
    }

