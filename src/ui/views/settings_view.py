import asyncio
import flet as ft

def settings_view(page: ft.Page) -> ft.View:
    """User preferences and disconnect options (Route: "/settings")"""

    # Load existing preferences
    current_name = page.session.store.get("user_display_name") or ""
    current_folder = page.session.store.get("drive_folder_id") or ""
    current_theme = page.session.store.get("theme_color") or ft.Colors.RED_700

    # ── Input Controls ──────────────────────────────────────────────────────
    name_field = ft.TextField(
        label="Display Name",
        value=current_name,
        bgcolor="#111111",
        border_color="transparent",
        prefix_icon=ft.Icons.PERSON,
        expand=True,
    )

    def clear_name(e):
        name_field.value = ""
        name_field.update()

    clear_name_btn = ft.IconButton(
        icon=ft.Icons.CLEAR_ROUNDED,
        icon_color="#888888",
        tooltip="Clear name",
        on_click=clear_name,
        icon_size=20,
    )

    folder_field = ft.TextField(
        label="Google Drive Folder ID / URL",
        value=current_folder,
        bgcolor="#111111",
        border_color="transparent",
        prefix_icon=ft.Icons.FOLDER_SHARED,
        expand=True,
    )

    # ── Drive Picker Logic ───────────────────────────────────────────────────
    drive_history = ["root"]
    dlg_content = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, width=400)

    async def load_drive_folders(parent_id):
        dlg_content.controls.clear()
        dlg_content.controls.append(
            ft.Container(content=ft.ProgressRing(), alignment=ft.Alignment(0, 0), padding=20)
        )
        page.update()

        from services.drive_service import get_folders
        token = page.session.store.get("drive_access_token")
        if not token:
            dlg_content.controls.clear()
            dlg_content.controls.append(ft.Text("Not authenticated with Google Drive."))
            page.update()
            return

        try:
            folders = await get_folders(token, parent_id)
        except Exception as e:
            if "UNAUTHENTICATED" in str(e):
                import os
                if os.path.exists(".token.json"):
                    try:
                        os.remove(".token.json")
                    except Exception:
                        pass
                page.session.store.clear()
                page.logout()
                await page.push_route("/")
                page.update()
                return
            else:
                folders = []
        dlg_content.controls.clear()

        if len(drive_history) > 1:
            dlg_content.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ARROW_BACK),
                    title=ft.Text(".. (Go Back)"),
                    on_click=on_folder_back,
                )
            )

        if not folders:
            dlg_content.controls.append(ft.Text("No folders found here.", italic=True, color="gray"))
        else:
            for f in folders:
                dlg_content.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE),
                        title=ft.Text(f["name"]),
                        on_click=lambda e, fid=f["id"]: page.run_task(on_folder_click, fid),
                    )
                )
        page.update()

    async def on_folder_click(folder_id):
        drive_history.append(folder_id)
        await load_drive_folders(folder_id)

    async def on_folder_back(e):
        if len(drive_history) > 1:
            drive_history.pop()
            await load_drive_folders(drive_history[-1])

    def close_dialog(e):
        drive_dialog.open = False
        page.update()

    def on_select_current_folder(e):
        folder_field.value = drive_history[-1]
        drive_dialog.open = False
        page.update()

    drive_dialog = ft.AlertDialog(
        title=ft.Text("Select Google Drive Folder"),
        content=dlg_content,
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.ElevatedButton(
                "Select Current Folder",
                color="white",
                bgcolor=ft.Colors.PRIMARY,
                on_click=on_select_current_folder,
            ),
        ],
    )

    def open_drive_picker(e):
        if drive_dialog not in page.overlay:
            page.overlay.append(drive_dialog)
        drive_dialog.open = True
        page.update()
        page.run_task(load_drive_folders, drive_history[-1])

    # ── Theme swatches ───────────────────────────────────────────────────────
    selected_color = current_theme

    def update_color_selection():
        for swatch in color_row.controls:
            if swatch.bgcolor == selected_color:
                swatch.content = ft.Icon(ft.Icons.CHECK, color="white")
            else:
                swatch.content = None
        page.update()

    def on_color_click(e):
        nonlocal selected_color
        selected_color = e.control.bgcolor
        update_color_selection()

    color_options = [
        ft.Colors.RED_700, ft.Colors.GREEN_700, ft.Colors.BLUE_700,
        ft.Colors.AMBER_700, ft.Colors.PURPLE_700,
    ]
    color_row = ft.Row(
        controls=[
            ft.Container(
                bgcolor=color,
                width=40,
                height=40,
                border_radius=20,
                data="swatch",
                on_click=on_color_click,
            )
            for color in color_options
        ]
    )
    update_color_selection()

    # ── Focusable button wrappers ────────────────────────────────────────────
    # Each button gets a Container that shows a glowing border when focused via
    # the remote control keyboard grid.

    _UNFOCUSED_BORDER = ft.Border(
        top=ft.BorderSide(2, "transparent"),
        bottom=ft.BorderSide(2, "transparent"),
        left=ft.BorderSide(2, "transparent"),
        right=ft.BorderSide(2, "transparent"),
    )

    def _focused_border(color="#FFFFFF"):
        return ft.Border(
            top=ft.BorderSide(2, color),
            bottom=ft.BorderSide(2, color),
            left=ft.BorderSide(2, color),
            right=ft.BorderSide(2, color),
        )

    _browse_inner = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.SEARCH, color="white"), ft.Text("Browse Drive", color="white", weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#333333",
        height=56,
        border_radius=10,
        padding=15,
    )
    browse_wrap = ft.Container(
        content=_browse_inner,
        border=_UNFOCUSED_BORDER,
        border_radius=12,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        on_click=open_drive_picker,
    )

    def browse_focus(focused: bool):
        browse_wrap.border = _focused_border("#FFFFFF") if focused else _UNFOCUSED_BORDER
        browse_wrap.shadow = ft.BoxShadow(
            spread_radius=0, blur_radius=18,
            color="#66FFFFFF", offset=ft.Offset(0, 0),
        ) if focused else None
        try: browse_wrap.update()
        except Exception: pass

    _save_inner = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.SAVE_ROUNDED, color="white"), ft.Text("Save Settings", color="white", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=ft.Colors.PRIMARY,
        height=56,
        width=220,
        border_radius=10,
        padding=15,
    )
    save_wrap = ft.Container(
        content=_save_inner,
        border=_UNFOCUSED_BORDER,
        border_radius=12,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        on_click=lambda e: page.run_task(on_save, e),
    )

    def save_focus(focused: bool):
        save_wrap.border = _focused_border(ft.Colors.PRIMARY) if focused else _UNFOCUSED_BORDER
        save_wrap.shadow = ft.BoxShadow(
            spread_radius=0, blur_radius=22,
            color="#88FFFFFF", offset=ft.Offset(0, 0),
        ) if focused else None
        try: save_wrap.update()
        except Exception: pass

    _disconnect_inner = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.LOGOUT_ROUNDED, color="red"), ft.Text("Disconnect Google", color="red", weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.CENTER),
        height=56,
        border_radius=10,
        border=ft.Border(
            top=ft.BorderSide(2, "red"),
            bottom=ft.BorderSide(2, "red"),
            left=ft.BorderSide(2, "red"),
            right=ft.BorderSide(2, "red"),
        ),
        padding=15,
    )
    disconnect_wrap = ft.Container(
        content=_disconnect_inner,
        border=_UNFOCUSED_BORDER,
        border_radius=12,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        on_click=None,
    )

    def disconnect_focus(focused: bool):
        disconnect_wrap.border = _focused_border("#FF5555") if focused else _UNFOCUSED_BORDER
        disconnect_wrap.shadow = ft.BoxShadow(
            spread_radius=0, blur_radius=20,
            color="#88FF3333", offset=ft.Offset(0, 0),
        ) if focused else None
        try: disconnect_wrap.update()
        except Exception: pass

    # ── Save / Disconnect logic ───────────────────────────────────────────────
    is_saving = False

    async def on_save(e):
        """Save preferences to session storage and apply theme."""
        nonlocal is_saving
        if is_saving:
            return
        is_saving = True

        raw_folder = folder_field.value.strip() if folder_field.value else ""
        extracted_id = raw_folder
        if "drive.google.com" in raw_folder and "folders/" in raw_folder:
            extracted_id = raw_folder.split("folders/")[-1].split("?")[0].split("/")[0]

        if extracted_id != page.session.store.get("drive_folder_id"):
            for cache_key in ["home_cached_media_groups", "home_cached_folder_id", "home_cached_processed_items"]:
                if page.session.store.contains_key(cache_key):
                    page.session.store.remove(cache_key)

        page.session.store.set("user_display_name", name_field.value)
        page.session.store.set("drive_folder_id", extracted_id)
        page.session.store.set("theme_color", selected_color)

        import json, os, tempfile
        prefs_path = os.path.join(tempfile.gettempdir(), "estreamo_prefs.json")
        prefs = {}
        if os.path.exists(prefs_path):
            try:
                with open(prefs_path, "r") as f:
                    prefs = json.load(f)
            except Exception: pass

        prefs["user_display_name"] = name_field.value
        prefs["drive_folder_id"] = extracted_id
        prefs["theme_color"] = selected_color

        with open(prefs_path, "w") as f:
            json.dump(prefs, f)

        page.theme = ft.Theme(color_scheme_seed=selected_color)
        page.snack_bar = ft.SnackBar(ft.Text("Settings Saved!"), bgcolor=ft.Colors.GREEN_800)
        page.snack_bar.open = True

        page.session.store.set("home_needs_refresh", True)

        page.views.pop()
        top_view = page.views[-1]
        if page.route != top_view.route:
            await page.push_route(top_view.route)
        page.update()
        is_saving = False

    async def perform_disconnect(e):
        disconnect_dialog.open = False
        page.update()

        import os, tempfile
        token_path = os.path.join(tempfile.gettempdir(), "estreamo_token.json")
        prefs_path = os.path.join(tempfile.gettempdir(), "estreamo_prefs.json")
        for path in (token_path, prefs_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        page.session.store.clear()
        try:
            page.logout()
        except Exception:
            pass   # page.logout() may throw in FLET_APP native mode
        page.go("/")

    def cancel_disconnect(e):
        disconnect_dialog.open = False
        page.update()

    disconnect_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.WARNING_ROUNDED, color="red"), ft.Text("Disconnect Account")]),
        content=ft.Text(
            "Are you sure you want to log out and disconnect your Google account from E-stream'o?"
        ),
        actions=[
            ft.TextButton("Cancel", on_click=cancel_disconnect),
            ft.ElevatedButton("Disconnect", bgcolor="red", color="white", on_click=perform_disconnect),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def confirm_disconnect(e):
        if disconnect_dialog not in page.overlay:
            page.overlay.append(disconnect_dialog)
        disconnect_dialog.open = True
        page.update()

    # Patch the disconnect button's on_click now that confirm_disconnect exists
    disconnect_wrap.on_click = confirm_disconnect

    # ── 2D Keyboard Focus Grid ───────────────────────────────────────────────
    # Row 0: [name_field, clear_name_btn]
    # Row 1: color swatches
    # Row 2: [folder_field, browse_wrap]
    # Row 3: [save_wrap, disconnect_wrap]
    grid = [
        [name_field, clear_name_btn],
        color_row.controls,
        [folder_field, browse_wrap],
        [save_wrap, disconnect_wrap],
    ]
    focus_state = {"r": 0, "c": 0}

    # Map focusable controls that have custom focus handlers
    _btn_focus_handlers = {
        id(browse_wrap): browse_focus,
        id(save_wrap): save_focus,
        id(disconnect_wrap): disconnect_focus,
    }

    dummy_focus = ft.TextField(width=0, height=0, border_color="transparent", text_size=0, opacity=0)

    async def update_settings_focus():
        """Apply / remove the focus indicator for every item in the grid."""
        # Clear all button highlights and swatch borders first
        for btn_id, handler in _btn_focus_handlers.items():
            handler(False)
        for swatch in color_row.controls:
            swatch.border = None

        target = grid[focus_state["r"]][focus_state["c"]]

        if isinstance(target, ft.Container) and getattr(target, "data", None) == "swatch":
            # Color swatch: white ring
            target.border = ft.Border(
                top=ft.BorderSide(3, "white"),
                bottom=ft.BorderSide(3, "white"),
                left=ft.BorderSide(3, "white"),
                right=ft.BorderSide(3, "white"),
            )
            # Pull native focus away from text fields
            try:
                res = dummy_focus.focus()
                if hasattr(res, "__await__"):
                    await res
            except Exception: pass
        elif id(target) in _btn_focus_handlers:
            # One of our wrapped buttons
            _btn_focus_handlers[id(target)](True)
            # Pull native focus away from text fields
            try:
                res = dummy_focus.focus()
                if hasattr(res, "__await__"):
                    await res
            except Exception: pass
        else:
            # TextField / IconButton — native focus
            try:
                res = target.focus()
                if hasattr(res, "__await__"):
                    await res
            except Exception:
                pass

        try:
            page.update()
        except Exception:
            pass

    async def settings_keyboard(e: ft.KeyboardEvent):
        # Dialogs consume all keys
        if drive_dialog.open or disconnect_dialog.open:
            if e.key in ["Escape", "BrowserBack", "Backspace"]:
                drive_dialog.open = False
                disconnect_dialog.open = False
                page.update()
            return

        if e.key in ["Escape", "BrowserBack", "Backspace"]:
            if page.route != "/home":
                page.go("/home")
            return

        r = focus_state["r"]
        c = focus_state["c"]

        if e.key == "Arrow Down":
            r = min(len(grid) - 1, r + 1)
            c = min(len(grid[r]) - 1, c)
        elif e.key == "Arrow Up":
            r = max(0, r - 1)
            c = min(len(grid[r]) - 1, c)
        elif e.key == "Arrow Right":
            c = min(len(grid[r]) - 1, c + 1)
        elif e.key == "Arrow Left":
            c = max(0, c - 1)
        elif e.key in ["Enter", "Space", "MediaPlayPause"]:
            ctrl = grid[r][c]
            try:
                if isinstance(ctrl, ft.Container) and getattr(ctrl, "on_click", None):
                    class MockEvent:
                        control = ctrl
                    res = ctrl.on_click(MockEvent())
                    if hasattr(res, "__await__"):
                        await res
                elif hasattr(ctrl, "on_click") and ctrl.on_click:
                    res = ctrl.on_click(None)
                    if hasattr(res, "__await__"):
                        await res
            except Exception:
                pass

        if r != focus_state["r"] or c != focus_state["c"]:
            focus_state["r"] = r
            focus_state["c"] = c
            await update_settings_focus()

    page.session.store.set("keyboard_handler", settings_keyboard)

    async def initial_focus():
        await asyncio.sleep(0.1)
        await update_settings_focus()

    page.run_task(initial_focus)

    # ── View Layout ──────────────────────────────────────────────────────────
    return ft.View(
        route="/settings",
        bgcolor="#111111",
        appbar=ft.AppBar(
            title=ft.Text("Settings", weight=ft.FontWeight.BOLD),
            bgcolor="#000000",
        ),
        padding=20,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Settings", size=32, weight=ft.FontWeight.W_900, color="white"),
            ft.Divider(height=20, color="transparent"),

            # ── Profile ──
            ft.Container(
                bgcolor="#1E1E1E",
                border_radius=15,
                padding=25,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=ft.Colors.PRIMARY),
                        ft.Text("Profile", size=20, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row(
                        controls=[name_field, clear_name_btn],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ]),
            ),

            ft.Container(height=10),

            # ── Appearance ──
            ft.Container(
                bgcolor="#1E1E1E",
                border_radius=15,
                padding=25,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.PALETTE, color=ft.Colors.PRIMARY),
                        ft.Text("Appearance", size=20, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Divider(height=10, color="transparent"),
                    color_row,
                ]),
            ),

            ft.Container(height=10),

            # ── Data Source ──
            ft.Container(
                bgcolor="#1E1E1E",
                border_radius=15,
                padding=25,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.STORAGE, color=ft.Colors.PRIMARY),
                        ft.Text("Data Source", size=20, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Text("Select the root folder containing your media.", color="gray"),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row(controls=[folder_field, browse_wrap]),
                ]),
            ),

            ft.Divider(height=40, color="transparent"),

            # ── Action Buttons ──
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[save_wrap, disconnect_wrap],
            ),
            dummy_focus
        ],
    )
