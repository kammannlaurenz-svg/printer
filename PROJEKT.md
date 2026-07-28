# Projekt „Bondrucker" — Kontext & Übersicht

Kompakte Referenz über das gesamte Projekt (Stand: 2026-07-28).
Ziel: vom Handy Text & Bilder an einen **Epson TM-T88IV** Bondrucker schicken.

Nutzer: Laurenz. Windows 11 PC. Mac + iPhone vorhanden (kein Raspberry Pi).

---

## 1. Architektur

```
[iPhone: PWA]  --Login prüft Passwort per RPC-->
[Supabase]  (Tabelle print_jobs + Funktion verify_web_password + RLS)
   ▲  Agent liest/aktualisiert mit geheimem Secret-Key
   │
[PC: agent/agent.py + ep.py]  -->  [Epson TM-T88IV per USB]
```

Ablauf **Text**: App schreibt Zeile in `print_jobs` (`status=pending`) → Agent pollt alle 2 s → druckt via `ep.py` → setzt `status=printed`.
Ablauf **Bild**: App verkleinert Bild im Browser (max 1000 px, JPEG) → als Base64-DataURL in Spalte `image` → Agent druckt es gedithert (S/W).

---

## 2. Ordnerstruktur (`C:\Users\kamma\Drucker\`)

```
Drucker/
├── PROJEKT.md   (diese Datei)   PLAN.md (Roadmap)   README.md (Anleitung)
├── .gitignore
├── web/                 → PWA (bei Netlify hosten)
│   ├── index.html       Login + Tabs Text/Bild + Verlauf
│   ├── app.js           Logik: Login-RPC, Jobs anlegen, Verlauf-Polling, SW
│   ├── style.css        Design (mobil, hell/dunkel, Indigo-Akzent)
│   ├── config.js        SUPABASE_URL + Publishable key (öffentlich, ok)
│   ├── manifest.json    PWA-Manifest (installierbar)
│   ├── service-worker.js  App-Hülle offline; Supabase geht ans Netz
│   ├── vercel.json      Vercel-Hosting-Konfig (Header, Clean-URLs)
│   ├── make_icons.py    erzeugt Icons
│   └── icons/           icon-192/512, maskable, apple-touch-icon
├── agent/               → Druck-Agent am PC
│   ├── agent.py         Hauptschleife: Jobs holen/drucken/aktualisieren/aufräumen
│   ├── ep.py            ESC/POS-Bibliothek (UNVERÄNDERT übernommen, nur Windows)
│   ├── tray_agent.py    Tray-Icon + Menü (Status, letztes Log, Log öffnen, neu starten, beenden)
│   ├── .env             GEHEIM (Secret key) — nicht committen
│   ├── .env.example     Vorlage
│   ├── requirements.txt requests, pywin32, Pillow, pystray
│   ├── start_agent.bat  Agent sichtbar (Konsole, zum Testen)
│   ├── start_tray.bat   Tray im Hintergrund (Alltag)
│   ├── icon.ico         Icon für Verknüpfung
│   └── agent.log        Log (gitignored)
└── supabase/
    └── setup.sql        Schema-Spalten + Passwort-Funktion + RLS
```

Alte Ordner `Desktop\printserver` und `Desktop\printwebsite` wurden gelöscht (Papierkorb).
`C:\Users\kamma\Epson` (Beispielskripte) und `EpsonLib` (ep, pip-installiert) bleiben.

---

## 3. Supabase

- Projekt-Ref: **`jyogmhegflsstuepisfl`**, URL `https://jyogmhegflsstuepisfl.supabase.co`.
- **Publishable key** (`sb_publishable_…`) → `web/config.js` (öffentlich).
- **Secret key** (`sb_secret_…`) → nur `agent/.env`. Umgeht RLS.

**Tabelle `print_jobs`** (Spalten): `id` (int, auto), `created_at`, `printed_at`,
`status` (`pending`/`printed`/`error`), `type` (`text`/`image`), `text`,
`image` (Base64-DataURL), `filename`, `username`, `error_message`.

**RLS ist AN:**
- anon (Publishable) darf: INSERT nur mit `status=pending`, SELECT alles. Kein UPDATE/DELETE.
- Agent (Secret) darf alles.

**Verstecktes Passwort:** Funktion `verify_web_password(pw)` (SECURITY DEFINER) prüft
gegen gehashten Wert in Tabelle `app_secrets` (bcrypt via pgcrypto). App ruft sie beim
Login per RPC. Passwort steht NICHT im Frontend. (Nicht `1234` — Laurenz hat eigenes gesetzt.)

---

## 4. Agent (PC)

- Läuft mit **`python` = 3.14.0** (dort sind win32print/PIL/pystray/requests/ep installiert; `py`=3.11.9 hat nichts).
- Eigener **`.env`-Loader** (kein python-dotenv). `.env`-Werte: `SUPABASE_URL`,
  `SUPABASE_SERVICE_KEY` (=Secret key), `PRINTER_NAME=TM-T88IV`, `CHECK_SECONDS=2`,
  `IMAGE_WIDTH=384`, `CLEANUP_DAYS=14`.
- Räumt gedruckte Jobs > `CLEANUP_DAYS` automatisch weg.
- Fehler → `status=error` + `error_message`.
- **Tray-Menü**: „● Agent läuft/○ gestoppt", „Zuletzt: <letzte Logzeile>", Log öffnen, neu starten, beenden. Tooltip zeigt Status.
- Wichtig: **nur eine Instanz** laufen lassen (Standalone ODER Tray), sonst Doppeldruck.
- `ep.py` API: `open/close/raw/reset/feed/cut`, `cp1252/cp437`, `write/line/box/lineline/bold/ori`, `image/image_base64/image_pil`.

---

## 5. Web-App (PWA)

- Reines Vanilla HTML/CSS/JS, keine Frameworks, keine externen Libs.
- Login: Name (nur Label) + gemeinsames Passwort (per RPC geprüft). Name in localStorage, bleibt eingeloggt.
- Text-Tab & Bild-Tab (mit Vorschau, Client-Verkleinerung). Verlauf zeigt die letzten 10
  eigenen Jobs mit Live-Status (Polling alle 3 s).
- Installierbar (Manifest + Service Worker). Icon = Drucker mit Bon auf Indigo-Verlauf.
- **Hosting: Vercel** (kostenlos, HTTPS). Weg A: `npm i -g vercel`, dann im `web`-Ordner `vercel` bzw. `vercel --prod`. Weg B: GitHub-Repo bei Vercel importieren, **Root Directory = `web`**. Dann URL in Safari → „Zum Home-Bildschirm".

---

## 6. Starten / Bedienen

- Agent Alltag: `agent/start_tray.bat` doppelklicken → Tray-Icon unten rechts.
- Agent testen: `agent/start_agent.bat` (Konsole sichtbar).
- Autostart: Verknüpfung zu `start_tray.bat` in `shell:startup`.
- App: Netlify-URL öffnen, einloggen, drucken.

---

## 7. Stolpersteine (wichtig!)

- `ep.py` nutzt `win32print` → **nur Windows**. Für Raspberry Pi müsste der Transport
  (`open/close/raw`) auf Linux umgestellt werden (z. B. `python-escpos` USB), Rest bleibt.
- pgcrypto liegt bei Supabase im Schema **`extensions`** → im SQL `extensions.crypt(...)` / `extensions.gen_salt(...)`.
- Secret key NIEMALS ins Frontend. Nur `agent/.env`.
- Zwei Agenten gleichzeitig = möglicher Doppeldruck.

---

## 8. Stand & offen

- ✅ Supabase (Passwort versteckt, Spalten, RLS), Agent (Tray, druckt), PWA gebaut & getestet.
- 👉 **Offen: Web-App bei Vercel hochladen** (macht Laurenz) und aufs iPhone holen.

## 9. Später geplant

- Agent auf **Raspberry Pi** (Linux-Transport in `ep.py`, `systemd`-Dienst, PC muss nicht mehr an sein).
- Native **iOS-App** (Swift) auf demselben Supabase-Backend.
- Bilder ggf. in **Supabase Storage** statt Base64 in der Tabelle.
```
