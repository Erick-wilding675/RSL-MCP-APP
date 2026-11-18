# Ferramentas MCP e Assistente Desktop de Descritores DeCS/MeSH (v2.10)

**Fase:** 21 · Versão 2.10 · **Situação:** pronta

## O que faz

1. **Servidor MCP (`src/rslapp/server.py`):**
   - Ferramenta MCP `lookup_descriptors(query: str, lang: str = "pt", max_results: int = 10)`:
     - Permite que a IA do pesquisador consulte descritores controlados e obtenha a equivalência oficial trilíngue e sinônimos.
   - Ferramenta MCP `build_multilingual_search_query(descriptors: list[str], operator: str = "OR")`:
     - Retorna as strings booleanas montadas em português, inglês e espanhol.
   - Totalizando 29 ferramentas especializadas no servidor MCP stdio e HTTP multiusuário.

2. **Interface Desktop (`src/rslapp/desktop/`):**
   - Método `lookup_descriptors` e `build_multilingual_query` no serviço `DesktopService`.
   - Assistente "Descritores DeCS/MeSH (PT/EN/ES)" na tela Buscar (`/`) e na tela Protocolos (`/protocolo/...`):
     - Campo de busca rápida com autocompletar;
     - Exibição de chips de sinônimos em PT, EN e ES;
     - Botão "Inserir na Busca" que copia a string booleana em inglês ou português diretamente para a caixa de busca.

## O que não faz

- Não força o uso exclusivo de vocabulário controlado (o pesquisador pode mesclar com termos livres).

## Decisões desta spec

- **Interface Sóbria Acadêmica (D-031):** Cores sutis (Deep Pine `#1B4D3E`, cinzas suaves `#4B5563`, caixas limpas) em harmonia com o tema light conservador.

## Para instituições (D-029)

Facilita oficinas de capacitação em bibliotecas universitárias sobre formulação de estratégias de busca bibliográfica.

## Pronto quando

- [x] Ferramentas MCP registradas no servidor stdio e HTTP.
- [x] Assistente integrado na interface desktop.
- [x] Testes passando 100%.
- [x] Linter ruff limpo.
