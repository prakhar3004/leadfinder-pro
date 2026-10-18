import sys
import os
import webbrowser
import threading
import time
import uvicorn

if sys.platform == "win32":
    try:
        if sys.stdout:
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr:
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   ⚡ GOOGLE MAPS LEAD FINDER PRO - LOCAL SERVER ⚡")
    print("="*60)
    print("  🌐 Dashboard URL : http://127.0.0.1:8000")
    print("  💡 Tip: Opening browser automatically...")
    print("  🛑 Press Ctrl + C to stop server")
    print("="*60 + "\n")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
