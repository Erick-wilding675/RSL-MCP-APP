# Deduplicação entre fontes

**Fase:** 3 · Mais fontes · **Situação:** para testar

## O que faz

No miolo, a junção dos resultados das três fontes numa lista só por pedido: o mesmo artigo vindo de mais de uma fonte aparece uma vez, com o id dele em cada fonte, as citações de cada fonte separadas e os campos preenchidos pela fonte que os tiver. A busca passa a consultar as fontes em paralelo (cada fonte continua fazendo uma chamada por vez dentro dela), e o log passa a dizer quantos artigos foram juntados e em quais campos as fontes divergiram.

## O que não faz

Não junta listas de pedidos diferentes. Não faz correspondência aproximada de título além do título normalizado. Não junta nem desambigua autores entre fontes: a lista de autores vem inteira da fonte que prevalece.

## Decisões desta spec

Tomadas pelo Claude Code em 2026-11-03, baratas de desfazer:

1. **Quando dois registros são o mesmo artigo:** mesmo DOI (minúsculo); ou, quando ao menos um dos dois não tem DOI, mesmo título normalizado (a regra da 02-02) **e** mesmo ano. Título igual com anos diferentes, ou com algum ano ausente, ficam como dois. Dois DOIs diferentes nunca se juntam.
2. **Qual campo prevalece:** a ordem é OpenAlex, Crossref, Semantic Scholar. Para cada campo simples (`title`, `doi`, `year`, `type`, `venue`, `abstract`, `references_count`) vale o primeiro valor não vazio nessa ordem. `authors` e `keywords` vêm inteiros da primeira fonte, nessa ordem, que os tiver não vazios.
3. **O que se soma sem perder nada:** `source_ids` e `citations` juntam as chaves de todas as fontes (as citações nunca são somadas, FR-14); `references` é a união, na ordem, sem repetir, com os ids da primeira fonte primeiro (ids do OpenAlex e DOIs convivem; a tarefa 04-01 troca os ids por DOI).
4. **Divergência:** quando duas fontes trazem valores diferentes e não vazios em `title` (comparado normalizado), `year`, `doi` ou `venue`, conta uma divergência daquele campo. A busca grava em `searches/` o campo `merge`: `{"merged": <artigos que vieram de mais de uma fonte>, "divergences": {"year": 3, "title": 1}}`, e o `log.md` ganha a linha `Junção: 12 artigos em mais de uma fonte · divergências: ano 3, título 1` (ou `· sem divergências`). Os valores divergentes não vão para o log, só a contagem por campo.
5. **Onde fica:** a regra de junção em `core/dedup.py` (funções puras, sem rede nem disco); `core/search.py` passa a chamar as fontes com `asyncio.gather` e a usar `dedup`; `store/log.py` ganha a linha de junção.
6. **A busca guarda os parâmetros de entrada**, para a 05-01 poder repeti-la: o JSON em `searches/` ganha `params`: `{"query": <texto pedido>, "max_results": <n>, "sources": [<nomes na ordem pedida>]}`. Nada muda no `log.md` por causa disso.
7. **As três fontes no servidor:** `server.py` passa a montar `[OpenAlexSource(), CrossrefSource(), SemanticScholarSource()]` (nessa ordem). Em `list_sources`, a Semantic Scholar continua `configured: true`, `needs_key: false` e `status: ok`, e a descrição da ferramenta (docstring) passa a dizer que a chave da Semantic Scholar é opcional e evita recusas por limite.

## Pronto quando

- [x] Teste: o mesmo DOI em duas ou três fontes vira um artigo, com as fontes e os ids registrados
- [x] Teste: sem DOI, o título normalizado igual e o mesmo ano contam como o mesmo artigo; título igual com anos diferentes, ou ano ausente, ficam como dois
- [x] Teste: quando duas fontes divergem num campo, prevalece a ordem OpenAlex, Crossref, Semantic Scholar, e a divergência é contada no `merge` da busca e na linha de junção do log
- [x] Teste: as referências das fontes viram a união sem repetir, e as citações de cada fonte ficam separadas e não são somadas (FR-14)
- [x] Teste: uma fonte em falha deixa a lista `incomplete` com a fonte e o motivo, e as outras seguem
- [x] Teste: as fontes são chamadas em paralelo (uma fonte simulada lenta não atrasa a chamada das outras)
- [x] Teste: resposta vinda do cache aparece marcada no log com a data de obtenção (NFR-06)
- [x] Teste: o `log.md` refeito por `rebuild_log` tem a mesma linha de junção
- [x] Teste: a busca gravada em `searches/` tem `params` com a consulta, o `max_results` e as fontes pedidas
- [x] Teste pelo servidor (`Client(mcp)` em memória, com as três fontes trocadas por simuladas): `search_works` consulta as três e junta o resultado; `list_sources` mostra as três, com a nota da chave da Semantic Scholar

## Vem de

FR-04, FR-08, FR-14, NFR-06, D-007. São os identificadores que o código leva como âncoras, para que qualquer pessoa pergunte por que aquele código existe e ache a resposta no próprio código.

## Antes de começar

Depende de 02-02, 03-01 e 03-02.

## Resultado da entrega

- **O que mudou:**
  - Implementado em `src/rslapp/core/dedup.py`:
    - Normalização de DOI (minúsculas, remoção de prefixos `https://doi.org/`, `http://doi.org/`, `https://dx.doi.org/`, `http://dx.doi.org/`, `doi:` e barras finais).
    - Normalização de título (remoção de acentos e pontuação, minúsculas, espaços simples) com garantia de que título vazio nunca junta trabalhos sem DOI.
    - Junção transitiva e agrupamento determinístico: todo registro que entra num grupo (inclusive por DOI) alimenta os índices de DOI e título normalizado + ano com os seus dados (cada registro só com o próprio ano: um ano ausente nunca é emprestado de outro membro, correção do Claude Code na integração). Registros sem DOI encontram o grupo por qualquer membro, independente da ordem de processamento das fontes (**FR-04**).
    - Regra estrita de DOIs: dois DOIs diferentes nunca se juntam mesmo se título e ano coincidirem. Se um registro casa com dois grupos distintos (um pelo DOI e outro pelo título), ele permanece no grupo do DOI (**FR-04**).
    - Prevalência de campos na ordem OpenAlex, Crossref, Semantic Scholar. Campos simples recebem o primeiro valor não vazio; `authors` e `keywords` vêm inteiros da primeira fonte não vazia (**FR-04**).
    - União de `references` sem repetição preservando a ordem e ids da primeira fonte; agregação de `citations` e `source_ids` sem somar valores de citações (**FR-14**).
    - Contagem de artigos juntados de mais de uma fonte e rastreamento de divergências nos campos `title` (comparado normalizado), `year`, `doi` e `venue` (**FR-04**).
  - Atualizado `src/rslapp/core/search.py`:
    - Consulta às fontes executada concorrentemente via `asyncio.gather` sem bloqueio mútuo (**FR-08**).
    - Gravação em `searches/s-NNNN.json` dos parâmetros `params` (`query`, `max_results`, `sources`) e das estatísticas de junção em `merge` (**FR-05**, **NFR-06**).
  - Atualizado `src/rslapp/store/log.py`:
    - Formatação da linha `Junção: <N> artigos em mais de uma fonte · divergências: ...` (ou `· sem divergências`) logo após a linha da lista, reproduzível de modo exato por `Store.rebuild_log()` (**FR-04**, **FR-13**, **D-007**).
  - Atualizado `src/rslapp/server.py`:
    - `_build_sources()` instancia incondicionalmente os conectores das três fontes: `[OpenAlexSource(), CrossrefSource(), SemanticScholarSource()]` sem inspeção de stack frames de teste (**FR-01**, **D-002**).
    - Docstring de `list_sources` informa que a chave da Semantic Scholar é opcional e evita recusas por limite de taxa (**FR-07**, **D-002**).
  - Atualizado `tests/test_server_search_works.py` para refletir as três fontes padrão instanciadas por `_build_sources()` conforme a Decisão 7.
  - Cobertura completa de testes automatizados adicionada em `tests/core/test_dedup.py` (incluindo permutações das ordens de fontes para junção transitiva e prevalência, ano ausente e desempate no grupo do DOI), `tests/store/test_log_merge.py`, `tests/test_server_three_sources.py` e expandida em `tests/core/test_search.py`.
- **Por que a entrega passou de 400 linhas:**
  - A tarefa introduziu o módulo central de deduplicação e fusão de metadados (`src/rslapp/core/dedup.py`, ~320 linhas) com suporte completo a junção transitiva, resolução de conflitos de DOI e divergências por campo, além de integração assíncrona concorrente em `search.py`, reconstrução de log em `log.py`, e extensa suíte de testes com permutações exaustivas e mocks em 4 arquivos de teste distintos para blindar o comportamento contra mutações e regressões.
- **Requisitos atendidos:** FR-01, FR-04, FR-05, FR-07, FR-08, FR-12, FR-13, FR-14, NFR-03, NFR-06, D-002, D-007.
- **O que foi assumido:**
  - O campo `merge` no `searches/s-NNNN.json` omite chaves de divergências cujo contador seja 0, conforme o exemplo da spec.
  - No log legível, o campo `venue` quando diverge é formatado em português como `veículo`.
- **O que não deu para verificar:**
  - Chamadas reais simultâneas com chaves reais das 3 APIs contra servidores de produção (os testes utilizam mocks e transporte simulado em memória para não consumir rede nem expor credenciais).

## Como testar

1. **Executar a suíte de testes de deduplicação e servidor:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest tests/core/test_dedup.py tests/store/test_log_merge.py tests/test_server_three_sources.py tests/core/test_search.py tests/test_server_search_works.py -v
   ```
   Deve exibir 35 testes passando (14 em dedup, 7 em log_merge, 4 em server_three_sources, 10 em search).

2. **Executar a checagem de estilo e os portões completos:**
   ```powershell
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev ruff check .
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.10 --extra dev pytest -q
   uv run --isolated --no-editable --reinstall-package rslapp --python 3.14 --extra dev pytest -q
   ```
   Deve passar sem avisos do ruff e com 147 testes aprovados no Python 3.10 e 3.14.

3. **Onde olhar primeiro (pontos de maior risco):**
   - `src/rslapp/core/dedup.py` (`deduplicate_works_with_merge`): verificar a junção transitiva independente da ordem das fontes (testes com permutações), garantia de que dois registros com DOIs distintos nunca se juntam mesmo com mesmo título e ano, que no empate duplo (DOI e título) o registro permanece no grupo do DOI, e que a prevalência obedece estritamente OpenAlex > Crossref > Semantic Scholar.
   - `src/rslapp/server.py` (`_build_sources`): verificar a instanciação incondicional das três fontes acadêmicas sem manipulação de stack frames.
   - `src/rslapp/core/search.py` (`run_search`): verificar que `asyncio.gather` dispara as consultas às fontes simultaneamente, e que `searches/` armazena `params` e `merge`.
   - `src/rslapp/store/log.py` (`_format_merge_line` e `format_log_entry`): conferir que a reconstrução do log via `rebuild_log()` reproduz fielmente a linha de junção salva no JSON da busca.

**Acompanhamentos da revisão (não bloqueiam):** com dois DOIs de mesmo título e ano, um registro sem DOI vai para o grupo do DOI que chegou primeiro (na ordem padrão, o do OpenAlex). `asyncio.gather` sem `return_exceptions`: uma fonte que levantar exceção derruba a busca (hoje nenhuma levanta). `_WorkCluster` compara por valor; `eq=False` seria mais barato.
