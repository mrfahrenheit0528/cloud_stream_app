import flet as ft
import subprocess
import sys

import mutagen
import os
sys.path.insert(0, os.path.abspath("src"))

from ui.router import AppRouter
from services.google_auth import handle_login_result

def main(page: ft.Page):
    try:
        page.title = "E-stream'o"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = "#111111"
        page.update() # Immediately push the black background to unlock the Flutter engine

        # Load persistent preferences securely using cross-platform temp directory
        import json
        import tempfile
        prefs_path = os.path.join(tempfile.gettempdir(), "estreamo_prefs.json")
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
        fv = None # Temporarily disable to check if media_kit is crashing Flutter on Android
        
        if fv:
            global_audio_engine = fv.Video(width=1, height=1, opacity=0.0, autoplay=False, visible=False)
            page.overlay.append(global_audio_engine)
            from services.audio_service import GlobalAudioState
            page.session.store.set("audio_state", GlobalAudioState(page, global_audio_engine))

        page.on_route_change = app_router.route_change
        page.on_view_pop = app_router.view_pop

        import time
        last_key_time = 0

        def on_keyboard(e: ft.KeyboardEvent):
            nonlocal last_key_time
            now = time.time()
            if now - last_key_time < 0.15:
                return
            last_key_time = now
            
            handler = page.session.store.get("keyboard_handler")
            if handler:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    page.run_task(handler, e)
                else:
                    handler(e)
                
        page.on_keyboard_event = on_keyboard

        def on_login(e: ft.LoginEvent):
            page.run_task(handle_login_result, e, page)

        page.on_login = on_login

        # Initialize the app routing securely via background task
        page.run_task(app_router.route_change, None)

    except Exception as ex:
        import traceback
        err_msg = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
        page.views.clear()
        page.views.append(ft.View(
            "/",
            [
                ft.Text("FATAL ERROR IN MAIN:", color="red", weight=ft.FontWeight.BOLD, size=24),
                ft.Text(err_msg, color="white", size=14, selectable=True)
            ],
            bgcolor="black",
            scroll=ft.ScrollMode.AUTO
        ))
        page.update()

if __name__ == "__main__":
    ft.run(main, assets_dir="assets")