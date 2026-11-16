# Janela do app no Windows quando o zip vem do navegador (2.1)

**Fase:** 12 · Conectar a IA ao app (2.1) · **Situação:** integrada (2026-11-16); sai na 2.1.1

## O que faz

Faz a janela do app abrir no Windows quando a pessoa baixa o zip pelo navegador e extrai pelo Explorer. É o caminho de quase todo pesquisador, e na 2.0.0 ele não funciona.

### O defeito (achado em 2026-11-16, no teste do Erick)

O Erick baixou `RSL.app-2.0.0-windows-x64.zip` da release, extraiu pelo Explorer e abriu o `RSL.app.exe`. Nenhuma janela apareceu. O servidor interno subiu e respondeu em `127.0.0.1:8000`, e o processo ficou rodando escondido. Cada clique deixava mais uma cópia parada.

**Causa, comprovada pelo Claude:**

- O Windows marca como "baixado da internet" o zip e todo arquivo extraído dele pelo Explorer (fluxo `Zone.Identifier`, `ZoneId=3`).
- A janela usa o pywebview, que carrega DLLs .NET pelo pythonnet: `Python.Runtime.dll`, `ClrLoader.dll` e as do WebView2 em `webview/lib`.
- O .NET Framework 4 não carrega uma DLL com essa marca, a não ser que o programa permita.
- O erro acontece no processo filho que abre a janela. Esse processo não tem saída de erros, então nada aparece: ele fica esperando para sempre.

**Provas:**

- A mesma pasta, com as marcas removidas (`Unblock-File`), abre a janela.
- A pasta com as marcas mais o arquivo `RSL.app.exe.config` abaixo também abre.
- O build local abre porque não tem as marcas.
- O teste de fumaça do workflow não pegou nada por dois motivos: os arquivos no CI não têm a marca, e o `--check` não carrega o .NET.

**Fonte oficial**, lida em 2026-11-16: [`<loadFromRemoteSources>`](https://learn.microsoft.com/en-us/dotnet/framework/configure-apps/file-schema/runtime/loadfromremotesources-element).

- Diz que um aplicativo copiado da web é tratado como vindo da web, mesmo estando no computador.
- As saídas que ela dá são mudar as propriedades do arquivo (desbloquear) ou usar esse elemento no arquivo de configuração do aplicativo.

### 1. Arquivo de configuração ao lado do `.exe`

- Crie `packaging/RSL.app.exe.config`, em UTF-8, com exatamente:

  ```xml
  <?xml version="1.0" encoding="utf-8"?>
  <configuration>
    <runtime>
      <loadFromRemoteSources enabled="true"/>
    </runtime>
  </configuration>
  ```

- No `.github/workflows/desktop.yml`, job do Windows, logo depois do `nicegui-pack`, copie esse arquivo para `dist/RSL.app/RSL.app.exe.config`. Ele entra no zip junto com o `.exe`.
- O nome tem de ser o do `.exe` mais `.config`. Se o nome do executável mudar, este muda junto.

### 2. O `--check` passa a carregar o .NET no Windows

- Em `_run_check` (`src/rslapp/desktop/app.py`), só quando `sys.platform == "win32"`, carregue o pythonnet e as DLLs do WebView2 que vêm com o pywebview.
- A carga tem de ser a mesma que a janela faz: as mesmas DLLs, pelo mesmo caminho. Se falhar, o `--check` sai com código diferente de zero e uma mensagem na saída de erros.
- Leia antes a documentação do pythonnet 3 e o código de `webview/platforms/winforms.py` da versão instalada (T-001, T-009). Não suponha nomes de função.
- O `--check` continua sem abrir janela e sem iniciar servidor.
- Fora do Windows, nada muda.

### 3. O teste de fumaça imita o arquivo baixado

No job do Windows, antes do passo `--check`:

- Grave em **todos** os arquivos de `dist/RSL.app` o fluxo `Zone.Identifier` com:

  ```
  [ZoneTransfer]
  ZoneId=3
  ```

  Pode ser com `Set-Content -Stream Zone.Identifier`.
- Rode o `--check`, que tem de passar.
- **Controle negativo**, para provar que o teste pega o defeito:
  - renomeie temporariamente o `.config`;
  - rode o `--check` e exija código diferente de zero;
  - devolva o nome original.
- Remova as marcas antes de compactar o zip. Assim o zip publicado fica igual ao de antes, mais o `.config`.

### 4. Documentos

- No `README.md`, onde explica o download para Windows, uma linha para quem ainda tem a 2.0.0 sem janela: clique com o botão direito no zip, Propriedades, marque **Desbloquear** e extraia de novo. Na 2.1 isso deixa de ser preciso.
- No `docs/hospedagem.md`, subseção "Distribuir o app aos pesquisadores", uma linha para quem distribui o zip nas máquinas da instituição: a partir da 2.1 o zip funciona extraído pelo Explorer; na 2.0.0, desbloqueie antes.

## O que não faz

- Não troca o pywebview, o pythonnet nem o .NET Framework pelo .NET Core.
- Não muda o NiceGUI nem o jeito de abrir a janela. O processo filho que trava em silêncio é do NiceGUI: fica registrado como limite conhecido, não se conserta aqui.
- Não assina o executável. Assinar custa dinheiro e é decisão do Erick; também não resolveria esta marca.
- Não mexe no Linux nem no `--mcp`, que não carrega o .NET.
- Não republica a 2.0.0. A 2.1.0 saiu antes desta correção, a pedido do Erick, com o aviso de desbloquear o zip; a correção sai na 2.1.1.

## Para instituições

Quem distribui o zip nos laboratórios (pasta de rede, Intune, cópia manual) recebe arquivos com a marca da internet, igual a quem baixa. Com a 2.1, a janela abre sem passo extra. A entrega atualiza a subseção "Distribuir o app aos pesquisadores" do `docs/hospedagem.md` (item 4).

## Pronto quando

- [x] `packaging/RSL.app.exe.config` existe e o workflow o copia para `dist/RSL.app/`
- [x] No Windows, o `--check` carrega o pythonnet e as DLLs do WebView2, com teste em `tests_desktop` que não exige Windows para passar fora dele
- [x] O workflow marca os arquivos como baixados, o `--check` passa, o controle negativo falha como esperado, e as marcas saem antes do zip
- [x] README e guia com a linha do desbloqueio para a 2.0.0
- [ ] O workflow roda verde num `workflow_dispatch` da branch
- [x] Os gates passam: `tests_desktop`, a suíte principal em 3.10 e 3.14, e o ruff

## Vem de

D-024, D-025, FR-16; teste do Erick em 2026-11-16.

## Antes de começar

- Leia `.github/workflows/desktop.yml`, `src/rslapp/desktop/app.py` e `tests_desktop/`.
- Um commit por item.

## Resultado da entrega

Código pelo Gemini (`agy`), um commit por item, mensagens em português (FR-16, D-025):

- `ddbf4f7` **Item 1 (config ao lado do `.exe`):** arquivo `packaging/RSL.app.exe.config` com `<loadFromRemoteSources enabled="true"/>`; no workflow `.github/workflows/desktop.yml`, passo de empacotamento copia o `.config` para `dist/RSL.app/RSL.app.exe.config`.
- `2616b9c` **Item 2 (`--check` carrega .NET no Windows):** `_ensure_windows_dotnet()` em `src/rslapp/desktop/app.py` carrega pythonnet, `winforms`, e as DLLs `Microsoft.Web.WebView2.Core.dll` e `Microsoft.Web.WebView2.WinForms.dll` via `interop_dll_path`; se falhar, imprime no stderr e sai com código != 0 (`SystemExit(1)`); testes em `tests_desktop/test_app.py` cobrem sucesso no Windows nativo, ausência de chamada fora do Windows, falha com código != 0 e mensagem no stderr; teste de integração em `tests/desktop/test_check.py` atualizado.
- `85868b6` **Item 3 (teste de fumaça imita arquivo baixado):** job do Windows no CI grava fluxo `Zone.Identifier` (`ZoneId=3`) em todos os arquivos de `dist/RSL.app`; executa `--check`; executa controle negativo renomeando temporariamente o `.config` para `.bak` e exigindo código diferente de zero; remove as marcas com `Unblock-File` antes de compactar o zip.
- `c5fbc92` **Item 4 (documentação):** linha no `README.md` orientando o desbloqueio do zip nas Propriedades para quem ainda tem a 2.0.0; linha em `docs/hospedagem.md` ("Distribuir o app aos pesquisadores") informando que a partir da 2.1 o zip funciona extraído diretamente pelo Explorer e na 2.0.0 exige desbloqueio.
- **Gates (2026-11-16):**
  - `tests_desktop` (Python 3.12): 25 passaram em 6.28s;
  - Suíte principal (Python 3.10): 707 passaram e 1 pulado em 71.62s;
  - `ruff`: all checks passed.
- **Revisão do Claude (2026-11-16):**
  - `_ensure_windows_dotnet()` carrega o .NET na mesma ordem e com o mesmo recuo para `coreclr` de `webview/platforms/winforms.py`.
  - Na primeira rodada do workflow, o controle negativo quebrou no próprio passo: o `Rename-Item` recebia um caminho no `-NewName`. O Gemini corrigiu em `990dfc5`.
  - A segunda rodada (run 43933801338) ficou verde: `--check` com os arquivos marcados, o controle negativo falhando sem o `.config` como devia, e o `--mcp`.
  - **Prova de ponta a ponta:** o Claude baixou o zip dessa rodada, marcou todos os arquivos com `ZoneId=3` e abriu o `RSL.app.exe`, e a janela abriu.
  - **Limite conhecido:** o `.exe` sem console não mostra a mensagem do erro no log do CI. A prova é que a única diferença entre a rodada que passa e a que falha é o `.config`.

## Como testar

**Onde olhar primeiro:**

1. O controle negativo no workflow. Se ele não falhar sem o `.config`, o teste não prova nada.
2. O `--check` no Windows: a carga das DLLs tem de ser a mesma da janela.

**Para conferir (Erick):**

- Baixe o zip da 2.1.1 pelo navegador, extraia pelo Explorer **sem** desbloquear e abra o `RSL.app.exe`: a janela abre.
