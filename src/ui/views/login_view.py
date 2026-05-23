import flet as ft
import webbrowser
from services.google_auth import get_google_provider, GOOGLE_SCOPES

# Shown in the OAuth callback tab after the user signs in.
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
    .card { text-align: center; padding: 40px; }
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
        await page.login(
            provider,
            scope=GOOGLE_SCOPES,
            complete_page_html=_COMPLETE_PAGE_HTML,
        )

    # Google misconfiguration error screen
    if "state=" in page.route and "code=" in page.route:
        return ft.View(
            route="/",
            bgcolor="#0A0A0A",
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
                    color="white",
                ),
            ],
        )

    # ── Background: deep radial glow behind the card ─────────────────────────
    bg_glow = ft.Container(
        expand=True,
        gradient=ft.RadialGradient(
            center=ft.Alignment(0, -0.3),
            radius=1.1,
            colors=["#1A0A1E", "#0A0A0A"],
        ),
    )

    # ── Google "G" logo built from text (no external assets needed) ──────────
    google_g = ft.Container(
        width=22,
        height=22,
        bgcolor="white",
        border_radius=11,
        alignment=ft.Alignment(0, 0),
        content=ft.Text(
            "G",
            size=14,
            weight=ft.FontWeight.BOLD,
            color="#DB4437",
        ),
    )

    # ── Sign-in button state (hover glow) ────────────────────────────────────
    sign_in_container = ft.Container(
        border_radius=30,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=0,
            color="#00000000",
            offset=ft.Offset(0, 4),
        ),
        content=ft.ElevatedButton(
            content=ft.Row(
                controls=[
                    google_g,
                    ft.Container(width=10),
                    ft.Text(
                        "Sign in with Google",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color="white",
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: current_theme,
                    ft.ControlState.HOVERED: ft.Colors.with_opacity(0.85, current_theme),
                },
                shape=ft.RoundedRectangleBorder(radius=30),
                padding=ft.Padding(left=32, top=18, right=36, bottom=18),
                elevation=8,
                shadow_color=ft.Colors.with_opacity(0.4, current_theme),
                overlay_color=ft.Colors.with_opacity(0.08, "white"),
            ),
            on_click=on_login_click,
        ),
    )

    def on_btn_hover(e):
        if e.data == "true":
            sign_in_container.shadow = ft.BoxShadow(
                spread_radius=2,
                blur_radius=28,
                color=ft.Colors.with_opacity(0.55, current_theme),
                offset=ft.Offset(0, 4),
            )
        else:
            sign_in_container.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=0,
                color="#00000000",
                offset=ft.Offset(0, 4),
            )
        sign_in_container.update()

    sign_in_container.content.on_hover = on_btn_hover

    # ── Feature pills ─────────────────────────────────────────────────────────
    def feature_pill(icon, label):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=14, color=ft.Colors.with_opacity(0.7, current_theme)),
                    ft.Text(label, size=12, color="#888888"),
                ],
                spacing=6,
                tight=True,
            ),
            bgcolor="#1A1A1A",
            border_radius=20,
            padding=ft.Padding(left=12, top=6, right=14, bottom=6),
        )

    # ── Glassmorphism card ────────────────────────────────────────────────────
    card = ft.Container(
        width=460,
        padding=ft.Padding(left=52, top=56, right=52, bottom=48),
        border_radius=28,
        bgcolor=ft.Colors.with_opacity(0.06, "white"),
        border=ft.Border(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.12, "white")),
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.04, "white")),
            left=ft.BorderSide(1, ft.Colors.with_opacity(0.10, "white")),
            right=ft.BorderSide(1, ft.Colors.with_opacity(0.04, "white")),
        ),
        shadow=ft.BoxShadow(
            spread_radius=-4,
            blur_radius=60,
            color=ft.Colors.with_opacity(0.6, "#000000"),
            offset=ft.Offset(0, 24),
        ),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            tight=True,
            controls=[
                # App icon with glow ring
                ft.Stack(
                    width=96,
                    height=96,
                    controls=[
                        ft.Container(
                            width=96,
                            height=96,
                            border_radius=48,
                            gradient=ft.RadialGradient(
                                center=ft.Alignment(0, 0),
                                radius=0.9,
                                colors=[
                                    ft.Colors.with_opacity(0.35, current_theme),
                                    ft.Colors.with_opacity(0.0, current_theme),
                                ],
                            ),
                        ),
                        ft.Container(
                            width=96,
                            height=96,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(
                                ft.Icons.CLOUD_DONE_ROUNDED,
                                size=52,
                                color=current_theme,
                            ),
                        ),
                    ],
                ),

                ft.Container(height=24),

                # App name
                ft.Text(
                    "E-stream'o",
                    size=40,
                    weight=ft.FontWeight.W_900,
                    color="white",
                    text_align=ft.TextAlign.CENTER,
                ),

                ft.Container(height=8),

                # Tagline
                ft.Text(
                    "Your personal high-performance streaming server.",
                    size=14,
                    color="#888888",
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_400,
                ),

                ft.Container(height=32),

                # Feature pills row
                ft.Row(
                    controls=[
                        feature_pill(ft.Icons.MOVIE_FILTER_ROUNDED, "Videos"),
                        feature_pill(ft.Icons.PHOTO_LIBRARY_ROUNDED, "Photos"),
                        feature_pill(ft.Icons.MUSIC_NOTE_ROUNDED, "Music"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),

                ft.Container(height=36),

                # Sign-in button
                sign_in_container,

                ft.Container(height=24),

                # Privacy note
                ft.Text(
                    "We only read your Drive files. Nothing is shared.",
                    size=11,
                    color="#555555",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )

    # ── Decorative floating blobs behind the card ─────────────────────────────
    blob_tl = ft.Container(
        width=320,
        height=320,
        border_radius=160,
        left=-80,
        top=-80,
        gradient=ft.RadialGradient(
            center=ft.Alignment(0, 0),
            radius=0.8,
            colors=[
                ft.Colors.with_opacity(0.12, current_theme),
                ft.Colors.with_opacity(0.0, current_theme),
            ],
        ),
    )
    blob_br = ft.Container(
        width=280,
        height=280,
        border_radius=140,
        right=-60,
        bottom=-60,
        gradient=ft.RadialGradient(
            center=ft.Alignment(0, 0),
            radius=0.8,
            colors=[
                ft.Colors.with_opacity(0.10, "#7C3AED"),
                ft.Colors.with_opacity(0.0, "#7C3AED"),
            ],
        ),
    )

    login_stack = ft.Stack(
        expand=True,
        controls=[
            # Layer 0: gradient background
            bg_glow,
            # Layer 1: decorative blobs
            blob_tl,
            blob_br,
            # Layer 2: centered card
            ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=card,
            ),
            # Layer 3: version watermark bottom-right
            ft.Container(
                right=20,
                bottom=16,
                content=ft.Text(
                    "E-stream'o  ·  v1.0",
                    size=11,
                    color="#333333",
                ),
            ),
        ],
    )

    return ft.View(
        route="/",
        bgcolor="#0A0A0A",
        padding=0,
        controls=[login_stack],
    )