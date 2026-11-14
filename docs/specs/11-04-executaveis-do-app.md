# Executáveis do app para Windows e Linux

**Fase:** 11 · App desktop (2.0) · **Situação:** a fazer

## O que faz

Monta o app desktop como executáveis pelo GitHub Actions (D-025) e documenta o app no README.

### Workflow `.github/workflows/desktop.yml`

- **Quando roda:** a cada tag `v*` e à mão (`workflow_dispatch`).
- **Windows** (`windows-latest`, Python 3.12):
  - instala o projeto com o extra `desktop` e o `pyinstaller`;
  - gera com `nicegui-pack --windowed --onedir --name RSL.app <ponto de entrada>`, com `--onedir` porque abre mais rápido que `--onefile`;
  - compacta a pasta em `RSL.app-<versão>-windows-x64.zip`.
- **Linux** (`ubuntu-22.04`, Python 3.12, a base mais antiga para o executável valer em mais sistemas):
  - instala o extra `desktop` **sem** a janela nativa: `nicegui`, sem o `[native]`, mais as dependências do `rslapp`;
  - o app detecta que não há janela e abre no navegador (11-01);
  - gera com `nicegui-pack --onedir --name RSL.app` e empacota como AppImage com o `appimagetool`, com o arquivo `.desktop` e um ícone simples em SVG ou PNG no repositório;
  - o resultado é `RSL.app-<versão>-linux-x86_64.AppImage`.
- **Destino:**
  - na tag, os dois arquivos vão para a release da tag com `gh release upload`. Se a release ainda não existe quando o job termina, ele a espera ou a cria como rascunho; escolha o caminho mais simples e explique na spec;
  - no `workflow_dispatch`, os dois ficam só como artifacts da execução.
- **Teste de fumaça:** em cada sistema, depois de gerar, roda o executável em modo de verificação por alguns segundos e confere que ele sobe.
  - Crie uma opção `--check` no `main()` que inicia, confirma que importou tudo e sai com código 0, sem abrir a janela.
  - O teste de fumaça chama essa opção.
- **Ações do GitHub:** use versões de ações que rodem em Node 24, como no `docker.yml`.

### README

Uma seção "App desktop", que explica:
- como baixar o `.zip` (Windows) ou o AppImage (Linux) na página de releases;
- que o Windows pode avisar que o app não é assinado, e como seguir;
- que no Linux o app abre no navegador;
- como instalar pelo `pip`: `pip install "rslapp[desktop]"` e `rslapp-desktop`, com Python 3.11+;
- que o app usa a mesma pasta de dados do servidor (as mesmas listas e o mesmo log) e onde ficam as chaves (D-026).

## O que não faz

- Não assina o executável do Windows (custa dinheiro; fica para quando houver motivo).
- Não monta para macOS.
- Não publica nada no PyPI.

## Pronto quando

- [ ] Uma execução manual (`workflow_dispatch`) gera os dois arquivos como artifacts, e o teste de fumaça passa nos dois sistemas
- [ ] Os gates normais passam (a opção `--check` tem teste em `tests/desktop`, sem o NiceGUI)
- [ ] README com a seção "App desktop"

## Vem de

FR-16, D-024, D-025, D-026.

## Antes de começar

- Leia a seção de empacotamento do NiceGUI 4: https://nicegui.io/documentation/section_configuration_deployment.
- Leia a página do `appimagetool`: https://github.com/AppImage/appimagetool.
- Leia o `docker.yml`, para seguir o estilo dos workflows.
- O teste do workflow é feito pelo Claude, que dispara o `workflow_dispatch` depois da integração. Quem escreve o código não precisa disparar.
- Tamanho esperado: cerca de 200 linhas. Um commit.

## Resultado da entrega

(preenche quem entrega)

## Como testar

(preenche quem entrega)
