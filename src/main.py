import flet as ft
from dotenv import load_dotenv
import subprocess
import sys

# Auto-install mutagen for ID3 Parsing
try:
    import mutagen
except ImportError:
    print("Mutagen not found. Installing automatically for high-performance ID3 caching...")
    subprocess.run([sys.executable, "-m", "pip", "install", "mutagen"], check=True)
    import mutagen

# Load variables BEFORE importing the router
load_dotenv(override=True)

from ui.router import AppRouter
from services.google_auth import handle_login_result

async def main(page: ft.Page):
    page.title = "E-stream'o"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#111111"

    # Load persistent preferences
    import json
    import os
    prefs_path = os.path.join(os.getcwd(), ".prefs.json")
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r") as f:
                prefs = json.load(f)
                for k, v in prefs.items():
                    page.session.store.set(k, v)
        except Exception:
            pass

    # Load custom theme color if the user saved one in settings
    saved_theme = page.session.store.get("theme_color") or ft.Colors.RED_700
    page.theme = ft.Theme(color_scheme_seed=saved_theme)

    app_router = AppRouter(page)
    
    # --- GLOBAL AUDIO ENGINE INJECTION ---
    try:
        import flet_video as fv
    except ImportError:
        try:
            import flet.video as fv
        except ImportError:
            fv = None

    if fv:
        global_audio_engine = fv.Video(width=50, height=50, opacity=0.01, autoplay=True, visible=True)
        page.overlay.append(global_audio_engine)
        from services.audio_service import GlobalAudioState
        page.session.store.set("audio_state", GlobalAudioState(page, global_audio_engine))

    page.on_route_change = app_router.route_change
    page.on_view_pop = app_router.view_pop

    # on_login fires on the SAME page session in web mode.
    # Must be async so we can await push_route() properly.
    async def on_login(e: ft.LoginEvent):
        await handle_login_result(e, page)

    page.on_login = on_login
    
    # Initialize the app routing securely
    # Since main is async, we can directly await the route_change handler to build the views 
    # sequentially before the app even displays, avoiding all race conditions and empty screens!
    await app_router.route_change(None)


if __name__ == "__main__":
    # If videos don't play in WEB_BROWSER mode (due to CORS), you can change this back to:
    # view=ft.AppView.FLET_APP
    # The app will now remember your login using the secure local .token.json file!
    ft.run(
        main,
        view=ft.AppView.FLET_APP,
        # view=ft.AppView.WEB_BROWSER,
        port=8550,
        assets_dir="../assets"
    )