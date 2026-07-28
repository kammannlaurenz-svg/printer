# Bondrucker

Vom Handy Text und Bilder an den Epson **TM-T88IV** Bondrucker schicken.

```
[iPhone: Web-App (PWA)]  --Login prüft Passwort bei Supabase-->
[Supabase]  (Tabelle print_jobs + Passwort-Funktion + RLS)
   ^  Agent liest/aktualisiert mit geheimem Secret-Key
   |
[PC: agent/agent.py + ep.py]  -->  [Epson TM-T88IV]
```

## Ordner

```
Drucker/
├── web/        Die Web-App (PWA) – wird bei Netlify gehostet
├── agent/      Der Druck-Agent, läuft am PC
├── supabase/   setup.sql (Datenbank-Einrichtung)
└── PLAN.md     Aufbauplan / Roadmap
```

---

## 1. Supabase (einmalig)

Im Supabase-Dashboard → **SQL Editor** die Datei `supabase/setup.sql` ausführen:
- Abschnitt 1 + 2: Spalten + verstecktes Passwort (Passwort in der SQL-Zeile eintragen).
- Abschnitt 3: RLS (Row-Level-Security) einschalten.

Keys (Project Settings → API keys):
- **Publishable key** (`sb_publishable_…`) → kommt in `web/config.js` (öffentlich, ok).
- **Secret key** (`sb_secret_…`) → kommt in `agent/.env` (GEHEIM, nur am PC).

---

## 2. Agent am PC

1. In `agent/` die Datei `.env.example` nach `.env` kopieren und den **Secret key** eintragen.
2. Benötigte Pakete (auf diesem PC bereits vorhanden):
   ```
   python -m pip install -r agent/requirements.txt
   ```
3. Starten:
   - **Testen (mit Konsole):** `agent/start_agent.bat` doppelklicken.
   - **Alltag (Tray-Icon, im Hintergrund):** `agent/start_tray.bat` doppelklicken.
     Unten rechts erscheint ein Drucker-Icon. Rechtsklick zeigt das Menü:
     - **Status** – „● Agent läuft" / „○ Agent gestoppt" (auch als Tooltip beim Hovern)
     - **Zuletzt: …** – der letzte Log-Eintrag direkt im Menü (Klick öffnet das Log)
     - **Log öffnen**, **Agent neu starten**, **Beenden**

   Für eine hübsche Verknüpfung: `agent/icon.ico` als Symbol setzen
   (Rechtsklick auf Verknüpfung → Eigenschaften → Anderes Symbol).

Der Agent fragt Supabase alle paar Sekunden nach neuen Aufträgen, druckt sie und
markiert sie als `printed`. Gedruckte Aufträge werden nach `CLEANUP_DAYS` gelöscht.

### Autostart (optional)
`start_tray.bat` als Verknüpfung in den Autostart-Ordner legen:
`Win + R` → `shell:startup` → Verknüpfung hineinziehen.

---

## 3. Web-App online stellen (Vercel)

Die App muss über **HTTPS** laufen, damit man sie aufs iPhone installieren kann.
Vercel hostet statische Seiten kostenlos.

**Weg A – Vercel CLI (schnell):**
1. Node.js installieren, falls nicht vorhanden: https://nodejs.org
2. Vercel-CLI installieren:
   ```
   npm i -g vercel
   ```
3. In den web-Ordner wechseln und deployen:
   ```
   cd C:\Users\kamma\Drucker\web
   vercel
   ```
   Beim ersten Mal: mit E-Mail/GitHub anmelden, die Fragen mit Enter bestätigen
   (Verzeichnis = `.`). Für die öffentliche Version danach:
   ```
   vercel --prod
   ```
4. Vercel gibt eine HTTPS-Adresse (z. B. `https://drucker.vercel.app`).

**Weg B – über GitHub (automatische Updates):**
Projekt zu GitHub pushen → auf vercel.com „Add New… → Project" → Repo importieren →
**Root Directory** auf `web` setzen → Deploy. Danach deployt jeder Git-Push automatisch.

**Aufs iPhone:** Adresse in **Safari** öffnen → Teilen-Symbol → **„Zum Home-Bildschirm"**.
→ Die App liegt als Icon auf dem Homescreen und öffnet im Vollbild.

Bei Änderungen an `web/`: `vercel --prod` erneut ausführen (Weg A) bzw. einfach pushen (Weg B).

---

## Bedienung

1. Name + Passwort → Einloggen.
2. **Text**-Tab: Text eingeben → Drucken.
3. **Bild**-Tab: Bild wählen (wird automatisch verkleinert) → Bild drucken.
4. **Verlauf** zeigt live `wartet → gedruckt → Fehler`.

---

## Was bleibt / wurde übernommen

- `agent/ep.py` – die ESC/POS-Druck-Bibliothek (unverändert übernommen).

## Später (Ideen)

- Agent auf einen **Raspberry Pi** umziehen (Linux-Transport in `ep.py`, `systemd`-Dienst).
- Native **iOS-App** auf demselben Supabase-Backend.
- Bilder in **Supabase Storage** statt als Base64 in der Tabelle.

Details & Fortschritt: siehe `PLAN.md`.
