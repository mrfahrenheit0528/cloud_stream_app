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

    async def route_change(self, e: ft.RouteChangeEvent):
        """Fires whenever push_route() is called. Must be async to use await push_route()."""
        self.page.session.store.set("keyboard_handler", None)
        self.page.views.clear()

        # 1. Fast-path Token Bypass for FLET_APP Native Desktop Mode
        token_cache_path = os.path.join(os.getcwd(), ".token.json")
        if not self.page.session.store.contains_key("drive_access_token"):
            if os.path.exists(token_cache_path):
                import json
                try:
                    with open(token_cache_path, "r") as f:
                        cached_data = json.load(f)
                        token = cached_data.get("access_token")
                        given_name = cached_data.get("given_name", "User")
                        if token:
                            self.page.session.store.set("drive_access_token", token)
                            self.page.session.store.set("user_given_name", given_name)
                except Exception:
                    pass

        is_logged_in = self.page.session.store.contains_key("drive_access_token")

        # Mutate route safely to avoid infinite looping
        if not is_logged_in and self.page.route != "/":
            self.page.route = "/"

        if is_logged_in and self.page.route == "/":
            self.page.route = "/home"

        # 2. Base Layer Logging Logic
        if self.page.route == "/":
            self.page.views.append(login_view(self.page))
        else:
            # If not on login screen, the Home screen is always the base layer
            # We disable it if it's covered by an overlay to prevent focus and click bleeding
            h_view = home_view(self.page)
            if self.page.route != "/home":
                h_view.controls[0].disabled = True
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