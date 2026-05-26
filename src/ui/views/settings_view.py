import asyncio
import urllib.parse
import flet as ft
import os
import json

def settings_view(page: ft.Page) -> ft.View:
    """User preferences and disconnect options (Route: "/settings")"""

    # Load existing preferences
    current_name = page.session.store.get("user_display_name") or ""
    current_folder = page.session.store.get("onedrive_folder_id") or ""
    current_theme = page.session.store.get("theme_color") or ft.Colors.RED_700

    # ── Input Controls ──────────────────────────────────────────────────────
    # Name Modal Logic
    modal_name_field = ft.TextField(label="Display Name", value=current_name)
    
    def close_name_modal(e):
        name_modal.open = False
        page.update()
        
    def save_name_modal(e):
        name_field.value = modal_name_field.value
        name_field.update()
        name_modal.open = False
        page.update()
        
    name_modal = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Display Name"),
        content=modal_name_field,
        actions=[
            ft.TextButton("Cancel", on_click=close_name_modal),
            ft.ElevatedButton("Save", on_click=save_name_modal),
        ]
    )

    async def edit_name(e):
        if name_modal not in page.overlay:
            page.overlay.append(name_modal)
        modal_name_field.value = name_field.value
        name_modal.open = True
        page.update()
        res = modal_name_field.focus()
        if hasattr(res, "__await__"): await res

    name_field = ft.TextField(
        label="Display Name",
        value=current_name,
        bgcolor="#111111",
        border_color="transparent",
        prefix_icon=ft.Icons.PERSON,
        disabled=True,
        expand=True,
    )

    edit_name_btn = ft.IconButton(
        icon=ft.Icons.EDIT_ROUNDED,
        icon_color="#888888",
        tooltip="Edit name",
        on_click=edit_name,
        icon_size=20,
    )

    # Folder Modal Logic
    modal_folder_field = ft.TextField(label="OneDrive Folder ID", value=current_folder or "root")
    
    def close_folder_modal(e):
        folder_modal.open = False
        page.update()
        
    def save_folder_modal(e):
        folder_field.value = modal_folder_field.value
        folder_field.update()
        folder_modal.open = False
        page.update()
        
    folder_modal = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Folder ID"),
        content=modal_folder_field,
        actions=[
            ft.TextButton("Cancel", on_click=close_folder_modal),
            ft.ElevatedButton("Save", on_click=save_folder_modal),
        ]
    )

    async def edit_folder(e):
        if folder_modal not in page.overlay:
            page.overlay.append(folder_modal)
        modal_folder_field.value = folder_field.value
        folder_modal.open = True
        page.update()
        res = modal_folder_field.focus()
        if hasattr(res, "__await__"): await res

    folder_field = ft.TextField(
        label="OneDrive Root Folder ID (or 'root')",
        value=current_folder or "root",
        bgcolor="#111111",
        border_color="transparent",
        prefix_icon=ft.Icons.FOLDER_SHARED,
        disabled=True,
        expand=True,
    )
    
    edit_folder_btn = ft.IconButton(
        icon=ft.Icons.EDIT_ROUNDED,
        icon_color="#888888",
        tooltip="Edit folder",
        on_click=edit_folder,
        icon_size=20,
    )

    # ── OneDrive Folder Picker Logic ─────────────────────────────────────────
    drive_history = ["root"]
    dlg_content = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, width=400)

    async def _get_onedrive_token() -> str:
        """Get a valid OneDrive access token: refresh from stored refresh token first."""
        rt = page.session.store.get("onedrive_refresh_token") or ""
        if rt:
            from services.onedrive_auth import refresh_access_token
            try:
                res = await refresh_access_token(rt)
                page.session.store.set("onedrive_access_token", res["access_token"])
                page.session.store.set("onedrive_refresh_token", res["refresh_token"])
                
                # Update persistent prefs file since refresh token rolls
                from config import get_persistent_data_dir
                prefs_path = os.path.join(get_persistent_data_dir(), "estreamo_prefs.json")
                prefs = {}
                if os.path.exists(prefs_path):
                    try:
                        with open(prefs_path, "r") as f:
                            prefs = json.load(f)
                    except Exception: pass
                prefs["onedrive_refresh_token"] = res["refresh_token"]
                with open(prefs_path, "w") as f:
                    json.dump(prefs, f)
                    
                # Update token cache as well
                token_path = os.path.join(get_persistent_data_dir(), "estreamo_token.json")
                if os.path.exists(token_path):
                    try:
                        with open(token_path, "r") as f:
                            t_cache = json.load(f)
                        t_cache["access_token"] = res["access_token"]
                        t_cache["refresh_token"] = res["refresh_token"]
                        with open(token_path, "w") as f:
                            json.dump(t_cache, f)
                    except Exception: pass
            except Exception:
                pass
        return page.session.store.get("onedrive_access_token") or ""

    async def load_drive_folders(parent_id):
        dlg_content.controls.clear()
        dlg_content.controls.append(
            ft.Container(content=ft.ProgressRing(), alignment=ft.Alignment(0, 0), padding=20)
        )
        page.update()

        from services.onedrive_service import get_folders
        token = await _get_onedrive_token()
        if not token:
            dlg_content.controls.clear()
            dlg_content.controls.append(ft.Text("Not authenticated. Please go back and Sign in with OneDrive."))
            page.update()
            return

        try:
            folders = await get_folders(token, parent_id)
        except Exception as e:
            if "UNAUTHENTICATED" in str(e):
                page.session.store.clear()
                page.go("/")
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
        title=ft.Text("Select OneDrive Folder"),
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

    async def open_phone_input():
        # 1. Start background HTTP server
        import urllib.parse
        import http.server
        import socket
        import threading
        
        local_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
            
        port = 8080
        server = None
        for p in range(8080, 8090):
            try:
                # Custom handler subclass to pass scope closures cleanly
                class LocalInputHandler(http.server.BaseHTTPRequestHandler):
                    def log_message(self, format, *args):
                        pass
                        
                    def do_GET(self):
                        parsed = urllib.parse.urlparse(self.path)
                        if parsed.path == "/submit":
                            query = urllib.parse.parse_qs(parsed.query)
                            url_val = query.get("url", [""])[0].strip()
                            
                            # Update TV text fields
                            folder_field.value = url_val
                            modal_folder_field.value = url_val
                            
                            # Success response
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(b'{"status":"success"}')
                            
                            # Trigger update and close dialog safely on the main thread
                            async def handle_url_received():
                                try:
                                    # 1. Close phone dialog first so the TV UI updates immediately
                                    phone_dialog.open = False
                                    try:
                                        phone_dialog.update()
                                    except:
                                        pass
                                    
                                    # 2. Update folder fields safely
                                    folder_field.value = url_val
                                    try:
                                        folder_field.update()
                                    except:
                                        pass
                                    
                                    modal_folder_field.value = url_val
                                    try:
                                        modal_folder_field.update()
                                    except:
                                        pass
                                    
                                    # 3. Update main page
                                    try:
                                        page.update()
                                    except:
                                        pass
                                    
                                    # 4. Show success premium Toast/SnackBar
                                    try:
                                        page.snack_bar = ft.SnackBar(
                                            content=ft.Text("Folder Link Linked Successfully!", color="white", weight=ft.FontWeight.BOLD),
                                            bgcolor=ft.Colors.GREEN_800
                                        )
                                        page.snack_bar.open = True
                                        page.update()
                                    except:
                                        pass
                                    
                                    # 5. Cleanly shut down HTTP server
                                    nonlocal server
                                    if server:
                                        server.shutdown()
                                        server = None
                                except Exception as ex:
                                    import traceback
                                    print(f"Error in handle_url_received: {ex}")
                                    traceback.print_exc()
                                
                            page.run_task(handle_url_received)
                            return
                            
                        # Serve the premium mobile page
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        
                        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>E-stream'o Remote Input</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            background-color: #0c0c14;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 30px;
            width: 100%;
            max-width: 450px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
        }}
        h2 {{ margin-top: 0; font-size: 28px; color: {current_theme}; font-weight: 900; letter-spacing: 1px; }}
        p {{ color: #888899; font-size: 14px; line-height: 1.5; margin-bottom: 25px; }}
        textarea {{
            width: 100%;
            height: 120px;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            color: white;
            padding: 12px;
            font-size: 14px;
            box-sizing: border-box;
            resize: none;
            margin-bottom: 20px;
            outline: none;
            transition: border-color 0.2s;
        }}
        textarea:focus {{ border-color: {current_theme}; }}
        button {{
            background: linear-gradient(135deg, {current_theme}, #1A1A2E);
            border: none;
            color: white;
            padding: 14px 28px;
            border-radius: 30px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        button:active {{ transform: scale(0.98); }}
        .success {{ color: #22c55e; font-weight: bold; margin-top: 15px; display: none; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>E-stream'o</h2>
        <p>Paste your OneDrive or SharePoint guest folder sharing link below to instantly send it to your Android TV.</p>
        <textarea id="url" placeholder="https://1drv.ms/f/s!A... or https://sharepoint.com/..."></textarea>
        <button onclick="send()">Send to TV</button>
        <div id="msg" class="success">Link Sent! You can close this tab now.</div>
    </div>
    <script>
        async function send() {{
            const url = document.getElementById('url').value.trim();
            if(!url) return alert('Please paste a link first!');
            try {{
                const res = await fetch('/submit?url=' + encodeURIComponent(url));
                const data = await res.json();
                if(data.status === 'success') {{
                    document.getElementById('msg').style.display = 'block';
                    document.getElementById('url').value = '';
                }} else {{
                    alert('Failed to send link.');
                }}
            }} catch(e) {{
                alert('Connection error: ' + e);
            }}
        }}
    </script>
</body>
</html>"""
                        self.wfile.write(html_content.encode("utf-8"))
                        
                server = http.server.HTTPServer(("0.0.0.0", p), LocalInputHandler)
                port = p
                break
            except OSError:
                continue
                
        if not server:
            return
            
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        
        local_web_url = f"http://{local_ip}:{port}"
        qr_src = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(local_web_url)}&bgcolor=111111&color=ffffff&margin=2"
        
        def close_phone_dialog(e):
            nonlocal server
            phone_dialog.open = False
            page.update()
            if server:
                server.shutdown()
                server = None
                
        phone_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Paste Link from Phone", weight=ft.FontWeight.BOLD, size=20, text_align=ft.TextAlign.CENTER),
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("1. Scan this QR code or type this URL on your phone/computer:", color="white70", size=13),
                        ft.Container(
                            bgcolor="#1E1E1E",
                            border_radius=8,
                            padding=ft.Padding(14, 8, 14, 8),
                            content=ft.Text(local_web_url, size=16, weight=ft.FontWeight.BOLD, color=current_theme)
                        ),
                        ft.Text("2. Paste your OneDrive/SharePoint sharing link.", color="white70", size=13),
                        ft.Text("3. Tap 'Send to TV' to link instantly.", color="white70", size=13),
                    ], spacing=10, expand=True),
                    ft.Column([
                        ft.Container(
                            bgcolor="white",
                            border_radius=8,
                            padding=4,
                            content=ft.Image(src=qr_src, width=140, height=140, fit=ft.BoxFit.CONTAIN)
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(color="#2A2A3E", height=1),
                ft.Row([
                    ft.ProgressRing(width=16, height=16, color=current_theme, stroke_width=2),
                    ft.Text("  Waiting for folder link from phone...", color="white54", size=13, italic=True)
                ], alignment=ft.MainAxisAlignment.CENTER)
            ], tight=True, spacing=14),
            actions=[
                ft.TextButton("Cancel", on_click=close_phone_dialog)
            ]
        )
        
        page.overlay.append(phone_dialog)
        phone_dialog.open = True
        page.update()


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
        content=ft.Row([ft.Icon(ft.Icons.SEARCH, color="white"), ft.Text("Browse OneDrive", color="white", weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.CENTER),
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

    _phone_inner = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.PHONELINK_SETUP_ROUNDED, color="white"), ft.Text("Link from Phone", color="white", weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#222222",
        height=56,
        border_radius=10,
        padding=15,
    )
    phone_wrap = ft.Container(
        content=_phone_inner,
        border=_UNFOCUSED_BORDER,
        border_radius=12,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        on_click=lambda e: page.run_task(open_phone_input),
    )

    def phone_focus(focused: bool):
        phone_wrap.border = _focused_border("#FFFFFF") if focused else _UNFOCUSED_BORDER
        phone_wrap.shadow = ft.BoxShadow(
            spread_radius=0, blur_radius=18,
            color="#66FFFFFF", offset=ft.Offset(0, 0),
        ) if focused else None
        try: phone_wrap.update()
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
        content=ft.Row([ft.Icon(ft.Icons.LOGOUT_ROUNDED, color="red"), ft.Text("Disconnect OneDrive", color="red", weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.CENTER),
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

        extracted_id = folder_field.value.strip() if folder_field.value else "root"

        if extracted_id != page.session.store.get("onedrive_folder_id"):
            for cache_key in ["home_cached_media_groups", "home_cached_folder_id", "home_cached_processed_items"]:
                if page.session.store.contains_key(cache_key):
                    page.session.store.remove(cache_key)

        page.session.store.set("user_display_name", name_field.value)
        page.session.store.set("onedrive_folder_id", extracted_id)
        page.session.store.set("theme_color", selected_color)

        from config import get_persistent_data_dir
        prefs_path = os.path.join(get_persistent_data_dir(), "estreamo_prefs.json")
        prefs = {}
        if os.path.exists(prefs_path):
            try:
                with open(prefs_path, "r") as f:
                    prefs = json.load(f)
            except Exception: pass

        prefs["user_display_name"] = name_field.value
        prefs["onedrive_folder_id"] = extracted_id
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

        from config import get_persistent_data_dir
        token_path = os.path.join(get_persistent_data_dir(), "estreamo_token.json")
        prefs_path = os.path.join(get_persistent_data_dir(), "estreamo_prefs.json")
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
        title=ft.Row([ft.Icon(ft.Icons.WARNING_ROUNDED, color="red"), ft.Text("Disconnect OneDrive")]),
        content=ft.Text(
            "Are you sure you want to log out and disconnect your Microsoft account from E-stream'o?"
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

    disconnect_wrap.on_click = confirm_disconnect

    # ── 2D Keyboard Focus Grid ───────────────────────────────────────────────
    # Row 0: [edit_name_btn]
    # Row 1: color swatches
    # Row 2: [edit_folder_btn, browse_wrap, phone_wrap]
    # Row 3: [save_wrap, disconnect_wrap]
    grid = [
        [edit_name_btn],
        color_row.controls,
        [edit_folder_btn, browse_wrap, phone_wrap],
        [save_wrap, disconnect_wrap],
    ]
    focus_state = {"r": 0, "c": 0}

    # Map focusable controls that have custom focus handlers
    _btn_focus_handlers = {
        id(browse_wrap): browse_focus,
        id(phone_wrap): phone_focus,
        id(save_wrap): save_focus,
        id(disconnect_wrap): disconnect_focus,
    }

    dummy_focus = ft.TextField(width=0, height=0, border_color="transparent", text_size=0, opacity=0)

    async def update_settings_focus():
        """Apply / remove the focus indicator for every item in the grid."""
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
            try:
                res = dummy_focus.focus()
                if hasattr(res, "__await__"):
                    await res
            except Exception: pass
        elif id(target) in _btn_focus_handlers:
            # One of our wrapped buttons
            _btn_focus_handlers[id(target)](True)
            try:
                res = dummy_focus.focus()
                if hasattr(res, "__await__"):
                    await res
            except Exception: pass
            except Exception: pass
        else:
            # TextField / IconButton — native focus
            try:
                res = target.focus()
                if hasattr(res, "__await__"):
                    await res
            except Exception:
                pass
                
        # Scroll logic to keep selected items in view
        try:
            if focus_state["r"] >= 2:
                # Scroll down to show action buttons (increased offset to prevent cut-offs on TVs)
                res = main_scroll_col.scroll_to(offset=500, duration=300)
            else:
                # Scroll back to the top
                res = main_scroll_col.scroll_to(offset=0, duration=300)
                
            if hasattr(res, "__await__"):
                await res
        except Exception: pass

        try:
            page.update()
        except Exception:
            pass

    async def settings_keyboard(e: ft.KeyboardEvent):
        # Dialogs consume all keys
        if drive_dialog.open or disconnect_dialog.open or getattr(name_modal, "open", False) or getattr(folder_modal, "open", False):
            if e.key in ["Escape", "BrowserBack", "Backspace"]:
                drive_dialog.open = False
                disconnect_dialog.open = False
                name_modal.open = False
                folder_modal.open = False
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
        elif e.key in ["Enter", "Space", "MediaPlayPause", "Select", "Gamepad Button A", "Numpad Enter"]:
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
    main_scroll_col = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.HIDDEN,
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
                        controls=[name_field, edit_name_btn],
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
                        ft.Text("OneDrive Source Folder", size=20, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Text("Select the root folder in OneDrive containing your media library.", color="gray"),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row(controls=[folder_field, edit_folder_btn, browse_wrap, phone_wrap]),
                ]),
            ),

            ft.Divider(height=40, color="transparent"),

            # ── Action Buttons ──
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[save_wrap, disconnect_wrap],
            ),
            ft.Container(height=100), # Spacer to ensure full visibility at bottom
            dummy_focus
        ]
    )

    return ft.View(
        route="/settings",
        bgcolor="#111111",
        appbar=ft.AppBar(
            title=ft.Text("Settings", weight=ft.FontWeight.BOLD),
            bgcolor="#000000",
        ),
        padding=20,
        controls=[main_scroll_col],
    )
