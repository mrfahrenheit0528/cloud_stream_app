import flet as ft
import asyncio
try:
    import flet_video as fv
except ImportError:
    try:
        import flet.video as fv
    except ImportError:
        fv = None

import os

def save_playback_position(file_id: str, position_ms: int):
    try:
        from config import get_persistent_data_dir
        import json
        path = os.path.join(get_persistent_data_dir(), "estreamo_playbacks.json")
        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[file_id] = position_ms
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as ex:
        print(f"Error saving playback: {ex}")

def load_playback_position(file_id: str) -> int:
    try:
        from config import get_persistent_data_dir
        import json
        path = os.path.join(get_persistent_data_dir(), "estreamo_playbacks.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(file_id, 0)
    except Exception:
        pass
    return 0

def format_time(ms):
    s = ms // 1000
    m = s // 60
    h = m // 60
    s = s % 60
    m = m % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"

def viewer_view(page: ft.Page, file_name: str) -> ft.View:
    """Full-screen media player overlay (Route: "/viewer/:file_name")"""
    
    # Retrieve the metadata we passed from the home view
    item_data_raw = page.session.store.get("current_media")
    if not item_data_raw:
        # Flet hot-reloaded or the app was restarted while viewing a media file, wiping the session.
        def redirect(e): page.go("/home")
        page.run_task(redirect)
        return ft.View(f"/viewer/{file_name}", [ft.Text("Restoring session...")], bgcolor="black")
    # Use a mutable dict so in-place video skipping can update the guard without re-creating the view
    item_data = dict(item_data_raw)
    
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
            
        cover_img = ft.Image(src=cover_url, width=200, height=200, fit="cover", border_radius=20)
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
            
        play_btn = build_transport_btn(ft.Icons.PAUSE_CIRCLE_FILLED if audio_state and audio_state.is_playing else ft.Icons.PLAY_CIRCLE_FILLED, 52, "white")
        shuffle_btn = build_transport_btn(ft.Icons.SHUFFLE, 18, page.theme.color_scheme_seed if audio_state and audio_state.is_shuffled else "white54")
        
        # Build a composite 'Loop One' icon to completely bypass missing font glyphs
        loop_base_icon = ft.Icon(ft.Icons.REPEAT, size=18, color="white54")
        loop_one_text = ft.Text("1", size=8, weight=ft.FontWeight.W_900, color=page.theme.color_scheme_seed, visible=False)
        loop_stack = ft.Stack([
            loop_base_icon,
            ft.Container(content=loop_one_text, alignment=ft.Alignment(0, 0))
        ], width=18, height=18)
        loop_btn = build_transport_btn(loop_stack, 18, "white54")
        
        def on_toggle(e): 
            if audio_state: 
                page.run_task(audio_state.toggle_play)
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
        
        prev_btn = build_transport_btn(ft.Icons.SKIP_PREVIOUS, 30, "white", on_prev)
        next_btn = build_transport_btn(ft.Icons.SKIP_NEXT, 30, "white", on_next)

        controls_row = ft.Row([
            shuffle_btn,
            prev_btn,
            play_btn,
            next_btn,
            loop_btn
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        focus_state = {
            "idx": 2,
            "pane": "controls",
            "queue_idx": 0
        }
        
        # No need to mutate engine properties here; audio_service handles secure engine recreation.
        
        left_pane = ft.Container(
            expand=7,
            content=ft.Column([
                ft.Container(content=cover_img, width=200, height=200, shadow=ft.BoxShadow(spread_radius=5, blur_radius=30, color=ft.Colors.BLACK87)),
                ft.Container(height=20),
                title_text,
                ft.Container(height=15),
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
            
            # Dynamic on-demand cover extraction for tracks over index 25 (which weren't cached on home view)
            if not track.get('url') and track.get('stream_url') and not track.get('_art_fetching'):
                track['_art_fetching'] = True
                async def fetch_current_track_art():
                    try:
                        from services.metadata_service import get_audio_metadata
                        meta = await get_audio_metadata(track['stream_url'], track['id'], track['name'])
                        
                        changed = False
                        if meta.get('title') and meta.get('title') != track['name']:
                            track['name'] = meta['title']
                            changed = True
                        if meta.get('cover_path'):
                            track['url'] = meta['cover_path']
                            changed = True
                            
                        if changed:
                            # Re-run update_player_ui safely
                            update_player_ui()
                    except Exception:
                        pass
                page.run_task(fetch_current_track_art)
            
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
            target_idx = 0
            for i, q_track in enumerate(audio_state.queue):
                # Self-healing metadata check: if track name has an extension, check the persistent database cache!
                name_lower = q_track['name'].lower()
                if any(name_lower.endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"]):
                    from config import get_persistent_data_dir
                    cache_dir = os.path.join(get_persistent_data_dir(), "estreamo_metadata_cache")
                    json_path = os.path.join(cache_dir, f"{q_track['id']}.json")
                    if os.path.exists(json_path):
                        try:
                            import json
                            with open(json_path, "r", encoding="utf-8") as f:
                                meta = json.load(f)
                                if meta.get("title"):
                                    q_track['name'] = meta["title"]
                                if meta.get("cover_path") and os.path.exists(meta["cover_path"]):
                                    q_track['url'] = meta["cover_path"]
                        except Exception:
                            pass

                is_current = (i == audio_state.current_index)
                is_focused = (focus_state.get("pane") == "queue" and i == focus_state.get("queue_idx", 0))
                
                if focus_state.get("pane") == "queue":
                    if is_focused:
                        target_idx = i
                else:
                    if is_current:
                        target_idx = i
                
                # Dynamic border and highlight for focused item
                border_val = ft.Border(
                    top=ft.BorderSide(2, ft.Colors.PRIMARY),
                    right=ft.BorderSide(2, ft.Colors.PRIMARY),
                    bottom=ft.BorderSide(2, ft.Colors.PRIMARY),
                    left=ft.BorderSide(2, ft.Colors.PRIMARY)
                ) if is_focused else None
                
                bg_val = "#44FFFFFF" if is_focused else ("#333333" if is_current else "transparent")
                text_color = "white" if (is_current or is_focused) else "gray"
                
                q_row = ft.Container(
                    bgcolor=bg_val,
                    border=border_val,
                    border_radius=5,
                    padding=5,
                    content=ft.Text(q_track['name'], color=text_color, weight=ft.FontWeight.BOLD if (is_current or is_focused) else ft.FontWeight.NORMAL, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                )
                queue_col.controls.append(q_row)
                
            try: page.update()
            except: pass
            
            # Smoothly scroll to the active item in the queue using precise offset calculations!
            if audio_state and len(audio_state.queue) > 0:
                try:
                    # Item height is ~28px + 5px spacing = ~33px
                    target_offset = max(0, (target_idx - 5) * 33)
                    
                    async def scroll_active():
                        import asyncio
                        await asyncio.sleep(0.05) # Super fast settle on direct offset scroll!
                        try:
                            res = queue_col.scroll_to(offset=target_offset, duration=200)
                            if asyncio.iscoroutine(res):
                                await res
                        except: pass
                    page.run_task(scroll_active)
                except: pass
            
        if audio_state:
            audio_state.ui_callbacks = [cb for cb in audio_state.ui_callbacks if cb.__name__ != "update_player_ui"]
            audio_state.ui_callbacks.append(update_player_ui)
            update_player_ui()

        # Define transport D-pad elements, update functions, and key bindings here after update_player_ui is defined
        focus_list = [shuffle_btn, prev_btn, play_btn, next_btn, loop_btn]
        
        def update_audio_focus():
            is_controls = (focus_state.get("pane", "controls") == "controls")
            for i, btn in enumerate(focus_list):
                if is_controls and i == focus_state["idx"]:
                    btn.container_control.bgcolor = "#33FFFFFF" # Subtle highlight
                else:
                    btn.container_control.bgcolor = ft.Colors.TRANSPARENT
            
            # Trigger player UI update to redraw list highlights & auto-scroll
            if audio_state:
                update_player_ui()
            else:
                try: page.update()
                except: pass
            
        update_audio_focus()
        
        def viewer_keyboard(e: ft.KeyboardEvent):
            if e.key in ["Backspace", "Escape", "BrowserBack"]:
                exit_player()
                return
                
            pane = focus_state.get("pane", "controls")
            
            if pane == "controls":
                if e.key == "Arrow Left":
                    focus_state["idx"] = max(0, focus_state["idx"] - 1)
                    update_audio_focus()
                elif e.key == "Arrow Right":
                    focus_state["idx"] = min(len(focus_list) - 1, focus_state["idx"] + 1)
                    update_audio_focus()
                elif e.key in ["Arrow Up", "Arrow Down"]:
                    # Jump focus to the queue list
                    if audio_state and len(audio_state.queue) > 0:
                        focus_state["pane"] = "queue"
                        focus_state["queue_idx"] = max(0, min(audio_state.current_index, len(audio_state.queue) - 1))
                        update_audio_focus()
                elif e.key in ["Enter", "Space", "MediaPlayPause", "Select", "Numpad Enter", "Gamepad Button A"]:
                    btn = focus_list[focus_state["idx"]]
                    if btn.on_click:
                        btn.on_click(None)
                        
            elif pane == "queue":
                if not audio_state or len(audio_state.queue) == 0:
                    focus_state["pane"] = "controls"
                    update_audio_focus()
                    return
                    
                if e.key == "Arrow Up":
                    focus_state["queue_idx"] = max(0, focus_state["queue_idx"] - 1)
                    update_audio_focus()
                elif e.key == "Arrow Down":
                    focus_state["queue_idx"] = min(len(audio_state.queue) - 1, focus_state["queue_idx"] + 1)
                    update_audio_focus()
                elif e.key in ["Arrow Left", "Arrow Right"]:
                    # Jump focus back to the control buttons
                    focus_state["pane"] = "controls"
                    update_audio_focus()
                elif e.key in ["Enter", "Space", "Select", "Numpad Enter", "Gamepad Button A"]:
                    # Play the selected track directly!
                    target_idx = focus_state["queue_idx"]
                    async def play_queue_item():
                        try:
                            await audio_state.play_index(target_idx)
                        except Exception: pass
                    page.run_task(play_queue_item)
                    
        page.session.store.set("keyboard_handler", viewer_keyboard)

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
        if hasattr(page, 'window') and page.window:
            try: page.window.full_screen = True
            except: pass
        saved_pos = load_playback_position(item_data["id"])
        has_saved_pos = saved_pos > 10000

        # Video Queue System
        gallery_list = page.session.store.get("current_gallery") or [item_data]
        video_list = [vid for vid in gallery_list if "video/" in vid.get("mimeType", "")]
        video_queue = []
        current_queue_idx = 0
        
        def rebuild_queue():
            nonlocal video_queue, current_queue_idx
            # Find the clicked item's natural index in the sequential list
            clicked_idx = 0
            for idx, vid in enumerate(video_list):
                if vid["id"] == item_data["id"]:
                    clicked_idx = idx
                    break
            # Shift the queue cyclically so the clicked item sits at index 0, followed sequentially by subsequent items
            video_queue = video_list[clicked_idx:] + video_list[:clicked_idx]
            current_queue_idx = 0
            
        rebuild_queue()
        
        played_indices = {0}
        play_history = [0]

        # Centered premium overlay video title
        video_title_text = ft.Text(
            item_data.get("name", file_name),
            size=20,
            weight=ft.FontWeight.BOLD,
            color="white",
            text_align=ft.TextAlign.CENTER,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS
        )
        video_title_container = ft.Container(
            content=video_title_text,
            alignment=ft.Alignment(0, 0),
            padding=ft.Padding(20, 10, 20, 10),
            bgcolor="#88000000",
            border_radius=10,
            animate_opacity=400,
            opacity=1,
            top=20,
            left=100,  # Ensure symmetric margins so it is perfectly centered and avoids back button
            right=100
        )

        # Video queue is now the canonical playlist order.
        # Build the complete fv.Video playlist from all queue entries upfront.
        # Since stream URLs are direct CDN links (no async resolution needed), this is instantaneous.
        _media_extras = {
            "cache": "yes",
            "demuxer-max-bytes": "67108864",
            "demuxer-max-back-bytes": "16777216",
            "hwdec": "auto",
            "sub-font-size": "36",
            "sub-scale": "0.8",
            "sub-border-size": "2",
            "sub-bg-color": "0.0/0.0/0.0/0.0",  # Remove ugly background block
            "sub-shadow-offset": "1",
            "sub-shadow-color": "0.0/0.0/0.0/0.6"
        }
        full_playlist = [
            fv.VideoMedia(vid.get("stream_url", ""), extras=_media_extras)
            for vid in video_queue
        ]

        # Configure the native player with global options and disable native keybindings to prevent conflicts
        video_config = fv.VideoConfiguration(
            mpv_properties={
                "input-default-bindings": "no",
                "input-vo-keyboard": "no",
                "cache": "yes",
                "demuxer-max-bytes": "67108864",
                "demuxer-max-back-bytes": "16777216",
                "hwdec": "auto",
            }
        )

        # Direct synchronous instantiation of the Video player widget for standard-compliant rendering
        video_engine = fv.Video(
            key=f"video_player_{item_data['id']}",
            playlist=full_playlist,
            autoplay=not has_saved_pos,
            expand=True,
            show_controls=False,
            configuration=video_config,
            on_track_change=lambda e: page.run_task(on_track_changed, e),
            playlist_mode=fv.PlaylistMode.SINGLE
        )

        # Dedicated layout wrapper (no more widget unmounting — it kills the WebSocket)
        video_container = ft.Container(content=video_engine, expand=True)

        async def on_track_changed(e=None):
            """Fires when flet_video/mpv changes the active playlist item via ANY means
            (our jump_to call, mpv's internal key bindings, playlist auto-advance, etc.).
            Keeps Python state in sync with the native player."""
            nonlocal current_queue_idx
            is_skipping[0] = True
            track_playing_started[0] = False
            try:
                raw = getattr(e, "data", None)
                if raw is None:
                    return
                new_idx = int(str(raw).strip())
                if new_idx == current_queue_idx:
                    return  # Already in sync, nothing to do
                if 0 <= new_idx < len(video_queue):
                    # Save position of the previous video before moving to the next one
                    try:
                        save_playback_position(video_queue[current_queue_idx]["id"], 0)
                    except: pass

                    current_queue_idx = new_idx
                    target_vid = video_queue[new_idx]
                    item_data.clear()
                    item_data.update(target_vid)
                    try:
                        page.session.store.set("current_media", target_vid)
                    except Exception: pass
                    # Sync video title in real-time
                    try:
                        video_title_text.value = target_vid.get("name", "")
                        video_title_text.update()
                    except Exception: pass
                    # Sync play/pause UI
                    is_playing[0] = True
                    try:
                        page.session.store.set("video_is_paused", False)
                        btn_play.icon = ft.Icons.PAUSE_ROUNDED
                        btn_play.update()
                    except Exception: pass
                    # Hide resume dialog for any track that wasn't explicitly resumed
                    try:
                        resume_overlay.visible = False
                        resume_overlay.update()
                    except Exception: pass
                    # Wake up controls to show the new title card for 4 seconds, then auto-fade
                    await wake_controls()
            except Exception as ex:
                print(f"[on_track_changed] error: {ex}")
            finally:
                # High-fidelity transition lock: hold skipping status for 2 seconds to let the underlying player fully buffer and start new track
                await asyncio.sleep(2.0)
                is_skipping[0] = False

        async def _do_in_place_skip(target_vid: dict):
            """In-place skip via jump_to() on the pre-built full playlist."""
            is_skipping[0] = True
            track_playing_started[0] = False
            try:
                res = video_engine.jump_to(current_queue_idx)
                if asyncio.iscoroutine(res): await res
            except Exception as ex:
                print(f"[Skip] jump_to({current_queue_idx}) error: {ex}")
                return

            item_data.clear()
            item_data.update(target_vid)

            try:
                video_title_text.value = target_vid.get("name", "")
                video_title_text.update()
            except Exception: pass

            try:
                page.session.store.set("current_media", target_vid)
            except Exception: pass

            is_playing[0] = True
            try:
                page.session.store.set("video_is_paused", False)
                btn_play.icon = ft.Icons.PAUSE_ROUNDED
                btn_play.update()
            except Exception: pass

            try:
                resume_overlay.visible = False
                resume_overlay.update()
            except Exception: pass
            
            await wake_controls()

        is_transitioning = [False]
        is_skipping = [False]
        track_playing_started = [False]

        async def on_next_video(e=None):
            if is_transitioning[0]:
                return
            is_transitioning[0] = True
            is_skipping[0] = True
            track_playing_started[0] = False
            try:
                nonlocal current_queue_idx
                # Save position of the current video before skipping
                try:
                    pos = await video_engine.get_current_position()
                    if pos is not None:
                        pos_ms = pos.in_milliseconds if hasattr(pos, "in_milliseconds") else int(pos)
                        save_playback_position(video_queue[current_queue_idx]["id"], pos_ms)
                except: pass
                
                is_shuffled = page.session.store.get("video_shuffle_enabled") or False
                if is_shuffled:
                    unplayed = set(range(len(video_queue))) - played_indices
                    if not unplayed:
                        exit_fullscreen(None)
                    else:
                        import random
                        target_idx = random.choice(list(unplayed))
                        current_queue_idx = target_idx
                        played_indices.add(target_idx)
                        play_history.append(target_idx)
                        await _do_in_place_skip(video_queue[current_queue_idx])
                else:
                    if current_queue_idx + 1 < len(video_queue):
                        current_queue_idx += 1
                        played_indices.add(current_queue_idx)
                        play_history.append(current_queue_idx)
                        await _do_in_place_skip(video_queue[current_queue_idx])
                    else:
                        exit_fullscreen(None)
            finally:
                await asyncio.sleep(0.3)
                is_transitioning[0] = False

        async def on_prev_video(e=None):
            if is_transitioning[0]:
                return
            is_transitioning[0] = True
            is_skipping[0] = True
            track_playing_started[0] = False
            try:
                nonlocal current_queue_idx
                # Save position of the current video before skipping
                try:
                    pos = await video_engine.get_current_position()
                    if pos is not None:
                        pos_ms = pos.in_milliseconds if hasattr(pos, "in_milliseconds") else int(pos)
                        save_playback_position(video_queue[current_queue_idx]["id"], pos_ms)
                except: pass
                
                is_shuffled = page.session.store.get("video_shuffle_enabled") or False
                if is_shuffled:
                    if len(play_history) > 1:
                        play_history.pop()
                        target_idx = play_history[-1]
                        current_queue_idx = target_idx
                        await _do_in_place_skip(video_queue[current_queue_idx])
                    else:
                        await wake_controls()
                else:
                    if current_queue_idx > 0:
                        current_queue_idx -= 1
                        played_indices.add(current_queue_idx)
                        play_history.append(current_queue_idx)
                        await _do_in_place_skip(video_queue[current_queue_idx])
                    else:
                        await wake_controls()
            finally:
                await asyncio.sleep(0.3)
                is_transitioning[0] = False

        async def on_toggle_shuffle(e=None):
            if is_transitioning[0]:
                return
            is_transitioning[0] = True
            try:
                active_media = page.session.store.get("current_media")
                if not active_media or active_media.get("id") != item_data.get("id"):
                    return
                current_val = page.session.store.get("video_shuffle_enabled") or False
                new_val = not current_val
                page.session.store.set("video_shuffle_enabled", new_val)
                
                is_shuffled = new_val
                shuffle_dot.visible = is_shuffled
                try: shuffle_dot.update()
                except: pass
                
                if focus_state["idx"] == 7: # focused
                    btn_shuffle.bgcolor = ft.Colors.PRIMARY
                    btn_shuffle.icon_color = "black"
                else: # not focused
                    btn_shuffle.bgcolor = ft.Colors.TRANSPARENT
                    btn_shuffle.icon_color = ft.Colors.PRIMARY if is_shuffled else "white"
                
                try: btn_shuffle.update()
                except: pass
                
                # Show a premium Toast/SnackBar notification
                try:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(
                            "Shuffle Active (videos will play randomly)" if new_val else "Shuffle Off (videos will play in order)",
                            color="white",
                            weight=ft.FontWeight.BOLD,
                            size=14
                        ),
                        bgcolor=page.theme.color_scheme_seed if new_val else "#333333",
                        duration=2000
                    )
                    page.snack_bar.open = True
                    page.update()
                except Exception: pass
                
                await wake_controls()
            finally:
                await asyncio.sleep(0.3)
                is_transitioning[0] = False



        
        def exit_fullscreen(e):
            if hasattr(page, 'window_full_screen'):
                page.window_full_screen = False
            if hasattr(page, 'window') and page.window:
                try: page.window.full_screen = False
                except: pass
            
            async def save_and_go():
                try:
                    pos = await video_engine.get_current_position()
                    if pos is not None:
                        pos_ms = pos.in_milliseconds if hasattr(pos, "in_milliseconds") else int(pos)
                        dur = await video_engine.get_duration()
                        dur_ms = dur.in_milliseconds if dur and hasattr(dur, "in_milliseconds") else (int(dur) if dur else 0)
                        current_id = video_queue[current_queue_idx]["id"]
                        if dur_ms > 0 and pos_ms > dur_ms - 15000:
                            save_playback_position(current_id, 0)
                        elif pos_ms > 10000:
                            save_playback_position(current_id, pos_ms)
                except Exception:
                    pass
                
                # Pause before going home (clean stop, no widget unmounting which would crash the WebSocket)
                try:
                    res = video_engine.pause()
                    if asyncio.iscoroutine(res): await res
                except: pass
                
                page.go("/home")
            page.run_task(save_and_go)
            
        back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_size=30,
            icon_color="white",
            on_click=exit_fullscreen,
            width=50,
            height=50,
            bgcolor="#88000000",
            top=20,
            left=20,
            animate_opacity=400,
            opacity=1,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        # Action callbacks for the HUD buttons
        async def seek_relative(ms):
            try:
                pos = await video_engine.get_current_position()
                dur = await video_engine.get_duration()
                if pos is not None:
                    pos_val = pos.in_milliseconds if hasattr(pos, "in_milliseconds") else int(pos)
                    dur_val = dur.in_milliseconds if dur and hasattr(dur, "in_milliseconds") else (int(dur) if dur else 0)
                    
                    if dur_val > 0:
                        new_pos = min(dur_val, max(0, pos_val + ms))
                    else:
                        new_pos = max(0, pos_val + ms)
                        
                    res = video_engine.seek(new_pos)
                    if asyncio.iscoroutine(res):
                        await res
            except Exception as ex:
                print(f"Error seeking: {ex}")
                
        async def on_rewind_large(e=None):
            await seek_relative(-60000)
            await wake_controls()

        async def on_rewind_small(e=None):
            await seek_relative(-10000)
            await wake_controls()
            
        async def on_forward_small(e=None):
            await seek_relative(10000)
            await wake_controls()

        async def on_forward_large(e=None):
            await seek_relative(60000)
            await wake_controls()
            
        is_playing = [not has_saved_pos]
        
        async def on_play_pause(e=None):
            if is_playing[0]:
                try:
                    res = video_engine.pause()
                    if asyncio.iscoroutine(res): await res
                except: pass
                is_playing[0] = False
                page.session.store.set("video_is_paused", True)
                btn_play.icon = ft.Icons.PLAY_ARROW_ROUNDED
            else:
                try:
                    res = video_engine.play()
                    if asyncio.iscoroutine(res): await res
                except: pass
                is_playing[0] = True
                page.session.store.set("video_is_paused", False)
                btn_play.icon = ft.Icons.PAUSE_ROUNDED
            try: btn_play.update()
            except: pass
            await wake_controls()
            
        btn_prev = ft.IconButton(
            icon=ft.Icons.SKIP_PREVIOUS_ROUNDED,
            icon_size=28,
            icon_color="white",
            on_click=lambda e: page.run_task(on_prev_video),
            width=50,
            height=50,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        btn_rewind_large = ft.IconButton(
            icon=ft.Icons.FAST_REWIND_ROUNDED,
            icon_size=28,
            icon_color="white",
            on_click=lambda e: page.run_task(on_rewind_large),
            width=50,
            height=50,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        btn_rewind_small = ft.IconButton(
            icon=ft.Icons.REPLAY_10_ROUNDED,
            icon_size=28,
            icon_color="white",
            on_click=lambda e: page.run_task(on_rewind_small),
            width=50,
            height=50,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        btn_play = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW_ROUNDED if has_saved_pos else ft.Icons.PAUSE_ROUNDED,
            icon_size=36,
            icon_color="white",
            on_click=lambda e: page.run_task(on_play_pause),
            width=60,
            height=60,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        btn_forward_small = ft.IconButton(
            icon=ft.Icons.FORWARD_10_ROUNDED,
            icon_size=28,
            icon_color="white",
            on_click=lambda e: page.run_task(on_forward_small),
            width=50,
            height=50,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        btn_forward_large = ft.IconButton(
            icon=ft.Icons.FAST_FORWARD_ROUNDED,
            icon_size=28,
            icon_color="white",
            on_click=lambda e: page.run_task(on_forward_large),
            width=50,
            height=50,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        btn_next = ft.IconButton(
            icon=ft.Icons.SKIP_NEXT_ROUNDED,
            icon_size=28,
            icon_color="white",
            on_click=lambda e: page.run_task(on_next_video),
            width=50,
            height=50,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        
        is_sp_shuffled = page.session.store.get("video_shuffle_enabled") or False
        btn_shuffle = ft.IconButton(
            icon=ft.Icons.SHUFFLE_ROUNDED,
            icon_size=24,
            icon_color="white",
            on_click=lambda e: page.run_task(on_toggle_shuffle),
            width=50,
            height=50,
            focus_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            splash_color=ft.Colors.TRANSPARENT
        )
        shuffle_dot = ft.Container(
            width=5,
            height=5,
            bgcolor=ft.Colors.GREEN_ACCENT,
            border_radius=2.5,
            visible=is_sp_shuffled,
            margin=ft.Margin(0, -12, 0, 0)  # Shift up slightly to bring it closer to the IconButton
        )
        shuffle_container = ft.Column([
            btn_shuffle,
            shuffle_dot
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)
        
        hud_buttons = [
            btn_prev,
            btn_rewind_large,
            btn_rewind_small,
            btn_play,
            btn_forward_small,
            btn_forward_large,
            btn_next,
            btn_shuffle
        ]
        
        control_bar = ft.Container(
            bgcolor="#DD000000",
            padding=ft.Padding(left=20, right=20, top=10, bottom=10),
            border_radius=15,
            content=ft.Row([
                btn_prev,
                btn_rewind_large,
                btn_rewind_small,
                btn_play,
                btn_forward_small,
                btn_forward_large,
                btn_next,
                shuffle_container
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            animate_opacity=400,
            opacity=1,
            bottom=20,
            left=20,
            right=20
        )

        # Resume playback overlay prompt
        async def do_resume(e=None):
            if not resume_overlay.visible:
                return
            resume_overlay.visible = False
            try:
                res = video_engine.play()
                if asyncio.iscoroutine(res): await res
            except Exception: pass
            focus_state["focus_area"] = "hud"
            focus_state["idx"] = 3 # Play button
            is_playing[0] = True
            page.session.store.set("video_is_paused", False)
            btn_play.icon = ft.Icons.PAUSE_ROUNDED
            update_focus_all()
            
            # Safely seek after the native media source pipeline is fully ready (polls get_duration())
            async def seek_after_load():
                for _ in range(50): # Up to 10 seconds (50 * 200ms)
                    await asyncio.sleep(0.2)
                    try:
                        dur = await video_engine.get_duration()
                        dur_val = dur.in_milliseconds if dur and hasattr(dur, "in_milliseconds") else (int(dur) if dur else 0)
                        if dur_val > 0:
                            res = video_engine.seek(saved_pos)
                            if asyncio.iscoroutine(res): await res
                            break
                    except Exception: pass
            page.run_task(seek_after_load)
            
        async def do_restart(e=None):
            if not resume_overlay.visible:
                return
            resume_overlay.visible = False
            try:
                res = video_engine.play()
                if asyncio.iscoroutine(res): await res
            except Exception: pass
            focus_state["focus_area"] = "hud"
            focus_state["idx"] = 3 # Play button
            is_playing[0] = True
            page.session.store.set("video_is_paused", False)
            btn_play.icon = ft.Icons.PAUSE_ROUNDED
            update_focus_all()

        btn_resume = ft.Button(
            content=ft.Text("Resume", color="black", weight=ft.FontWeight.BOLD, size=15),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(18, 8, 18, 8),
            ),
            on_click=lambda e: page.run_task(do_resume)
        )
        
        btn_restart = ft.Button(
            content=ft.Text("Start Over", color="white", weight=ft.FontWeight.BOLD, size=15),
            style=ft.ButtonStyle(
                bgcolor="white10",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(18, 8, 18, 8),
            ),
            on_click=lambda e: page.run_task(do_restart)
        )

        resume_overlay = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Resume Playback?", size=22, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text(f"Would you like to resume from where you left off at {format_time(saved_pos)}?", size=14, color="white70", text_align=ft.TextAlign.CENTER),
                    ft.Container(height=15),
                    ft.Row([
                        btn_resume,
                        btn_restart
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#EA101010",
                padding=30,
                border_radius=20,
                border=ft.Border.all(1, "white12"),
                width=450,
                height=200,
            ),
            alignment=ft.Alignment(0, 0),
            visible=has_saved_pos,
            expand=True
        )
        
        focus_state = {
            "idx": 0 if has_saved_pos else 3, # Resume gd or Play button
            "focus_area": "resume_dialog" if has_saved_pos else "hud"
        }
        
        def safe_focus(control):
            try:
                if hasattr(control, "focus"):
                    res = control.focus()
                    if asyncio.iscoroutine(res):
                        async def run_focus():
                            try: await res
                            except: pass
                        page.run_task(run_focus)
            except Exception:
                pass
                
        def update_focus_all():
            area = focus_state["focus_area"]
            try:
                is_shuffled = page.session.store.get("video_shuffle_enabled") or False
            except Exception:
                is_shuffled = False
                
            if area == "back":
                safe_focus(back_btn)
                back_btn.bgcolor = ft.Colors.PRIMARY
                back_btn.icon_color = "black"
                for btn in hud_buttons:
                    btn.bgcolor = ft.Colors.TRANSPARENT
                    if btn == btn_shuffle:
                        btn.icon_color = ft.Colors.PRIMARY if is_shuffled else "white"
                        shuffle_dot.visible = is_shuffled
                        try: shuffle_dot.update()
                        except: pass
                    else:
                        btn.icon_color = "white"
            elif area == "resume_dialog":
                back_btn.bgcolor = "#88000000"
                back_btn.icon_color = "white"
                for btn in hud_buttons:
                    btn.bgcolor = ft.Colors.TRANSPARENT
                    if btn == btn_shuffle:
                        btn.icon_color = ft.Colors.PRIMARY if is_shuffled else "white"
                        shuffle_dot.visible = is_shuffled
                        try: shuffle_dot.update()
                        except: pass
                    else:
                        btn.icon_color = "white"
                
                if focus_state["idx"] == 0:
                    btn_resume.style.bgcolor = ft.Colors.PRIMARY
                    btn_resume.content.color = "black"
                    btn_restart.style.bgcolor = "white10"
                    btn_restart.content.color = "white"
                    safe_focus(btn_resume)
                else:
                    btn_resume.style.bgcolor = "white10"
                    btn_resume.content.color = "white"
                    btn_restart.style.bgcolor = ft.Colors.PRIMARY
                    btn_restart.content.color = "black"
                    safe_focus(btn_restart)
            else:
                back_btn.bgcolor = "#88000000"
                back_btn.icon_color = "white"
                idx = focus_state["idx"]
                for i, btn in enumerate(hud_buttons):
                    if i == idx:
                        safe_focus(btn)
                        btn.bgcolor = ft.Colors.PRIMARY
                        btn.icon_color = "black"
                    else:
                        btn.bgcolor = ft.Colors.TRANSPARENT
                        if btn == btn_shuffle:
                            btn.icon_color = ft.Colors.PRIMARY if is_shuffled else "white"
                            shuffle_dot.visible = is_shuffled
                            try: shuffle_dot.update()
                            except: pass
                        else:
                            btn.icon_color = "white"
            try:
                page.update()
            except:
                pass
                
        # Apply initial highlight
        update_focus_all()
        
        async def wake_controls() -> bool:
            page.session.store.set("video_idle_ticks", 0)
            if back_btn.opacity == 0 or control_bar.opacity == 0 or video_title_container.opacity == 0:
                back_btn.opacity = 1
                control_bar.opacity = 1
                video_title_container.opacity = 1
                try:
                    back_btn.update()
                    control_bar.update()
                    video_title_container.update()
                except: pass
                return True
            return False
 
        page.session.store.set("video_is_paused", has_saved_pos)
        page.session.store.set("video_idle_ticks", 0)
 
        async def viewer_keyboard(e: ft.KeyboardEvent):
            woke = await wake_controls()
            
            if e.key in ["Backspace", "Escape", "BrowserBack"]:
                exit_fullscreen(None)
                return
                
            if woke and e.key in ["Arrow Left", "Arrow Right", "Arrow Up", "Arrow Down", "Enter", "Space", "Select", "Numpad Enter", "Gamepad Button A"]:
                return  # Consume the keypress only to wake HUD, don't execute action or navigation immediately
                
            area = focus_state["focus_area"]
            
            if area == "resume_dialog":
                if e.key == "Arrow Left":
                    focus_state["idx"] = 0
                    update_focus_all()
                elif e.key == "Arrow Right":
                    focus_state["idx"] = 1
                    update_focus_all()
                elif e.key in ["Enter", "Space", "Select", "Numpad Enter", "Gamepad Button A"]:
                    if focus_state["idx"] == 0:
                        page.run_task(do_resume)
                    else:
                        page.run_task(do_restart)
                return
 
            if e.key == "Arrow Up":
                focus_state["focus_area"] = "back"
                update_focus_all()
                return
            elif e.key == "Arrow Down":
                focus_state["focus_area"] = "hud"
                update_focus_all()
                return
                
            if area == "back":
                if e.key in ["Enter", "Space", "Select", "Numpad Enter", "Gamepad Button A"]:
                    exit_fullscreen(None)
            else: # "hud"
                if e.key == "Arrow Left":
                    focus_state["idx"] = max(0, focus_state["idx"] - 1)
                    update_focus_all()
                elif e.key == "Arrow Right":
                    focus_state["idx"] = min(len(hud_buttons) - 1, focus_state["idx"] + 1)
                    update_focus_all()
                elif e.key in ["Enter", "Space", "Select", "Numpad Enter", "Gamepad Button A"]:
                    idx = focus_state["idx"]
                    if idx == 0:
                        page.run_task(on_prev_video)
                    elif idx == 1:
                        page.run_task(on_rewind_large)
                    elif idx == 2:
                        page.run_task(on_rewind_small)
                    elif idx == 3:
                        page.run_task(on_play_pause)
                    elif idx == 4:
                        page.run_task(on_forward_small)
                    elif idx == 5:
                        page.run_task(on_forward_large)
                    elif idx == 6:
                        page.run_task(on_next_video)
                    elif idx == 7:
                        page.run_task(on_toggle_shuffle)
            
            if e.key in ["MediaPlayPause", "Media Play Pause"]:
                page.run_task(on_play_pause)
                    
        page.session.store.set("keyboard_handler", viewer_keyboard)
 
        async def video_idle_loop():
            save_ticks = 0
            while True:
                await asyncio.sleep(0.5)
                try:
                    if not hasattr(page, 'route') or not page.route.startswith("/viewer/"):
                        break
                        
                    # Cleanly terminate loop if user navigated to a different media file (prevent multi-loop cascading leaks)
                    active_media = page.session.store.get("current_media")
                    if not active_media or active_media.get("id") != item_data.get("id"):
                        break
                        
                    if focus_state.get("focus_area") == "resume_dialog":
                        continue
                        
                    # Auto-save position every 5 seconds (10 ticks)
                    save_ticks += 1
                    if save_ticks >= 10:
                        save_ticks = 0
                        try:
                            if track_playing_started[0]:
                                pos = await video_engine.get_current_position()
                                dur = await video_engine.get_duration()
                                if pos is not None and dur is not None:
                                    pos_ms = pos.in_milliseconds if hasattr(pos, "in_milliseconds") else int(pos)
                                    dur_ms = dur.in_milliseconds if hasattr(dur, "in_milliseconds") else int(dur)
                                    current_id = video_queue[current_queue_idx]["id"]
                                    
                                    if dur_ms > 0 and pos_ms > dur_ms - 15000:
                                        save_playback_position(current_id, 0)
                                    elif pos_ms > 10000:
                                        save_playback_position(current_id, pos_ms)
                        except Exception:
                            pass
                        
                    # Detect video natural completion in background loop
                    try:
                        pos = await video_engine.get_current_position()
                        dur = await video_engine.get_duration()
                        if pos is not None and dur is not None:
                            pos_ms = pos.in_milliseconds if hasattr(pos, "in_milliseconds") else int(pos)
                            dur_ms = dur.in_milliseconds if hasattr(dur, "in_milliseconds") else int(dur)
                            if dur_ms > 0:
                                # A track has playing started if we see any position that is not the stale completion position of the previous track
                                if not track_playing_started[0]:
                                    if pos_ms < dur_ms - 2000 or pos_ms < 1000 or pos_ms == 0:
                                        track_playing_started[0] = True
                                        
                                if track_playing_started[0] and not is_skipping[0] and not is_transitioning[0]:
                                    if pos_ms > 2000 and pos_ms >= dur_ms - 1500:
                                        is_skipping[0] = True
                                        track_playing_started[0] = False
                                        page.run_task(on_next_video)
                    except: pass

                    # If paused, keep controls visible!
                    if page.session.store.get("video_is_paused"):
                        if back_btn.opacity == 0 or control_bar.opacity == 0 or video_title_container.opacity == 0:
                            back_btn.opacity = 1
                            control_bar.opacity = 1
                            video_title_container.opacity = 1
                            try:
                                back_btn.update()
                                control_bar.update()
                                video_title_container.update()
                            except: pass
                        continue
                        
                    ticks = page.session.store.get("video_idle_ticks") or 0
                    ticks += 1
                    page.session.store.set("video_idle_ticks", ticks)
                    
                    if ticks >= 8: # 4 seconds of idle
                        if back_btn.opacity == 1 or control_bar.opacity == 1 or video_title_container.opacity == 1:
                            back_btn.opacity = 0
                            control_bar.opacity = 0
                            video_title_container.opacity = 0
                            try:
                                back_btn.update()
                                control_bar.update()
                                video_title_container.update()
                            except: pass
                            
                            # Wait for the 400ms fade-out animation to completely finish before updating focus
                            await asyncio.sleep(0.45)
                            
                            # Reset D-pad focus highlight to the Pause button (index 3) once controls are fully hidden
                            focus_state["focus_area"] = "hud"
                            focus_state["idx"] = 3
                            update_focus_all()
                except Exception:
                    # Session or page destroyed, break loop cleanly!
                    break
                    
        page.run_task(video_idle_loop)
        
        player = ft.Stack([
            video_container,
            back_btn,
            video_title_container,
            control_bar,
            resume_overlay
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