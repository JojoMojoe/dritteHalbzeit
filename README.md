# Dritte Halbzeit

## Start

```bash
python dritte_halbzeit.py
```

Die Teams werden aus `_Anmeldungen.txt` gelesen. Die App erzeugt/aktualisiert:

- `index.html`
- `stand.json`
- `buchungen.csv`

## GitHub Pages Upload

Die App enthält einen timerbasierten GitHub-Push.

Wichtig: Die App muss aus dem lokal geklonten GitHub-Repository gestartet werden, also aus dem Ordner, in dem auch der versteckte `.git`-Ordner liegt.

Beispiel:

```bash
git clone https://github.com/DEINNAME/DEINREPO.git
cd DEINREPO
python dritte_halbzeit.py
```

Ablauf:

- Jeder Klick aktualisiert sofort `stand.json`, `buchungen.csv` und `index.html` lokal.
- Alle 30 Sekunden prüft die App, ob Änderungen vorgemerkt sind.
- Dann führt sie automatisch aus:
  - `git add index.html stand.json buchungen.csv`
  - `git commit -m "Update Dritte Halbzeit"`
  - `git push`

Wenn die App nicht aus einem Git-Repository gestartet wird, läuft sie trotzdem normal, aber ohne GitHub-Upload.

## Voraussetzungen für Auto-Push

- Git ist installiert.
- Das Repository wurde lokal geklont.
- `git push` funktioniert einmalig manuell ohne Rückfrage.

Zum Testen:

```bash
git status
git push
```

Wenn GitHub nach Login fragt, am besten GitHub Desktop oder Git Credential Manager einrichten.
