# Fonte BDTD (Biblioteca Digital Brasileira de Teses e Dissertações)

**Fase:** 14 · Versão 2.3 · **Situação:** pronta

## O que faz

O conector `sources/bdtd.py`, com a mesma interface das outras fontes (`Source`, em `sources/base.py`): busca por termos na Biblioteca Digital Brasileira de Teses e Dissertações (IBICT) pela API REST do VuFind (`https://bdtd.ibict.br/vufind/api/v1/search`) e traduz cada registro para `Work`, com autores, orientadores, instituição de defesa, resumo, palavras-chave, formato (tese ou dissertação), ano e link/DOI.

## O que não faz

- Não entra nas fontes padrão do servidor nem em `server.py` até a tarefa 14-02.
- Não faz colheita em lote por OAI-PMH (o conector é para busca sob demanda em tempo real).
- Não deduplica entre fontes (a deduplicação do núcleo faz isso na 14-02).

## Conferência do T-001 (BDTD / IBICT)

Conferida pelo Antigravity / Claude Code em 2026-11-16 através da API oficial do portal BDTD (`https://bdtd.ibict.br/vufind/api/v1/search`) e inspeção de respostas reais:

- **Endereço base:** `https://bdtd.ibict.br/vufind/api/v1/search`.
- **Autenticação:** Aberta, gratuita e pública, mantida pelo IBICT. Não exige chave ou token.
- **Parâmetros de busca suportados:**
  - `lookfor`: termos de busca.
  - `page`: página (1, 2, 3...).
  - `limit`: quantidade por página (até 100).
  - `field[]`: lista de campos requeridos para evitar payload desnecessário (`id`, `title`, `authors`, `publicationDates`, `summary`, `urls`, `institutions`, `formats`, `subjects`, `languages`).
- **Estrutura da resposta JSON:**
  - `status`: `"OK"`.
  - `resultCount`: total de registros encontrados.
  - `records`: lista de dicionários com os metadados requisitados:
    - `id`: identificador único na BDTD (ex: `PUC_RIO-1_69e0bed4d4ce05f2e6664e5d6c5677e8`).
    - `title`: título do trabalho, por vezes prefixado com marcação de idioma (ex: `[pt] A RESPONSABILIDADE CIVIL NA INTELIGÊNCIA ARTIFICIAL`).
    - `authors`: objeto com chaves `primary` (dicionário com nomes dos autores principais como chaves), `secondary` (orientadores/banca) e `corporate`.
    - `publicationDates`: lista de strings de anos (ex: `["2023"]`).
    - `summary`: lista de resumos em texto livre.
    - `urls`: lista de objetos `{"desc": "...", "url": "..."}` com URLs de acesso ao repositório institucional e/ou resolvedor de DOI.
    - `institutions`: lista de siglas/nomes de instituições (ex: `["PUC_RIO"]`, `["USP"]`).
    - `formats`: lista de formatos (ex: `["doctoralThesis"]`, `["masterThesis"]`).
    - `subjects`: lista de assuntos / palavras-chave.

## Decisões desta spec

1. **Interface:** Implementa `Source` (`sources/base.py`) com identificador `name = "bdtd"` e `display_name = "BDTD (Teses e Dissertações)"`.
2. **Paginação:** Lotes de até 100 registros por requisição até atingir `max_results` ou o total disponível (`resultCount`).
3. **Mapeamento para `Work`:**
   - `title`: texto limpo de prefixos como `[pt] `, `[en] `, `[es] ` e espaços extras.
   - `year`: extraído dos primeiros 4 dígitos da primeira entrada de `publicationDates`.
   - `abstract`: primeiro item de `summary`, com prefixos de idioma removidos.
   - `venue`: nome/sigla da instituição de defesa (ex: `PUC_RIO`) ou `"BDTD / IBICT"`.
   - `type`: `"thesis"` para `doctoralThesis` ou `"dissertation"` para `masterThesis` (ou `"thesis"` padrão).
   - `doi`: extraído das `urls` quando contiver `doi.org/10.` ou `10.NNNN/`.
   - `url`: a URL de acesso primária do documento.
   - `authors`: autor principal de `authors.primary` (posição 1), seguido de orientadores de `authors.secondary`. Filiação preenchida com a instituição de defesa.
   - `keywords`: coletadas de `subjects`, normalizadas e sem duplicatas.
   - `source_ids`: `{"bdtd": id}`.
4. **Resiliência:** HTTP timeout de 15 segundos, retentativas em erros transitórios (5xx, timeouts, 429) com backoff exponencial.

## Pronto quando

- [x] Arquivo `src/rslapp/sources/bdtd.py` implementado seguindo a interface `Source`.
- [x] Testes unitários com simulação de respostas (`httpx.MockTransport`) em `tests/sources/test_bdtd.py`.
- [x] Teste de mapeamento completo: título sem prefixo de idioma, autores e orientadores com instituição, resumo, ano, DOI extraído de URL, palavras-chave e tipo de documento.
- [x] Teste de paginação em lotes de até 100 até `max_results`.
- [x] Teste de tolerância a falhas (respostas vazias, 500, tempo esgotado e registro sem título).
- [x] Todos os gates passam (Ruff limpo, testes em Python 3.10 e 3.14).
