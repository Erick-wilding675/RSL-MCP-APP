"""Tema visual do app desktop: cores, tipografia, modo escuro e CSS comum (D-031)."""

from __future__ import annotations

from nicegui import ui

from rslapp.desktop.settings import get_theme

# D-031: CSS comum aplicado por ui.add_css num só lugar
COMMON_CSS: str = """
/* D-031: Letra com pilha acadêmica limpa e tamanho base de 14.5px */
body, .nicegui-content {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
  font-size: 14.5px !important;
}

/* D-031: Títulos de página com 22px, peso 700 e hierarquia acadêmica sóbria */
.page-title {
  font-size: 22px !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
  letter-spacing: -0.01em !important;
}

/* D-031: Área de conteúdo centralizada com largura máxima de 1100px e margem de 24px */
.nicegui-content {
  max-width: 1100px !important;
  margin: 0 auto !important;
  padding: 24px !important;
}

/* D-031: Fundo da página e variáveis de cores no tema claro (estilo papel de pesquisa com detalhes verdes discretos) */
body:not(.body--dark) {
  background-color: #F8FAF9 !important;
}

/* D-031: Fundo da página e variáveis de cores Quasar no tema escuro acadêmico */
body.body--dark {
  background-color: #0F172A !important;
  --q-primary: #34D399 !important;
  --q-secondary: #94A3B8 !important;
  --q-accent: #10B981 !important;
  --q-positive: #22C55E !important;
  --q-negative: #EF4444 !important;
  --q-warning: #F59E0B !important;
  --q-info: #38BDF8 !important;
}

/* D-031: Cartões com cantos de 6px (sóbrio/estruturado), borda nítida e sombra muito leve */
.q-card {
  border-radius: 6px !important;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
  transition: background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease !important;
}
body:not(.body--dark) .q-card {
  background-color: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
}
body.body--dark .q-card {
  background-color: #1E293B !important;
  border: 1px solid #334155 !important;
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
  background-color: #1E293B !important;
  border-right: 1px solid #334155 !important;
}

/* Estilos de itens de navegação ativo e inativo com acento verde discreto */
.nav-item-active {
  background-color: rgba(27, 77, 62, 0.08) !important;
  color: #1B4D3E !important;
  font-weight: 600 !important;
  border-radius: 4px !important;
  border-left: 3px solid #1B4D3E !important;
}
body.body--dark .nav-item-active {
  background-color: rgba(52, 211, 153, 0.12) !important;
  color: #34D399 !important;
  border-left: 3px solid #34D399 !important;
}
.nav-item-inactive {
  border-radius: 4px !important;
  border-left: 3px solid transparent !important;
  color: #374151 !important;
  transition: background-color 150ms ease !important;
}
.nav-item-inactive:hover {
  background-color: rgba(27, 77, 62, 0.04) !important;
}
body.body--dark .nav-item-inactive:hover {
  background-color: rgba(255, 255, 255, 0.04) !important;
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
  color: #F8FAFC !important;
}

/* Herança da cor rsl-title para checkboxes dentro de cartões de fonte */
.rsl-title .q-checkbox__label,
.rsl-surface-2 .q-checkbox__label {
  color: inherit !important;
}

.rsl-muted {
  color: #4B5563 !important;
}
body.body--dark .rsl-muted {
  color: #94A3B8 !important;
}

.rsl-surface-2 {
  background-color: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
  color: #111827 !important;
}
body.body--dark .rsl-surface-2 {
  background-color: #1E293B !important;
  border: 1px solid #334155 !important;
  color: #F8FAFC !important;
}

.rsl-surface-disabled {
  background-color: #F3F4F6 !important;
  border: 1px solid #E5E7EB !important;
  opacity: 0.65 !important;
}
body.body--dark .rsl-surface-disabled {
  background-color: #0F172A !important;
  border: 1px solid #334155 !important;
  opacity: 0.65 !important;
}

.rsl-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  background-color: #F9FAFB !important;
  color: #111827 !important;
  border: 1px solid #E5E7EB !important;
}
body.body--dark .rsl-code {
  background-color: #0F172A !important;
  color: #E2E8F0 !important;
  border: 1px solid #334155 !important;
}

/* D-031: Cartão de progresso e divisor do rodapé do drawer */
.progress-card {
  background-color: rgba(27, 77, 62, 0.04) !important;
  border: 1px solid rgba(27, 77, 62, 0.2) !important;
  border-radius: 6px !important;
}
body.body--dark .progress-card {
  background-color: rgba(52, 211, 153, 0.1) !important;
  border: 1px solid rgba(52, 211, 153, 0.2) !important;
}

/* D-031: Tabela com cabeçalho fixo e linhas alternadas suaves */
.sticky-header-table thead tr th {
  position: sticky !important;
  z-index: 1 !important;
  top: 0 !important;
}
body:not(.body--dark) .sticky-header-table thead tr th {
  background-color: #F9FAFB !important;
  border-bottom: 2px solid #E5E7EB !important;
}
body.body--dark .sticky-header-table thead tr th {
  background-color: #1E293B !important;
  border-bottom: 2px solid #334155 !important;
}

body:not(.body--dark) .q-table tbody tr:nth-child(even) {
  background-color: rgba(0, 0, 0, 0.015) !important;
}
body.body--dark .q-table tbody tr:nth-child(even) {
  background-color: rgba(255, 255, 255, 0.015) !important;
}

.drawer-footer {
  border-top: 1px solid #E5E7EB !important;
}
body.body--dark .drawer-footer {
  border-top: 1px solid #334155 !important;
}

/* D-031: Caixa de informação info compatível com tema claro e escuro */
.rsl-info-box {
  background-color: #F0FDF4 !important;
  border: 1px solid #BBF7D0 !important;
  color: #166534 !important;
  border-radius: 6px !important;
}
body.body--dark .rsl-info-box {
  background-color: #0F172A !important;
  border: 1px solid #1D4ED8 !important;
  color: #93C5FD !important;
}

/* D-031: Caixa de aviso warning compatível com tema claro e escuro */
.rsl-warning-box {
  background-color: #FFFBEB !important;
  border: 1px solid #FCD34D !important;
  color: #78350F !important;
  border-radius: 6px !important;
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
  border-radius: 6px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
  transition: background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease !important;
}
.save-bar-clean {
  background-color: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
}
body.body--dark .save-bar-clean {
  background-color: #1E293B !important;
  border: 1px solid #334155 !important;
}
.save-bar-dirty {
  background-color: #F0FDF4 !important;
  border: 1px solid #86EFAC !important;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15) !important;
}
body.body--dark .save-bar-dirty {
  background-color: #062817 !important;
  border: 1px solid #15803D !important;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.15) !important;
}
"""


# D-031, FR-16: Aplica cores, modo escuro, tipografia e CSS comum a uma página do app desktop
def apply_theme() -> ui.dark_mode:
    """Configura o tema da página: cores Quasar, DarkMode conforme desktop.json, fontes e CSS global."""
    # 1. Cores acadêmicas sóbrias com detalhes verdes discretos (Deep Pine, Ardósia e tons clássicos)
    ui.colors(
        primary="#1B4D3E",
        secondary="#4B5563",
        accent="#2D6A4F",
        positive="#15803D",
        negative="#991B1B",
        warning="#92400E",
        info="#155E75",
        dark_page="#0F172A",
        dark="#1E293B",
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
