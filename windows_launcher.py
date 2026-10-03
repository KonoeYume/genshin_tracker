"""Start the local tracker and open its browser page from the Windows launcher."""
from pathlib import Path
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

HOST = '127.0.0.1'
PORT = 8000
URL = f'http://{HOST}:{PORT}/'


def open_when_ready(stop):
    deadline = time.monotonic() + 45
    while not stop.is_set() and time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(URL, timeout=1) as response:
                ready = response.status == 200
            if ready:
                if not stop.is_set():
                    webbrowser.open(URL)
                return
        except OSError:
            pass
        stop.wait(0.25)
    if not stop.is_set():
        print(f'Browser did not open automatically. Open {URL} after the server starts.')


def main():
    folder = Path(__file__).resolve().parent
    os.chdir(folder)
    sys.path.insert(0, str(folder))
    if not (folder / 'app_v2.py').is_file() or not (folder / 'genshin_v2.db').is_file():
        print('Place the launcher beside app_v2.py and genshin_v2.db.')
        return 1
    with socket.socket() as probe:
        try:
            probe.bind((HOST, PORT))
        except OSError:
            print(f'Port {PORT} is already in use. If the tracker is running, open {URL}')
            print('Otherwise, close the program using this port and launch again.')
            return 1
    import uvicorn
    print(f'Genshin Tracker: {URL}')
    print('Keep this window open while using the app. Press Ctrl+C here to stop it.')
    stop = threading.Event()
    threading.Thread(target=open_when_ready, args=(stop,), daemon=True).start()
    try:
        uvicorn.run('app_v2:app', host=HOST, port=PORT)
    finally:
        stop.set()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
