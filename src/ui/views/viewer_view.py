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
        
    mime_type = item_data.get("mimeType", "")
    stream_url = f"https://www.googleapis.com/drive/v3/files/{item_data['id']}?alt=media"
    
    # Base layout configurations
    appbar_title = ft.Text(file_name, size=14)
    appbar = ft.AppBar(title=appbar_title, bgcolor="transparent")
    
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
            hr_url = current.get("url", f"https://www.googleapis.com/drive/v3/files/{current['id']}?alt=media")
            if hr_url and "=" in hr_url:
                hr_url = hr_url.rsplit("=", 1)[0] + "=s0"
            
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
        
    # --- CUSTOM AUDIO PLAYER ---
    elif "audio/" in mime_type and fv:
        audio_state = page.session.store.get("audio_state")
        
        # Left Pane: Controls
        cover_url = item_data.get("url", "")
        if cover_url and "=" in cover_url:
            cover_url = cover_url.rsplit("=", 1)[0] + "=s1080"
        if not cover_url:
            cover_url = "https://images.unsplash.com/photo-1614149162883-504ce4d13909?q=80&w=1000&auto=format&fit=crop"
            
        cover_img = ft.Image(src=cover_url, width=280, height=280, fit="cover", border_radius=20)
        title_text = ft.Text(item_data['name'], size=24, weight=ft.FontWeight.W_900, color="white", text_align=ft.TextAlign.CENTER, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
        play_btn = ft.IconButton(ft.Icons.PAUSE_CIRCLE_FILLED_ROUNDED if audio_state and audio_state.is_playing else ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED, icon_size=70, icon_color="white")
        shuffle_btn = ft.IconButton(ft.Icons.SHUFFLE, icon_color=page.theme.color_scheme_seed if audio_state and audio_state.is_shuffled else "white54")
        loop_btn = ft.IconButton(ft.Icons.REPEAT, icon_color="white54")
        
        def on_toggle(e): 
            if audio_state: page.run_task(audio_state.toggle_play)
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
        
        controls_row = ft.Row([
            shuffle_btn,
            ft.IconButton(ft.Icons.SKIP_PREVIOUS, icon_color="white", icon_size=40, on_click=on_prev),
            play_btn,
            ft.IconButton(ft.Icons.SKIP_NEXT, icon_color="white", icon_size=40, on_click=on_next),
            loop_btn
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        left_pane = ft.Container(
            expand=7,
            content=ft.Column([
                ft.Container(content=cover_img, shadow=ft.BoxShadow(spread_radius=5, blur_radius=30, color=ft.Colors.BLACK87)),
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
            
            cover = track.get('url')
            if cover and "=" in cover: cover = cover.rsplit("=", 1)[0] + "=s1080"
            if not cover: cover = "https://images.unsplash.com/photo-1614149162883-504ce4d13909?q=80&w=1000&auto=format&fit=crop"
            
            cover_img.src = cover
            title_text.value = track['name']
            
            play_btn.icon = ft.Icons.PAUSE_CIRCLE_FILLED_ROUNDED if audio_state.is_playing else ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED
            shuffle_btn.icon_color = page.theme.color_scheme_seed if audio_state.is_shuffled else "white54"
            
            if audio_state.loop_mode == 0:
                loop_btn.icon = ft.Icons.REPEAT
                loop_btn.icon_color = "white54"
            elif audio_state.loop_mode == 1:
                loop_btn.icon = ft.Icons.REPEAT
                loop_btn.icon_color = page.theme.color_scheme_seed
            elif audio_state.loop_mode == 2:
                loop_btn.icon = ft.Icons.REPEAT_ONE
                loop_btn.icon_color = page.theme.color_scheme_seed
            
            # Rebuild queue list
            queue_col.controls.clear()
            for i, q_track in enumerate(audio_state.queue):
                is_current = (i == audio_state.current_index)
                
                # capture loop variable
                def make_remove_cb(idx):
                    return lambda e: audio_state.remove_from_queue(idx)
                    
                def make_play_cb(idx):
                    async def play_coro():
                        await audio_state.play_index(idx)
                    return lambda e: page.run_task(play_coro)
                    
                q_row = ft.Container(
                    bgcolor="#333333" if is_current else "transparent",
                    border_radius=5,
                    padding=5,
                    content=ft.Row([
                        ft.GestureDetector(
                            on_tap=make_play_cb(i),
                            mouse_cursor=ft.MouseCursor.CLICK,
                            expand=True,
                            content=ft.Text(q_track['name'], color="white" if is_current else "gray", weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                        ),
                        ft.IconButton(ft.Icons.CLOSE, icon_size=16, icon_color="red" if not is_current else "transparent", tooltip="Remove", on_click=make_remove_cb(i) if not is_current else None)
                    ])
                )
                queue_col.controls.append(q_row)
                
            try: page.update()
            except: pass
            
        if audio_state:
            audio_state.ui_callbacks = [cb for cb in audio_state.ui_callbacks if cb.__name__ != "update_player_ui"]
            audio_state.ui_callbacks.append(update_player_ui)
            update_player_ui()

        # Wrap in a Stack to add the ambient background
        player = ft.Stack([
            ft.Container(
                content=ft.Image(src=cover_img.src, fit="cover", opacity=0.15, expand=True),
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
                http_headers={"Authorization": f"Bearer {token}"},
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
            padding=2
        )
        
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