import urllib.request
import urllib.parse
import urllib.error
import json
import asyncio
import base64
import http.cookiejar

# Module-level caches for SharePoint business sharing links
_sharepoint_openers = {}  # domain -> opener with its CookieJar
_sharepoint_drive_info = {} # shareToken -> (domain, driveId, rootId)

def get_sharepoint_opener(domain: str):
    if domain not in _sharepoint_openers:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            ('Accept', 'application/json')
        ]
        _sharepoint_openers[domain] = opener
    return _sharepoint_openers[domain]

def get_url_from_share_token(stoken: str) -> str:
    if stoken.startswith("u!"):
        pure_b64 = stoken[2:]
        # Restore padding
        padding = len(pure_b64) % 4
        if padding > 0:
            pure_b64 += "=" * (4 - padding)
        # Restore base64 url safe characters
        raw_b64 = pure_b64.replace("-", "+").replace("_", "/")
        try:
            return base64.b64decode(raw_b64.encode("utf-8")).decode("utf-8")
        except Exception:
            pass
    return ""

async def resolve_sharepoint_share(sharing_url: str):
    """
    Performs cookie handshake and fetches the driveId and rootId for a SharePoint/Business share URL.
    Returns (domain, driveId, rootId).
    """
    parsed = urllib.parse.urlparse(sharing_url)
    domain = parsed.netloc
    
    stoken = get_share_token(sharing_url)
    if stoken in _sharepoint_drive_info:
        return _sharepoint_drive_info[stoken]
        
    def task():
        opener = get_sharepoint_opener(domain)
        # Phase 1: Cookie Handshake
        try:
            opener.open(sharing_url)
        except Exception as e:
            print(f"SharePoint Cookie Handshake failed: {e}")
            raise e
            
        # Phase 2: Fetch root metadata
        root_url = f"https://{domain}/_api/v2.0/shares/{stoken}/root"
        try:
            with opener.open(root_url) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                drive_id = data["parentReference"]["driveId"]
                root_id = data["id"]
                _sharepoint_drive_info[stoken] = (domain, drive_id, root_id)
                return domain, drive_id, root_id
        except Exception as e:
            print(f"SharePoint fetch root metadata failed: {e}")
            raise e
            
    res = await asyncio.to_thread(task)
    return res[0], res[1], res[2]

async def _fetch_sharepoint_api(url: str, domain: str) -> dict:
    """Helper to make an async HTTP GET request to SharePoint direct API using cookies."""
    def fetch():
        opener = get_sharepoint_opener(domain)
        try:
            with opener.open(url) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"SharePoint direct API error on {url}: {e}")
            return {"value": []}
            
    return await asyncio.to_thread(fetch)

async def _fetch_api(url: str, token: str) -> dict:
    """Helper to make an async HTTP GET request to Microsoft Graph APIs, following redirects."""
    
    def fetch():
        current_url = url
        for _ in range(5):
            req = urllib.request.Request(current_url)
            req.add_header('Authorization', f'Bearer {token}')
            req.add_header('Accept', 'application/json')
            try:
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                # Follow 301, 302, 307, 308 redirects automatically!
                if e.code in [301, 302, 307, 308]:
                    loc = e.headers.get('Location')
                    if loc:
                        current_url = loc
                        continue
                
                try:
                    error_info = e.read().decode('utf-8')
                except Exception:
                    error_info = ""
                print(f"OneDrive API HTTP Error {e.code}: {error_info}")
                if e.code == 401:
                    raise Exception("UNAUTHENTICATED")
                break
            except Exception as e:
                print(f"OneDrive API Error: {e}")
                break
        return {"value": []}
            
    return await asyncio.to_thread(fetch)

def get_share_token(sharing_url: str) -> str:
    import base64
    raw_b64 = base64.b64encode(sharing_url.encode("utf-8")).decode("utf-8")
    safe_b64 = raw_b64.replace("+", "-").replace("/", "_").rstrip("=")
    return f"u!{safe_b64}"

def is_sharing_link(url_str: str) -> bool:
    if not url_str:
        return False
    return url_str.startswith("http://") or url_str.startswith("https://")

def parse_folder_path(folder_id: str):
    """Parses folder_id to determine if it is a sharing link or sub-share."""
    if not folder_id:
        return "root", None, None
        
    if is_sharing_link(folder_id):
        token = get_share_token(folder_id)
        return "share_root", token, None
        
    if folder_id.startswith("share_"):
        try:
            parts = folder_id[6:].split(":", 1)
            if len(parts) == 2:
                return "share_item", parts[0], parts[1]
        except Exception:
            pass
            
    return "personal", None, folder_id

async def get_folders(token: str, parent_id: str = "root") -> list:
    """Fetches sub-folders within a specific OneDrive folder."""
    ftype, stoken, fid = parse_folder_path(parent_id)
    
    # Check if we should upgrade to SharePoint guest routing
    if ftype in ["share_root", "share_item"]:
        orig_url = get_url_from_share_token(stoken)
        if orig_url and ".sharepoint.com" in orig_url.lower():
            try:
                await resolve_sharepoint_share(orig_url)
                if ftype == "share_root":
                    ftype = "sharepoint_root"
                else:
                    ftype = "sharepoint_item"
            except Exception as e:
                print(f"Failed to resolve SharePoint guest access: {e}")

    if ftype == "sharepoint_root":
        domain, drive_id, root_id = _sharepoint_drive_info[stoken]
        url = f"https://{domain}/_api/v2.0/drives/{drive_id}/items/{root_id}/children"
        data = await _fetch_sharepoint_api(url, domain)
    elif ftype == "sharepoint_item":
        domain, drive_id, _ = _sharepoint_drive_info[stoken]
        url = f"https://{domain}/_api/v2.0/drives/{drive_id}/items/{fid}/children"
        data = await _fetch_sharepoint_api(url, domain)
    elif ftype == "share_root":
        url = f"https://graph.microsoft.com/v1.0/shares/{stoken}/root/children"
        data = await _fetch_api(url, token)
    elif ftype == "share_item":
        url = f"https://graph.microsoft.com/v1.0/shares/{stoken}/items/{fid}/children"
        data = await _fetch_api(url, token)
    elif not parent_id or parent_id == "root":
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        data = await _fetch_api(url, token)
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}/children"
        data = await _fetch_api(url, token)
        
    raw_items = data.get("value", [])
    
    # Filter for folders only and map to {"id": ..., "name": ...}
    folders = []
    for item in raw_items:
        if "folder" in item:
            # If we are under a share, encode the subfolder's ID to carry the shareToken!
            if ftype in ["share_root", "share_item", "sharepoint_root", "sharepoint_item"]:
                encoded_id = f"share_{stoken}:{item['id']}"
            else:
                encoded_id = item["id"]
                
            folders.append({
                "id": encoded_id,
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
        
        ftype, stoken, sub_fid = parse_folder_path(fid)
        
        # Check if we should upgrade to SharePoint guest routing
        if ftype in ["share_root", "share_item"]:
            orig_url = get_url_from_share_token(stoken)
            if orig_url and ".sharepoint.com" in orig_url.lower():
                try:
                    await resolve_sharepoint_share(orig_url)
                    if ftype == "share_root":
                        ftype = "sharepoint_root"
                    else:
                        ftype = "sharepoint_item"
                except Exception as e:
                    print(f"Failed to resolve SharePoint guest access: {e}")

        if ftype == "sharepoint_root":
            domain, drive_id, root_id = _sharepoint_drive_info[stoken]
            url = f"https://{domain}/_api/v2.0/drives/{drive_id}/items/{root_id}/children?$expand=thumbnails"
            data = await _fetch_sharepoint_api(url, domain)
        elif ftype == "sharepoint_item":
            domain, drive_id, _ = _sharepoint_drive_info[stoken]
            url = f"https://{domain}/_api/v2.0/drives/{drive_id}/items/{sub_fid}/children?$expand=thumbnails"
            data = await _fetch_sharepoint_api(url, domain)
        elif ftype == "share_root":
            url = f"https://graph.microsoft.com/v1.0/shares/{stoken}/root/children?$expand=thumbnails"
            data = await _fetch_api(url, token)
        elif ftype == "share_item":
            url = f"https://graph.microsoft.com/v1.0/shares/{stoken}/items/{sub_fid}/children?$expand=thumbnails"
            data = await _fetch_api(url, token)
        elif fid == "root":
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children?$expand=thumbnails"
            data = await _fetch_api(url, token)
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
            
            if not (is_video or is_audio or is_image):
                if name_lower.endswith((".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v")):
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
            download_url = item.get("@microsoft.graph.downloadUrl") or item.get("@content.downloadUrl") or ""
            
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
