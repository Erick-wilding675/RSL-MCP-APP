# Publicação da 1.1.0 e teste real

**Fase:** 8 · Uso por link (v2) · **Situação:** a fazer

## O que faz

Publica a v2 como `rslapp` 1.1.0 (o modo stdio não muda, então é uma versão menor) e faz o teste de ponta a ponta que fecha a fase 8.

- **Publicação** (Claude Code, como na 1.0.1): `version` no `pyproject.toml` e `__version__` em `src/rslapp/__init__.py`; `uv build --no-sources`; conferir o sdist (`tar -tzf`); `lore secrets run --env prod -- uv publish` só dos arquivos da 1.1.0; tag `v1.1.0`, que dispara a publicação da imagem no ghcr.io (08-06); `gh release create` com notas em português; conferir com `uvx` vindo do PyPI e com `docker pull` da imagem.
- **Teste real do Erick**, seguindo o `docs/hospedagem.md` copiado:
  1. subir o compose num servidor com domínio e HTTPS;
  2. cadastrar dois códigos (`erick` e um segundo);
  3. no Claude, adicionar o link como conector, fazer login com o código dele, fazer uma busca e baixar o RIS pelo link, e abrir no VOSviewer;
  4. com o segundo código (outra conta ou o Claude Code), conferir que as listas do Erick não aparecem;
  5. revogar o segundo código e conferir que ele perde o acesso na hora.

## O que não faz

- Não anuncia o modo hospedado: isso espera a LGPD (T-007, D-018).
- Não escolhe onde hospedar o teste: é decisão do Erick, porque pode ter custo (um servidor pequeno alugado, uma máquina da universidade ou a máquina dele com as portas abertas). Trazer as opções antes de começar esta tarefa.

## Pronto quando

- [ ] `rslapp` 1.1.0 no PyPI e conferido com `uvx`
- [ ] Imagem `1.1.0` e `latest` no ghcr.io, conferida com `docker pull`
- [ ] Tag e release `v1.1.0` no GitHub
- [ ] Teste manual do Erick: os cinco passos acima passam
- [ ] O que o teste real achar vira itens desta spec ou uma tarefa nova, como na 05-05

## Vem de

D-011, D-015, D-017 e D-018, e D-008 (publicação no PyPI).

## Antes de começar

08-01 a 08-06 integradas e prontas. O Lore conectado (o token do PyPI está nele). O Erick escolhe onde hospedar o teste.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
