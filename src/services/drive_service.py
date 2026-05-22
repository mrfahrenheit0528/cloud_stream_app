import urllib.request
import urllib.parse
import json
import asyncio

BASE_URL = "https://www.googleapis.com/drive/v3/files"

async def _fetch_api(url: str, token: str) -> dict:
    """Helper to make an async HTTP GET request to Google APIs."""
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/json')
    
    def fetch():
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_info = e.read().decode('utf-8')
            print(f"Drive API HTTP Error {e.code}: {error_info}")
            if e.code == 401:
                raise Exception("UNAUTHENTICATED")
            return {"files": []}
        except Exception as e:
            print(f"Drive API Error: {e}")
            return {"files": []}
            
    return await asyncio.to_thread(fetch)

async def get_folders(token: str, parent_id: str = "root") -> list:
    """Fetches sub-folders within a specific Drive folder."""
    query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    params = {
        "q": query,
        "fields": "files(id, name)",
        "orderBy": "name"
    }
    qs = urllib.parse.urlencode(params)
    url = f"{BASE_URL}?{qs}"
    
    data = await _fetch_api(url, token)
    return data.get("files", [])

async def get_media(token: str, folder_id: str, include_subfolders: bool = True) -> list:
    """Fetches images, videos, and audio grouped by their parent folder."""
    folders_to_query = [{"id": folder_id, "name": "Root"}]
    
    if include_subfolders:
        subfolders = await get_folders(token, folder_id)
        folders_to_query.extend(subfolders)
        
    async def fetch_for_folder(folder_info):
        fid = folder_info["id"]
        fname = folder_info["name"]
        query = f"'{fid}' in parents and (mimeType contains 'image/' or mimeType contains 'video/' or mimeType contains 'audio/') and trashed=false"
        params = {
            "q": query,
            "fields": "files(id, name, mimeType, thumbnailLink, hasThumbnail, iconLink, imageMediaMetadata, videoMediaMetadata)",
            "orderBy": "createdTime desc"
        }
        qs = urllib.parse.urlencode(params)
        url = f"{BASE_URL}?{qs}"
        
        data = await _fetch_api(url, token)
        return {
            "folder_id": fid,
            "folder_name": fname,
            "files": data.get("files", [])
        }

    # Fetch from all folders concurrently for maximum speed
    results = await asyncio.gather(*[fetch_for_folder(finfo) for finfo in folders_to_query])
    
    return results
