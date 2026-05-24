import urllib.parse
import urllib.request
import urllib.error
import json
import asyncio
import flet as ft

async def initiate_device_flow() -> dict:
    """Start a Microsoft OneDrive Device Authorization flow."""
    from config import ONEDRIVE_CLIENT_ID
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
    data = urllib.parse.urlencode({
        "client_id": ONEDRIVE_CLIENT_ID,
        "scope": "offline_access Files.Read.All User.Read"
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        def fetch():
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        return await asyncio.to_thread(fetch)
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = {}
        raise Exception(f"Device Flow error: {err.get('error_description', str(e))}")

async def poll_device_token(device_code: str, interval: int) -> dict:
    """Poll Microsoft until the user has entered the code on their phone."""
    from config import ONEDRIVE_CLIENT_ID
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    while True:
        data = urllib.parse.urlencode({
            "client_id": ONEDRIVE_CLIENT_ID,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        try:
            def fetch():
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read().decode("utf-8"))
            return await asyncio.to_thread(fetch)
        except urllib.error.HTTPError as e:
            try:
                error_body = json.loads(e.read().decode("utf-8"))
            except Exception:
                error_body = {}
            error_code = error_body.get("error", "")
            if error_code == "authorization_pending":
                await asyncio.sleep(interval)
                continue
            elif error_code == "slow_down":
                interval += 5
                await asyncio.sleep(interval)
                continue
            else:
                raise Exception(f"Token polling error: {error_body.get('error_description', error_code or str(e))}")
        except Exception as e:
            raise Exception(f"Failed to poll device token: {str(e)}")

async def refresh_access_token(refresh_token: str) -> dict:
    """
    Exchange a OneDrive refresh token for a fresh access token and possibly a new refresh token.
    Microsoft access tokens expire after 1 hour but are renewed seamlessly.
    """
    from config import ONEDRIVE_CLIENT_ID
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": ONEDRIVE_CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        def fetch():
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        result = await asyncio.to_thread(fetch)
        if "access_token" not in result:
            raise Exception(result.get("error_description", "No access_token returned"))
        return {
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token", refresh_token)
        }
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = {}
        raise Exception(f"Token refresh failed: {err.get('error_description', str(e))}")

async def fetch_user_profile(access_token: str) -> dict:
    """Retrieve the user's display name and profile picture from Microsoft Graph."""
    try:
        req = urllib.request.Request(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        def fetch():
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        res = await asyncio.to_thread(fetch)
        display_name = res.get("displayName", "User")
        given_name = res.get("givenName", display_name.split(" ")[0])
        
        # Fetch profile photo
        picture_path = ""
        try:
            photo_req = urllib.request.Request(
                "https://graph.microsoft.com/v1.0/me/photo/$value",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            def fetch_photo():
                with urllib.request.urlopen(photo_req) as response:
                    return response.read()
            photo_bytes = await asyncio.to_thread(fetch_photo)
            
            from config import get_persistent_data_dir
            import os
            dest_path = os.path.join(get_persistent_data_dir(), "estreamo_avatar.jpg")
            with open(dest_path, "wb") as f:
                f.write(photo_bytes)
            picture_path = dest_path
        except Exception:
            # Silently ignore photo fetch errors (e.g. 404 if no photo is set)
            pass

        return {
            "given_name": given_name,
            "picture": picture_path
        }
    except Exception:
        return {"given_name": "User", "picture": ""}
