import urllib.request
import urllib.parse
import urllib.error
import json
import asyncio

async def _fetch_api(url: str, token: str) -> dict:
    """Helper to make an async HTTP GET request to Microsoft Graph APIs."""
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/json')
    
    def fetch():
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_info = e.read().decode('utf-8')
            print(f"OneDrive API HTTP Error {e.code}: {error_info}")
            if e.code == 401:
                raise Exception("UNAUTHENTICATED")
            return {"value": []}
        except Exception as e:
            print(f"OneDrive API Error: {e}")
            return {"value": []}
            
    return await asyncio.to_thread(fetch)

async def get_folders(token: str, parent_id: str = "root") -> list:
    """Fetches sub-folders within a specific OneDrive folder."""
    if not parent_id or parent_id == "root":
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}/children"
        
    data = await _fetch_api(url, token)
    raw_items = data.get("value", [])
    
    # Filter for folders only and map to {"id": ..., "name": ...}
    folders = []
    for item in raw_items:
        if "folder" in item:
            folders.append({
                "id": item["id"],
                "name": item["name"]
            })
    return folders

async def get_media(token: str, folder_id: str, include_subfolders: bool = True) -> list:
    """Fetches images, videos, and audio grouped by their parent folder from OneDrive."""
    if not folder_id:
        folder_id = "root"
    folders_to_query = [{"id": folder_id, "name": "Root"}]
    
    if include_subfolders:
        subfolders = await get_folders(token, folder_id)
        folders_to_query.extend(subfolders)
        
    async def fetch_for_folder(folder_info):
        fid = folder_info["id"]
        fname = folder_info["name"]
        
        # Expand thumbnails to get images efficiently in one call
        if fid == "root":
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children?$expand=thumbnails"
        else:
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{fid}/children?$expand=thumbnails"
            
        data = await _fetch_api(url, token)
        raw_items = data.get("value", [])
        
        files = []
        for item in raw_items:
            # Skip folders
            if "folder" in item:
                continue
                
            # Check if it's a file
            file_meta = item.get("file", {})
            mime_type = file_meta.get("mimeType", "")
            
            # Determine category based on MIME type, Graph facets, or file extension
            is_video = False
            is_audio = False
            is_image = False
            
            name_lower = item["name"].lower()
            
            if "video" in item:
                is_video = True
            elif "audio" in item:
                is_audio = True
            elif "image" in item:
                is_image = True
            elif mime_type.startswith("video/"):
                is_video = True
            elif mime_type.startswith("audio/"):
                is_audio = True
            elif mime_type.startswith("image/"):
                is_image = True
            elif name_lower.endswith((".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v")):
                is_video = True
            elif name_lower.endswith((".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma")):
                is_audio = True
            elif name_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff")):
                is_image = True
                
            if not (is_video or is_audio or is_image):
                continue
                
            # Coerce the MIME type to a valid category so Flet UI routes and players handle it properly
            if is_video and not mime_type.startswith("video/"):
                mime_type = "video/mp4"
            elif is_audio and not mime_type.startswith("audio/"):
                mime_type = "audio/mpeg"
            elif is_image and not mime_type.startswith("image/"):
                mime_type = "image/jpeg"
                
            # Get direct streaming URL (CDN link)
            download_url = item.get("@microsoft.graph.downloadUrl", "")
            
            # Get thumbnail URL
            thumbnails = item.get("thumbnails", [])
            thumbnail_url = ""
            if thumbnails:
                sizes = thumbnails[0]
                thumbnail_url = sizes.get("large", {}).get("url", sizes.get("medium", {}).get("url", ""))
            
            # Fallback to thumbnail_url if no download_url exists, or vice versa
            if not thumbnail_url and is_image:
                thumbnail_url = download_url
                
            files.append({
                "id": item["id"],
                "name": item["name"],
                "mimeType": mime_type,
                "url": download_url, # Direct streaming / image link
                "thumbnailLink": thumbnail_url,
                "hasThumbnail": bool(thumbnail_url),
                "iconLink": "",
                "audio": item.get("audio") or {},
            })
            
        return {
            "folder_id": fid,
            "folder_name": fname,
            "files": files
        }
        
    results = await asyncio.gather(*[fetch_for_folder(finfo) for finfo in folders_to_query])
    return results

def get_direct_stream_url_sync(url: str) -> str:
    """Modern media engines follow redirects natively, so we return the direct stream link immediately."""
    return url

async def get_direct_stream_url(url: str) -> str:
    """Modern media engines follow redirects natively, so we return the direct stream link immediately."""
    return url
