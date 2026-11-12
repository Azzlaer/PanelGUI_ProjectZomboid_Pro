"""Enterprise v2.0 navigation shell for Project Zomboid Manager PRO.

A left sidebar owns the main sections and a second level of tab pages exposes
the existing functional views. No extra GUI packages are required.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass

DARK = {
    "root": "#0b1220",
    "sidebar": "#0e1b2d",
    "surface": "#15243a",
    "surface_alt": "#1b304a",
    "text": "#ecf3fc",
    "muted": "#9aafc7",
    "accent": "#45b7e9",
    "active": "#184563",
    "border": "#263e56",
    "success": "#69deb2",
}
LIGHT = {
    "root": "#eff4f9", "sidebar": "#e3ecf5", "surface": "#ffffff",
    "surface_alt": "#dce9f5", "text": "#15243a", "muted": "#526b87",
    "accent": "#086c9c", "active": "#b8e0f2", "border": "#d1e0ee",
    "success": "#167b55",
}

# Group labels are purposefully distinct from existing Tk Notebook tab labels.
# The original tabs remain accessible and operational; the sidebar is a visual
# navigation layer instead of a rewrite of proven backend logic.
SECTIONS = (
    ("Dashboard", ("Dashboard",)),
    ("Servidor", ("Consola integrada", "Windows Nativo", "Consola RCON")),
    ("Jugadores", ("Jugadores",)),
    ("Configuración", ("Configuración y Mods", "Ajustes")),
    ("Workshop", ("Workshop Mods",)),
    ("Backups", ("Backups",)),
    ("Logs", ("Logs",)),
    ("Perfiles", ("Perfiles",)),
    ("Integraciones", ("Auditoría / Discord",)),
)


def section_for_tab(name: str) -> str | None:
    for group, tabs in SECTIONS:
        if name in tabs:
            return group
    return None


def all_tabs() -> tuple[str, ...]:
    return tuple(item for _, tabs in SECTIONS for item in tabs)


def set_dpi_awareness() -> None:
    """Opt into per-monitor DPI on Windows; safe no-op elsewhere."""
    import os
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError, ValueError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


class EnterpriseChrome:
    def __init__(self, root: tk.Tk, status_var: tk.StringVar, *,
                 theme: str = "dark", on_theme_change=None):
        self.root = root
        self.status_var = status_var
        self.on_theme_change = on_theme_change
        self.theme_name = "light" if theme == "light" else "dark"
        self.colors = LIGHT if self.theme_name == "light" else DARK
        self.current_group = "Dashboard"
        self.sidebar_buttons = {}
        self.child_buttons = {}
        self._changing = False
        self.notebook = None
        self._build()

    def _build(self):
        c = self.colors
        self.root.configure(bg=c["root"])
        self.container = tk.Frame(self.root, bg=c["root"])
        self.container.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.container, bg=c["sidebar"], width=224)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="PZ  /  PRO", fg=c["accent"], bg=c["sidebar"],
                 font=("Segoe UI Semibold", 21, "bold"), anchor="w").pack(
                     fill="x", padx=20, pady=(23, 2))
        tk.Label(self.sidebar, text="ENTERPRISE CONSOLE", fg=c["muted"],
                 bg=c["sidebar"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x", padx=20, pady=(0, 26))
        self.nav_host = tk.Frame(self.sidebar, bg=c["sidebar"])
        self.nav_host.pack(fill="both", expand=True, padx=10)
        tk.Label(self.sidebar, text="PROJECT ZOMBOID  •  v2.2", fg=c["muted"],
                 bg=c["sidebar"], font=("Segoe UI", 8)).pack(
                     side="bottom", padx=14, pady=20, anchor="w")

        self.main = tk.Frame(self.container, bg=c["root"])
        self.main.pack(side="left", fill="both", expand=True)

        self.header = tk.Frame(self.main, bg=c["root"], height=88)
        self.header.pack(fill="x", padx=25, pady=(15, 0))
        self.header.pack_propagate(False)
        left = tk.Frame(self.header, bg=c["root"])
        left.pack(side="left", fill="both", expand=True)
        self.breadcrumb = tk.Label(left, text="OPERATIONS / DASHBOARD", fg=c["muted"],
                                   bg=c["root"], font=("Segoe UI", 9, "bold"), anchor="w")
        self.breadcrumb.pack(anchor="w", pady=(4, 3))
        self.heading = tk.Label(left, text="Dashboard", fg=c["text"], bg=c["root"],
                                font=("Segoe UI Semibold", 22, "bold"), anchor="w")
        self.heading.pack(anchor="w")
        right = tk.Frame(self.header, bg=c["root"])
        right.pack(side="right", anchor="e", pady=(11, 0))
        self.status_label = tk.Label(right, textvariable=self.status_var, fg=c["success"],
                                     bg=c["surface"], font=("Segoe UI", 10, "bold"),
                                     padx=14, pady=10)
        self.status_label.pack(side="right", padx=(8, 0))
        self.theme_btn = tk.Button(right, text="Claro" if self.theme_name == "dark" else "Oscuro",
                                   command=self.toggle_theme, bg=c["surface"], fg=c["text"],
                                   activebackground=c["active"], activeforeground=c["text"],
                                   bd=0, cursor="hand2", padx=13, pady=9)
        self.theme_btn.pack(side="right")
        self.subtab_bar = tk.Frame(self.main, bg=c["root"], height=44)
        self.subtab_bar.pack(fill="x", padx=25, pady=(5, 0))
        self.subtab_bar.pack_propagate(False)
        self.content = tk.Frame(self.main, bg=c["root"])
        self.content.pack(fill="both", expand=True, padx=23, pady=(7, 8))
        self._make_sidebar()

    def _make_sidebar(self):
        c = self.colors
        for _, button in list(self.sidebar_buttons.items()):
            button.destroy()
        self.sidebar_buttons.clear()
        for group, _ in SECTIONS:
            button = tk.Button(
                self.nav_host, text="   " + group, anchor="w",
                command=lambda item=group: self.go_group(item),
                font=("Segoe UI", 10, "bold"), bd=0,
                relief="flat", padx=12, pady=11, cursor="hand2",
                activebackground=c["active"], activeforeground=c["text"])
            button.pack(fill="x", pady=2)
            self.sidebar_buttons[group] = button
        self._style_sidebar()

    def _style_sidebar(self):
        c = self.colors
        for group, button in self.sidebar_buttons.items():
            selected = group == self.current_group
            button.configure(bg=c["active"] if selected else c["sidebar"],
                             fg=c["accent"] if selected else c["text"])

    def attach_notebook(self, notebook: ttk.Notebook):
        self.notebook = notebook
        notebook.bind("<<NotebookTabChanged>>", self._tab_changed, add="+")
        self.go_group("Dashboard")

    def _available(self, group: str) -> list[str]:
        if self.notebook is None:
            return []
        return [name for g, names in SECTIONS if g == group
                for name in names if self._index_for_name(name) is not None]

    def _index_for_name(self, name: str) -> int | None:
        if self.notebook is None:
            return None
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == name:
                return i
        return None

    def go_group(self, group: str):
        if group not in self.sidebar_buttons or self.notebook is None:
            return
        available = self._available(group)
        if not available:
            return
        current = self.notebook.tab(self.notebook.select(), "text")
        target = current if current in available else available[0]
        self.current_group = group
        self._style_sidebar()
        self.go_tab(target)

    def go_tab(self, name: str):
        index = self._index_for_name(name)
        if index is None or self.notebook is None:
            return
        if self.notebook.index(self.notebook.select()) != index:
            self.notebook.select(index)
        self._sync_current(name)

    def _tab_changed(self, _event=None):
        if self.notebook is not None and self.notebook.select():
            self._sync_current(self.notebook.tab(self.notebook.select(), "text"))

    def _sync_current(self, name):
        group = section_for_tab(name)
        if group is None:
            return
        self.current_group = group
        self._style_sidebar()
        c = self.colors
        self.heading.configure(text=group)
        self.breadcrumb.configure(text="OPERATIONS  /  " + group.upper())
        for button in self.child_buttons.values():
            button.destroy()
        self.child_buttons.clear()
        for page in self._available(group):
            selected = page == name
            button = tk.Button(
                self.subtab_bar, text=page,
                command=lambda p=page: self.go_tab(p),
                fg=c["accent"] if selected else c["muted"],
                bg=c["surface_alt"] if selected else c["root"],
                activeforeground=c["text"], activebackground=c["active"],
                font=("Segoe UI", 10, "bold" if selected else "normal"),
                padx=13, pady=7, bd=0, cursor="hand2")
            button.pack(side="left", padx=(0, 7))
            self.child_buttons[page] = button

    def toggle_theme(self):
        new = "light" if self.theme_name == "dark" else "dark"
        if self.on_theme_change:
            self.on_theme_change(new)
        else:
            self.set_theme(new)

    def set_theme(self, new):
        """Theme the navigation chrome (legacy content widgets retain own styles)."""
        self.theme_name = "light" if new == "light" else "dark"
        self.colors = LIGHT if self.theme_name == "light" else DARK
        c = self.colors
        for widget in (self.container, self.main, self.header, self.subtab_bar, self.content):
            widget.configure(bg=c["root"])
        self.root.configure(bg=c["root"])
        self.sidebar.configure(bg=c["sidebar"])
        self.nav_host.configure(bg=c["sidebar"])
        for widget in self.sidebar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=c["sidebar"])
        for widget in self.header.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=c["root"])
                for child in widget.winfo_children():
                    if child == self.status_label:
                        child.configure(bg=c["surface"], fg=c["success"])
                    elif child == self.theme_btn:
                        child.configure(bg=c["surface"], fg=c["text"],
                                        activebackground=c["active"], activeforeground=c["text"],
                                        text="Claro" if self.theme_name == "dark" else "Oscuro")
                    elif isinstance(child, tk.Label):
                        child.configure(bg=c["root"], fg=c["text"] if child == self.heading else c["muted"])
        self._make_sidebar()
        if self.notebook and self.notebook.select():
            self._sync_current(self.notebook.tab(self.notebook.select(), "text"))
