# PanelGUI Project Zomboid PRO — Windows Local Console

Administrador gráfico de **Project Zomboid Dedicated Server** para **Windows 11 x64** usando Python 3.10+ y Tkinter. **No requiere Docker**.

## v2.1 — Inicio del servidor local corregido

El botón **Dashboard → Iniciar servidor** ejecuta el lanzador oficial `StartServer64.bat` de tu instalación de Project Zomboid. Abre una **consola Windows interactiva y visible**, por lo que puedes responder preguntas del primer inicio y ver los errores directamente. Si no has definido la instalación, el programa te pide seleccionarla antes de arrancar.

El modo antiguo Docker ya no aparece en los ajustes y las configuraciones existentes se migran a modo local.

### Requisitos

- Windows 11 x64 o Windows Server compatible con la versión del juego.
- Python 3.10 o superior (para usar `main.py`) o el ejecutable Windows cuando se compile.
- **Project Zomboid Dedicated Server** instalado. Debe existir `StartServer64.bat` en su carpeta de instalación.
- SteamCMD es **opcional** si ya instalaste el servidor; úsalo solamente para instalación/actualización.
- RCON es **opcional para iniciar**, pero necesario para enviar comandos desde el panel o solicitar apagado desde la GUI.

### Ejecución

```powershell
git clone https://github.com/Azzlaer/PanelGUI_ProjectZomboid_Pro.git
cd PanelGUI_ProjectZomboid_Pro
py -3 main.py
```

Si ya tienes el repositorio, ejecuta `git pull origin main` antes de iniciarlo.

Alternativamente, usa `start.bat`.

### Iniciar el servidor por primera vez

1. Abre **Dashboard** y pulsa **Seleccionar instalación**.
2. Elige la **carpeta donde está `StartServer64.bat`**; por ejemplo, `C:\Servidores\ProjectZomboid`.
3. Pulsa **Iniciar servidor**. Aparecerá una ventana de consola; no la cierres mientras el servidor deba seguir funcionando.
4. Sigue las indicaciones del propio servidor, especialmente si solicita la contraseña de administración inicial.
5. Comprueba la consola antes de intentar conectarte con el juego. Si el lanzador termina inmediatamente, revisa lo que informa Windows (Java, archivos o configuración).

> **No confundas rutas:** la carpeta de instalación contiene `StartServer64.bat`. La carpeta de datos normalmente está en `%USERPROFILE%\Zomboid` y contiene partidas, logs y `Server\servertest.ini`. **No necesitas rellenar la carpeta de datos ni el INI para pulsar Iniciar.**

### Alternativa si la GUI principal tiene problemas

Ejecuta **`iniciar_servidor_windows.bat`**. Es un iniciador independiente que lee la instalación guardada o pregunta por una carpeta con `StartServer64.bat`, y abre una consola Windows del servidor.

### Control y estado

- **Iniciar servidor:** abre el lanzador local en consola Windows.
- **Actualizar estado:** comprueba el proceso de consola iniciado desde esta sesión del GUI. No equivale a una comprobación de que el mundo terminó de cargarse.
- **Detener por RCON:** solicita el cierre usando `quit` con confirmación. Si RCON está deshabilitado, puedes utilizar los controles del servidor directamente desde su consola.
- **Guardar mundo:** envía `save` por RCON si está habilitado.
- **Consola / Logs:** intenta leer los logs locales en la carpeta `Zomboid\Logs`; para el primer inicio, mira la ventana de consola.
- **Instalar / actualizar:** ejecuta SteamCMD previamente instalado para la app dedicada `380870`; nunca actualices la instalación mientras el servidor esté abierto.

### Otros módulos integrados

- Consola RCON y comandos de moderación.
- Edición y copia de seguridad previa de `server.ini`.
- Gestión pareada de `WorkshopItems` y `Mods`.
- Respaldos ZIP con validación CRC y SHA-256.
- Preparación de restauración a una carpeta nueva (no reemplaza mundos).
- Auditoría local SQLite, webhook de prueba Discord y perfiles.
- Interfaz Enterprise con menú lateral, subpestañas y temas claro/oscuro.
- Detección guiada de la carpeta `Zomboid` y los archivos `.ini`.

### Importante sobre backups

El programador automático antiguo de Docker se **desactivó** en esta modalidad local. Puedes crear respaldos manuales **solo después de detener el servidor**. La aplicación comprueba el proceso que ella abrió, pero no puede confirmar que otra instancia externa esté detenida. La restauración nunca sobrescribe directamente los datos en uso.

### Seguridad y limitaciones

- El archivo `%APPDATA%\PanelGUI_ProjectZomboid_Pro\config.json` todavía guarda contraseña RCON y webhook sin cifrado; no lo compartas.
- No expongas RCON a Internet. Usa localhost o una red privada confiable.
- El administrador supervisa el proceso abierto por esta sesión, no cualquier servidor iniciado externamente. Si un lanzador inicia otros procesos y se cierra, puede dejar de ser posible detectar el proceso real desde el GUI.
- **Las pruebas automáticas pasan en Windows y Linux, Python 3.10 y 3.12**; la ejecución con un servidor Project Zomboid real requiere validación en tu equipo.
- Para compilar a EXE: **GitHub → Actions → Build Windows EXE → Run workflow**. El archivo generado se obtiene desde los artefactos de la ejecución; no está firmado digitalmente.

## Estructura del proyecto

| Archivo | Función |
|---|---|
| `main.py` | Consola gráfica y punto de entrada |
| `iniciar_servidor_windows.bat` / `launch_server.py` | Iniciador local independiente |
| `pz_native.py` | Lanzador de procesos Windows, SteamCMD y perfiles |
| `pz_backup.py` | Backups y validaciones |
| `pz_features.py` | RCON/moderación, SQLite, mods y Discord |
| `pz_paths.py` | Detección de rutas de configuración |
| `ui_enterprise.py` | Navegación Enterprise y temas |
| `tests/` | Pruebas unitarias e integración |

## Créditos

Proyecto Python independiente inspirado funcionalmente en [trongio/Zomboid_Server_Manager_Docker](https://github.com/trongio/Zomboid_Server_Manager_Docker). No contiene código copiado del original.
