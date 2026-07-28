"""
Druck-Agent fuer den Epson TM-T88IV.

Holt offene Druckauftraege aus Supabase und druckt sie ueber ep.py.
Konfiguration kommt aus der Datei  agent/.env  (siehe .env.example).
"""

import os
import time
import traceback
from datetime import datetime, timedelta, UTC

import requests
import ep


# ------------------------------------------------------------
# .env laden (ohne Zusatz-Paket)
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "agent.log")


def load_env(filename=".env"):
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


load_env()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
PRINTER_NAME = os.environ.get("PRINTER_NAME", "TM-T88IV")
CHECK_SECONDS = float(os.environ.get("CHECK_SECONDS", "2"))
IMAGE_WIDTH = int(os.environ.get("IMAGE_WIDTH", "384"))
CLEANUP_DAYS = int(os.environ.get("CLEANUP_DAYS", "14"))   # 0 = nie aufraeumen

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit(
        "SUPABASE_URL und SUPABASE_SERVICE_KEY muessen in agent/.env stehen. "
        "Vorlage: .env.example"
    )

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
def log(msg):
    text = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(text)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(text + "\n")


# ------------------------------------------------------------
# Supabase
# ------------------------------------------------------------
def get_pending_job():
    url = f"{SUPABASE_URL}/rest/v1/print_jobs"
    params = {"status": "eq.pending", "order": "created_at.asc", "limit": "1"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    jobs = r.json()
    return jobs[0] if jobs else None


def update_job(job_id, status, error_message=None):
    url = f"{SUPABASE_URL}/rest/v1/print_jobs"
    params = {"id": f"eq.{job_id}"}
    data = {"status": status}

    if status == "printed":
        data["printed_at"] = datetime.now(UTC).isoformat()
    if error_message:
        data["error_message"] = str(error_message)[:500]

    r = requests.patch(url, headers=HEADERS, params=params, json=data, timeout=20)
    r.raise_for_status()


def cleanup_old_jobs():
    """Loescht gedruckte Auftraege, die aelter als CLEANUP_DAYS sind."""
    if CLEANUP_DAYS <= 0:
        return
    cutoff = (datetime.now(UTC) - timedelta(days=CLEANUP_DAYS)).isoformat()
    url = f"{SUPABASE_URL}/rest/v1/print_jobs"
    params = {"status": "eq.printed", "printed_at": f"lt.{cutoff}"}
    try:
        r = requests.delete(url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        log(f"Aufraeumen: alte Auftraege vor {cutoff[:10]} geloescht.")
    except Exception as e:
        log(f"Aufraeumen fehlgeschlagen: {e}")


# ------------------------------------------------------------
# Drucken
# ------------------------------------------------------------
def get_image_text(job):
    return job.get("image") or job.get("image_data") or ""


def is_image_job(job):
    job_type = str(job.get("type") or job.get("job_type") or "").lower().strip()
    return job_type == "image" or bool(get_image_text(job))


BOX_MARK = "[BOX]"


def print_text_job(job):
    text = job.get("text") or ""
    username = job.get("username") or "Unbekannt"

    # Erste Zeile kann eine Box-Ueberschrift sein:  "[BOX]Titel"
    title = None
    body = text
    nl = text.find("\n")
    first_line = text if nl == -1 else text[:nl]
    if first_line.startswith(BOX_MARK):
        title = first_line[len(BOX_MARK):].strip()
        body = "" if nl == -1 else text[nl + 1:]

    ep.ori(0)
    if title:
        ep.box(title.upper())
        ep.line("")
    if body:
        ep.line(body)
    ep.line("")
    ep.ori(2)
    ep.line(f"--{username}")
    ep.ori(0)


def print_image_job(job):
    username = job.get("username") or "Unbekannt"
    img = get_image_text(job)

    if not img:
        raise ValueError("Bild fehlt: Spalte 'image' bzw. 'image_data' ist leer.")

    log(f"Bilddaten empfangen: {len(img)} Zeichen")

    ep.ori(1)
    ep.line(f"Bild von {username}")
    ep.feed(1)
    ep.image_base64(img, width=IMAGE_WIDTH)
    ep.feed(1)
    ep.ori(2)
    ep.line(f"--{username}")
    ep.ori(0)


def print_job(job):
    ep.open(PRINTER_NAME)
    try:
        ep.reset()
        if is_image_job(job):
            print_image_job(job)
        else:
            print_text_job(job)
        ep.feed(6)
        ep.cut()
    finally:
        ep.close()


# ------------------------------------------------------------
# Hauptschleife
# ------------------------------------------------------------
def main():
    log("Agent gestartet")
    log(f"Supabase: {SUPABASE_URL}")
    log(f"Drucker:  {PRINTER_NAME}")
    log(f"ep geladen von: {getattr(ep, '__file__', 'unbekannt')}")

    cleanup_old_jobs()
    last_cleanup = time.time()

    while True:
        try:
            job = get_pending_job()

            if job:
                job_id = job["id"]
                typ = "image" if is_image_job(job) else "text"
                log(f"Job gefunden: {job_id} ({typ})")

                try:
                    print_job(job)
                    update_job(job_id, "printed")
                    log(f"Job gedruckt: {job_id}")
                except Exception as printer_error:
                    log(f"Druckerfehler bei Job {job_id}: {printer_error}")
                    log(traceback.format_exc())
                    update_job(job_id, "error", error_message=str(printer_error))

            # einmal pro Stunde aufraeumen
            if time.time() - last_cleanup > 3600:
                cleanup_old_jobs()
                last_cleanup = time.time()

            time.sleep(CHECK_SECONDS)

        except Exception as error:
            log(f"Agent Fehler: {error}")
            log(traceback.format_exc())
            time.sleep(5)


if __name__ == "__main__":
    main()
