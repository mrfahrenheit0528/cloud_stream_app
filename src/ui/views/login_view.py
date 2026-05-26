import flet as ft
import os
import tempfile
import json
from services.onedrive_auth import initiate_device_flow, poll_device_token, fetch_user_profile

def login_view(page: ft.Page) -> ft.View:
    current_theme = page.session.store.get("theme_color") or ft.Colors.RED_700

    def build_microsoft_logo():
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(width=8, height=8, bgcolor="#F25022"),
                    ft.Container(width=8, height=8, bgcolor="#7FBA00"),
                ], spacing=2, tight=True),
                ft.Row([
                    ft.Container(width=8, height=8, bgcolor="#00A4EF"),
                    ft.Container(width=8, height=8, bgcolor="#FFB900"),
                ], spacing=2, tight=True),
            ], spacing=2, tight=True),
            alignment=ft.Alignment(0, 0),
            width=24, height=24
        )

    async def on_login_click(e):
        # Reset the button state visually
        btn = e.control
        btn.disabled = True
        btn.content = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.ProgressRing(width=22, height=22, color="white", stroke_width=2.5)]
        )
        page.update()

        try:
            # Step 1: Get the device code from Microsoft
            device_info = await initiate_device_flow()

            user_code = device_info.get("user_code", "")
            verify_url = device_info.get("verification_url", "https://microsoft.com/devicelogin")
            device_code = device_info.get("device_code", "")
            interval = device_info.get("interval", 5)

            # QR code pointing to microsoft.com/devicelogin for quick phone scanning
            qr_src = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={verify_url}&bgcolor=111111&color=ffffff&margin=2"

            # Step 2: Show the classic TV sign-in dialog
            dialog = ft.AlertDialog(
                title=ft.Text(
                    "Sign in with OneDrive",
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    size=20,
                ),
                content=ft.Column([
                    # Two-column layout: instructions + QR code
                    ft.Row([
                        ft.Column([
                            ft.Text(
                                "On your phone or computer:",
                                color=ft.Colors.WHITE70,
                                size=13,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Container(
                                bgcolor="#1A1A2E",
                                border_radius=8,
                                padding=ft.Padding(left=14, top=8, right=14, bottom=8),
                                content=ft.Text(
                                    verify_url,
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=current_theme,
                                ),
                            ),
                            ft.Text(
                                "Then enter this code:",
                                color=ft.Colors.WHITE70,
                                size=13,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Container(
                                bgcolor="#0D0D1A",
                                border_radius=10,
                                border=ft.Border.all(2, current_theme),
                                padding=ft.Padding(left=20, top=12, right=20, bottom=12),
                                content=ft.Text(
                                    user_code,
                                    size=44,
                                    weight=ft.FontWeight.BOLD,
                                    color="white",
                                    text_align=ft.TextAlign.CENTER,
                                    font_family="monospace",
                                ),
                            ),
                        ],
                        spacing=10,
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Column([
                            ft.Text("Scan QR:", color=ft.Colors.WHITE54, size=12),
                            ft.Container(
                                bgcolor="#ffffff",
                                border_radius=8,
                                padding=4,
                                content=ft.Image(
                                    src=qr_src,
                                    width=140, height=140,
                                    fit=ft.BoxFit.CONTAIN,
                                ),
                            ),
                        ],
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                    ),
                    ft.Divider(color="#2A2A3E", height=1),
                    ft.Row([
                        ft.ProgressRing(width=16, height=16, color=current_theme, stroke_width=2),
                        ft.Text(
                            "  Waiting for you to sign in...",
                            color=ft.Colors.WHITE54,
                            size=13,
                            italic=True,
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ],
                tight=True,
                spacing=14,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                modal=True,
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

            # Step 3: Poll Microsoft in the background until approved
            token_result = await poll_device_token(device_code, interval)

            dialog.open = False
            page.update()

            # Step 4: Fetch the user's profile info
            user_info = await fetch_user_profile(token_result["access_token"])
            display_name = user_info.get("given_name", "User")
            picture_url = user_info.get("picture", "")

            # Step 5: Persist token to disk for speed loading
            from config import get_persistent_data_dir
            token_cache_path = os.path.join(get_persistent_data_dir(), "estreamo_token.json")
            with open(token_cache_path, "w") as f:
                json.dump({
                    "access_token": token_result["access_token"],
                    "refresh_token": token_result.get("refresh_token", ""),
                    "given_name": display_name,
                    "picture_url": picture_url,
                }, f)

            # Store in session state
            page.session.store.set("onedrive_access_token", token_result["access_token"])
            page.session.store.set("onedrive_refresh_token", token_result.get("refresh_token", ""))
            page.session.store.set("user_display_name", display_name)
            page.session.store.set("user_picture_url", picture_url)

            # Also write to standard persistent preferences so it survives app restarts
            prefs_path = os.path.join(get_persistent_data_dir(), "estreamo_prefs.json")
            prefs = {}
            if os.path.exists(prefs_path):
                try:
                    with open(prefs_path, "r") as f:
                        prefs = json.load(f)
                except Exception:
                    pass
            prefs["onedrive_refresh_token"] = token_result.get("refresh_token", "")
            prefs["user_display_name"] = display_name
            try:
                with open(prefs_path, "w") as f:
                    json.dump(prefs, f)
            except Exception:
                pass

            page.go("/home")

        except Exception as ex:
            btn.disabled = False
            btn.content = ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    build_microsoft_logo(),
                    ft.Text("Sign in with OneDrive", size=18, weight=ft.FontWeight.W_600, color="white")
                ]
            )
            snack = ft.SnackBar(ft.Text(str(ex), color="white"), bgcolor="red")
            page.overlay.append(snack)
            snack.open = True
            page.update()

    # The sign-in button — use ft.Button so it is natively D-pad focusable
    signin_btn = ft.Button(
        width=340,
        autofocus=True,
        style=ft.ButtonStyle(
            bgcolor=current_theme,
            color="white",
            shape=ft.RoundedRectangleBorder(radius=30),
            padding=ft.Padding(left=40, top=18, right=40, bottom=18),
            overlay_color=ft.Colors.with_opacity(0.15, "white"),
            elevation=4,
        ),
        on_click=on_login_click,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                build_microsoft_logo(),
                ft.Text("Sign in with OneDrive", size=18, weight=ft.FontWeight.W_600, color="white")
            ]
        ),
    )

    content = ft.Container(
        expand=True,
        bgcolor="#111111",
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=40,
            controls=[
                ft.Image(
                    src="Logo.png",
                    width=120,
                    height=120,
                    fit=ft.BoxFit.CONTAIN
                ),
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        ft.Text("E-stream'o", size=48, weight=ft.FontWeight.BOLD, color="white"),
                        ft.Text("Your personal high-performance streaming server.", size=16, color="#888888")
                    ]
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                    controls=[
                        ft.Chip(label=ft.Text("Videos"), leading=ft.Icon(ft.Icons.MOVIE, color=current_theme), bgcolor="#1A1A1A"),
                        ft.Chip(label=ft.Text("Photos"), leading=ft.Icon(ft.Icons.PHOTO_LIBRARY, color=current_theme), bgcolor="#1A1A1A"),
                        ft.Chip(label=ft.Text("Music"), leading=ft.Icon(ft.Icons.MUSIC_NOTE, color=current_theme), bgcolor="#1A1A1A"),
                    ]
                ),
                signin_btn,
                ft.Text("We only read your OneDrive files. Nothing is shared.", size=12, color="#555555")
            ]
        )
    )

    return ft.View(
        route="/",
        controls=[content],
        padding=0
    )