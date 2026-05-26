import asyncio
import os
import json
import urllib.request
import io
from urllib.error import HTTPError

# We will lazily import mutagen so the app doesn't crash if it's not installed yet
mutagen = None

from config import get_persistent_data_dir
CACHE_DIR = os.path.join(get_persistent_data_dir(), "estreamo_metadata_cache")

# Create the cache directory if it doesn't exist
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)

# To prevent Google Drive API from blocking us for Too Many Requests
# we limit concurrent ID3 parsing downloads to 5 at a time.
download_semaphore = asyncio.Semaphore(5)

async def _download_partial_file(stream_url: str, chunk_size: int = 512000) -> bytes:
    """Downloads the first chunk_size bytes of a file from OneDrive."""
    if not stream_url:
        return None
        
    # Resolve the redirect to a direct CDN stream first!
    from services.onedrive_service import get_direct_stream_url_sync
    resolved_url = get_direct_stream_url_sync(stream_url)
    
    parsed = urllib.parse.urlparse(resolved_url)
    domain = parsed.netloc
    
    is_sp = ".sharepoint.com" in domain.lower()
    
    if is_sp:
        from services.onedrive_service import get_sharepoint_opener
        opener = get_sharepoint_opener(domain)
        req = urllib.request.Request(resolved_url)
        req.add_header('Range', f'bytes=0-{chunk_size}')
        def fetch():
            try:
                with opener.open(req, timeout=8) as response:
                    return response.read()
            except HTTPError as e:
                if e.code in (200, 206):
                    return e.read()
                print(f"Failed to fetch partial SharePoint file: {e.code}")
                return None
            except Exception as e:
                print(f"Error fetching partial SharePoint file: {e}")
                return None
    else:
        req = urllib.request.Request(resolved_url)
        req.add_header('Range', f'bytes=0-{chunk_size}')
        req.add_header('User-Agent', 'Mozilla/5.0')
        def fetch():
            try:
                with urllib.request.urlopen(req, timeout=8) as response:
                    return response.read()
            except HTTPError as e:
                if e.code in (200, 206):
                    return e.read()
                print(f"Failed to fetch partial file: {e.code}")
                return None
            except Exception as e:
                print(f"Error fetching partial file: {e}")
                return None
                
    return await asyncio.to_thread(fetch)

async def get_audio_metadata(stream_url: str, file_id: str, original_filename: str):
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
        file_bytes = await _download_partial_file(stream_url)
        
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
