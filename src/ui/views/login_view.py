import flet as ft
from services.google_auth import get_google_provider

def login_view(page: ft.Page) -> ft.View:
    """The initial landing screen (Route: "/")"""
    
    provider = get_google_provider()

    # Create an asynchronous click handler to await the login coroutine
    async def on_login_click(e):
        await page.login(provider)

    return ft.View(
        route="/",
        bgcolor="#111111",
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.Icons.CLOUD_DONE, size=80, color="#E50914"),
            ft.Text("CloudStream", size=32, weight=ft.FontWeight.W_900, color="white"),
            ft.Text("Access your Drive media beautifully.", size=14, color="#AAAAAA"),
            ft.Container(height=30), # Spacer
            ft.ElevatedButton(
                "Sign in with Google",
                icon=ft.Icons.LOGIN,
                color="white",
                bgcolor="#E50914",
                on_click=on_login_click 
            )
        ]
    )