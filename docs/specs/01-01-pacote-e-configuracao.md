# Pacote e configuração

**Fase:** 1 · Esqueleto · **Situação:** não iniciada

## O que faz

O pacote Python `rslapp` com `pyproject.toml` (layout `src/`, Python 3.10 ou mais, dependências `mcp>=2,<3` e `httpx`, `pytest` e `ruff` para desenvolvimento) e o módulo `config.py`. A configuração lê, de variáveis de ambiente: `RSL_DATA_DIR` (padrão: pasta `RSL.app` na pasta do usuário), `RSL_EXPORT_DIR` (padrão: `exports/` dentro da pasta de dados), `RSL_CACHE_DAYS` (padrão 7), `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` e `RSL_CONTACT_EMAIL` (opcional, para a fila educada da Crossref). O comando de entrada `rslapp` aponta para o servidor (criado na tarefa 01-02).

## O que não faz

Não tem servidor MCP, fontes nem armazenamento. As chaves só são lidas, nunca gravadas nem devolvidas.

## Pronto quando

- [ ] `pip install -e .` e `pytest` rodam sem erro num ambiente limpo
- [ ] `ruff check` passa
- [ ] `config.load()` devolve as pastas e quais chaves estão configuradas (sim ou não), sem expor o valor de nenhuma chave
- [ ] Teste: sem nenhuma variável, os padrões são usados; com `RSL_DATA_DIR` definido, a pasta muda
- [ ] Teste: o texto devolvido por `repr` e por `str` da configuração não contém o valor de nenhuma chave

## Vem de

FR-07, NFR-02, NFR-03, D-001, D-008. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Nenhuma.

## Resultado da entrega

- **O que mudou:**
  - `pyproject.toml`: definição do pacote `rslapp` (`0.1.0`, Python `>=3.10`, licença MIT, backend `hatchling` em layout `src/`), dependências `mcp>=2,<3` e `httpx`, extra `dev` (`pytest`, `ruff`), comando de entrada `rslapp = "rslapp.server:main"` e configuração do Ruff e do Pytest (**D-001**, **D-008**).
  - `src/rslapp/__init__.py`: pacote raiz com `__version__ = "0.1.0"` (**D-001**).
  - `src/rslapp/config.py`: dataclass imutável `Config` (`frozen=True`) e função `load()` que lê `RSL_DATA_DIR`, `RSL_EXPORT_DIR`, `RSL_CACHE_DAYS`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` e `RSL_CONTACT_EMAIL` a cada chamada, sem criar pastas nem reter o valor das chaves, e levanta `ValueError` com `from None` (trazendo só o nome da variável, sem o valor recebido) quando `RSL_CACHE_DAYS` não é inteiro positivo (**FR-07**, **NFR-02**, **NFR-03**).
  - `tests/test_config.py`: 18 testes unitários isolados com `monkeypatch` cobrindo padrões, expansão de `~`, derivação de `export_dir` a partir de `data_dir`, validação de `RSL_CACHE_DAYS`, independência de cada chave de API, imutabilidade, verificação exata de `dataclasses.fields(Config)` e não exposição de chaves e e-mail em `repr`/`str`/`vars`/`asdict` nem em exceções de `RSL_CACHE_DAYS`.
- **O que foi assumido:**
  - `RSL_CONTACT_EMAIL` vazio ou apenas com espaços resulta em `contact_email=None`.
- **O que não deu para verificar:**
  - Nesta pasta com acento (`Síntese Labs`), a instalação editável não importa `rslapp` fora do `pytest` em Python 3.10 e 3.11, enquanto a instalação normal (`--no-editable --reinstall-package rslapp`) funciona.
  - A execução do comando `rslapp` de ponta a ponta depende de `rslapp.server:main`, que pertence à tarefa 01-02 (o registro do entrypoint no pacote instalado já foi verificado via `importlib.metadata.entry_points`).
  - O item "`pip install -e .` num ambiente limpo" fica para a conferência do gerente.

## Como testar

1. **Comandos para rodar:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev python -c "from rslapp import config; print(config.load())"
   ```
2. **O que deve aparecer:**
   - `All checks passed!` no `ruff check .`
   - `18 passed` em ambas as execuções do `pytest` (Python 3.10 e Python 3.14).
   - No comando manual: `Config(data_dir=..., export_dir=..., cache_days=7, openalex_key_configured=False, semantic_scholar_key_configured=False)`, sem expor `contact_email` nem valores de chaves.
3. **Onde olhar primeiro (pontos de risco, do mais crítico ao menos crítico):**
   1. **Não exposição de chaves e dados do usuário (`src/rslapp/config.py` — `Config`, `_is_key_configured` e `load()`, NFR-03):** confirmar que os valores de `OPENALEX_API_KEY` e `SEMANTIC_SCHOLAR_API_KEY` nunca entram em nenhum atributo de `Config` (apenas os booleanos `openalex_key_configured` e `semantic_scholar_key_configured`, cada um lendo sua própria variável), e que `contact_email` usa `field(default=None, repr=False)` para não vazar em `repr(cfg)` nem `str(cfg)`.
   2. **Resolução das pastas locais sem criação no disco (`src/rslapp/config.py` — `load()`, FR-07, NFR-02):** verificar que `export_dir` deriva de `data_dir / "exports"` quando `RSL_EXPORT_DIR` está ausente (mesmo quando `RSL_DATA_DIR` foi alterado), que `~` é expandido em ambas e que `load()` não cria nenhuma pasta no sistema de arquivos.
   3. **Validação de `RSL_CACHE_DAYS` sem vazar valores (`src/rslapp/config.py` — `_parse_cache_days()`, FR-07, NFR-03):** conferir que zero, números negativos, decimais, texto ou string vazia levantam `ValueError` com `from None` contendo apenas o nome `"RSL_CACHE_DAYS"` na mensagem, sem repetir o valor recebido.
