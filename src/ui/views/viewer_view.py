import flet as ft
try:
    import flet_video as fv
except ImportError:
    try:
        import flet.video as fv
    except ImportError:
        fv = None

import os

def viewer_view(page: ft.Page, file_name: str) -> ft.View:
    """Full-screen media player overlay (Route: "/viewer/:file_name")"""
    
    # Retrieve the metadata we passed from the home view
    item_data = page.session.store.get("current_media")
    if not item_data:
        # Flet hot-reloaded or the app was restarted while viewing a media file, wiping the session.
        def redirect(e): page.go("/home")
        page.run_task(redirect)
        return ft.View(f"/viewer/{file_name}", [ft.Text("Restoring session...")], bgcolor="black")
    
    token = page.session.store.get("onedrive_access_token")
    
    if not token:
        return ft.View(
            route=f"/viewer/{file_name}",
            bgcolor="black",
            appbar=ft.AppBar(title=ft.Text("Error"), bgcolor="transparent"),
            controls=[ft.Text("Media data lost. Please go back.", color="red")]
        )
        
    mime_type = item_data.get("mimeType", "")
    
    # Follow HTTP redirects in Python first to give the player a raw CDN stream URL
    from services.onedrive_service import get_direct_stream_url_sync
    stream_url = get_direct_stream_url_sync(item_data.get("stream_url", ""))
    
    # Base layout configurations
    category = item_data.get("category", file_name)
    appbar_title = ft.Text(category, size=14)
    
    def exit_player():
        audio_state = page.session.store.get("audio_state")
        if audio_state and "audio/" in mime_type:
            page.run_task(audio_state.stop_audio)
        page.go("/home")
        
    custom_back_btn = ft.GestureDetector(
        content=ft.Container(
            content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, color="white", size=20),
            padding=10
        ),
        on_tap=lambda e: exit_player(),
        mouse_cursor=ft.MouseCursor.CLICK
    )

    appbar = ft.AppBar(
        leading=custom_back_btn,
        leading_width=50,
        title=appbar_title, 
        bgcolor="transparent", 
        automatically_imply_leading=False
    )
    
    # --- IMAGE GALLERY PLAYER ---
    if "image/" in mime_type:
        gallery_list = page.session.store.get("current_gallery") or [item_data]
        photo_list = [img for img in gallery_list if "image/" in img.get("mimeType", "")]
        if not photo_list:
            photo_list = [item_data]
            
        state = {"idx": 0}
        for i, p in enumerate(photo_list):
            if p["id"] == item_data["id"]:
                state["idx"] = i
                break
                
        img_control = ft.Image(src="", expand=True, fit="contain")
        
        def update_gallery(idx):
            state["idx"] = idx
            current = photo_list[idx]
            from services.onedrive_service import get_direct_stream_url_sync
            hr_url = get_direct_stream_url_sync(current.get("stream_url", ""))
            
            img_control.src = hr_url
            appbar_title.value = current["name"]
            
            left_btn.opacity = 1 if idx > 0 else 0
            left_btn.disabled = not (idx > 0)
            
            right_btn.opacity = 1 if idx < len(photo_list) - 1 else 0
            right_btn.disabled = not (idx < len(photo_list) - 1)
            
            page.update()

        def on_prev(e):
            if state["idx"] > 0:
                update_gallery(state["idx"] - 1)
                
        def on_next(e):
            if state["idx"] < len(photo_list) - 1:
                update_gallery(state["idx"] + 1)
                
        left_btn = ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_size=60, on_click=on_prev, icon_color="white", opacity=0, disabled=True)
        right_btn = ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_size=60, on_click=on_next, icon_color="white", opacity=0, disabled=True)
        
        player = ft.Stack([
            ft.Container(content=img_control, alignment=ft.Alignment(0,0), expand=True),
            ft.Container(content=left_btn, left=20, top=0, bottom=0, alignment=ft.Alignment(0,0)),
            ft.Container(content=right_btn, right=20, top=0, bottom=0, alignment=ft.Alignment(0,0)),
        ], expand=True)
        
        update_gallery(state["idx"]) # Initial render
        
        def viewer_keyboard(e: ft.KeyboardEvent):
            if e.key == "Arrow Left":
                on_prev(None)
            elif e.key == "Arrow Right":
                on_next(None)
            elif e.key == "Backspace" or e.key == "Escape":
                page.go("/home")
        page.session.store.set("keyboard_handler", viewer_keyboard)
        
    # --- CUSTOM AUDIO PLAYER ---
    elif "audio/" in mime_type:
        audio_state = page.session.store.get("audio_state")
        
        def resolve_cover_url(url, stream_url=""):
            """Resolve a track's thumbnail URL. Returns 'Logo.png' as fallback."""
            if not url:
                return "Logo.png"
            if not url.startswith("http") and not os.path.isabs(url):
                return "Logo.png"
            # OneDrive thumbnail service URL → valid image, use as-is
            if "mediap.svc.ms" in url or "microsoftpersonalcontent.com" in url:
                return url
            # Google Drive image URL → force high-res
            if "googleusercontent.com" in url and "=" in url:
                return url.rsplit("=", 1)[0] + "=s1080"
            # Reject if url points to an audio file itself
            from urllib.parse import urlparse
            path = urlparse(url).path.lower()
            if any(path.endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"]):
                return "Logo.png"
            if url == stream_url:
                return "Logo.png"
            return url
        
        # Left Pane: Controls
        cover_url = resolve_cover_url(item_data.get("url", ""), item_data.get("stream_url", ""))
            
        cover_img = ft.Image(src=cover_url, width=280, height=280, fit="cover", border_radius=20)
        title_text = ft.Text(item_data['name'], size=24, weight=ft.FontWeight.W_900, color="white", text_align=ft.TextAlign.CENTER, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
        def build_transport_btn(icon_name_or_control, size, color, on_click=None):
            icon = icon_name_or_control if isinstance(icon_name_or_control, ft.Control) else ft.Icon(icon_name_or_control, size=size, color=color)
            container = ft.Container(
                content=icon,
                padding=10,
                border_radius=50,
                bgcolor=ft.Colors.TRANSPARENT
            )
            
            def handle_tap(e):
                if hasattr(btn, "on_click") and btn.on_click:
                    btn.on_click(e)
                    
            btn = ft.GestureDetector(
                content=container,
                on_tap=handle_tap,
                mouse_cursor=ft.MouseCursor.CLICK
            )
            btn.icon_control = icon
            btn.container_control = container
            btn.on_click = on_click
            return btn
            
        play_btn = build_transport_btn(ft.Icons.PAUSE_CIRCLE_FILLED if audio_state and audio_state.is_playing else ft.Icons.PLAY_CIRCLE_FILLED, 70, "white")
        shuffle_btn = build_transport_btn(ft.Icons.SHUFFLE, 24, page.theme.color_scheme_seed if audio_state and audio_state.is_shuffled else "white54")
        
        # Build a composite 'Loop One' icon to completely bypass missing font glyphs
        loop_base_icon = ft.Icon(ft.Icons.REPEAT, size=24, color="white54")
        loop_one_text = ft.Text("1", size=10, weight=ft.FontWeight.W_900, color=page.theme.color_scheme_seed, visible=False)
        loop_stack = ft.Stack([
            loop_base_icon,
            ft.Container(content=loop_one_text, alignment=ft.Alignment(0, 0))
        ], width=24, height=24)
        
        loop_btn = build_transport_btn(loop_stack, 24, "white54")
        
        def on_toggle(e): 
            if audio_state: 
                page.run_task(audio_state.toggle_play)
            else:
        def on_prev(e): 
            if audio_state: page.run_task(audio_state.prev)
        def on_next(e): 
            if audio_state: page.run_task(audio_state.next)
        def on_shuffle(e):
            if audio_state: audio_state.toggle_shuffle()
        def on_loop(e):
            if audio_state: audio_state.toggle_loop()
            
        play_btn.on_click = on_toggle
        shuffle_btn.on_click = on_shuffle
        loop_btn.on_click = on_loop
        
        prev_btn = build_transport_btn(ft.Icons.SKIP_PREVIOUS, 40, "white", on_prev)
        next_btn = build_transport_btn(ft.Icons.SKIP_NEXT, 40, "white", on_next)

        controls_row = ft.Row([
            shuffle_btn,
            prev_btn,
            play_btn,
            next_btn,
            loop_btn
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        focus_list = [shuffle_btn, prev_btn, play_btn, next_btn, loop_btn]
        focus_state = {"idx": 2}
        
        def update_audio_focus():
            for i, btn in enumerate(focus_list):
                if i == focus_state["idx"]:
                    btn.container_control.bgcolor = "#33FFFFFF" # Subtle highlight
                else:
                    btn.container_control.bgcolor = ft.Colors.TRANSPARENT
            try: page.update()
            except: pass
            
        update_audio_focus()
        


        def viewer_keyboard(e: ft.KeyboardEvent):
            if e.key in ["Backspace", "Escape", "BrowserBack"]:
                exit_player()
            elif e.key == "Arrow Left":
                focus_state["idx"] = max(0, focus_state["idx"] - 1)
                update_audio_focus()
            elif e.key == "Arrow Right":
                focus_state["idx"] = min(len(focus_list) - 1, focus_state["idx"] + 1)
                update_audio_focus()
            elif e.key in ["Enter", "Space", "MediaPlayPause"]:
                btn = focus_list[focus_state["idx"]]
                if btn.on_click:
                    btn.on_click(None)
                    
        page.session.store.set("keyboard_handler", viewer_keyboard)
        
        # No need to mutate engine properties here; audio_service handles secure engine recreation.
        
        left_pane = ft.Container(
            expand=7,
            content=ft.Column([
                ft.Container(content=cover_img, width=280, height=280, shadow=ft.BoxShadow(spread_radius=5, blur_radius=30, color=ft.Colors.BLACK87)),
                ft.Container(height=30),
                title_text,
                ft.Container(height=20),
                controls_row
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        
        # Right Pane: Queue
        queue_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=5)
        
        right_pane = ft.Container(
            expand=3,
            bgcolor="#1A1A1A",
            padding=20,
            content=ft.Column([
                ft.Text("Next in Queue", size=20, weight=ft.FontWeight.BOLD, color="white"),
                ft.Divider(color="white24"),
                queue_col
            ])
        )
        
        def update_player_ui():
            if not audio_state or audio_state.current_index < 0:
                return
            
            track = audio_state.queue[audio_state.current_index]
            
            cover = resolve_cover_url(track.get('url', ''), track.get('stream_url', ''))
            
            # Update current_media in session so the back button / viewer rebuild stays correct
            page.session.store.set("current_media", track)
            
            cover_img.src = cover
            if "bg_img" in focus_state:
                focus_state["bg_img"].src = cover
            title_text.value = track['name']
            
            play_btn.icon_control.icon = ft.Icons.PAUSE_CIRCLE_FILLED if audio_state.is_playing else ft.Icons.PLAY_CIRCLE_FILLED
            shuffle_btn.icon_control.color = page.theme.color_scheme_seed if audio_state.is_shuffled else "white54"
            
            if audio_state.loop_mode == 0:
                loop_base_icon.color = "white54"
                loop_one_text.visible = False
            elif audio_state.loop_mode == 1:
                loop_base_icon.color = page.theme.color_scheme_seed
                loop_one_text.visible = False
            elif audio_state.loop_mode == 2:
                loop_base_icon.color = page.theme.color_scheme_seed
                loop_one_text.visible = True
            
            def safe_update(ctrl):
                try: ctrl.update()
                except: pass
                
            safe_update(loop_base_icon)
            safe_update(loop_one_text)
            safe_update(cover_img)
            safe_update(title_text)
            safe_update(play_btn.icon_control)
            safe_update(shuffle_btn.icon_control)
            if "bg_img" in focus_state:
                safe_update(focus_state["bg_img"])
            
            # Rebuild queue list
            queue_col.controls.clear()
            for i, q_track in enumerate(audio_state.queue):
                is_current = (i == audio_state.current_index)
                
                q_row = ft.Container(
                    bgcolor="#333333" if is_current else "transparent",
                    border_radius=5,
                    padding=5,
                    content=ft.Text(q_track['name'], color="white" if is_current else "gray", weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                )
                queue_col.controls.append(q_row)
                
            try: page.update()
            except: pass
            
        if audio_state:
            audio_state.ui_callbacks = [cb for cb in audio_state.ui_callbacks if cb.__name__ != "update_player_ui"]
            audio_state.ui_callbacks.append(update_player_ui)
            update_player_ui()

        bg_img = ft.Image(src=cover_img.src, fit="cover", opacity=0.15, expand=True)
        focus_state["bg_img"] = bg_img

        # Wrap in a Stack to add the ambient background
        player = ft.Stack([
            ft.Container(
                content=bg_img,
                left=0, right=0, top=0, bottom=0
            ),
            ft.Row([left_pane, right_pane], expand=True)
        ], expand=True)

    # --- NATIVE VIDEO PLAYER ---
    elif "video/" in mime_type and fv:
        # Fullscreen distraction-free video!
        appbar = None 
        if hasattr(page, 'window_full_screen'):
            page.window_full_screen = True
        elif hasattr(page, 'window'):
            page.window.full_screen = True
            
        video_engine = fv.Video(
            playlist=[fv.VideoMedia(
                stream_url,
                extras={
                    "cache": "yes",
                    "demuxer-max-bytes": "1000000000",
                    "demuxer-max-back-bytes": "100000000",
                    "hwdec": "auto"
                }
            )],
            autoplay=True,
            expand=True
        )
        
        def exit_fullscreen(e):
            if hasattr(page, 'window_full_screen'):
                page.window_full_screen = False
            elif hasattr(page, 'window'):
                page.window.full_screen = False
            page.update()
            page.go("/home")
            
        back_btn = ft.Container(
            content=ft.IconButton(ft.Icons.ARROW_BACK, icon_size=30, icon_color="white", on_click=exit_fullscreen),
            top=20, left=20,
            bgcolor="#88000000", # Semi-transparent black background
            border_radius=50,
            padding=2,
            animate_opacity=400,
            opacity=1
        )
        
        import asyncio
        async def wake_controls():
            ticks = page.session.store.get("video_idle_ticks") or 0
            
            # If the controls have faded out natively, force Flutter to rebuild the overlay
            if ticks >= 5:
                try:
                    video_engine.show_controls = False
                    video_engine.update()
                    await asyncio.sleep(0.05) # Micro-delay ensures the websocket transmits both states
                    video_engine.show_controls = True
                    video_engine.update()
                except Exception: pass
                
            back_btn.opacity = 1
            try: back_btn.update()
            except Exception: pass
            
            page.session.store.set("video_idle_ticks", 0)

        is_playing = [True]
        page.session.store.set("video_is_paused", False)
        page.session.store.set("video_idle_ticks", 0)

        async def viewer_keyboard(e: ft.KeyboardEvent):
            await wake_controls()
            
            if e.key in ["Backspace", "Escape", "BrowserBack"]:
                exit_fullscreen(None)
                return
                
            if e.key in ["Enter", "Space", "MediaPlayPause"]:
                if is_playing[0]:
                    try: video_engine.pause()
                    except: pass
                    is_playing[0] = False
                    page.session.store.set("video_is_paused", True)
                else:
                    try: video_engine.play()
                    except: pass
                    is_playing[0] = True
                    page.session.store.set("video_is_paused", False)
                    
        page.session.store.set("keyboard_handler", viewer_keyboard)

        import asyncio
        async def video_idle_loop():
            while True:
                await asyncio.sleep(0.5)
                if not hasattr(page, 'route') or not page.route.startswith("/viewer/"):
                    break
                    
                if page.session.store.get("video_is_paused"):
                    if back_btn.opacity == 0:
                        back_btn.opacity = 1
                        try: back_btn.update()
                        except: pass
                    continue
                    
                ticks = page.session.store.get("video_idle_ticks") or 0
                ticks += 1
                page.session.store.set("video_idle_ticks", ticks)
                
                if ticks == 6: # 3 seconds
                    back_btn.opacity = 0
                    try: back_btn.update()
                    except: pass
                    
        page.run_task(video_idle_loop)
        
        player = ft.Stack([
            ft.Container(content=video_engine, expand=True),
            back_btn
        ], expand=True)
    else:
        player = ft.Text("Unsupported media type.", color="red")

    return ft.View(
        route=f"/viewer/{file_name}",
        bgcolor="black", # Pure black for immersive viewing
        appbar=appbar,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        padding=0,
        controls=[
            player
        ]
    )