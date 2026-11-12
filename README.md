# PanelGUI Project Zomboid PRO

Administrador de escritorio para **Project Zomboid** desarrollado en Python 3.10+ (Tkinter), diseñado para Windows con acceso a Docker y RCON.

## v1.1 — funcionalidades implementadas en código

- Dashboard: inspección de estado del contenedor y operaciones de inicio, apagado y reinicio.
- Métricas Docker a demanda: CPU, RAM y tráfico de red.
- Consola RCON: comandos manuales, jugadores, guardado y ayuda.
- Moderación: kick, ban, unban, nivel de acceso y entrega de ítems con validación de argumentos y confirmaciones.
- Editor `server.ini` con respaldo local previo.
- Gestor visual básico de `WorkshopItems` y `Mods`: validación de parejas, edición y respaldo del INI.
- Backup ZIP manual del directorio local y verificador **estructural** de ZIP (sin extracción).
- Auditoría SQLite local de acciones y errores (`audit.sqlite3`).
- Integración de **prueba manual** de webhook Discord.
- Estilo oscuro, trabajos Docker/RCON/Discord fuera del hilo principal de Tkinter.

**Nota:** publicado en GitHub; esta versión no se ha probado todavía contra una instalación real de Project Zomboid.

## Inicio rápido

```powershell
git clone https://github.com/Azzlaer/PanelGUI_ProjectZomboid_Pro.git
cd PanelGUI_ProjectZomboid_Pro
.\start.bat
```

Alternativa: `py -3 main.py`. No requiere paquetes pip para ejecutar estas funciones. Es necesario tener Python 3.10+; para la pestaña Docker, el CLI de Docker y el daemon deben estar instalados; para RCON, el servidor debe permitir una conexión por una red confiable.

Configura en **Ajustes**: nombre del contenedor, RCON host, puerto y contraseña, rutas **locales accesibles** para datos e INI y, opcionalmente, webhook Discord. Un volumen interno Docker Linux no equivale a una ruta Windows.

## Pruebas

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q main.py pz_features.py
```

## Advertencias de seguridad

- `%APPDATA%\PanelGUI_ProjectZomboid_Pro\config.json` guarda contraseña y webhook **en texto plano**. No lo compartas; se migrará a almacenamiento seguro.
- Evita exponer el puerto RCON a Internet.
- Detén el servidor para realizar copias de archivos de mundo coherentes.
- Los respaldos se verifican solo por rutas y estructura ZIP; **no** se restauran automáticamente.
- La compatibilidad de comandos RCON (incluidos jugadores/ítems) depende del build PZ.
- `server.ini` y los archivos sandbox pueden depender de versión/build.

## Comparación y próximos desarrollos

Consulta [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) para una matriz de capacidades frente al proyecto original y un roadmap de entregas.

## Créditos

Inspiración funcional: [trongio/Zomboid_Server_Manager_Docker](https://github.com/trongio/Zomboid_Server_Manager_Docker) (AGPL-3.0). El código de este repositorio es una implementación independiente en Python; no se ha trasladado el código original.
