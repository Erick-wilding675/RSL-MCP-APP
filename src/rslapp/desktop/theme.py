"""Tema visual do app desktop: cores, tipografia, modo escuro e CSS comum (D-031)."""

from __future__ import annotations

from nicegui import ui

from rslapp.desktop.settings import get_theme

# D-031: CSS comum aplicado por ui.add_css num só lugar
COMMON_CSS: str = """
/* D-031: Letra com pilha do sistema e tamanho base de 15px */
body, .nicegui-content {
  font-family: "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, "Ubuntu", "Cantarell", "Noto Sans", sans-serif !important;
  font-size: 15px !important;
}

/* D-031: Títulos de página com 24px e peso 600 */
.page-title {
  font-size: 24px !important;
  font-weight: 600 !important;
  line-height: 1.3 !important;
}

/* D-031: Área de conteúdo centralizada com largura máxima de 1100px e margem de 24px */
.nicegui-content {
  max-width: 1100px !important;
  margin: 0 auto !important;
  padding: 24px !important;
}

/* D-031: Fundo da página e variáveis de cores no tema claro */
body:not(.body--dark) {
  background-color: #F6F7FB !important;
}

/* D-031: Fundo da página e variáveis de cores Quasar no tema escuro */
body.body--dark {
  background-color: #0B1020 !important;
  --q-primary: #818CF8 !important;
  --q-secondary: #2DD4BF !important;
  --q-accent: #5EEAD4 !important;
  --q-positive: #4ADE80 !important;
  --q-negative: #F87171 !important;
  --q-warning: #FBBF24 !important;
  --q-info: #60A5FA !important;
}

/* D-031: Cartões com cantos de 12px, borda fina (1px) e sombra leve */
.q-card {
  border-radius: 12px !important;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05) !important;
  transition: background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease !important;
}
body:not(.body--dark) .q-card {
  background-color: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
}
body.body--dark .q-card {
  background-color: #121933 !important;
  border: 1px solid #1F2A4D !important;
}

/* D-031: Foco visível (contorno de 2px na cor primary) em todo elemento que recebe teclado */
:focus-visible {
  outline: 2px solid var(--q-primary) !important;
  outline-offset: 2px !important;
}

/* D-031: Transições curtas (150 ms) em elementos interativos */
button, a, input, textarea, select, .q-btn, .q-field {
  transition: color 150ms ease, background-color 150ms ease, border-color 150ms ease, outline 150ms ease, box-shadow 150ms ease !important;
}

/* D-031: Estilos da barra lateral drawer */
body:not(.body--dark) .q-drawer {
  background-color: #FFFFFF !important;
  border-right: 1px solid #E5E7EB !important;
}
body.body--dark .q-drawer {
  background-color: #0D1429 !important;
  border-right: 1px solid #1F2A4D !important;
}

/* Estilos de itens de navegação ativo e inativo */
.nav-item-active {
  background-color: rgba(79, 70, 229, 0.12) !important;
  color: var(--q-primary) !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
}
body.body--dark .nav-item-active {
  background-color: rgba(129, 140, 248, 0.18) !important;
  color: var(--q-primary) !important;
}
.nav-item-inactive {
  border-radius: 8px !important;
  color: inherit !important;
  transition: background-color 150ms ease !important;
}
.nav-item-inactive:hover {
  background-color: rgba(0, 0, 0, 0.04) !important;
}
body.body--dark .nav-item-inactive:hover {
  background-color: rgba(255, 255, 255, 0.05) !important;
}

/* Oculta subtítulo e versão quando o drawer recolhe em modo mini */
.q-drawer--mini .drawer-full-only {
  display: none !important;
}
.q-drawer--mini .drawer-footer-row {
  justify-content: center !important;
}

/* D-031: Classes semânticas próprias para suporte confiável ao tema claro e escuro */
.rsl-title {
  color: #111827 !important;
}
body.body--dark .rsl-title {
  color: #F3F4F6 !important;
}

/* Herança da cor rsl-title para checkboxes dentro de cartões de fonte */
.rsl-title .q-checkbox__label,
.rsl-surface-2 .q-checkbox__label {
  color: inherit !important;
}

.rsl-muted {
  color: #6B7280 !important;
}
body.body--dark .rsl-muted {
  color: #9CA3AF !important;
}

.rsl-surface-2 {
  background-color: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
  color: #111827 !important;
}
body.body--dark .rsl-surface-2 {
  background-color: #18213F !important;
  border: 1px solid #2A3766 !important;
  color: #F3F4F6 !important;
}

.rsl-surface-disabled {
  background-color: #F3F4F6 !important;
  border: 1px solid #E5E7EB !important;
  opacity: 0.6 !important;
}
body.body--dark .rsl-surface-disabled {
  background-color: #141B33 !important;
  border: 1px solid #2A3766 !important;
  opacity: 0.6 !important;
}

.rsl-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  background-color: #F3F4F6 !important;
  color: #1F2937 !important;
  border: 1px solid #E5E7EB !important;
}
body.body--dark .rsl-code {
  background-color: #0F1630 !important;
  color: #E5E7EB !important;
  border: 1px solid #2A3766 !important;
}

/* D-031: Cartão de progresso e divisor do rodapé do drawer */
.progress-card {
  background-color: rgba(79, 70, 229, 0.06) !important;
  border: 1px solid rgba(79, 70, 229, 0.25) !important;
}
body.body--dark .progress-card {
  background-color: rgba(129, 140, 248, 0.12) !important;
  border: 1px solid rgba(129, 140, 248, 0.25) !important;
}

/* D-031: Tabela com cabeçalho fixo e linhas alternadas suaves */
.sticky-header-table thead tr th {
  position: sticky !important;
  z-index: 1 !important;
  top: 0 !important;
}
body:not(.body--dark) .sticky-header-table thead tr th {
  background-color: #F9FAFB !important;
}
body.body--dark .sticky-header-table thead tr th {
  background-color: #121933 !important;
}

body:not(.body--dark) .q-table tbody tr:nth-child(even) {
  background-color: rgba(0, 0, 0, 0.02) !important;
}
body.body--dark .q-table tbody tr:nth-child(even) {
  background-color: rgba(255, 255, 255, 0.02) !important;
}

.drawer-footer {
  border-top: 1px solid #E5E7EB !important;
}
body.body--dark .drawer-footer {
  border-top: 1px solid #1F2A4D !important;
}

/* D-031: Caixa de informação info compatível com tema claro e escuro */
.rsl-info-box {
  background-color: #EFF6FF !important;
  border: 1px solid #BFDBFE !important;
  color: #1E40AF !important;
}
body.body--dark .rsl-info-box {
  background-color: #0B1936 !important;
  border: 1px solid #1D4ED8 !important;
  color: #93C5FD !important;
}

/* D-031: Caixa de aviso warning compatível com tema claro e escuro */
.rsl-warning-box {
  background-color: #FFFBEB !important;
  border: 1px solid #FCD34D !important;
  color: #78350F !important;
}
body.body--dark .rsl-warning-box {
  background-color: #2D2005 !important;
  border: 1px solid #78350F !important;
  color: #FDE68A !important;
}

/* D-031: Barra de salvar fixa no pé da página */
.save-bar {
  position: sticky !important;
  bottom: 16px !important;
  z-index: 30 !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08) !important;
  transition: background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease !important;
}
.save-bar-clean {
  background-color: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
}
body.body--dark .save-bar-clean {
  background-color: #121933 !important;
  border: 1px solid #1F2A4D !important;
}
.save-bar-dirty {
  background-color: #F0FDF4 !important;
  border: 1px solid #86EFAC !important;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2) !important;
}
body.body--dark .save-bar-dirty {
  background-color: #062817 !important;
  border: 1px solid #15803D !important;
  box-shadow: 0 4px 16px rgba(34, 197, 94, 0.2) !important;
}
"""


# D-031, FR-16: Aplica cores, modo escuro, tipografia e CSS comum a uma página do app desktop
def apply_theme() -> ui.dark_mode:
    """Configura o tema da página: cores Quasar, DarkMode conforme desktop.json, fontes e CSS global."""
    # 1. Cores da tabela da spec
    ui.colors(
        primary="#4F46E5",
        secondary="#0F766E",
        accent="#0D9488",
        positive="#15803D",
        negative="#B91C1C",
        warning="#B45309",
        info="#1D4ED8",
        dark_page="#0B1020",
        dark="#121933",
    )

    # 2. Modo escuro conforme desktop.json (auto=None, light=False, dark=True)
    pref = get_theme()
    dm_value: bool | None
    if pref == "light":
        dm_value = False
    elif pref == "dark":
        dm_value = True
    else:
        dm_value = None

    dm = ui.dark_mode(dm_value)
    if hasattr(ui.context, "client") and ui.context.client is not None:
        ui.context.client._rsl_dark_mode = dm

    # 3. CSS comum (fontes, cartões, foco visível, transições de 150ms)
    ui.add_css(COMMON_CSS)

    return dm
