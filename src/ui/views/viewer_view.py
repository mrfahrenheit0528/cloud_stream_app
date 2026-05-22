import flet as ft

def viewer_view(page: ft.Page, file_id: str) -> ft.View:
    """Full-screen media player overlay (Route: "/viewer/:file_id")"""
    return ft.View(
        route=f"/viewer/{file_id}",
        bgcolor="black", # Pure black for immersive viewing
        appbar=ft.AppBar(
            title=ft.Text(f"Playing: {file_id}", size=14),
            bgcolor="transparent",
        ),
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.Icons.PLAY_CIRCLE_FILL, size=100, color="white"),
            ft.Text("Media Player Placeholder", color="white")
        ]
    )