import asyncio
import os
import json
import urllib.request
import io
from urllib.error import HTTPError

# We will lazily import mutagen so the app doesn't crash if it's not installed yet
mutagen = None

CACHE_DIR = os.path.join(os.getcwd(), "src", ".metadata_cache")

# Create the cache directory if it doesn't exist
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)

# To prevent Google Drive API from blocking us for Too Many Requests
# we limit concurrent ID3 parsing downloads to 5 at a time.
download_semaphore = asyncio.Semaphore(5)

async def _download_partial_file(file_id: str, token: str, chunk_size: int = 512000) -> bytes:
    """Downloads the first chunk_size bytes of a file from Google Drive."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Range', f'bytes=0-{chunk_size}')
    
    def fetch():
        try:
            with urllib.request.urlopen(req) as response:
                return response.read()
        except HTTPError as e:
            # 206 Partial Content is actually a success for Range requests!
            if e.code == 206:
                return e.read()
            print(f"Failed to fetch partial file {file_id}: {e.code}")
            return None
        except Exception as e:
            print(f"Error fetching partial file {file_id}: {e}")
            return None
            
    return await asyncio.to_thread(fetch)

async def get_audio_metadata(file_id: str, token: str, original_filename: str):
    """
    Checks the local cache for the file's ID3 metadata and album art.
    If not found, downloads the first 500KB of the file, parses the ID3 tags,
    saves the album art as a JPG, and caches the metadata to disk.
    """
    global mutagen
    if mutagen is None:
        try:
            import mutagen
            from mutagen.id3 import ID3
            from mutagen.mp4 import MP4
        except ImportError:
            return {"title": original_filename, "cover_path": None}

    json_path = os.path.join(CACHE_DIR, f"{file_id}.json")
    
    # 1. Check if we already have it cached!
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            pass

    # 2. Not cached. We must download and parse it.
    async with download_semaphore:
        print(f"Downloading ID3 chunk for {original_filename}...")
        file_bytes = await _download_partial_file(file_id, token)
        
        if not file_bytes:
            return {"title": original_filename, "cover_path": None}
            
        file_obj = io.BytesIO(file_bytes)
        
        title = original_filename
        cover_path = None
        
        try:
            from mutagen.id3 import ID3
            from mutagen.mp4 import MP4
            from mutagen.flac import FLAC
            
            # Attempt to parse as ID3 (MP3)
            try:
                tags = ID3(file_obj)
                
                # Extract Title (TIT2)
                if 'TIT2' in tags:
                    title = str(tags['TIT2'])
                    
                # Extract Album Art (APIC)
                apic_frames = tags.getall('APIC')
                if apic_frames:
                    art_data = apic_frames[0].data
                    cover_filename = f"{file_id}.jpg"
                    cover_path = os.path.join(CACHE_DIR, cover_filename)
                    with open(cover_path, "wb") as img_file:
                        img_file.write(art_data)
            except Exception:
                # Fallback for MP4/M4A or FLAC
                pass
                
        except Exception as e:
            print(f"Error parsing tags for {original_filename}: {e}")
            
        # 3. Save to Cache
        cache_data = {"title": title, "cover_path": cover_path}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
            
        return cache_data
