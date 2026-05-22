import flet as ft
try:
    import flet_video as fv
except ImportError:
    try:
        import flet.video as fv
    except ImportError:
        fv = None

def viewer_view(page: ft.Page, file_name: str) -> ft.View:
    """Full-screen media player overlay (Route: "/viewer/:file_name")"""
    
    # Retrieve the metadata we passed from the home view
    item_data = page.session.store.get("current_media")
    token = page.session.store.get("drive_access_token")
    
    if not item_data or not token:
        return ft.View(
            route=f"/viewer/{file_name}",
            bgcolor="black",
            appbar=ft.AppBar(title=ft.Text("Error"), bgcolor="transparent"),
            controls=[ft.Text("Media data lost. Please go back.", color="red")]
        )
        
    # Construct the base streaming URL using the Google Drive API
    stream_url = f"https://www.googleapis.com/drive/v3/files/{item_data['id']}?alt=media"
    mime_type = item_data.get("mimeType", "")
    
    # Determine the correct player based on the mime type
    if "image/" in mime_type:
        # Google Drive strictly blocks direct API images in web browsers due to CORS. 
        # But we can take the pre-authenticated thumbnail link and request original size (=s0)!
        high_res_url = item_data.get("url", stream_url)
        if high_res_url and "=" in high_res_url:
            high_res_url = high_res_url.rsplit("=", 1)[0] + "=s0"
            
        player = ft.Image(
            src=high_res_url,
            expand=True
        )
    elif ("video/" in mime_type or "audio/" in mime_type) and fv:
        # We use fv.Video for BOTH video and audio!
        player_control = fv.Video(
            playlist=[fv.VideoMedia(
                stream_url,
                http_headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                extras={
                    "cache": "yes",
                    "demuxer-max-bytes": "1000000000", # Aggressively buffer up to 1GB in RAM
                    "demuxer-max-back-bytes": "100000000",
                    "hwdec": "auto" # Force hardware acceleration to prevent CPU stuttering
                }
            )],
            autoplay=True,
            expand=True
        )
        
        # If it's audio, add a large music icon behind the player so it's not just a black screen
        if "audio/" in mime_type:
            player = ft.Stack([
                ft.Container(
                    content=ft.Icon(ft.Icons.MUSIC_NOTE, size=150, color="white24"),
                    alignment=ft.Alignment(0, 0),
                    expand=True
                ),
                player_control
            ], expand=True)
        else:
            player = player_control
    elif "video/" in mime_type or "audio/" in mime_type:
        player = ft.Text("Video/Audio player requires the 'flet-video' package. Please install it via pip.", color="red")
    else:
        player = ft.Text("Unsupported media type.", color="red")

    return ft.View(
        route=f"/viewer/{file_name}",
        bgcolor="black", # Pure black for immersive viewing
        appbar=ft.AppBar(
            title=ft.Text(f"Playing: {file_name}", size=14),
            bgcolor="transparent",
        ),
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            player
        ]
    )