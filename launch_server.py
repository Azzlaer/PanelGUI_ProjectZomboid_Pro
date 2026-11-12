"""Launch the embedded Project Zomboid console from the standalone shortcut.

The server remains owned by the desktop manager; leaving the application
running is required while the server is running.
"""
from main import Application
from ui_enterprise import set_dpi_awareness


def main():
    set_dpi_awareness()
    app = Application()
    app.after(100, lambda: app.chrome.go_tab("Consola integrada"))
    app.mainloop()


if __name__ == "__main__":
    main()
