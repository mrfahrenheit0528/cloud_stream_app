import flet as ft

# Import the extracted view functions from your views directory
from .views.login_view import login_view
from .views.home_view import home_view
from .views.settings_view import settings_view
from .views.viewer_view import viewer_view

class AppRouter:
    """Handles the navigation state and view stacking for the application."""
    def __init__(self, page: ft.Page):
        self.page = page

    def route_change(self, e: ft.RouteChangeEvent):
        """Fires whenever page.go() is called."""
        self.page.views.clear()

        # 1. Base Layer Logging Logic
        if self.page.route == "/":
            self.page.views.append(login_view(self.page))
        else:
            # If not on login screen, the Home screen is always the base layer
            self.page.views.append(home_view(self.page))

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

    def view_pop(self, e: ft.ViewPopEvent):
        """Fires when the user clicks the physical Android back button or Appbar back arrow."""
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)