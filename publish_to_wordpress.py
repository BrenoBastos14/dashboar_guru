"""
Publica a landing page no WordPress via REST API com template Elementor Canvas.

Como usar:
  1. Gere uma senha de aplicativo no WordPress:
       Painel WP → Usuários → Seu Perfil → Senhas de Aplicativo → Adicionar nova
  2. Preencha as variáveis WP_URL, WP_USER e WP_APP_PASSWORD abaixo.
  3. Execute:
       python publish_to_wordpress.py
  4. O script cria a página como RASCUNHO e exibe o link de prévia.
     Quando estiver satisfeito, mude manualmente para "Publicado" no WP.
"""

import sys
from pathlib import Path
import requests

# ── CONFIGURAÇÃO ────────────────────────────────────────────────────────────
WP_URL        = "https://seusite.com"          # ← substitua pelo seu domínio
WP_USER       = "seu_usuario"                  # ← seu usuário WP
WP_APP_PASSWORD = "xxxx xxxx xxxx xxxx xxxx"   # ← senha de aplicativo gerada no WP

PAGE_TITLE    = "Assista agora o podcast exclusivo da Renata Pocztaruk sobre Inteligência Artificial na Arquitetura"
HTML_FILE     = Path(__file__).parent / "landing_page.html"
PAGE_STATUS   = "draft"   # "draft" ou "publish"
# ─────────────────────────────────────────────────────────────────────────────


def load_html(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def publish_page(wp_url: str, user: str, password: str, title: str, html: str, status: str) -> dict:
    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages"
    payload = {
        "title":    title,
        "content":  html,
        "status":   status,
        "template": "elementor_canvas",  # página em branco — sem header/footer do tema
    }
    response = requests.post(endpoint, auth=(user, password), json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    if not HTML_FILE.exists():
        print(f"[ERRO] Arquivo HTML não encontrado: {HTML_FILE}")
        sys.exit(1)

    print(f"[INFO] Carregando HTML de: {HTML_FILE}")
    html_content = load_html(HTML_FILE)
    print(f"[INFO] HTML carregado — {len(html_content):,} caracteres")

    print(f"[INFO] Publicando no WordPress: {WP_URL}")
    data = publish_page(
        wp_url=WP_URL,
        user=WP_USER,
        password=WP_APP_PASSWORD,
        title=PAGE_TITLE,
        html=html_content,
        status=PAGE_STATUS,
    )

    page_id   = data.get("id")
    page_link = data.get("link")
    edit_link = f"{WP_URL.rstrip('/')}/wp-admin/post.php?post={page_id}&action=edit"

    print("\n✅  Página criada com sucesso!")
    print(f"   ID da página : {page_id}")
    print(f"   Status       : {PAGE_STATUS}")
    print(f"   Preview URL  : {page_link}")
    print(f"   Editar no WP : {edit_link}")
    print("\n   Acesse o link de edição para revisar e mudar para 'Publicado' quando quiser.")


if __name__ == "__main__":
    main()
