import flet as ft
from flet.auth.providers import GoogleOAuthProvider
import os

def get_google_provider() -> GoogleOAuthProvider:
    """
    Initializes and returns the Google OAuth Provider using credentials from the .env file.
    Requests read-only access to Google Drive.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    # Define a redirect URL (defaulting to Flet's standard local testing port)
    redirect_url = os.environ.get("GOOGLE_REDIRECT_URL", "http://localhost:8550/api/oauth/redirect")

    if not client_id or not client_secret:
        print("WARNING: Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env file.")

    # Initialize with the required redirect_url argument
    provider = GoogleOAuthProvider(
        client_id=client_id,
        client_secret=client_secret,
        redirect_url=redirect_url
    )
    
    # Flet's provider doesn't accept a 'scopes' argument in its constructor.
    # Instead, we override its 'user_scopes' attribute to request Drive access,
    # keeping the default profile/email scopes for a standard Google login.
    provider.user_scopes = [
        "profile",
        "email",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    return provider

def handle_login_result(e: ft.LoginEvent, page: ft.Page):
    """
    Callback fired when the OAuth web flow completes.
    Stores the access token and navigates to the home screen on success.
    """
    if e.error:
        print(f"Login failed: {e.error} - {e.error_description}")
        # Optionally show an error Snackbar to the user here
        return

    # Store the token securely in the user's session
    page.session.set("drive_access_token", page.auth.token.access_token)
    print("Login successful! Token acquired.")
    
    # Navigate to the home dashboard
    page.push_route("/home")