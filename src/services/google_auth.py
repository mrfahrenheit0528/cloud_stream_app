import flet as ft
from flet.auth.providers import GoogleOAuthProvider
import os
import asyncio
import json
import os

# Scopes requested from Google — passed to page.login(scope=...) at call site.
GOOGLE_SCOPES = [
    "profile",
    "email",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_google_provider() -> GoogleOAuthProvider:
    """
    Initializes and returns the Google OAuth Provider using credentials
    from the .env file.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    # Must match one of the Authorised Redirect URIs in Google Cloud Console.
    # In Flet 0.85, the internal FastAPI web app automatically listens on
    # exactly "/oauth_callback" to process logins.
    redirect_url = os.environ.get(
        "GOOGLE_REDIRECT_URL", "http://localhost:8550/oauth_callback"
    )

    if not client_id or not client_secret:
        print("WARNING: Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env file.")

    return GoogleOAuthProvider(
        client_id=client_id,
        client_secret=client_secret,
        redirect_url=redirect_url,
    )


async def handle_login_result(e: ft.LoginEvent, page: ft.Page):
    """
    Async callback fired by page.on_login when Google OAuth completes.
    """
    try:
        if e.error:
            print(f"Login failed: {e.error} - {e.error_description}")
            return

        if page.auth is None:
            print("Login error: page.auth is None after login event.")
            return

        token = await page.auth.get_token()
        if token is None:
            print("Login error: get_token() returned None.")
            return

        access_token = token.access_token

        given_name = "User"
        picture_url = ""
        if page.auth.user:
            given_name = page.auth.user.get("given_name", page.auth.user.get("name", "User"))
            picture_url = page.auth.user.get("picture", "")

        print(f"Login successful for '{given_name}'. Storing token and navigating...")

        import os, tempfile, json
        token_cache_path = os.path.join(tempfile.gettempdir(), "estreamo_token.json")
        try:
            with open(token_cache_path, "w") as f:
                json.dump({
                    "access_token": access_token,
                    "given_name": given_name,
                    "picture_url": picture_url
                }, f)
        except Exception as err:
            print(f"Could not write token cache: {err}")

        page.session.store.set("drive_access_token", access_token)
        page.session.store.set("user_given_name", given_name)
        page.session.store.set("user_display_name", given_name)
        page.session.store.set("profile_pic_url", picture_url)

        page.go("/home")

    except Exception:
        import traceback
        error_msg = f"CRASH in handle_login_result:\n{traceback.format_exc()}"
        print(error_msg)
        raise