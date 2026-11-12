# PanelGUI Project Zomboid PRO — Enterprise Embedded Console

Administrador gráfico de **Project Zomboid Dedicated Server** para **Windows 11 x64** usando Python 3.10+ y Tkinter. **No requiere Docker**.

## v2.2 — Consola integrada, sin ventanas CMD externas

El servidor **se inicia en segundo plano** utilizando `StartServer64.bat`, con `stdin`, `stdout` y `stderr` conectados a la pestaña **Servidor → Consola integrada**.

- **Iniciar:** ejecuta el servidor Windows sin mostrar una consola externa.
- **Salida en vivo:** mensajes del juego, errores, advertencias y progreso aparecen dentro de la ventana Python.
- **Entrada de comandos:** escribe una orden o respuesta en el campo inferior y pulsa **Enviar** / Enter. Puede utilizarse durante la configuración inicial si el juego admite lectura desde entrada estándar.
- **Autoscroll:** control de desplazamiento automático y límite de líneas para evitar consumo de memoria excesivo.
- **Acciones:** detener ordenadamente con `quit`, limpiar la vista y exportar la salida.
- **Persistencia:** la salida también se registra localmente en `%APPDATA%\\PanelGUI_ProjectZomboid_Pro\\native_server.log`.
- **Sin secretos en eco del GUI:** el campo enviado no se muestra automáticamente en el historial por si contiene la contraseña del primer arranque. No se puede garantizar que el propio juego no incluya información sensible en sus logs.
- **Cierre protegido:** con el proceso iniciado, el panel solicita apagar antes de cerrar, para no romper su conexión a las tuberías de la consola.
- La pestaña **Consola RCON** continúa independiente, para administración por red cuando está habilitado.

**Limitación:** los lanzadores de terceros que abren procesos independientes, se desacoplan o usan APIs de consola Windows en vez de entrada/salida estándar podrían no comportarse correctamente con redirección de tuberías. Para esos casos será necesario integrar un adaptador específico. No se ha probado todavía contra tu instalación real.

El acceso directo `iniciar_servidor_windows.bat` ahora abre el manager en la sección Consola integrada. Debes pulsar Iniciar dentro del panel.

## v2.1 — Inicio local

El botón **Dashboard → Iniciar servidor** ejecuta el lanzador oficial `StartServer64.bat` de tu instalación de Project Zomboid. Redirige la salida y entrada del proceso a la **consola integrada** del panel, sin mostrar una ventana CMD externa. Si no has definido la instalación, el programa te pide seleccionarla antes de arrancar.

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
3. Pulsa **Iniciar servidor**. Ve a **Servidor → Consola integrada** para ver los mensajes y enviar comandos, sin CMD externo.
4. Sigue las indicaciones del servidor en la consola integrada; si solicita contraseña, ingrésala en el campo de entrada. Algunas versiones o launchers pueden no aceptar entrada redirigida.
5. Comprueba la consola integrada antes de conectarte. Si el servidor sale inmediatamente, revisa el error mostrado o `native_server.log`.

> **No confundas rutas:** la carpeta de instalación contiene `StartServer64.bat`. La carpeta de datos normalmente está en `%USERPROFILE%\Zomboid` y contiene partidas, logs y `Server\servertest.ini`. **No necesitas rellenar la carpeta de datos ni el INI para pulsar Iniciar.**

### Alternativa si la GUI principal tiene problemas

Ejecuta **`iniciar_servidor_windows.bat`** para abrir directamente el GUI en la pestaña Consola integrada. Desde allí selecciona la instalación y pulsa Iniciar.

### Control y estado

- **Iniciar servidor:** ejecuta el lanzador local en un proceso oculto y conecta su salida al panel.
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
- El administrador supervisa el proceso abierto por esta sesión, no cualquier servidor iniciado externamente. Si el .bat se desacopla o abre otros procesos, la supervisión puede no representar el servidor real.
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
