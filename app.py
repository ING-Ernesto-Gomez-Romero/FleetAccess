from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "fleet.db"

NAVY = "#14213D"
BLUE = "#1D6FE8"
TEAL = "#149E91"
PAPER = "#F4F6F8"
WHITE = "#FFFFFF"
INK = "#1F2937"
MUTED = "#667085"

FIELDS = (
    ("plate", "Placa"),
    ("company", "Empresa transportista"),
    ("driver", "Conductor"),
    ("destination", "Destino"),
    ("cargo_type", "Tipo de carga"),
    ("axles", "Numero de ejes"),
    ("weight_kg", "Peso aproximado (kg)"),
    ("scheduled_time", "Hora programada (HH:MM)"),
)


class FleetRepository:
    def __init__(self, path: Path = DB_PATH) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate TEXT NOT NULL,
                company TEXT NOT NULL,
                driver TEXT NOT NULL,
                destination TEXT NOT NULL,
                cargo_type TEXT NOT NULL,
                axles INTEGER NOT NULL CHECK(axles > 0),
                weight_kg REAL NOT NULL CHECK(weight_kg >= 0),
                scheduled_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'En patio',
                registered_at TEXT NOT NULL,
                departed_at TEXT
            )
            """
        )
        self.connection.commit()
        self._seed_demo_rows()

    def _seed_demo_rows(self) -> None:
        count = self.connection.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        if count:
            return
        rows = (
            ("DEM-102-A", "Transportes Norte", "Laura Mendoza", "Queretaro", "Electrónica", 4, 8500, "09:30"),
            ("DEM-248-B", "Logistica Central", "Miguel Santos", "Puebla", "Alimentos secos", 5, 11200, "11:15"),
            ("DEM-551-C", "Carga Metropolitana", "Ana Ruiz", "Toluca", "Paqueteria", 3, 6200, "13:00"),
        )
        now = datetime.now().isoformat(timespec="seconds")
        self.connection.executemany(
            """
            INSERT INTO vehicles(
                plate, company, driver, destination, cargo_type, axles,
                weight_kg, scheduled_time, registered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [row + (now,) for row in rows],
        )
        self.connection.commit()

    def add(self, values: dict[str, str]) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO vehicles(
                plate, company, driver, destination, cargo_type, axles,
                weight_kg, scheduled_time, registered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values["plate"].upper(), values["company"], values["driver"],
                values["destination"], values["cargo_type"], int(values["axles"]),
                float(values["weight_kg"]), values["scheduled_time"],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        self.connection.commit()
        return cursor.lastrowid

    def search(self, term: str = "", status: str = "Todos"):
        where = []
        params = []
        if term.strip():
            token = f"%{term.strip()}%"
            where.append("(CAST(id AS TEXT) LIKE ? OR plate LIKE ? OR company LIKE ? OR driver LIKE ?)")
            params.extend([token] * 4)
        if status != "Todos":
            where.append("status = ?")
            params.append(status)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        return self.connection.execute(
            f"SELECT * FROM vehicles {clause} ORDER BY id DESC", params
        ).fetchall()

    def register_departure(self, vehicle_id: int) -> None:
        self.connection.execute(
            "UPDATE vehicles SET status = 'Salida registrada', departed_at = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), vehicle_id),
        )
        self.connection.commit()

    def counts(self) -> tuple[int, int]:
        total = self.connection.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        active = self.connection.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'En patio'").fetchone()[0]
        return total, active


class FleetApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Fleet Access")
        self.geometry("1180x720")
        self.minsize(960, 620)
        self.configure(bg=PAPER)
        self.repository = FleetRepository()
        self.entries = {}
        self.visible_rows = []
        self._configure_styles()
        self._build_ui()
        self.refresh()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=PAPER)
        style.configure("Panel.TFrame", background=WHITE)
        style.configure("TLabel", background=PAPER, foreground=INK, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=WHITE, foreground=INK, font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"))
        style.configure("Metric.TLabel", background=WHITE, foreground=NAVY, font=("Segoe UI", 22, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Primary.TButton", background=[("active", TEAL)])
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=NAVY, height=78)
        header.pack(fill="x")
        tk.Label(header, text="FLEET ACCESS", bg=NAVY, fg=WHITE, font=("Segoe UI", 20, "bold")).pack(side="left", padx=24, pady=20)
        tk.Label(header, text="Control operativo de transporte", bg=NAVY, fg="#CBD5E1", font=("Segoe UI", 11)).pack(side="left", pady=24)

        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        metrics = ttk.Frame(body)
        metrics.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        self.total_label = self._metric(metrics, "Registros", 0)
        self.active_label = self._metric(metrics, "Unidades en patio", 1)

        form = ttk.Frame(body, style="Panel.TFrame", padding=18)
        form.grid(row=1, column=0, sticky="ns", padx=(0, 14))
        ttk.Label(form, text="Registrar unidad", style="Panel.TLabel", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 12))
        for row, (key, label) in enumerate(FIELDS, start=1):
            ttk.Label(form, text=label, style="Panel.TLabel").grid(row=row * 2 - 1, column=0, sticky="w", pady=(3, 0))
            entry = ttk.Entry(form, width=32)
            entry.grid(row=row * 2, column=0, sticky="ew", pady=(2, 4))
            self.entries[key] = entry
        ttk.Button(form, text="Registrar entrada", style="Primary.TButton", command=self.add_vehicle).grid(row=18, column=0, sticky="ew", pady=(12, 5))
        ttk.Button(form, text="Limpiar campos", command=self.clear_form).grid(row=19, column=0, sticky="ew")

        content = ttk.Frame(body)
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)
        ttk.Label(content, text="Registro de unidades", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        filters = ttk.Frame(content)
        filters.grid(row=1, column=0, sticky="ew", pady=10)
        filters.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(filters)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda _event: self.refresh())
        self.status_filter = ttk.Combobox(filters, values=("Todos", "En patio", "Salida registrada"), state="readonly", width=18)
        self.status_filter.set("Todos")
        self.status_filter.grid(row=0, column=1, padx=(0, 8))
        self.status_filter.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        ttk.Button(filters, text="Buscar", command=self.refresh).grid(row=0, column=2)

        table_frame = ttk.Frame(content)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("id", "plate", "company", "driver", "destination", "cargo", "time", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = ("Folio", "Placa", "Empresa", "Conductor", "Destino", "Carga", "Hora", "Estado")
        widths = (60, 90, 145, 140, 110, 120, 65, 120)
        for column, heading, width in zip(columns, headings, widths):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, minwidth=50)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        actions = ttk.Frame(content)
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(actions, text="Registrar salida", style="Primary.TButton", command=self.mark_departure).pack(side="left")
        ttk.Button(actions, text="Exportar CSV", command=self.export_csv).pack(side="right")
        ttk.Button(actions, text="Exportar PDF", command=self.export_pdf).pack(side="right", padx=8)

    def _metric(self, parent, title, column):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=(18, 10))
        card.grid(row=0, column=column, sticky="w", padx=(0, 10))
        value = ttk.Label(card, text="0", style="Metric.TLabel")
        value.pack(side="left", padx=(0, 10))
        ttk.Label(card, text=title, style="Panel.TLabel").pack(side="left")
        return value

    def add_vehicle(self) -> None:
        values = {key: entry.get().strip() for key, entry in self.entries.items()}
        if any(not value for value in values.values()):
            messagebox.showwarning("Campos incompletos", "Todos los campos son obligatorios.")
            return
        try:
            axles = int(values["axles"])
            weight = float(values["weight_kg"])
            datetime.strptime(values["scheduled_time"], "%H:%M")
            if axles <= 0 or weight < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Datos invalidos", "Revisa ejes, peso y hora. La hora debe usar el formato HH:MM.")
            return
        record_id = self.repository.add(values)
        self.clear_form()
        self.refresh()
        messagebox.showinfo("Entrada registrada", f"La unidad se registro con el folio {record_id:04d}.")

    def clear_form(self) -> None:
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def refresh(self) -> None:
        self.visible_rows = self.repository.search(self.search_entry.get(), self.status_filter.get())
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.visible_rows:
            self.tree.insert("", "end", values=(f"{row['id']:04d}", row["plate"], row["company"], row["driver"], row["destination"], row["cargo_type"], row["scheduled_time"], row["status"]))
        total, active = self.repository.counts()
        self.total_label.config(text=str(total))
        self.active_label.config(text=str(active))

    def selected_id(self) -> int | None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Seleccion requerida", "Selecciona una unidad en la tabla.")
            return None
        return int(self.tree.item(selected[0], "values")[0])

    def mark_departure(self) -> None:
        vehicle_id = self.selected_id()
        if vehicle_id is None:
            return
        self.repository.register_departure(vehicle_id)
        self.refresh()

    def export_csv(self) -> None:
        if not self.visible_rows:
            messagebox.showwarning("Sin resultados", "No hay datos para exportar.")
            return
        EXPORT_DIR.mkdir(exist_ok=True)
        path = EXPORT_DIR / f"fleet_{datetime.now():%Y%m%d_%H%M%S}.csv"
        headers = list(self.visible_rows[0].keys())
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows([tuple(row) for row in self.visible_rows])
        messagebox.showinfo("Exportacion completada", f"Archivo creado en:\n{path}")

    def export_pdf(self) -> None:
        if not self.visible_rows:
            messagebox.showwarning("Sin resultados", "No hay datos para exportar.")
            return
        EXPORT_DIR.mkdir(exist_ok=True)
        path = EXPORT_DIR / f"fleet_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        document = SimpleDocTemplate(str(path), pagesize=landscape(letter), rightMargin=0.35 * inch, leftMargin=0.35 * inch, topMargin=0.35 * inch, bottomMargin=0.35 * inch)
        styles = getSampleStyleSheet()
        elements = [Paragraph("Fleet Access - Reporte operativo", styles["Title"]), Spacer(1, 10)]
        data = [["Folio", "Placa", "Empresa", "Conductor", "Destino", "Carga", "Hora", "Estado"]]
        for row in self.visible_rows:
            data.append([f"{row['id']:04d}", row["plate"], row["company"], row["driver"], row["destination"], row["cargo_type"], row["scheduled_time"], row["status"]])
        table = Table(data, repeatRows=1, colWidths=[0.55*inch, 0.75*inch, 1.4*inch, 1.35*inch, 1.05*inch, 1.15*inch, 0.6*inch, 1.15*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
        document.build(elements)
        messagebox.showinfo("Exportacion completada", f"Archivo creado en:\n{path}")


if __name__ == "__main__":
    FleetApp().mainloop()
