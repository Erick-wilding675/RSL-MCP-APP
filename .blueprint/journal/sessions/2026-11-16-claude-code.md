# 2026-11-16 · Claude Code (continuação da sessão de 2026-11-15)

- 12-01 integrada: o `.exe` `--windowed` conversa por stdio (teste de fumaça no workflow, Windows e Linux). O Linux falhou na primeira vez por um erro do script (`./` some no `Path`), corrigido pelo `agy`.
- 12-03 escrita pelo Claude: guia com "Para instituições de ensino" e o ChatGPT. OAuth do servidor de teste conferido contra as páginas da OpenAI. Um cadastro igual ao do ChatGPT foi aceito (201). Falta o teste do Erick.
- 12-02 integrada: tela "Conectar IA".
- Revisão geral pedida pelo Erick. Achados de código viraram a 12-05 (integrada):
  - o compose não repassava as variáveis opcionais do guia;
  - `RSL_CACHE_DAYS` vazio derrubava o servidor;
  - faltavam as anotações só de leitura;
  - o caso `pip` da 12-02 não lia o `desktop.json`;
  - o comando do VS Code perdia as aspas no PowerShell 5.1 (testado com um `.cmd` que imita o `code.cmd`).
- Achados de documento corrigidos direto: o contrato, as variáveis no guia e no README, o comando do Claude Code, D-028 verificada e o plano de testes.
- Ideias para as próximas versões em `docs/ideias-proximas-versoes.md`, a pedido do Erick.
- O `agy` foi parado duas vezes por falta de memória (12-01 e 12-05), nas duas depois dos commits de código. O Claude escreveu as seções da spec que faltavam.
- Próximo: o Erick revisa, testa o ChatGPT e o Claude Desktop, e dá o ok para publicar a 2.1.0.
