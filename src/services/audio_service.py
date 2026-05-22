import flet as ft
import random
import asyncio

try:
    import flet_video as fv
except ImportError:
    try:
        import flet.video as fv
    except ImportError:
        fv = None

class GlobalAudioState:
    def __init__(self, page: ft.Page, engine):
        self.page = page
        self.engine = engine
        
        self.queue = []
        self.original_queue = []
        self.current_index = -1
        self.is_playing = False
        self.is_shuffled = False
        self.loop_mode = 0 # 0: Off, 1: Loop Queue, 2: Loop Song
        
        self.pos_ms = 0
        self.dur_ms = 0
        
        self.ui_callbacks = []
        
        # Start background polling loop
        self.page.run_task(self._poll_loop)
        
    async def _poll_loop(self):
        while True:
            if not self.engine.page:
                break
                
            if self.is_playing and self.queue and self.current_index >= 0:
                try:
                    dur = await self.engine.get_duration()
                    pos = await self.engine.get_current_position()
                    if dur is not None: self.dur_ms = int(dur)
                    if pos is not None: self.pos_ms = int(pos)
                    
                    # Auto-skip detection
                    if self.dur_ms > 0 and self.pos_ms >= self.dur_ms - 500:
                        await self.next()
                        continue
                except Exception: 
                    pass
                
            self.notify_ui()
            await asyncio.sleep(1)
            
    def notify_ui(self):
        for cb in self.ui_callbacks:
            try: cb()
            except Exception: pass
            
    async def play_index(self, index):
        if index < 0 or index >= len(self.queue):
            return
            
        self.current_index = index
        track = self.queue[index]
        stream_url = f"https://www.googleapis.com/drive/v3/files/{track['id']}?alt=media"
        token = self.page.session.store.get("drive_access_token")
        
        if fv and token:
            media = fv.VideoMedia(
                stream_url,
                http_headers={"Authorization": f"Bearer {token}"},
                extras={"cache": "yes", "hwdec": "auto"}
            )
            self.engine.playlist = [media]
            self.engine.update()
            
            # Reset time tracker state immediately before playback updates
            self.pos_ms = 0
            self.dur_ms = 0
            self.is_playing = True
            # Let the Flet UI flush before trying to await play, though Flet usually queues it fine
            self.notify_ui()
            
            try:
                # Slight delay to ensure engine accepted playlist
                await asyncio.sleep(0.1)
                await self.engine.play()
            except Exception:
                pass
        
    async def toggle_play(self):
        if self.is_playing:
            try: await self.engine.pause()
            except: pass
            self.is_playing = False
        else:
            try: await self.engine.play()
            except: pass
            self.is_playing = True
        self.notify_ui()
        
    async def stop_audio(self):
        try: await self.engine.pause()
        except: pass
        self.engine.playlist = []
        try: self.engine.update()
        except: pass
        self.is_playing = False
        self.notify_ui()
            
    async def next(self):
        if self.loop_mode == 2: # Loop Song
            await self.play_index(self.current_index)
        elif self.current_index < len(self.queue) - 1:
            await self.play_index(self.current_index + 1)
        elif self.loop_mode == 1 and self.queue: # Loop Queue
            await self.play_index(0)
        else:
            try: await self.engine.pause()
            except: pass
            self.is_playing = False
            self.pos_ms = 0
            self.notify_ui()
            
    async def prev(self):
        if self.pos_ms > 3000:
            try: await self.engine.seek(0)
            except: pass
            self.pos_ms = 0
        else:
            if self.current_index > 0:
                await self.play_index(self.current_index - 1)
        self.notify_ui()
        
    def add_to_queue(self, track):
        # Add a song without duplicate check if we want to allow same song twice, 
        # but to keep it simple we avoid dupes or identify them.
        # Actually duplicate song IDs in the list can break index lookup later, so only add if not present.
        if not any(t['id'] == track['id'] for t in self.queue):
            self.queue.append(track)
            if not self.is_shuffled:
                self.original_queue.append(track)
        self.notify_ui()
        
    def remove_from_queue(self, index):
        if 0 <= index < len(self.queue):
            track = self.queue.pop(index)
            # Safe remove from original queue
            for idx, orig in enumerate(self.original_queue):
                if orig['id'] == track['id']:
                    self.original_queue.pop(idx)
                    break
            
            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index:
                if self.queue:
                    # Wrapper for async task
                    async def async_play_idx():
                        await self.play_index(min(self.current_index, len(self.queue)-1))
                    self.page.run_task(async_play_idx)
                else:
                    self.current_index = -1
                    self.is_playing = False
                    async def async_pause():
                        try: await self.engine.pause()
                        except: pass
                    self.page.run_task(async_pause)
            self.notify_ui()
            
    def set_queue(self, new_queue, start_index=0):
        self.queue = list(new_queue)
        self.original_queue = list(new_queue)
        self.is_shuffled = False
        
        async def async_play_idx():
            await self.play_index(start_index)
        self.page.run_task(async_play_idx)
        
    def toggle_shuffle(self):
        self.is_shuffled = not self.is_shuffled
        if self.is_shuffled:
            if self.current_index >= 0 and self.queue:
                current_track = self.queue[self.current_index]
                rest = [t for t in self.queue if t['id'] != current_track['id']]
                random.shuffle(rest)
                self.queue = [current_track] + rest
                self.current_index = 0
        else:
            if self.current_index >= 0 and self.queue:
                current_track = self.queue[self.current_index]
                self.queue = list(self.original_queue)
                # Find new index based on ID
                idx = 0
                for i, t in enumerate(self.queue):
                    if t['id'] == current_track['id']:
                        idx = i
                        break
                self.current_index = idx
        self.notify_ui()

    def toggle_loop(self):
        self.loop_mode = (self.loop_mode + 1) % 3
        self.notify_ui()
