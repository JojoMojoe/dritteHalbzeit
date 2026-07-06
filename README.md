# Dritte Halbzeit

## Übersicht

**Dritte Halbzeit** ist eine Python-Anwendung zur Verwaltung der
Challenge *„Dritte Halbzeit"*.

Das Barpersonal erfasst die ausgegebenen Getränke über eine einfache
GUI. Aus den Buchungen wird automatisch eine HTML-Rangliste erzeugt, die
über GitHub Pages veröffentlicht werden kann.

------------------------------------------------------------------------

# Funktionen

-   Einfache GUI mit `+`-Buttons je Getränk und Mannschaft
-   Automatische Berechnung der Punkte
-   Automatische Sortierung nach Gesamtpunkten
-   HTML-Rangliste im modernen Design
-   Rückgängig-Funktion für beliebig viele Buchungen
-   Automatische Speicherung aller Daten
-   Optionaler automatischer GitHub-Push im Hintergrund

------------------------------------------------------------------------

# Projektstruktur

  --------------------------------------------------------------------------
  Datei                      Beschreibung
  -------------------------- -----------------------------------------------
  `dritte_halbzeit.py`       Hauptprogramm mit GUI, Datenverwaltung und
                             HTML-Erzeugung

  `_Anmeldungen.txt`         Mannschaften (eine Mannschaft pro Zeile)

  `stand.json`               Aktueller Spielstand

  `buchungen.csv`            Protokoll aller Buchungen

  `index.html`               Automatisch erzeugte Rangliste

  `FCMG Logo 4 farbig.PNG`   Vereinslogo (rechts oben in der HTML)

  `qrCode.jpeg`              QR-Code (links oben in der HTML)

  `README.md`                Projektdokumentation
  --------------------------------------------------------------------------

------------------------------------------------------------------------

# Bedienungsanleitung

## Mannschaften anlegen

Die Datei `_Anmeldungen.txt` bearbeiten.

Beispiel:

``` text
FC Muster
Die Zapfmeister
Team Bier
```

Jede Mannschaft steht in einer eigenen Zeile.

------------------------------------------------------------------------

## Programm starten

``` bash
python dritte_halbzeit.py
```

------------------------------------------------------------------------

## Getränke buchen

-   Linksklick auf **+** → Getränk buchen
-   Rechtsklick auf **+** → Buchung entfernen
-   Änderungen werden sofort gespeichert.

------------------------------------------------------------------------

## Buchung rückgängig

Über den Button

> **↶ Letzte Buchung rückgängig**

kann beliebig oft die zuletzt durchgeführte Buchung zurückgenommen
werden.

------------------------------------------------------------------------

## HTML

Nach jeder Änderung werden automatisch aktualisiert:

-   `stand.json`
-   `buchungen.csv`
-   `index.html`

Die HTML-Seite aktualisiert sich zusätzlich selbst regelmäßig.

------------------------------------------------------------------------

# GitHub Pages

Empfohlener Ablauf:

1.  Repository lokal klonen.
2.  Projekt in den Repository-Ordner legen.
3.  GitHub Pages aktivieren.
4.  Das Programm übernimmt anschließend den automatischen Push.

------------------------------------------------------------------------

# Punktewertung

  Getränk                Punkte
  -------------------- --------
  Bier                        2
  Daiquiri / Radler           1
  Wein / Weinschorle          2
  Sekt                        2
  Schnaps                     1

------------------------------------------------------------------------

# Datensicherung

Alle relevanten Daten befinden sich in:

-   `stand.json`
-   `buchungen.csv`

Diese beiden Dateien reichen aus, um den aktuellen Stand
wiederherzustellen.

------------------------------------------------------------------------

# Voraussetzungen

-   Python 3.11 oder neuer
-   Tkinter
-   Git (optional, für automatischen Upload)

------------------------------------------------------------------------

# Lizenz

Erstellt für die Challenge **Dritte Halbzeit**.
