# CropAI — Local dev (static site)

This folder contains a small static front-end for the CropAI detection demo. To open the site and land directly on the login page, use the provided PowerShell helper (Windows).

Quick start (Windows PowerShell)

1. Open PowerShell and change to this folder:

```powershell
cd "d:\New folder\minor-project-2\minor.project"
```

2. Run the helper script to start a static server and open the login page:

```powershell
.\\start_server.ps1
```

Notes
- The script starts Python's `http.server` on port 8000. Make sure `python` is available on your PATH.
- If PowerShell prevents the script from running, run it with bypassed execution policy:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_server.ps1
```

Manual alternative (no script)

```powershell
cd "d:\New folder\minor-project-2\minor.project"
python -m http.server 8000
# then open http://localhost:8000/login.html in your browser
```

What the site does
- The site checks `localStorage.userProfile`. If missing, `index.html` redirects to `login.html` so the login page is shown first.
- The login form saves `userProfile` to localStorage and redirects back to `index.html#detect` to reveal the prediction UI.
 - The project helper (`start_server.ps1`) opens `login.html` directly when you run it. `index.html` no longer contains an automatic redirect — this prevents the full site from loading before the login page.
 - The login form saves `userProfile` to localStorage and redirects back to `index.html#detect` to reveal the prediction UI.

Next steps
- Add server-side login/session storage (Flask/FastAPI) if you want persistence across devices.
- Wire the form to an API endpoint to store user records.
