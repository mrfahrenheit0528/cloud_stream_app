<div align="center">
  <img src="assets/Logo.png" width="120" alt="E-stream'o Logo"/>
  <h1>E-stream'o</h1>
  <p><strong>Stream your OneDrive & SharePoint media library directly on Android TV and Windows — no subscriptions, no uploads, just your files.</strong></p>

  <p>
    <a href="https://github.com/mrfahrenheit0528/cloud_stream_app/releases/latest">
      <img src="https://img.shields.io/github/v/release/mrfahrenheit0528/cloud_stream_app?color=%23e53935&label=Latest%20Release&style=for-the-badge" alt="Latest Release"/>
    </a>
    <a href="https://github.com/mrfahrenheit0528/cloud_stream_app/releases/latest">
      <img src="https://img.shields.io/github/downloads/mrfahrenheit0528/cloud_stream_app/total?color=%231565c0&style=for-the-badge&label=Downloads" alt="Downloads"/>
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge" alt="Apache 2.0 License"/>
    </a>
  </p>
</div>

---

## ✨ Features

- 🎬 **Stream videos** directly from your OneDrive or SharePoint shared folder — no re-uploading needed
- 🎵 **Music player** with shuffle, loop, album art, and a full-featured D-pad navigable queue
- 🖼️ **Photo viewer** with fullscreen support
- 📺 **Android TV optimized** — complete D-pad remote control navigation, cinematic auto-hide HUD, and zero lag
- 🔗 **"Link from Phone" onboarding** — scan a QR code to wirelessly paste your folder URL from your phone instead of typing on a TV keyboard
- 💾 **Playback memory** — videos resume from where you left off
- 🎨 **Customizable accent colors** — choose from 6 premium theme colors in settings
- 🔒 **Secure & local** — your sharing links stay on your local network, never sent to any cloud service
- ⚡ **Snappy** — all remote inputs are low-latency, all scrolling and media control actions are asynchronous

---

## 📥 Download

Head to the [**Releases page**](https://github.com/mrfahrenheit0528/cloud_stream_app/releases/latest) to download the latest version:

| Platform | File | Notes |
|---|---|---|
| 🤖 **Android TV** | `E-streamo-android.apk` | Sideload via USB or "Send Files to TV" app |
| 🖥️ **Windows** | `E-streamo-windows.zip` | Extract and run `E-streamo.exe` |

---

## 🚀 Getting Started

### Android TV Setup

1. **Download** `E-streamo-android.apk` from the [Releases page](https://github.com/mrfahrenheit0528/cloud_stream_app/releases/latest)
2. **Transfer to TV** using one of:
   - A USB flash drive + a file manager app (e.g. *FX File Explorer*)
   - The [Send Files to TV](https://play.google.com/store/apps/details?id=com.yablio.sendfilestotv) app (phone + TV)
3. **Enable Unknown Sources** in your TV's security settings, then install the APK
4. **Install a browser** on your TV (e.g. *TV Bro*, *JioPages*, or *Puffin TV Browser*) — required for the Microsoft sign-in flow, since most Android TVs don't include one
5. **Launch E-stream'o**, sign in with your Microsoft account, and paste your OneDrive/SharePoint folder link

> **Tip:** Use **"Link from Phone"** in Settings to wirelessly send your sharing URL directly from your phone — no remote typing needed!

### Windows Setup

1. **Download** `E-streamo-windows.zip` from the [Releases page](https://github.com/mrfahrenheit0528/cloud_stream_app/releases/latest)
2. **Extract** the archive to any folder
3. **Run** `E-streamo.exe`
4. Sign in with Microsoft and paste your OneDrive/SharePoint folder link

---

## 🔧 Building from Source

### Prerequisites

- Python 3.11+
- Flutter SDK
- Flet CLI: `pip install flet`

### Clone & Install Dependencies

```bash
git clone https://github.com/mrfahrenheit0528/cloud_stream_app.git
cd cloud_stream_app
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Run in Development

```bash
flet run main.py
```

> **Note:** You will need to create a `src/config.py` file with your own Microsoft Azure app credentials (`CLIENT_ID`, `REDIRECT_URI`, `SCOPES`) to enable OneDrive authentication.

### Build Android APK

```bash
flet build apk --project "E-streamo" --org "com.estreamo" --company "E-stream'o" --copyright "Copyright 2026 mrfahrenheit0528" --splash-color "#0c0c14" --splash-dark-color "#0c0c14" --compile-app --compile-packages --cleanup-app --cleanup-packages
```

### Build Windows EXE

```bash
flet build windows --project "E-streamo" --org "com.estreamo" --company "E-stream'o" --copyright "Copyright 2026 mrfahrenheit0528" --compile-app --compile-packages --cleanup-app --cleanup-packages
```

---

## 🗂️ Project Structure

```
cloud_stream_app/
├── main.py                  # App entry point & global keyboard handler
├── assets/                  # App icons and theme images
├── src/
│   ├── ui/
│   │   ├── router.py        # Navigation & route management
│   │   └── views/
│   │       ├── login_view.py    # Microsoft sign-in page
│   │       ├── home_view.py     # Media library dashboard
│   │       ├── viewer_view.py   # Video / audio / photo player
│   │       └── settings_view.py # Settings & "Link from Phone"
│   └── services/
│       ├── onedrive_service.py  # Microsoft Graph & SharePoint API
│       ├── audio_service.py     # Background music playback engine
│       └── metadata_service.py  # Thumbnail & ID3 tag extractor
```

---

## 📄 License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for full details.

Copyright © 2026 [mrfahrenheit0528](https://github.com/mrfahrenheit0528)

---

<div align="center">
  <sub>Built with ❤️ using <a href="https://flet.dev">Flet</a> (Flutter + Python)</sub>
</div>
