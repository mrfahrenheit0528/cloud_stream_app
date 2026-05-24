import flet as ft
import os

# Import the extracted view functions from your views directory
from .views.login_view import login_view
from .views.home_view import home_view
from .views.settings_view import settings_view
from .views.viewer_view import viewer_view

class AppRouter:
    """Handles the navigation state and view stacking for the application."""
    def __init__(self, page: ft.Page):
        self.page = page
        self._cached_home_view = None  # Cache to prevent repeated rebuilds

    async def route_change(self, e: ft.RouteChangeEvent):
        """Fires whenever push_route() is called. Must be async to use await push_route()."""
        try:
            self.page.session.store.set("keyboard_handler", None)
            self.page.views.clear()

            # 1. Fast-path Token Bypass for Native Desktop/Mobile Mode
            import os, tempfile, json
            token_cache_path = os.path.join(tempfile.gettempdir(), "estreamo_token.json")
            prefs_path = os.path.join(tempfile.gettempdir(), "estreamo_prefs.json")

            # Load saved preferences (refresh token, folder, theme) on every cold start
            if os.path.exists(prefs_path) and not self.page.session.store.contains_key("_prefs_loaded"):
                try:
                    with open(prefs_path, "r") as f:
                        prefs = json.load(f)
                    for key in ["onedrive_refresh_token", "onedrive_folder_id", "theme_color", "user_display_name"]:
                        if key in prefs and prefs[key]:
                            self.page.session.store.set(key, prefs[key])
                    self.page.session.store.set("_prefs_loaded", True)
                except Exception:
                    pass

            if not self.page.session.store.contains_key("onedrive_access_token"):
                # Try refreshing using our stored refresh token
                rt = self.page.session.store.get("onedrive_refresh_token")
                if rt:
                    from services.onedrive_auth import refresh_access_token
                    try:
                        res = await refresh_access_token(rt)
                        self.page.session.store.set("onedrive_access_token", res["access_token"])
                        self.page.session.store.set("onedrive_refresh_token", res["refresh_token"])
                        
                        # Persist rolled refresh token
                        prefs_to_save = {}
                        if os.path.exists(prefs_path):
                            try:
                                with open(prefs_path, "r") as f:
                                    prefs_to_save = json.load(f)
                            except Exception: pass
                        prefs_to_save["onedrive_refresh_token"] = res["refresh_token"]
                        with open(prefs_path, "w") as f:
                            json.dump(prefs_to_save, f)
                    except Exception:
                        pass

                # If refresh failed or was not available, fallback to the direct cache
                if not self.page.session.store.contains_key("onedrive_access_token") and os.path.exists(token_cache_path):
                    try:
                        with open(token_cache_path, "r") as f:
                            data = json.load(f)
                            self.page.session.store.set("onedrive_access_token", data["access_token"])
                            self.page.session.store.set("onedrive_refresh_token", data.get("refresh_token", ""))
                            if not self.page.session.store.contains_key("user_display_name"):
                                self.page.session.store.set("user_display_name", data.get("given_name", "User"))
                            self.page.session.store.set("user_picture_url", data.get("picture_url", ""))
                    except Exception:
                        pass

            is_logged_in = self.page.session.store.contains_key("onedrive_access_token")

            # Mutate route safely to avoid infinite looping
            if not is_logged_in and self.page.route != "/":
                self.page.route = "/"

            if is_logged_in and self.page.route == "/":
                self.page.route = "/home"

            # 2. Base Layer Logging Logic
            if self.page.route == "/":
                self._cached_home_view = None  # Clear cache on logout so fresh data loads after re-login
                self.page.views.append(login_view(self.page))
            else:
                # If not on login screen, the Home screen is always the base layer.
                # We CACHE the home view so that navigating to /settings and back
                # does NOT rebuild the home view, which would re-schedule the background
                # data-fetch task and cause the "reload" visual glitch.
                # Exception: if settings were just saved, we invalidate the cache so the
                # home view rebuilds with the updated name, theme, and folder.
                if self.page.session.store.get("home_needs_refresh"):
                    self.page.session.store.set("home_needs_refresh", False)
                    self._cached_home_view = None
                if self._cached_home_view is None:
                    self._cached_home_view = home_view(self.page)
                h_view = self._cached_home_view
                if self.page.route != "/home":
                    h_view.controls[0].disabled = True
                else:
                    h_view.controls[0].disabled = False
                self.page.views.append(h_view)

            # 2. View Stacking (Overlays)
            # We push these views ON TOP of the home view so the back button works naturally
            if self.page.route == "/settings":
                self.page.views.append(settings_view(self.page))

            elif self.page.route.startswith("/viewer/"):
                # Extract the unique file ID from the URL string
                url_parts = self.page.route.split("/")
                file_id = url_parts[-1]
                self.page.views.append(viewer_view(self.page, file_id))

            # Re-register the keyboard handler for the current route.
            # Because the home view is cached (not rebuilt), we store its handler separately
            # and restore it here every time we land on /home.
            if self.page.route == "/home":
                saved_home_kb = self.page.session.store.get("home_keyboard_handler")
                if saved_home_kb:
                    self.page.session.store.set("keyboard_handler", saved_home_kb)

            self.page.update()
        except Exception as ex:
            import traceback
            err_msg = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
            self.page.views.clear()
            self.page.views.append(ft.View(
                "/",
                [
                    ft.Text("FATAL ERROR IN ROUTER:", color="red", weight=ft.FontWeight.BOLD, size=24),
                    ft.Text(err_msg, color="white", size=14, selectable=True)
                ],
                bgcolor="black",
                scroll=ft.ScrollMode.AUTO
            ))
            self.page.update()

    async def view_pop(self, e: ft.ViewPopEvent):
        """Fires when the user clicks the Android back button or Appbar back arrow."""
        # Ensure we always exit fullscreen mode when backing out of the Media Viewer
        if hasattr(self.page, 'window_full_screen'):
            self.page.window_full_screen = False
        elif hasattr(self.page, 'window'):
            self.page.window.full_screen = False
            
        self.page.views.pop()
        top_view = self.page.views[-1]
        
        if top_view.route == "/home":
            audio_state = self.page.session.store.get("audio_state")
            if audio_state:
                self.page.run_task(audio_state.stop_audio)
                    
        await self.page.push_route(top_view.route)