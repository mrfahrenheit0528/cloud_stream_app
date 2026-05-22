import flet as ft
from datetime import datetime
import urllib.request
import json

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

    # Extract the user's name directly from Google using our secure access token
    user_name = "User"
    
    # Check if the key exists in the Flet session before accessing it
    if page.session.contains_key("drive_access_token"):
        token = page.session.get("drive_access_token")
        try:
            # Make a live API call to Google to prove the token works and get the profile
            req = urllib.request.Request("https://www.googleapis.com/oauth2/v1/userinfo?alt=json")
            req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req) as response:
                user_info = json.loads(response.read())
                user_name = user_info.get("given_name", user_info.get("name", "User"))
        except Exception as e:
            print(f"Failed to fetch profile from Google: {e}")

    # Mock database layout mimicking incoming structure from your Google Drive scan
    drive_media_cache = {
        "Recent Camera Uploads": [
            {"name": "IMG_001.jpg", "url": "https://picsum.photos/400/600?random=1"},
            {"name": "IMG_002.jpg", "url": "https://picsum.photos/400/600?random=2"},
            {"name": "IMG_003.jpg", "url": "https://picsum.photos/400/600?random=3"},
            {"name": "IMG_004.jpg", "url": "https://picsum.photos/400/600?random=4"},
            {"name": "IMG_005.jpg", "url": "https://picsum.photos/400/600?random=5"},
        ],
        "Vacation Videos": [
            {"name": "VID_Shoreline.mp4", "url": "https://picsum.photos/400/600?random=6"},
            {"name": "VID_Mountain.mp4", "url": "https://picsum.photos/400/600?random=7"},
            {"name": "VID_Roadtrip.mp4", "url": "https://picsum.photos/400/600?random=8"},
            {"name": "VID_Bonfire.mp4", "url": "https://picsum.photos/400/600?random=9"},
        ],
        "Documents & Captures": [
            {"name": "Receipt_01.png", "url": "https://picsum.photos/400/600?random=10"},
            {"name": "Invoice_May.png", "url": "https://picsum.photos/400/600?random=11"},
            {"name": "Notes_Draft.jpg", "url": "https://picsum.photos/400/600?random=12"},
        ]
    }

    # Card Factory Component
    def build_media_card(item_data):
        """Constructs an individual asset poster card with anti-aliasing constraints."""
        return ft.GestureDetector(
            on_tap=lambda e: page.push_route(f"/viewer/{item_data['name']}"),
            content=ft.Container(
                width=130,
                height=195,  # Traditional 2:3 streaming aspect ratio
                border_radius=8,
                bgcolor="#222222",
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Stack([
                    ft.Image(
                        src=item_data["url"],
                        fit="cover",
                        expand=True,
                    ),
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

    # Main App Scaffold Layout
    header_bar = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text(f"{greeting}, {user_name}!", size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("CloudStream", size=14, weight=ft.FontWeight.W_900, color="red"),
                ]
            ),
            ft.IconButton(icon=ft.Icons.SETTINGS, icon_color="white", on_click=lambda _: page.push_route("/settings"))
        ]
    )

    shelf_container = ft.ListView(
        expand=True,
        spacing=28,  # Generous gaps between major horizontal categories
        controls=[
            build_category_shelf(title, contents) 
            for title, contents in drive_media_cache.items()
        ]
    )

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