from __future__ import annotations

import csv
import html
import json
import shutil
import subprocess
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

BASE_DIR = Path(__file__).resolve().parent
TEAMS_FILE = BASE_DIR / "_Anmeldungen.txt"
DATA_FILE = BASE_DIR / "stand.json"
LOG_FILE = BASE_DIR / "buchungen.csv"
HTML_FILE = BASE_DIR / "index.html"
LOGO_FILE = BASE_DIR / "FCMG Logo 4 farbig.PNG"
HTML_UPDATE_INTERVAL_S = 10
GITHUB_PUSH_INTERVAL_MS = 6_000

DRINK_POINTS: dict[str, int] = {
    "Bier": 2,
    "Daiquiri / Radler": 1,
    "Sekt / Wein": 2,
    "Weinschorle": 2,
    "Schnaps": 1,
}

DRINK_ICONS: dict[str, str] = {
    "Bier": "🍺",
    "Daiquiri / Radler": "🍹 🚲",
    "Sekt / Wein": "🍾 🍷",
    "Weinschorle": "🥂",
    "Schnaps": "🥃",
}

DRINK_COLORS: dict[str, str] = {
    "Bier": "#fff3cf",
    "Daiquiri / Radler": "#eaf8df",
    "Sekt / Wein": "#f7e8f8",
    "Weinschorle": "#edf8df",
    "Schnaps": "#fff0e4",
}

DRINK_DESC = {
    "Bier": "<br>Menge: 0,5 l <br>Alkohol: 5,0 % <br>Konsum: 0,025g <br>Punkte: 2",
    "Daiquiri / Radler": "<br>Menge: 0,2 / 0,5 l <br>Alkohol:  5,0 / 2,4 % <br>Konsum: 0,012g <br>Punkte: 1",
    "Sekt / Wein": "<br>Menge: 0,2 l <br>Alkohol: 12,0 % <br>Konsum: 0,024g <br>Punkte: 2",
    "Weinschorle": "<br>Menge: 0,5 l  <br>Alkohol: 5,0 % <br>Konsum: 0,025g <br>Punkte: 2",
    "Schnaps": "<br>Menge: 0,02 l <br>Alkohol: 40,0 % <br>Konsum: 0,008g <br>Punkte: 1",
}

COLUMN_WIDTHS = {
    "team": 310,
    "drink": 116,
    "points": 150,
}


@dataclass
class Booking:
    timestamp: str
    team: str
    drink: str
    amount: int
    points: int


def load_teams() -> list[str]:
    if not TEAMS_FILE.exists():
        raise FileNotFoundError(f"Missing team file: {TEAMS_FILE}")
    teams = []
    for line in TEAMS_FILE.read_text(encoding="utf-8").splitlines():
        team = line.strip()
        if team:
            teams.append(team)
    if not teams:
        raise ValueError("No teams found in _Anmeldungen.txt")
    return sorted(dict.fromkeys(teams), key=str.casefold)


def empty_state(teams: list[str]) -> dict[str, dict[str, int]]:
    return {team: {drink: 0 for drink in DRINK_POINTS} for team in teams}


def load_state(teams: list[str]) -> dict[str, dict[str, int]]:
    state = empty_state(teams)
    if DATA_FILE.exists():
        saved = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            for team in teams:
                if isinstance(saved.get(team), dict):
                    for drink in DRINK_POINTS:
                        state[team][drink] = max(0, int(saved[team].get(drink, 0) or 0))
    return state


def save_state(state: dict[str, dict[str, int]]) -> None:
    DATA_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def team_points(values: dict[str, int]) -> int:
    return sum(int(values.get(drink, 0)) * points for drink, points in DRINK_POINTS.items())


def ranking(state: dict[str, dict[str, int]]) -> list[tuple[str, dict[str, int], int]]:
    rows = [(team, values, team_points(values)) for team, values in state.items()]
    return sorted(rows, key=lambda row: (-row[2], row[0].casefold()))


def load_bookings() -> list[Booking]:
    if not LOG_FILE.exists():
        return []
    bookings: list[Booking] = []
    with LOG_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            try:
                bookings.append(
                    Booking(
                        timestamp=row.get("timestamp", ""),
                        team=row.get("team", ""),
                        drink=row.get("drink", ""),
                        amount=int(row.get("amount", 0)),
                        points=int(row.get("points", 0)),
                    )
                )
            except (TypeError, ValueError):
                continue
    return [b for b in bookings if b.team and b.drink in DRINK_POINTS and b.amount != 0]


def write_bookings(bookings: list[Booking]) -> None:
    with LOG_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["timestamp", "team", "drink", "amount", "points"])
        for b in bookings:
            writer.writerow([b.timestamp, b.team, b.drink, b.amount, b.points])


def append_log(booking: Booking) -> None:
    file_exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        if not file_exists:
            writer.writerow(["timestamp", "team", "drink", "amount", "points"])
        writer.writerow([booking.timestamp, booking.team, booking.drink, booking.amount, booking.points])


def medal(place: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(place, str(place))


def write_html(state: dict[str, dict[str, int]]) -> None:
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    logo_html = ""
    if LOGO_FILE.exists():
        logo_html = '<img class="logo" src="FCMG Logo 4 farbig.PNG" alt="FCMG Logo">'

    drink_headers = "".join(
        f"<th>{DRINK_ICONS[drink]}<br>{html.escape(drink)}<small>{points} Punkt{'e' if points != 1 else ''}</small></th>"
        for drink, points in DRINK_POINTS.items()
    )

    ranked = ranking(state)
    max_points = max([points for _, _, points in ranked] + [1])
    rows = []
    previous_points: int | None = None
    for place, (team, values, points) in enumerate(ranked, start=1):
        classes = ["rank-row"]
        if place <= 3:
            classes.append(f"top-{place}")
        if previous_points is not None and points < previous_points:
            classes.append("new-score-group")
        previous_points = points
        width = max(3, round(points / max_points * 100)) if points else 0
        drink_cells = "".join(f"<td class='drink-count'>{int(values.get(drink, 0))}</td>" for drink in DRINK_POINTS)
        rows.append(
            f"<tr class='{' '.join(classes)}'>"
            f"<td class='place'>{medal(place)}</td>"
            f"<td class='team'>{html.escape(team)}</td>"
            f"<td class='points-cell'><div class='points-wrap'>"
            f"<div class='points-bar' style='width:{width}%'></div>"
            f"<span class='points-badge'>{points}</span>"
            f"</div></td>"
            f"{drink_cells}</tr>"
        )

    legend_items = "".join(
            f"""
            <div class='legend-item'>
                <span class='legend-icon'>{DRINK_ICONS[drink]}</span>
                <div>
                    <b>{html.escape(drink)}</b>
                    <small>{DRINK_DESC[drink]}</small>
                </div>
            </div>
            """
            for drink, points in DRINK_POINTS.items()
        )

    doc = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{str(HTML_UPDATE_INTERVAL_S)}">
  <title>Dritte Halbzeit</title>
  <style>
    :root {{
      --blue: #063b7a;
      --blue-dark: #041f43;
      --red: #e5252a;
      --line: #dde6f2;
      --text: #07152d;
      --muted: #65748b;
      --bg: #eef3f9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px;
      font-family: Arial, Helvetica, sans-serif;
      background: radial-gradient(circle at top left, #ffffff 0, #eef3f9 42%, #dce7f4 100%);
      color: var(--text);
    }}
    .page {{
      position: relative;
      max-width: 1220px;
      margin: 0 auto;
      background: rgba(255,255,255,.96);
      border: 1px solid rgba(6,59,122,.14);
      border-radius: 22px;
      box-shadow: 0 18px 50px rgba(4,31,67,.16);
      padding: 28px;
      overflow: visible;
    }}
    header {{
      position: relative;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      min-height: 145px;
      margin-bottom: 22px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2.6rem, 6vw, 5.1rem);
      line-height: .95;
      letter-spacing: -0.04em;
      color: var(--blue-dark);
    }}
    .subtitle {{
      margin-top: 14px;
      color: #31415c;
      font-size: 1.15rem;
      font-weight: 700;
    }}
    .redline {{ 
        width: 105px; 
        height: 7px; 
        background: var(--red); 
        border-radius: 99px; 
        margin: 14px auto 0; 
    }}
    .qr-code {{
      width: 120px;
      height: auto;
      object-fit: contain;
      flex-shrink: 0;
    }}
    .title {{
      flex: 1;
      text-align: center;
    }}
    .logo {{
       width: 120px;
       height: auto;
       object-fit: contain;
       flex-shrink: 0;
    }}
    .table-card {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.8);
    }}
    table {{
      width: 100%;
      min-width: 980px;
      border-collapse: separate;
      border-spacing: 0;
      table-layout: fixed;
    }}
    col.place-col {{ width: 74px; }}
    col.team-col {{ width: 38%; }}
    col.points-col {{ width: 245px; }}
    col.drink-col {{ width: 92px; }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: linear-gradient(180deg, #074990, #052f67);
      color: #fff;
      padding: 13px 10px;
      font-size: .95rem;
      border-right: 1px solid rgba(255,255,255,.18);
      text-align: center;
    }}
    th small {{ display: block; margin-top: 3px; opacity: .88; font-weight: 400; }}
    td {{
      padding: 10px 10px;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      text-align: center;
      background: rgba(255,255,255,.88);
    }}
    .rank-row:nth-child(even) td {{ background: rgba(246,249,253,.92); }}
    .rank-row:hover td {{ background: #edf5ff; }}
    .team {{ text-align: left; font-weight: 900; min-width: 300px; font-size: 1.02rem; }}
    .place {{ width: 74px; font-weight: 900; }}
    .drink-count {{ font-size: .95rem; color: #23324a; font-weight: 700; }}
    .top-1 td {{ background: linear-gradient(90deg, #fff2ba, #fffaf0) !important; }}
    .top-2 td {{ background: linear-gradient(90deg, #f1f4f8, #ffffff) !important; }}
    .top-3 td {{ background: linear-gradient(90deg, #ffe0c2, #fff6ee) !important; }}
    .new-score-group td {{ border-top: 4px solid rgba(6,59,122,.18); }}
    .points-cell {{ min-width: 245px; padding: 8px 12px; }}
    .points-wrap {{
      position: relative;
      height: 32px;
      border-radius: 999px;
      background: #edf2f8;
      overflow: hidden;
      border: 1px solid #d6e1ee;
    }}
    .points-bar {{
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      background: linear-gradient(90deg, rgba(229,37,42,.45), rgba(6,59,122,.42));
    }}
    .points-badge {{
      position: relative;
      z-index: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 54px;
      height: 100%;
      padding: 0 14px;
      border-radius: 999px;
      background: var(--blue-dark);
      color: #fff;
      font-size: 1.08rem;
      font-weight: 950;
      box-shadow: 0 4px 10px rgba(4,31,67,.24);
    }}
    .legend {{
      margin-top: 22px;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px 20px;
      background: linear-gradient(180deg, #ffffff, #f6f9fd);
    }}
    .legend h2 {{ margin: 0 0 14px; color: var(--blue-dark); }}
    .legend-grid {{ 
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
        gap: 12px; 
    }}
    .legend-item {{
      display: grid;
      grid-template-columns: 40px 1fr;
      align-items: center;
      gap: 12px;
      padding: 12px;
      border: 1px solid #dce6f3;
      border-radius: 13px;
      background: #fff;
    }}
    .legend-icon {{ 
        width: 40px;
        text-align: center;
        font-size: 1.8rem;
    }}
    .status {{
      margin-top: 20px;
      background: linear-gradient(90deg, #052f67, #063b7a);
      color: #fff;
      border-radius: 12px;
      padding: 12px 16px;
      font-weight: 700;
    }}
    @media (max-width: 760px) {{
      body {{ padding: 10px; }}
      .page {{ padding: 16px; border-radius: 14px; }}
      header {{ padding-right: 102px; min-height: 104px; }}
      .logo {{ width: 84px; right: 4px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header>
        <img class="qr-code" src="qrCode.jpeg" alt="QR-Code">
        <div class="title">
            <h1>Dritte Halbzeit</h1>
            <div class="redline"></div>
            <div class="subtitle">Aktueller Stand der Mannschaften</div>
        </div>
        <img class="logo" src="FCMG Logo 4 farbig.PNG" alt="FCMG Logo">
    </header>

    <div class="table-card">
      <table>
        <colgroup>
          <col class="place-col">
          <col class="team-col">
          <col class="points-col">
          <col class="drink-col">
          <col class="drink-col">
          <col class="drink-col">
          <col class="drink-col">
          <col class="drink-col">
        </colgroup>
        <thead><tr><th>#</th><th>Team</th><th>Punkte<br><small>Gesamt</small></th>{drink_headers}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>

    <section class="legend">
      <h2>Wertung der Getränke</h2>
      <div class="legend-grid">{legend_items}</div>
    </section>

    <div class="status">Stand: {html.escape(now)} · Aktualisierung automatisch alle {str(HTML_UPDATE_INTERVAL_S)} Sekunden</div>
  </div>
</body>
</html>"""
    HTML_FILE.write_text(doc, encoding="utf-8")


def run_git_command(args: list[str], timeout: int = 20) -> tuple[bool, str]:
    """Run a git command in the app folder and return success plus output."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=BASE_DIR,
            text=True,
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return False, "Git not installed or in the PATH."
    except subprocess.TimeoutExpired:
        return False, "Git command elapse too long. "
    output = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, output


def is_git_repository() -> bool:
    ok, output = run_git_command(["rev-parse", "--is-inside-work-tree"], timeout=5)
    return ok and output.strip().lower() == "true"


def has_git_remote() -> bool:
    ok, output = run_git_command(["remote"], timeout=5)
    return ok and bool(output.strip())


def has_git_changes() -> bool:
    ok, output = run_git_command(["status", "--porcelain"], timeout=10)
    return ok and bool(output.strip())


def commit_and_push_to_github() -> tuple[bool, str]:
    """Commit all local changes and push them to the configured GitHub remote."""
    if not is_git_repository():
        return False, "No Git-Repository. App has to be started in git repo. ."
    if not has_git_remote():
        return False, "The clone of the repo doesn't work correct. "
    if not has_git_changes():
        return True, "No changes for git"

    ok, output = run_git_command(["add", "index.html", "stand.json", "buchungen.csv"], timeout=20)
    if not ok:
        return False, f"git add fehlgeschlagen: {output}"

    # Do not fail when there is nothing to commit after add.
    ok, output = run_git_command(["commit", "-m", "Update Dritte Halbzeit"], timeout=30)
    if not ok and "nothing to commit" not in output.lower():
        return False, f"git commit fehlgeschlagen: {output}"

    ok, output = run_git_command(["push"], timeout=60)
    if not ok:
        return False, f"git push fehlgeschlagen: {output}"
    return True, "GitHub aktualisiert."


class DritteHalbzeitApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Dritte Halbzeit")
        self.geometry("1180x760")
        self.minsize(1000, 560)
        self.configure(bg="#f1f5fb")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Primary.TButton", font=("Arial", 11, "bold"), padding=(12, 8))
        style.configure("Small.TButton", font=("Arial", 10), padding=(10, 7))
        style.configure("Title.TLabel", font=("Arial", 22, "bold"), background="#f1f5fb", foreground="#062b5f")
        style.configure("Status.TLabel", font=("Arial", 10, "bold"), background="#f1f5fb", foreground="#064fb2")

        self.teams = load_teams()
        self.state = load_state(self.teams)
        self.bookings = load_bookings()
        self.count_labels: dict[tuple[str, str], tk.Label] = {}
        self.points_labels: dict[str, tk.Label] = {}
        self.row_frames: dict[str, tk.Frame] = {}
        self.github_dirty = False
        self.github_push_running = False
        self.github_enabled = is_git_repository() and has_git_remote()

        save_state(self.state)
        write_html(self.state)
        self._build_ui()
        self._refresh_all_rows()
        self._update_github_status_initial()
        self._mark_github_dirty()
        self.after(GITHUB_PUSH_INTERVAL_MS, self._github_push_timer)

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg="#f1f5fb", padx=16, pady=12)
        top.pack(fill="x")
        ttk.Label(top, text="Dritte Halbzeit", style="Title.TLabel").pack(side="left")
        self.status_var = tk.StringVar(value="Bereit · HTML wird automatisch aktualisiert")
        self.github_status_var = tk.StringVar(value="GitHub: wird geprüft …")
        ttk.Label(top, textvariable=self.github_status_var, style="Status.TLabel").pack(side="right", padx=(18, 0))
        ttk.Label(top, textvariable=self.status_var, style="Status.TLabel").pack(side="right")

        header_wrap = tk.Frame(self, bg="#0b3972", padx=0, pady=0)
        header_wrap.pack(fill="x", padx=16)
        self._make_header(header_wrap)

        body_wrap = tk.Frame(self, bg="#f1f5fb")
        body_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.canvas = tk.Canvas(body_wrap, bg="#ffffff", highlightthickness=1, highlightbackground="#d7e2f0")
        scrollbar = ttk.Scrollbar(body_wrap, orient="vertical", command=self.canvas.yview)
        self.rows_frame = tk.Frame(self.canvas, bg="#ffffff")

        self.rows_frame.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        bottom = tk.Frame(self, bg="#f1f5fb", padx=16)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="↶ Letzte Buchung rückgängig", style="Primary.TButton", command=self.undo_last_booking).pack(side="left")
        ttk.Button(bottom, text="HTML jetzt öffnen", style="Small.TButton", command=self.open_html).pack(side="left", padx=(10, 0))
        hint = "Linksklick auf + bucht +1 · Rechtsklick auf + bucht -1"
        tk.Label(bottom, text=hint, bg="#f1f5fb", fg="#52627a", font=("Arial", 10)).pack(side="right")

        for row_index, team in enumerate(self.teams):
            self._make_team_row(row_index, team)

    def _make_header(self, parent: tk.Frame) -> None:
        cells = [("Team", COLUMN_WIDTHS["team"])]
        cells.extend((f"{d}\n{p} P.", COLUMN_WIDTHS["drink"]) for d, p in DRINK_POINTS.items())
        cells.append(("Gesamt\nPunkte", COLUMN_WIDTHS["points"]))
        for column, (text, width) in enumerate(cells):
            label = tk.Label(
                parent,
                text=text,
                width=max(1, width // 8),
                height=2,
                bg="#0b3972",
                fg="white",
                font=("Arial", 10, "bold"),
                relief="flat",
                padx=8,
                pady=8,
            )
            label.grid(row=0, column=column, sticky="nsew")
            parent.grid_columnconfigure(column, minsize=width)

    def _make_team_row(self, row_index: int, team: str) -> None:
        row_bg = "#ffffff" if row_index % 2 == 0 else "#f7faff"
        frame = tk.Frame(self.rows_frame, bg=row_bg, highlightbackground="#dfe7f2", highlightthickness=1)
        frame.grid(row=row_index, column=0, sticky="ew")
        self.row_frames[team] = frame

        team_label = tk.Label(frame, text=team, anchor="w", bg=row_bg, fg="#0d1b33", font=("Arial", 10, "bold"), padx=10)
        team_label.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, minsize=COLUMN_WIDTHS["team"])

        for col_index, drink in enumerate(DRINK_POINTS, start=1):
            cell = tk.Frame(frame, bg=DRINK_COLORS[drink], padx=14, pady=4)
            cell.grid(row=0, column=col_index, sticky="nsew")
            frame.grid_columnconfigure(col_index, minsize=COLUMN_WIDTHS["drink"])

            count_var = tk.Label(cell, text="0", bg=DRINK_COLORS[drink], fg="#0d1b33", font=("Arial", 11, "bold"), width=4)
            count_var.pack(side="left", padx=(2, 4))
            self.count_labels[(team, drink)] = count_var

            btn = ttk.Button(cell, text="+", style="Primary.TButton", width=4)
            btn.pack(side="right")
            btn.configure(command=lambda t=team, d=drink: self.book(t, d, +1))
            btn.bind("<Button-3>", lambda event, t=team, d=drink: self.book(t, d, -1))

        points = tk.Label(frame, text="0", bg=row_bg, fg="#062b5f", font=("Arial", 13, "bold"), padx=8)
        points.grid(row=0, column=len(DRINK_POINTS) + 1, sticky="nsew")
        frame.grid_columnconfigure(len(DRINK_POINTS) + 1, minsize=COLUMN_WIDTHS["points"])
        self.points_labels[team] = points

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def book(self, team: str, drink: str, amount: int) -> None:
        current = self.state[team][drink]
        if current + amount < 0:
            self.status_var.set(f"Nicht möglich: {team} · {drink} würde unter 0 fallen")
            return

        self.state[team][drink] = current + amount
        points = amount * DRINK_POINTS[drink]
        booking = Booking(datetime.now().isoformat(timespec="seconds"), team, drink, amount, points)
        self.bookings.append(booking)
        append_log(booking)
        self._persist_and_refresh(team)
        self.status_var.set(f"Gebucht: {team} · {drink} {amount:+d} · {points:+d} Punkte")

    def undo_last_booking(self) -> None:
        while self.bookings:
            booking = self.bookings.pop()
            if booking.team in self.state and booking.drink in DRINK_POINTS:
                current = self.state[booking.team][booking.drink]
                new_value = current - booking.amount
                if new_value >= 0:
                    self.state[booking.team][booking.drink] = new_value
                    write_bookings(self.bookings)
                    self._persist_and_refresh(booking.team)
                    self.status_var.set(f"Rückgängig: {booking.team} · {booking.drink} {booking.amount:+d}")
                    return
        self.status_var.set("Keine Buchung zum Rückgängigmachen vorhanden")

    def _persist_and_refresh(self, changed_team: str | None = None) -> None:
        save_state(self.state)
        write_html(self.state)
        self._mark_github_dirty()
        if changed_team:
            self._refresh_row(changed_team)
        else:
            self._refresh_all_rows()

    def _refresh_row(self, team: str) -> None:
        for drink in DRINK_POINTS:
            self.count_labels[(team, drink)].configure(text=str(self.state[team][drink]))
        self.points_labels[team].configure(text=str(team_points(self.state[team])))

    def _refresh_all_rows(self) -> None:
        for team in self.teams:
            self._refresh_row(team)


    def _update_github_status_initial(self) -> None:
        if self.github_enabled:
            self.github_status_var.set("GitHub: bereit · Push alle 30 s bei Änderungen")
        else:
            self.github_status_var.set("GitHub: aus · Ordner ist kein geklontes Repo")

    def _mark_github_dirty(self) -> None:
        if self.github_enabled:
            self.github_dirty = True
            self.github_status_var.set("GitHub: Änderung vorgemerkt")

    def _github_push_timer(self) -> None:
        if self.github_enabled and self.github_dirty and not self.github_push_running:
            self.github_push_running = True
            self.github_status_var.set("GitHub: Upload läuft …")
            thread = threading.Thread(target=self._github_push_worker, daemon=True)
            thread.start()
        self.after(GITHUB_PUSH_INTERVAL_MS, self._github_push_timer)

    def _github_push_worker(self) -> None:
        ok, message = commit_and_push_to_github()
        self.after(0, lambda: self._github_push_finished(ok, message))

    def _github_push_finished(self, ok: bool, message: str) -> None:
        self.github_push_running = False
        if ok:
            self.github_dirty = False
            self.github_status_var.set(f"GitHub: {message}")
        else:
            # Keep dirty=True so the next timer tries again.
            self.github_dirty = True
            self.github_status_var.set(f"GitHub Fehler: {message}")

    def open_html(self) -> None:
        import webbrowser
        write_html(self.state)
        webbrowser.open(HTML_FILE.resolve().as_uri())
        self.status_var.set("HTML geöffnet")


def main() -> None:
    try:
        app = DritteHalbzeitApp()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("Dritte Halbzeit", str(exc))
        raise


if __name__ == "__main__":
    main()
