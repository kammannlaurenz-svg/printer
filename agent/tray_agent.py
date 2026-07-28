"""
Tray-Programm fuer den Bondrucker-Agent.

Zeigt unten rechts ein Drucker-Icon mit Menue:
  - Status (laeuft / gestoppt)
  - letzter Log-Eintrag
  - Log oeffnen
  - Agent neu starten
  - Beenden

Start ueber start_tray.bat (laeuft im Hintergrund, ohne Konsolenfenster).
"""

import os
import sys
import time
import threading
import subprocess

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_PATH = os.path.join(BASE_DIR, "agent.py")
LOG_PATH = os.path.join(BASE_DIR, "agent.log")

ACCENT = (79, 70, 229, 255)      # Indigo
ACCENT2 = (99, 102, 241, 255)    # helleres Indigo
WHITE = (255, 255, 255, 255)

agent_process = None


# ------------------------------------------------------------
# Icon zeichnen (Drucker mit Bon, passend zur App)
# ------------------------------------------------------------
def make_icon(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64.0

    def px(v):
        return int(v * s)

    # abgerundeter Hintergrund
    d.rounded_rectangle([px(2), px(2), px(62), px(62)], radius=px(14), fill=ACCENT)

    # Bon (kommt oben heraus)
    d.rectangle([px(20), px(11), px(44), px(34)], fill=WHITE)
    # Zackenrand unten am Bon
    teeth = 5
    tw = (px(44) - px(20)) / teeth
    for i in range(teeth):
        x = px(20) + i * tw
        d.polygon([(x, px(34)), (x + tw / 2, px(34) + px(3)), (x + tw, px(34))], fill=WHITE)
    # Textzeilen auf dem Bon
    for i, w in enumerate([0.85, 0.6, 0.75]):
        ly = px(16) + i * px(5)
        d.rounded_rectangle(
            [px(23), ly, px(23) + int((px(44) - px(26)) * w), ly + px(2)],
            radius=px(1), fill=ACCENT2,
        )

    # Druckerkorpus
    d.rounded_rectangle([px(12), px(30), px(52), px(51)], radius=px(4), fill=WHITE)
    # kleiner Punkt (Power)
    d.ellipse([px(45), px(35), px(49), px(39)], fill=ACCENT)

    return img


# ------------------------------------------------------------
# Agent-Prozess steuern
# ------------------------------------------------------------
def is_running():
    return agent_process is not None and agent_process.poll() is None


def start_agent():
    global agent_process
    if not is_running():
        agent_process = subprocess.Popen(
            [sys.executable, AGENT_PATH],
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def stop_agent():
    global agent_process
    if is_running():
        agent_process.terminate()
    agent_process = None


def restart_agent(icon=None, menu_item=None):
    stop_agent()
    time.sleep(0.3)
    start_agent()


# ------------------------------------------------------------
# Log
# ------------------------------------------------------------
def last_log_line():
    """Letzte nicht-leere Zeile des Logs (liest nur das Ende der Datei)."""
    try:
        with open(LOG_PATH, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 2048))
            tail = f.read().decode("utf-8", errors="replace")
        lines = [ln for ln in tail.splitlines() if ln.strip()]
        return lines[-1] if lines else "Noch keine Logs."
    except FileNotFoundError:
        return "Noch keine Logs."
    except Exception as e:
        return f"Log-Fehler: {e}"


def open_log(icon=None, menu_item=None):
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("Noch keine Logs.\n")
    os.startfile(LOG_PATH)


def quit_app(icon, menu_item=None):
    stop_agent()
    icon.stop()


# ------------------------------------------------------------
# Menue (Labels aktualisieren sich beim Oeffnen)
# ------------------------------------------------------------
def status_label(menu_item):
    return "● Agent laeuft" if is_running() else "○ Agent gestoppt"


def last_log_label(menu_item):
    line = last_log_line()
    if len(line) > 48:
        line = line[:48] + "…"
    return "Zuletzt: " + line


def build_menu():
    return pystray.Menu(
        item(status_label, None, enabled=False),
        item(last_log_label, open_log),
        pystray.Menu.SEPARATOR,
        item("Log öffnen", open_log),
        item("Agent neu starten", restart_agent),
        item("Beenden", quit_app),
    )


def refresh_loop(icon):
    """Haelt Tooltip + Menue-Labels aktuell."""
    while True:
        try:
            icon.title = "Bondrucker-Agent — " + ("läuft" if is_running() else "gestoppt")
            icon.update_menu()
        except Exception:
            pass
        time.sleep(3)


def run_tray():
    start_agent()
    icon = pystray.Icon("bondrucker", make_icon(), "Bondrucker-Agent", build_menu())
    threading.Thread(target=refresh_loop, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    run_tray()
