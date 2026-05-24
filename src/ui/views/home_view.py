import asyncio
import flet as ft
from datetime import datetime

def home_view(page: ft.Page) -> ft.View:
    """The main dashboard screen (Route: "/home")"""

    # --- Dynamic Greeting Logic ---
    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # Extract the user's name, prioritizing their custom settings
    user_name = "User"
    custom_name = page.session.store.get("user_display_name")
    
    if custom_name:
        user_name = custom_name
    elif page.auth and page.auth.user:
        user_name = page.auth.user.get("given_name", page.auth.user.get("name", "User"))
    elif page.session.store.contains_key("user_given_name"):
        user_name = page.session.store.get("user_given_name")
        
    # Get profile picture URL
    profile_pic = page.session.store.get("profile_pic_url")

    # Remove the hardcoded mock database
    # We will populate the shelves dynamically via the drive_service.

    # --- Hero Banner State & Components ---
    hero_state = {"media": None}
    
    # Map current theme to the local background assets
    current_theme = page.session.store.get("theme_color") or ft.Colors.RED_700
    theme_bg_map = {
        ft.Colors.RED_700: "Red.png",
        ft.Colors.GREEN_700: "Green.png",
        ft.Colors.BLUE_700: "Blue.png",
        ft.Colors.AMBER_700: "Yellow.png",
        ft.Colors.PURPLE_700: "Purple.png",
    }
    default_bg = theme_bg_map.get(current_theme, "Red.png")
    
    # Use a raw ft.Image wrapped in an expanding container to force full-bleed stretch
    hero_image = ft.Image(
        src=default_bg,
        fit="cover",
        opacity=0.4,
        expand=True,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT)
    )
    
    hero_title = ft.Text(
        "E-stream'o", size=54, weight=ft.FontWeight.W_900, color="white", max_lines=2, 
        overflow=ft.TextOverflow.ELLIPSIS, opacity=1, animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT)
    )
    hero_subtitle = ft.Text(
        "Your personal high-performance streaming server.", size=18, color="#CCCCCC", 
        weight=ft.FontWeight.W_500, opacity=1, animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT)
    )
    
    def on_hero_play_click(e):
        if hero_state["media"]:
            # Play the hero media
            page.session.store.set("current_media", hero_state["media"])
            if hero_state.get("gallery"):
                page.session.store.set("current_gallery", hero_state["gallery"])
            page.run_task(page.push_route, f"/viewer/{hero_state['media']['name']}")
            
    hero_play_container = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED),
            ft.Text("Play Media", weight=ft.FontWeight.BOLD)
        ], tight=True),
        bgcolor=current_theme,
        padding=ft.Padding(left=30, right=30, top=20, bottom=20),
        border_radius=8,
        border=ft.Border(
            top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            left=ft.BorderSide(0, ft.Colors.TRANSPARENT)
        )
    )
    
    def on_hero_play_focus(focused):
        if focused:
            hero_play_container.border = ft.Border(
                top=ft.BorderSide(3, ft.Colors.PRIMARY),
                right=ft.BorderSide(3, ft.Colors.PRIMARY),
                bottom=ft.BorderSide(3, ft.Colors.PRIMARY),
                left=ft.BorderSide(3, ft.Colors.PRIMARY)
            )
        else:
            hero_play_container.border = ft.Border(
                top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                left=ft.BorderSide(0, ft.Colors.TRANSPARENT)
            )
        hero_play_container.update()

    hero_play_btn = ft.GestureDetector(
        content=hero_play_container,
        on_tap=on_hero_play_click,
        visible=False,
        opacity=0,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT)
    )
    hero_play_btn.focus_node = {
        "is_card": False,
        "set_focus": on_hero_play_focus,
        "click": lambda: on_hero_play_click(None)
    }

    # We make the hero_banner expand natively without a fixed height constraint
    hero_banner = ft.Container(
        expand=True,
        content=ft.Stack([
            # Background Image Layer (No longer inside AnimatedSwitcher, allowing full stretch)
            ft.Container(
                content=hero_image,
                left=0, right=0, top=0, bottom=0
            ),
            # Gradient Left-to-Right (Fades out image on the left)
            ft.Container(
                left=0, right=0, top=0, bottom=0,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(-1.0, 0.0),
                    end=ft.Alignment(0.5, 0.0),
                    colors=["#111111", "#00111111"]
                )
            ),
            # Gradient Bottom-to-Top (Fades out image into the shelves below)
            ft.Container(
                left=0, right=0, top=0, bottom=0,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(0.0, 1.0),
                    end=ft.Alignment(0.0, -0.3),
                    colors=["#111111", "#00111111"]
                )
            ),
            # Text Content Overlay (Fixed positioning)
            ft.Container(
                left=40, right=40, top=160,
                content=ft.Column([
                    hero_title,
                    hero_subtitle,
                    ft.Container(height=15),
                    hero_play_btn
                ])
            )
        ])
    )


    # Card Factory Component
    def build_media_card(item_data, parent_list=None, horizontal_row=None, parent_row_key=None):
        """Constructs an individual asset poster card with anti-aliasing constraints."""
        
        is_audio = item_data.get("is_audio", False)
        w_val = item_data.get("width", 0)
        h_val = item_data.get("height", 0)
        
        # Determine aesthetic aspect ratios
        if is_audio:
            card_w, card_h = 180, 180 # 1:1 for music
        elif h_val > w_val:
            card_w, card_h = 135, 180 # 3:4 for portrait
        else:
            card_w, card_h = 270, 180 # 3:2 for landscape (or fallback)
        
        # Determine the visual content (thumbnail or fallback icon)
        import os
        image_src = item_data.get("url")
        if image_src and (image_src.startswith("http") or os.path.isabs(image_src)):
            visual_content = ft.Image(src=image_src, fit="cover", width=card_w, height=card_h)
        else:
            # Fallback for music or missing thumbnails
            icon_name = ft.Icons.MUSIC_NOTE if is_audio else ft.Icons.IMAGE_NOT_SUPPORTED
            visual_content = ft.Container(
                content=ft.Icon(icon_name, size=50, color="white54"),
                alignment=ft.Alignment(0, 0),
                width=card_w,
                height=card_h
            )

        async def update_hero_banner(data, gallery_list=None):
            try:
                page.session.store.set("hero_update_target", data["id"])
                if hero_state["media"] and hero_state["media"]["id"] == data["id"]:
                    return
                    
                hero_state["media"] = data
                hero_state["gallery"] = gallery_list
                
                # --- PHASE 1: FADE OUT TO BLACK ---
                hero_image.opacity = 0
                hero_title.opacity = 0
                hero_subtitle.opacity = 0
                hero_play_btn.opacity = 0
                if page.route == "/home":
                    try: page.update()
                    except Exception: pass
                
                # Wait for the fade out to finish (allows image loading in background)
                await asyncio.sleep(0.4)
                
                # Debounce check: if user Arrowed past this card during the 400ms fade, abort!
                if page.session.store.get("hero_update_target") != data["id"]:
                    return
                    
                # --- PHASE 2: UPDATE CONTENT ---
                img_url = data.get("url", "")
                if img_url:
                    # Force Google Drive API to return a 1080p high-res thumbnail
                    if "googleusercontent.com" in img_url and "=" in img_url:
                        base_url = img_url.split("=")[0]
                        img_url = f"{base_url}=s1080"
                    
                    hero_opacity = 0.5
                else:
                    # Fallback to default cinematic background if media has no thumbnail
                    img_url = "Logo.png"
                    hero_opacity = 0.4
                
                hero_image.src = img_url
                hero_title.value = data["name"]
                
                if data.get("is_audio"):
                    hero_subtitle.value = "Audio • High Quality"
                    hero_play_container.content.controls[0].icon = ft.Icons.PLAY_ARROW_ROUNDED
                    hero_play_container.content.controls[1].value = "Play Media"
                elif "video/" in data.get("mimeType", ""):
                    hero_subtitle.value = "Video • Ready to Stream"
                    hero_play_container.content.controls[0].icon = ft.Icons.PLAY_ARROW_ROUNDED
                    hero_play_container.content.controls[1].value = "Play Media"
                else:
                    hero_subtitle.value = "Photo • View Fullscreen"
                    hero_play_container.content.controls[0].icon = ft.Icons.IMAGE
                    hero_play_container.content.controls[1].value = "View Image"
                    
                hero_play_btn.visible = True
                
                # --- PHASE 3: FADE CONTENT BACK IN ---
                hero_image.opacity = hero_opacity
                hero_title.opacity = 1
                hero_subtitle.opacity = 1
                hero_play_btn.opacity = 1
                if page.route == "/home":
                    try: page.update()
                    except Exception: pass
            except Exception:
                pass

        async def on_card_tap(e, data=item_data):
            if hero_state["media"] and hero_state["media"]["id"] == data["id"]:
                # Second click -> Play the media!
                page.session.store.set("current_media", data)
                if parent_list:
                    page.session.store.set("current_gallery", parent_list)
                    
                if data.get("is_audio"):
                    audio_state = page.session.store.get("audio_state")
                    if audio_state and parent_list:
                        audio_queue = [f for f in parent_list if f.get("is_audio")]
                        idx = 0
                        for i, f in enumerate(audio_queue):
                            if f['id'] == data['id']:
                                idx = i
                                break
                        audio_state.set_queue(audio_queue, idx)
                        
                page.run_task(page.push_route, f"/viewer/{data['name']}")
            else:
                # First click -> Update Hero Banner
                page.run_task(update_hero_banner, data, parent_list)

        focus_overlay = ft.Container(
            border=ft.Border(
                top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                left=ft.BorderSide(0, ft.Colors.TRANSPARENT)
            ),
            border_radius=12,
            left=0, right=0, top=0, bottom=0 # Fills the stack perfectly without pushing content
        )

        def set_focus(focused):
            if focused:
                focus_overlay.border = ft.Border(
                    top=ft.BorderSide(4, ft.Colors.PRIMARY),
                    right=ft.BorderSide(4, ft.Colors.PRIMARY),
                    bottom=ft.BorderSide(4, ft.Colors.PRIMARY),
                    left=ft.BorderSide(4, ft.Colors.PRIMARY)
                )
                import asyncio
                page.run_task(update_hero_banner, item_data, parent_list)
            else:
                focus_overlay.border = ft.Border(
                    top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                    right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                    bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                    left=ft.BorderSide(0, ft.Colors.TRANSPARENT)
                )
            focus_overlay.update()

        card_stack = ft.Stack([
            visual_content,
            # Subtle dark text overlay at the bottom of the card for filenames
            ft.Container(
                alignment=ft.Alignment(-1.0, 1.0),
                padding=12,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(0.0, -0.5),
                    end=ft.Alignment(0.0, 1.0),
                    colors=["#00000000", "#D9000000"]
                ),
                content=ft.Text(
                    item_data["name"],
                    size=12,
                    max_lines=3, # Allow up to 3 lines for long filenames
                    overflow=ft.TextOverflow.ELLIPSIS,
                    color="white",
                    weight=ft.FontWeight.W_600
                )
            ),
            focus_overlay
        ])
        
        import uuid
        card_key = f"card_{uuid.uuid4()}"
        
        btn = ft.GestureDetector(
            key=card_key,
            on_tap=lambda e: page.run_task(on_card_tap, e),
            content=ft.Container(
                width=card_w,
                height=card_h,
                border_radius=12,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=card_stack
            )
        )
        
        btn.focus_node = {
            "is_card": True,
            "row_key": parent_row_key,
            "card_w": card_w,
            "horizontal_row": horizontal_row,
            "set_focus": set_focus,
            "click": lambda: page.run_task(on_card_tap, None)
        }
        return btn

    # Horizontal Category Row Factory
    def build_category_shelf(category_title, items_list):
        """Creates a distinct vertical cluster containing a section title and a swipable row."""
        import uuid
        row_key = f"shelf_{uuid.uuid4()}"
        
        horizontal_row = ft.Row(
            scroll=ft.ScrollMode.HIDDEN, # Hide scrollbars for a cleaner UI
            spacing=12,
        )
        horizontal_row.controls = [build_media_card(item, items_list, horizontal_row, row_key) for item in items_list]
        
        return ft.Column(
            key=row_key,
            controls=[
                ft.Text(
                    value=category_title,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color="#E5E5E5"
                ),
                horizontal_row
            ],
            spacing=8
        )

    # Create the profile avatar
    avatar = ft.CircleAvatar(
        radius=22,
        background_image_src=profile_pic if profile_pic else None,
        content=ft.Text(user_name[0].upper()) if not profile_pic else None,
        bgcolor=ft.Colors.PRIMARY if not profile_pic else None,
    )
    
    transparent_border = ft.Border(
        top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
        right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
        bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
        left=ft.BorderSide(0, ft.Colors.TRANSPARENT)
    )
    
    primary_border = ft.Border(
        top=ft.BorderSide(3, ft.Colors.PRIMARY),
        right=ft.BorderSide(3, ft.Colors.PRIMARY),
        bottom=ft.BorderSide(3, ft.Colors.PRIMARY),
        left=ft.BorderSide(3, ft.Colors.PRIMARY)
    )
    
    avatar_container = ft.Container(
        content=avatar,
        border_radius=25,
        padding=0,
        border=transparent_border
    )
    
    def on_settings_focus(focused):
        if focused:
            avatar_container.border = primary_border
        else:
            avatar_container.border = transparent_border
        avatar_container.update()

    settings_button = ft.GestureDetector(
        content=avatar_container,
        on_tap=lambda _: page.run_task(page.push_route, "/settings")
    )
    settings_button.focus_node = {
        "is_card": False,
        "set_focus": on_settings_focus,
        "click": lambda: page.go("/settings") if page.route != "/settings" else None
    }

    # Main App Scaffold Layout
    header_bar = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text(f"{greeting}, {user_name}!", size=26, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("E-stream'o", size=14, weight=ft.FontWeight.W_900, color=ft.Colors.PRIMARY),
                ]
            ),
            settings_button
        ]
    )

    shelf_container = ft.Column(
        expand=True,
        spacing=28,
        scroll=ft.ScrollMode.HIDDEN # Hide scrollbars for a cleaner UI
    )

    async def load_dashboard_content():
        """Fetches the actual media from Google Drive and updates the UI."""
        def safe_update():
            if page.route == "/home":
                try: page.update()
                except Exception: pass

        if page.route != "/home":
            return
            
        try:
            shelf_container.controls.append(
                ft.Container(content=ft.ProgressRing(), alignment=ft.Alignment(0, 0), padding=50)
            )
            safe_update()
        except RuntimeError: return
        
        from services.onedrive_service import get_media
        token = page.session.store.get("onedrive_access_token")
        folder_id = page.session.store.get("onedrive_folder_id")
        
        if not token:
            shelf_container.controls.clear()
            shelf_container.controls.append(ft.Text("Not authenticated. Please log in.", color="red"))
            page.session.store.set("home_focus_grid", [[settings_button.focus_node]])
            safe_update()
            return
            
        if not folder_id:
            shelf_container.controls.clear()
            shelf_container.controls.append(
                ft.Container(
                    alignment=ft.Alignment(0, 0),
                    padding=40,
                    content=ft.Column([
                        ft.Icon(ft.Icons.FOLDER_OFF, size=48, color="gray"),
                        ft.Text("No folder selected.", size=18, color="white"),
                        ft.Text("Please go to Settings and browse for your OneDrive folder.", color="gray")
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
            page.session.store.set("home_focus_grid", [[settings_button.focus_node]])
            safe_update()
            return

        media_groups = page.session.store.get("home_cached_media_groups")
        cached_folder_id = page.session.store.get("home_cached_folder_id")

        if not media_groups or cached_folder_id != folder_id:
            try:
                media_groups = await get_media(token, folder_id)
                page.session.store.set("home_cached_media_groups", media_groups)
                page.session.store.set("home_cached_folder_id", folder_id)
                shelf_container.controls.clear()
            except Exception as e:
                if "UNAUTHENTICATED" in str(e):
                    import os, tempfile
                    token_cache_path = os.path.join(tempfile.gettempdir(), "estreamo_token.json")
                    if os.path.exists(token_cache_path):
                        try:
                            os.remove(token_cache_path)
                        except Exception:
                            pass
                    page.session.store.clear()
                    page.logout()
                    await page.push_route("/")
                    safe_update()
                    return
                else:
                    shelf_container.controls.clear()
                    shelf_container.controls.append(ft.Text("An error occurred while loading media.", color="red"))
                    page.session.store.set("home_focus_grid", [[settings_button.focus_node]])
                    safe_update()
                    return
        else:
            shelf_container.controls.clear()
        
        if not media_groups or all(len(g["files"]) == 0 for g in media_groups):
            shelf_container.controls.append(
                ft.Text("No photos or videos found in this folder.", italic=True, color="gray")
            )
            page.session.store.set("home_focus_grid", [[settings_button.focus_node]])
            safe_update()
            return
            
        def extract_dims(m):
            w, h = 0, 0
            if "imageMediaMetadata" in m:
                w = m["imageMediaMetadata"].get("width", 0)
                h = m["imageMediaMetadata"].get("height", 0)
            elif "videoMediaMetadata" in m:
                w = m["videoMediaMetadata"].get("width", 0)
                h = m["videoMediaMetadata"].get("height", 0)
            return w, h
        cached_processed_dict = page.session.store.get("home_cached_processed_items") or {}
        new_processed_dict = {}

        for group in media_groups:
            files = group["files"]
            folder_name = group["folder_name"]
            if not files:
                continue
                
            async def process_item(m):
                w, h = extract_dims(m)
                is_audio = "audio/" in m.get("mimeType", "")
                
                name = m["name"]
                thumb_url = m.get("thumbnailLink", "")
                
                if is_audio:
                    from services.metadata_service import get_audio_metadata
                    audio_meta = m.get("audio", {})
                    if audio_meta and audio_meta.get("title"):
                        artist = audio_meta.get("artist", "")
                        if artist:
                            name = f"{artist} - {audio_meta['title']}"
                        else:
                            name = audio_meta["title"]
                            
                    # ALWAYS extract ID3 tags to get the local cover art, because
                    # OneDrive's mediap.svc.ms thumbnail URLs frequently expire/fail in Flet
                    meta = await get_audio_metadata(m.get("url", ""), m["id"], name)
                    if meta.get("title") and meta.get("title") != name and name == m["name"]:
                        name = meta["title"]
                    if meta.get("cover_path"):
                        thumb_url = meta["cover_path"]
                    elif "mediap.svc.ms" in thumb_url or "microsoftpersonalcontent.com" in thumb_url:
                        thumb_url = ""
                        
                cat = "Music" if is_audio else ("Photos" if "image/" in m.get("mimeType", "") else "Videos") if folder_name == "Root" else folder_name
                
                return {
                    "id": m["id"], 
                    "mimeType": m["mimeType"], 
                    "name": name, 
                    "url": thumb_url, 
                    "stream_url": m.get("url", ""), # Store the OneDrive direct stream link here!
                    "width": w, 
                    "height": h,
                    "is_audio": is_audio,
                    "category": cat
                }

            if folder_name in cached_processed_dict:
                processed_items = cached_processed_dict[folder_name]
            else:
                raw_results = await asyncio.gather(*[process_item(m) for m in files], return_exceptions=True)
                processed_items = [r for r in raw_results if isinstance(r, dict)]
                
            new_processed_dict[folder_name] = processed_items
                
            if folder_name == "Root":
                photos = [i for i in processed_items if not i["is_audio"] and "image/" in i["mimeType"]]
                videos = [i for i in processed_items if not i["is_audio"] and "video/" in i["mimeType"]]
                music = [i for i in processed_items if i["is_audio"]]
                
                if photos:
                    shelf_container.controls.append(build_category_shelf("Photos", photos))
                if videos:
                    shelf_container.controls.append(build_category_shelf("Videos", videos))
                if music:
                    shelf_container.controls.append(build_category_shelf("Music", music))
            else:
                # Group all media within a subfolder into its own dedicated category shelf
                shelf_container.controls.append(build_category_shelf(folder_name, processed_items))
                
        page.session.store.set("home_cached_processed_items", new_processed_dict)
                
        # Build the 2D Grid for strict Up/Down/Left/Right HTPC Navigation!
        grid = []
        top_row = [settings_button.focus_node]
        if hero_play_btn.visible:
            top_row.append(hero_play_btn.focus_node)
        grid.append(top_row)
        
        for shelf in shelf_container.controls:
            if isinstance(shelf, ft.Column) and len(shelf.controls) > 1:
                row = shelf.controls[1]
                if isinstance(row, ft.Row):
                    grid_row = [c.focus_node for c in row.controls if c.visible is not False and hasattr(c, "focus_node")]
                    if grid_row:
                        grid.append(grid_row)
                        
        try:
            page.session.store.set("home_focus_grid", grid)
            
            if page.session.store.get("home_grid_pos") is None:
                page.session.store.set("home_grid_pos", (0, 0))
                
            safe_update()
        except Exception:
            pass
        
    async def home_keyboard(e: ft.KeyboardEvent):
        grid = page.session.store.get("home_focus_grid")
        if not grid: return
        
        r, c = page.session.store.get("home_grid_pos") or (0, 0)
        
        # Guard against dynamic grid mutations
        r = min(max(0, r), len(grid) - 1)
        if len(grid) > 0 and len(grid[r]) > 0:
            c = min(max(0, c), len(grid[r]) - 1)
        else:
            return
        
        old_node = grid[r][c]
        try:
            old_node["set_focus"](False)
        except Exception: pass
        
        if e.key == "Arrow Right":
            c = min(c + 1, len(grid[r]) - 1)
        elif e.key == "Arrow Left":
            c = max(c - 1, 0)
        elif e.key == "Arrow Down":
            r = min(r + 1, len(grid) - 1)
            c = 0
        elif e.key == "Arrow Up":
            r = max(r - 1, 0)
            c = 0
        elif e.key == "Enter" or e.key == "Space":
            try:
                res = old_node["click"]()
                old_node["set_focus"](True)
                if hasattr(res, "__await__"):
                    await res
            except Exception: pass
            return
        else:
            try:
                old_node["set_focus"](True)
            except Exception: pass
            return
            
        page.session.store.set("home_grid_pos", (r, c))
        new_node = grid[r][c]
        try:
            new_node["set_focus"](True)
        except Exception: pass
        
        try:
            if r > 0:
                target_y = max(0, (r - 1) * 240)
                import asyncio
                res = shelf_container.scroll_to(offset=target_y, duration=300)
                if asyncio.iscoroutine(res):
                    await res
                shelf_container.update()
            elif r == 0:
                import asyncio
                res = shelf_container.scroll_to(offset=0, duration=300)
                if asyncio.iscoroutine(res):
                    await res
                shelf_container.update()
        except Exception:
            pass
            
        if new_node.get("is_card") and new_node.get("horizontal_row"):
            try:
                card_w = new_node.get("card_w", 180)
                target_x = max(0, (c - 1) * (card_w + 12))
                row = new_node["horizontal_row"]
                import asyncio
                res = row.scroll_to(offset=target_x, duration=300)
                if asyncio.iscoroutine(res):
                    async def safe_scroll(c):
                        try: await c
                        except Exception: pass
                    page.run_task(safe_scroll, res)
                row.update()
            except Exception: pass
            
    page.session.store.set("keyboard_handler", home_keyboard)
    page.session.store.set("home_keyboard_handler", home_keyboard)  # Persistent key for router cache restoration
        
    # Kick off the data fetch in the background only if the user is actually looking at the dashboard
    if page.route == "/home":
        page.run_task(load_dashboard_content)

    # Apply a shader mask to the shelves to create a cinematic fade at the top
    masked_shelves = ft.ShaderMask(
        content=shelf_container,
        blend_mode=ft.BlendMode.DST_IN,
        shader=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER,
            end=ft.Alignment.BOTTOM_CENTER,
            colors=["#00000000", "#FF000000", "#FF000000"],
            stops=[0.0, 0.35, 1.0] # Fades from transparent to opaque over the top 35%
        ),
    )

    # Return the assembled View object!
    main_stack = ft.Stack(
        expand=True,
        controls=[
            # 1. FIXED BACKGROUND: Hero Banner (Max 3/4 of the window height)
            ft.Container(
                content=hero_banner,
                left=0, right=0, top=0, height=650 # Leaves the bottom completely empty/black
            ),
            
            # 2. FIXED HEADER: Top Bar (Always perfectly pinned)
            ft.Container(
                padding=ft.Padding(left=40, top=30, right=40, bottom=0),
                content=header_bar,
                left=0, right=0, top=0
            ),
            
            # 3. BOUNDED SCROLLABLE VIEWPORT: The Shelves
            ft.Container(
                padding=ft.Padding(left=40, right=40, top=0, bottom=20),
                content=masked_shelves,
                left=0, right=0, top=420, bottom=0
            )
        ]
    )

    return ft.View(
        route="/home",
        bgcolor="#111111",
        padding=0, # Remove edge padding to allow full bleed
        controls=[main_stack]
    )