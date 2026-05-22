import flet as ft
import webbrowser
from services.google_auth import get_google_provider, GOOGLE_SCOPES

# Shown in the OAuth callback tab after the user signs in.
# Auto-closes after 2 seconds so the user doesn't have to close it manually.
_COMPLETE_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Signed in to E-stream'o</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #111;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }
    .card {
      text-align: center;
      padding: 40px;
    }
    .icon { font-size: 56px; margin-bottom: 16px; }
    h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
    p  { color: #aaa; font-size: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✓</div>
    <h1>Signed in!</h1>
    <p>You can close this tab and return to E-stream'o.</p>
  </div>
  <script>
    // Attempt to auto-close this tab after a short delay.
    setTimeout(function() { window.close(); }, 1800);
  </script>
</body>
</html>
"""


def login_view(page: ft.Page) -> ft.View:
    """The initial landing screen (Route: "/")"""

    provider = get_google_provider()
    current_theme = page.session.store.get("theme_color") or ft.Colors.RED_700

    async def on_login_click(e):
        # Flet's default behavior in web mode is to use UrlLauncher().open_window(url)
        # which opens a Javascript popup window. This is required so that the completion
        # page's `window.close()` script actually works (browsers block window.close() 
        # on regular tabs).
        await page.login(
            provider,
            scope=GOOGLE_SCOPES,
            complete_page_html=_COMPLETE_PAGE_HTML,
        )

    # Check if Google incorrectly redirected back to the root URL (due to user misconfiguration)
    if "state=" in page.route and "code=" in page.route:
        return ft.View(
            route="/",
            bgcolor="#111111",
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=80, color="red"),
                ft.Text("Google Console Misconfigured!", size=24, weight=ft.FontWeight.BOLD, color="red"),
                ft.Text(
                    "You must update your 'Authorised redirect URIs' in Google Cloud Console.\n"
                    "It is currently pointing to the app root, but it MUST point exactly to:\n\n"
                    "http://localhost:8550/oauth_callback",
                    text_align=ft.TextAlign.CENTER,
                    color="white"
                ),
            ],
        )

    return ft.View(
        route="/",
        bgcolor="#111111",
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.Icons.CLOUD_DONE, size=80, color=current_theme),
            ft.Text("E-stream'o", size=32, weight=ft.FontWeight.W_900, color="white"),
            ft.Text("Access your Drive media beautifully.", size=14, color="#AAAAAA"),
            ft.Container(height=30),  # Spacer
            ft.ElevatedButton(
                "Sign in with Google",
                icon=ft.Icons.LOGIN,
                color="white",
                bgcolor=current_theme,
                on_click=on_login_click,
            ),
        ],
    )