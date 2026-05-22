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

    # Card Factory Component
    def build_media_card(item_data):
        """Constructs an individual asset poster card with anti-aliasing constraints."""
        
        # Determine the visual content (thumbnail or fallback icon)
        image_src = item_data.get("url")
        if image_src and image_src.startswith("http"):
            visual_content = ft.Image(src=image_src, fit="cover", expand=True)
        else:
            # Fallback for music or missing thumbnails
            is_audio = item_data.get("is_audio", False)
            icon_name = ft.Icons.MUSIC_NOTE if is_audio else ft.Icons.IMAGE_NOT_SUPPORTED
            visual_content = ft.Container(
                content=ft.Icon(icon_name, size=40, color="white54"),
                alignment=ft.Alignment(0, 0),
                expand=True
            )

        def on_card_tap(e, data=item_data):
            page.session.store.set("current_media", data)
            asyncio.create_task(page.push_route(f"/viewer/{data['name']}"))

        return ft.GestureDetector(
            on_tap=on_card_tap, 
            content=ft.Container(
                width=130,
                height=195,  # Traditional 2:3 streaming aspect ratio
                border_radius=8,
                bgcolor="#333333",
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Stack([
                    visual_content,
                    # Subtle dark text overlay at the bottom of the card for filenames
                    ft.Container(
                        alignment=ft.Alignment(-1.0, 1.0),
                        padding=8,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment(0.0, -1.0),
                            end=ft.Alignment(0.0, 1.0),
                            colors=["#00000000", "#AA000000"]
                        ),
                        content=ft.Text(
                            item_data["name"],
                            size=11,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            color="white"
                        )
                    )
                ])
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
                    scroll=ft.ScrollMode.HIDDEN,
                    spacing=12,
                    controls=[build_media_card(item) for item in items_list]
                )
            ],
            spacing=8
        )

    # Create the profile avatar
    avatar = ft.CircleAvatar(
        radius=18,
        background_image_src=profile_pic if profile_pic else None,
        content=ft.Text(user_name[0].upper()) if not profile_pic else None,
        bgcolor=ft.Colors.PRIMARY if not profile_pic else None,
    )

    # Main App Scaffold Layout
    header_bar = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text(f"{greeting}, {user_name}!", size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("CloudStream", size=14, weight=ft.FontWeight.W_900, color=ft.Colors.PRIMARY),
                ]
            ),
            ft.Row(
                spacing=10,
                controls=[
                    avatar,
                    ft.IconButton(icon=ft.Icons.SETTINGS, icon_color="white", on_click=lambda _: asyncio.create_task(page.push_route("/settings")))
                ]
            )
        ]
    )

    shelf_container = ft.Column(
        expand=True,
        spacing=28,
        scroll=ft.ScrollMode.HIDDEN
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

        media = await get_media(token, folder_id)
        shelf_container.controls.clear()
        
        if not media:
            shelf_container.controls.append(
                ft.Text("No photos or videos found in this folder.", italic=True, color="gray")
            )
            page.update()
            return
            
        # Categorize media by mimeType, keeping id and mimeType intact for playback
        photos = [{"id": m["id"], "mimeType": m["mimeType"], "name": m["name"], "url": m.get("thumbnailLink", ""), "is_audio": False} for m in media if "image/" in m.get("mimeType", "")]
        videos = [{"id": m["id"], "mimeType": m["mimeType"], "name": m["name"], "url": m.get("thumbnailLink", ""), "is_audio": False} for m in media if "video/" in m.get("mimeType", "")]
        music = [{"id": m["id"], "mimeType": m["mimeType"], "name": m["name"], "url": m.get("thumbnailLink", ""), "is_audio": True} for m in media if "audio/" in m.get("mimeType", "")]
        
        if photos:
            shelf_container.controls.append(build_category_shelf("Photos", photos))
        if videos:
            shelf_container.controls.append(build_category_shelf("Videos", videos))
        if music:
            shelf_container.controls.append(build_category_shelf("Music", music))
            
        page.update()
        
    # Kick off the data fetch in the background as soon as the view renders
    asyncio.create_task(load_dashboard_content())

    # Return the assembled View object!
    return ft.View(
        route="/home",
        bgcolor="#111111",
        padding=ft.Padding(left=15, top=20, right=15, bottom=20),
        controls=[
            header_bar,
            ft.Divider(height=10, color="#222222"),
            shelf_container
        ]
    )