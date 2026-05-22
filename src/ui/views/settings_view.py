import flet as ft

def settings_view(page: ft.Page) -> ft.View:
    """User preferences and disconnect options (Route: "/settings")"""
    return ft.View(
        route="/settings",
        bgcolor="#111111",
        appbar=ft.AppBar(
            title=ft.Text("Settings", weight=ft.FontWeight.BOLD),
            bgcolor="#000000",
        ),
        controls=[
            ft.ListTile(
                leading=ft.Icon(ft.Icons.LOGOUT, color="red"),
                title=ft.Text("Disconnect Google Drive", color="white"),
                on_click=lambda _: page.go("/")
            ),
        ]
    )