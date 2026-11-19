# Versão 3.0.0 · A Revisão Completa: Publicação e Teste Real (22-06)

Fecha a fase 22 e a versão 3.0.0 do RSL.app com a suíte de testes 100% limpa, documentação atualizada e instrução de teste real para o Erick.

## O que faz
1. **Subida de versão:**
   - `pyproject.toml`: `version = "3.0.0"`
   - `src/rslapp/__init__.py`: `__version__ = "3.0.0"`
   - `uv.lock` sincronizado.
2. **Documentação:**
   - `README.md` atualizado com as novas capacidades de Texto Completo OA, Metanálise/Extração, Risco de Viés e Kappa de Cohen.
   - `docs/plan.md` e `.blueprint/state.md` atualizados.
3. **Gates:**
   - Suíte de testes do núcleo (mais de 850 testes) 100% passando.
   - Suíte de testes do desktop 100% passando.
   - Linter `ruff` sem avisos nem erros.
