# Bondrucker-Projekt — Neuaufbau-Plan

Stand: 2026-07-28

Kompletter, sauberer Neuaufbau des bestehenden Systems (Web-Seite + Druck-Agent),
Backend (Supabase) und Druck-Logik (`ep.py`) bleiben erhalten.

---

## 1. Ziel

Ein aufgeräumtes, richtig gebautes System, um vom Handy Text und Bilder an den
Epson **TM-T88IV** Bondrucker zu schicken.

- **Jetzt:** Installierbare **App (PWA)** aufs iPhone, Druck-Agent bleibt am **PC** (Windows).
- **Später (optional):** Raspberry Pi als Agent-Host, native iOS-App.

## 2. Was bleibt (funktioniert schon)

| Teil | Warum bleibt es |
|------|-----------------|
| `ep.py` | Die ESC/POS-Druck-Bibliothek läuft sauber. Wird übernommen. |
| Supabase | Bleibt als Backend (Datenbank für Druckaufträge). |
| Login mit Name + gemeinsamem Passwort | Bewusst simpel gehalten (Familien-Drucker). |

## 3. Was neu / besser wird

1. **Passwort nicht mehr im Code sichtbar** — Prüfung läuft bei Supabase
   (Passwort liegt **gehasht in der DB**, nicht im Frontend-Code).
2. **Neue PWA** statt der alten `index.html` — neues Design, **installierbar** auf
   dem iPhone-Homescreen (eigenes Icon, Vollbild).
3. **Verlauf mit Live-Status** — man sieht `wartet → gedruckt → Fehler`.
4. **Agent neu & sauber** — Keys in `.env` (nicht im Code), Fehler werden in einer
   `error_message`-Spalte gespeichert, alte Aufträge werden automatisch aufgeräumt.
5. **Sicherheit richtig getrennt** — Agent nutzt den geheimen `service_role`-Key
   (nur lokal am PC), das Frontend nur den öffentlichen `anon`-Key.
6. **Bilder** werden vorm Senden im Browser verkleinert (kleinere Datenmenge).

## 4. Ordnerstruktur (Ziel)

Alles unter `C:\Users\kamma\Drucker` (neben den Epson-Ordnern):

```
Drucker/
├── PLAN.md                (dieser Plan)
├── README.md              (Anleitung – kommt beim Bauen)
├── .gitignore
├── web/                   → neue PWA (ersetzt printwebsite)
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── config.js          (öffentliche Supabase-URL + anon-Key)
│   ├── manifest.json
│   ├── service-worker.js
│   └── icons/
├── agent/                 → Druck-Agent für den PC (ersetzt printserver)
│   ├── agent.py           (neu, sauber)
│   ├── ep.py              (übernommen)
│   ├── tray_agent.py      (übernommen/angepasst)
│   ├── requirements.txt
│   ├── .env.example
│   ├── start_tray.bat
│   └── start_agent.bat
└── supabase/
    └── setup.sql          (Schema + RLS + Passwort-Funktion)
```

Die alten Ordner (`Desktop/printserver`, `Desktop/printwebsite`, `Epson`, `EpsonLib`)
bleiben als Backup unangetastet.

## 5. Architektur (Zielbild)

```
[iPhone: PWA] --(Login prüft Passwort bei Supabase)-->
[Supabase: Tabelle print_jobs, Passwort-Funktion, RLS]
   ^  Agent liest/aktualisiert mit geheimem service_role-Key
   |
[PC: agent.py + ep.py] --> [Epson TM-T88IV]
```

## 6. Umsetzungs-Reihenfolge

**Schritt A — Supabase vorbereiten** (du klickst, ich liefere fertiges SQL)
- `setup.sql` im Supabase-SQL-Editor ausführen: Spalte `error_message` ergänzen,
  RLS-Regeln setzen, Passwort-Funktion + gehashtes Passwort anlegen.
- `service_role`-Key aus den Supabase-Einstellungen kopieren (für den Agent).

**Schritt B — Agent neu bauen** (`agent/`)
- `agent.py` sauber neu, `.env` für die Keys, `ep.py` übernehmen.
- Lokal testen: Auftrag anlegen → druckt.

**Schritt C — PWA bauen** (`web/`)
- Neues Design, Login (verstecktes Passwort), Text + Bild senden, Verlauf.
- Icons erzeugen, als App installierbar machen.

**Schritt D — PWA online stellen**
- Hosting mit HTTPS (nötig für iPhone-Installation): **Vercel** (kostenlos).
  Via `vercel`-CLI im `web`-Ordner oder GitHub-Import (Root = `web`).
  Danach auf dem iPhone „Zum Home-Bildschirm hinzufügen".

**Schritt E — Aufräumen & Doku**
- `README.md` mit Anleitung, alte Ordner als Backup markieren.

## 7. Später (nicht jetzt)

- **Raspberry Pi:** `ep.py` bekommt einen Linux-Transport (`python-escpos` über USB),
  Agent läuft als `systemd`-Dienst → PC muss nicht mehr an sein.
- **Native iOS-App** (Swift) auf demselben Supabase-Backend (Mac vorhanden).

## 8. Offene Entscheidungen

- **Hosting:** Vercel (entschieden).
- **Bilder-Speicherung:** vorerst als Base64 in der Tabelle + Auto-Aufräumen.
  Später ggf. auf Supabase Storage umstellen (sauberer, aber mehr Setup).
```
