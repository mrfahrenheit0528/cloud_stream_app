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
            page.session.store.set("current_media", hero_state["media"])
            asyncio.create_task(page.push_route(f"/viewer/{hero_state['media']['name']}"))
            
    hero_play_btn = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED),
            ft.Text("Play Media", weight=ft.FontWeight.BOLD)
        ], tight=True),
        bgcolor=current_theme,
        color="white",
        on_click=on_hero_play_click,
        visible=False,
        opacity=0,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        style=ft.ButtonStyle(
            padding=ft.Padding(left=30, right=30, top=20, bottom=20),
            shape=ft.RoundedRectangleBorder(radius=8)
        )
    )

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
    def build_media_card(item_data, parent_list=None):
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
                        
                asyncio.create_task(page.push_route(f"/viewer/{data['name']}"))
            else:
                # First click -> Update Hero Banner
                hero_state["media"] = data
                
                # --- PHASE 1: FADE OUT TO BLACK ---
                hero_image.opacity = 0
                hero_title.opacity = 0
                hero_subtitle.opacity = 0
                hero_play_btn.opacity = 0
                page.update()
                
                # Wait for the fade out to finish (allows image loading in background)
                await asyncio.sleep(0.4)
                
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
                    img_url = default_bg
                    hero_opacity = 0.4
                
                hero_image.src = img_url
                hero_title.value = data["name"]
                
                if data.get("is_audio"):
                    hero_subtitle.value = "Audio • High Quality"
                    hero_play_btn.content.controls[0].name = ft.Icons.PLAY_ARROW_ROUNDED
                    hero_play_btn.content.controls[1].value = "Play Media"
                elif "video/" in data.get("mimeType", ""):
                    hero_subtitle.value = "Video • Ready to Stream"
                    hero_play_btn.content.controls[0].name = ft.Icons.PLAY_ARROW_ROUNDED
                    hero_play_btn.content.controls[1].value = "Play Media"
                else:
                    hero_subtitle.value = "Photo • View Fullscreen"
                    hero_play_btn.content.controls[0].name = ft.Icons.IMAGE
                    hero_play_btn.content.controls[1].value = "View Image"
                    
                hero_play_btn.visible = True
                
                # --- PHASE 3: FADE CONTENT BACK IN ---
                hero_image.opacity = hero_opacity
                hero_title.opacity = 1
                hero_subtitle.opacity = 1
                hero_play_btn.opacity = 1
                page.update()

        def on_card_hover(e):
            e.control.content.scale = 1.05 if e.data == "true" else 1.0
            e.control.content.update()

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
            )
        ])
        
        return ft.GestureDetector(
            on_tap=on_card_tap, 
            on_hover=on_card_hover,
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                width=card_w,
                height=card_h,
                border_radius=12,
                bgcolor="#222222",
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                scale=1.0,
                animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT_CUBIC),
                content=card_stack
            )
        )

    # Horizontal Category Row Factory
    def build_category_shelf(category_title, items_list):
        """Creates a distinct vertical cluster containing a section title and a swipable row."""
        return ft.Column(
            controls=[
                ft.Text(
                    value=category_title,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color="#E5E5E5"
                ),
                ft.Row(
                    scroll=ft.ScrollMode.HIDDEN, # Hide scrollbars for a cleaner UI
                    spacing=12,
                    controls=[build_media_card(item, items_list) for item in items_list]
                )
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
    
    settings_button = ft.GestureDetector(
        content=avatar,
        on_tap=lambda _: asyncio.create_task(page.push_route("/settings")),
        mouse_cursor=ft.MouseCursor.CLICK
    )

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
        shelf_container.controls.append(
            ft.Container(content=ft.ProgressRing(), alignment=ft.Alignment(0, 0), padding=50)
        )
        page.update()
        
        from services.drive_service import get_media
        token = page.session.store.get("drive_access_token")
        folder_id = page.session.store.get("drive_folder_id")
        
        if not token:
            shelf_container.controls.clear()
            shelf_container.controls.append(ft.Text("Not authenticated. Please log in.", color="red"))
            page.update()
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
                        ft.Text("Please go to Settings and browse for your Google Drive folder.", color="gray")
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
            page.update()
            return

        try:
            media = await get_media(token, folder_id)
            shelf_container.controls.clear()
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
                shelf_container.controls.clear()
                shelf_container.controls.append(ft.Text("An error occurred while loading media.", color="red"))
                page.update()
                return
        
        media_groups = await get_media(token, folder_id)
        shelf_container.controls.clear()
        
        if not media_groups or all(len(g["files"]) == 0 for g in media_groups):
            shelf_container.controls.append(
                ft.Text("No photos or videos found in this folder.", italic=True, color="gray")
            )
            page.update()
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

        from services.metadata_service import get_audio_metadata

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
                    metadata = await get_audio_metadata(m["id"], token, m["name"])
                    if metadata.get("title"):
                        name = metadata["title"]
                    if metadata.get("cover_path"):
                        thumb_url = metadata["cover_path"]
                        
                return {
                    "id": m["id"], 
                    "mimeType": m["mimeType"], 
                    "name": name, 
                    "url": thumb_url, 
                    "width": w, 
                    "height": h,
                    "is_audio": is_audio
                }

            # Concurrently parse all ID3 tags in this folder!
            processed_items = await asyncio.gather(*[process_item(m) for m in files])
                
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
                
        page.update()
        
    # Kick off the data fetch in the background as soon as the view renders
    asyncio.create_task(load_dashboard_content())

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