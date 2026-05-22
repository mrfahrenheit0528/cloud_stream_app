import asyncio
import flet as ft

def settings_view(page: ft.Page) -> ft.View:
    """User preferences and disconnect options (Route: "/settings")"""

    # Load existing preferences
    current_name = page.session.store.get("user_display_name") or ""
    current_pic = page.session.store.get("profile_pic_url") or ""
    current_folder = page.session.store.get("drive_folder_id") or ""
    current_theme = page.session.store.get("theme_color") or ft.Colors.RED_700

    # Input Controls
    name_field = ft.TextField(
        label="Display Name", 
        value=current_name,
        bgcolor="#222222",
        border_color="transparent"
    )
    pic_field = ft.TextField(
        label="Profile Picture URL", 
        value=current_pic,
        bgcolor="#222222",
        border_color="transparent"
    )
    folder_field = ft.TextField(
        label="Google Drive Folder ID / Name", 
        value=current_folder,
        bgcolor="#222222",
        border_color="transparent",
        expand=True
    )

    # --- Drive Picker Logic ---
    drive_history = ["root"]
    dlg_content = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, width=400)
    
    async def load_drive_folders(parent_id):
        dlg_content.controls.clear()
        dlg_content.controls.append(ft.Container(content=ft.ProgressRing(), alignment=ft.Alignment(0, 0), padding=20))
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
                    on_click=on_folder_back
                )
            )
            
        if not folders:
            dlg_content.controls.append(ft.Text("No folders found here.", italic=True, color="gray"))
        else:
            for f in folders:
                # Use default arguments (fid=f["id"]) to capture the variable in the lambda
                dlg_content.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE),
                        title=ft.Text(f["name"]),
                        on_click=lambda e, fid=f["id"]: asyncio.create_task(on_folder_click(fid))
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
            ft.ElevatedButton("Select Current Folder", color="white", bgcolor=ft.Colors.PRIMARY, on_click=on_select_current_folder)
        ]
    )

    def open_drive_picker(e):
        if drive_dialog not in page.overlay:
            page.overlay.append(drive_dialog)
        drive_dialog.open = True
        page.update()
        asyncio.create_task(load_drive_folders(drive_history[-1]))
    # -------------------------

    # State to hold the currently selected color
    selected_color = current_theme

    def update_color_selection():
        """Updates the checkmark on the selected color swatch."""
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

    # Theme Swatches
    color_options = [ft.Colors.RED_700, ft.Colors.GREEN_700, ft.Colors.BLUE_700, ft.Colors.AMBER_700, ft.Colors.PURPLE_700]
    color_row = ft.Row(
        controls=[
            ft.Container(
                bgcolor=color,
                width=40,
                height=40,
                border_radius=20,
                on_click=on_color_click
            ) for color in color_options
        ]
    )
    # Initialize the border highlight
    update_color_selection()

    async def on_save(e):
        """Save preferences to session storage and apply theme."""
        
        # Extract folder ID if the user pasted a full URL
        raw_folder = folder_field.value.strip() if folder_field.value else ""
        extracted_id = raw_folder
        if "drive.google.com" in raw_folder and "folders/" in raw_folder:
            extracted_id = raw_folder.split("folders/")[-1].split("?")[0].split("/")[0]

        page.session.store.set("user_display_name", name_field.value)
        page.session.store.set("profile_pic_url", pic_field.value)
        page.session.store.set("drive_folder_id", extracted_id)
        page.session.store.set("theme_color", selected_color)

        # Persist preferences to disk so they survive logout/restart
        import json
        import os
        prefs_path = os.path.join(os.getcwd(), ".prefs.json")
        prefs = {}
        if os.path.exists(prefs_path):
            try:
                with open(prefs_path, "r") as f:
                    prefs = json.load(f)
            except Exception:
                pass
                
        prefs["user_display_name"] = name_field.value
        prefs["profile_pic_url"] = pic_field.value
        prefs["drive_folder_id"] = extracted_id
        prefs["theme_color"] = selected_color
        
        with open(prefs_path, "w") as f:
            json.dump(prefs, f)

        # Apply theme immediately
        page.theme = ft.Theme(color_scheme_seed=selected_color)
        
        # Show a snackbar confirmation
        page.snack_bar = ft.SnackBar(ft.Text("Settings Saved!"), bgcolor=ft.Colors.GREEN_800)
        page.snack_bar.open = True
        
        # Go back to home
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)
        page.update()

    async def on_disconnect(e):
        """Clear auth state and return to login screen."""
        page.session.store.clear()
        page.logout()
        await page.push_route("/")

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
            ft.Text("Profile", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            name_field,
            pic_field,
            
            ft.Divider(height=20, color="transparent"),
            
            ft.Text("Appearance", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            ft.Text("Theme Color", color="white"),
            color_row,

            ft.Divider(height=20, color="transparent"),

            ft.Text("Data Source", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            ft.Row(
                controls=[
                    folder_field,
                    ft.ElevatedButton(
                        "Browse Drive", 
                        icon=ft.Icons.FOLDER_OPEN,
                        color="white",
                        bgcolor="#333333",
                        on_click=open_drive_picker,
                        height=55
                    )
                ]
            ),

            ft.Divider(height=40, color="transparent"),
            
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.ElevatedButton(
                        "Save Changes", 
                        icon=ft.Icons.SAVE, 
                        color="white", 
                        bgcolor=ft.Colors.PRIMARY, 
                        on_click=on_save
                    ),
                    ft.TextButton(
                        "Disconnect Google",
                        icon=ft.Icons.LOGOUT,
                        icon_color="red",
                        style=ft.ButtonStyle(color="red"),
                        on_click=on_disconnect
                    )
                ]
            )
        ]
    )