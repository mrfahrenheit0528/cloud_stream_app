import flet as ft
from dotenv import load_dotenv

# Load variables BEFORE importing the router
load_dotenv()

from ui.router import AppRouter
from services.google_auth import handle_login_result  # Import the handler here

def main(page: ft.Page):
    page.title = "Drive Stream Engine"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#111111"

    app_router = AppRouter(page)
    
    page.on_route_change = app_router.route_change
    page.on_view_pop = app_router.view_pop
    
    # GLOBAL LISTENER: Always listen for the Google OAuth callback
    page.on_login = lambda e: handle_login_result(e, page)

    app_router.route_change(None)

# Force web browser view and specific port for OAuth redirects
ft.run(main, view=ft.AppView.WEB_BROWSER, port=8550)