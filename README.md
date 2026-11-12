# PanelGUI Project Zomboid PRO — Windows Local Console

**Administrador gráfico de Project Zomboid Dedicated Server para Windows 11 x64. No requiere Docker.**

## Corrección v2.1: arranque local sin Docker

Se eliminó el selector Docker/Native de la interfaz y el botón principal **Iniciar servidor** ahora invoca el lanzador local `StartServer64.bat`. El sistema migra automáticamente los ajustes antiguos en modo Docker a modo local Windows.

### Cómo iniciar el servidor

1. Instala **Project Zomboid Dedicated Server** con SteamCMD o desde Steam Tools. Necesitas los archivos reales del servidor, en particular `StartServer64.bat`.
2. Abre la aplicación con `start.bat` o `py -3 main.py`.
3. En **Dashboard → Seleccionar instalación** (o **Servidor → Windows Nativo**) elige la carpeta de instalación que contiene `StartServer64.bat`. **No** elijas `%USERPROFILE%Zomboid`: esa es la carpeta de partidas, configuraciones y datos.
4. Pulsa **Iniciar servidor**. Se abre una **ventana de consola Windows visible**. En el primer inicio puede solicitar la contraseña del administrador.
5. Los datos del mundo normalmente se crean en `%USERPROFILE%Zomboid`, y el INI en `%USERPROFILE%ZomboidServerservertest.ini`. Esas rutas se configuran aparte y no son obligatorias para ejecutar `StartServer64.bat`.
6. Para enviar comandos desde el GUI, habilita RCON en la configuración del servidor y proporciona su host, puerto y contraseña en Ajustes. El cierre por RCON usa el comando `quit` con confirmación.

### Rutas: son dos cosas distintas

| Campo | Ejemplo | ¿Necesario para iniciar? |
|---|---|---|
| Instalación del servidor | `C:ServidoresProjectZomboid` — debe incluir `StartServer64.bat` | **Sí** |
| Carpeta de datos | `C:UsersTU_USUARIOZomboid` | No |
| Configuración INI | `C:UsersTU_USUARIOZomboidServerservertest.ini` | No |
| SteamCMD | `C:SteamCMDsteamcmd.exe` | Solo para instalar/actualizar |
| RCON | `127.0.0.1:27015` | Solo para comandos/stop remoto |

**Estado:** validado mediante pruebas de Python, sin prueba todavía contra un servidor Project Zomboid real en Windows. En caso de error de juego/Java, revisa la ventana de consola; la aplicación no fuerza la terminación de procesos de terceros.

**Backups:** solo manuales, con confirmación explícita de que el mundo está detenido; el programador anterior está desactivado al pasar a nativo para evitar copias inconsistentes.

---

## v2.0 Enterprise UI — Sidebar + TabPages + Windows 11 x64

La versión v2.0 agrega un shell administrativo totalmente reorganizado, **conservando los módulos locales y quitando la dependencia Docker del flujo de ejecución**:

- **Sidebar izquierda** con categorías Dashboard, Servidor, Jugadores, Configuración, Workshop, Backups, Logs, Perfiles e Integraciones.
- **Subpestañas contextuales** dentro de los grupos: Servidor → Windows Nativo / Consola RCON; Configuración → Configuración y Mods / Ajustes.
- **Header de estado** dinámico, navegación contextual, botones con estados y un diseño visual renovado.
- **Dos temas**, oscuro y claro, con escala DPI preparada para Windows 11.
- **Detección automática de rutas**: busca ubicaciones habituales de `Zomboid\Server`, precarga carpeta de datos y archivo `.ini` (revisar la selección si hay varios servidores).
- Las funciones originales siguen en `main.py`, `pz_native.py`, `pz_backup.py` y `pz_features.py`.
- La nueva interfaz está implementada con **Tkinter/ttk estándar**, sin requerir dependencias visuales externas.

**Alcance de pruebas:** CI verifica compilación, importación de módulos y navegación de pestañas a nivel de datos. Todavía se debe validar la presentación visual y los controles en Windows 11 x64 con un servidor real.

## v1.3.1 — fusión e integración de módulos

- Dashboard: iniciar consola de servidor Windows, estado del proceso lanzado y solicitud de parada RCON.
- Ejecución interactiva de StartServer64.bat en una consola Windows visible.
- Consola RCON: comandos manuales, jugadores, guardado y ayuda.
- Moderación: kick, ban, unban, nivel de acceso y entrega de ítems con validación de argumentos y confirmaciones.
- Editor `server.ini` con respaldo local previo.
- Gestor visual básico de `WorkshopItems` y `Mods`: validación de parejas, edición y respaldo del INI.
- Backups ZIP con manifiesto SHA-256 y verificación CRC/archivos. Escritura temporal y publicación al terminar.
- Preparación segura de restauración en carpeta nueva y separada: **no sobrescribe el mundo activo**.
- El antiguo backup programado Docker está deshabilitado en modo local hasta incorporar una comprobación robusta de estado offline.
- Rotación manual o posterior a backup diario; conserva número configurable de copias del formato propio.
- Logs locales del servidor con filtro de texto, recarga y exportación a TXT.
- Consulta periódica del estado Docker cada minuto mientras el GUI esté abierto.
- Auditoría SQLite local de acciones y errores (`audit.sqlite3`).
- Integración de **prueba manual** de webhook Discord.
- **Windows Nativo**: ejecutar un servidor existente a través de `StartServer64.bat`, comprobar el archivo y leer su log local.
- **SteamCMD**: instalar/actualizar y validar el servidor dedicado (app ID 380870) desde la GUI; SteamCMD debe estar previamente instalado.
- **Perfiles**: guardar y cargar rutas, modo docker/native y preferencias sin copiar contraseñas ni webhooks entre servidores.
- **Compilación EXE**: workflow manual de GitHub Actions para construir `PanelGUI_ProjectZomboid_Pro.exe`.
- **Fusión v1.3.1**: eliminado el backup antiguo duplicado; se usa el motor de respaldos SHA-256 desde `pz_backup.py`.
- Ajustes con desplazamiento vertical para acceder a todos los campos, y pruebas de integración entre módulos.
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
py -3 -m compileall -q main.py pz_features.py pz_backup.py pz_native.py pz_paths.py ui_enterprise.py
```

## Advertencias de seguridad

- `%APPDATA%\PanelGUI_ProjectZomboid_Pro\config.json` guarda contraseña y webhook **en texto plano**. No lo compartas; se migrará a almacenamiento seguro.
- Evita exponer el puerto RCON a Internet.
- Detén el servidor para realizar copias de archivos de mundo coherentes. Los backups manuales dependen de confirmación del operador; los automáticos exigen Docker detenido.
- Los nuevos backups usan SHA-256 y CRC; los ZIP antiguos pueden verificarse solo por CRC. La restauración se **prepara** en directorio nuevo sin afectar el mundo activo. El reemplazo final requiere operación manual offline.
- La compatibilidad de comandos RCON (incluidos jugadores/ítems) depende del build PZ.
- `server.ini` y los archivos sandbox pueden depender de versión/build.

## Windows nativo / SteamCMD

1. Instala SteamCMD por tu cuenta y apunta a `steamcmd.exe`. La aplicación no descarga SteamCMD por sí misma.
2. En **Ajustes**, escribe `native` como modo, la ruta de instalación y el lanzador `StartServer64.bat` (por defecto).
3. Abre **Windows Nativo** y utiliza **Instalar / actualizar** para ejecutar SteamCMD. El juego se descarga de Steam con app ID **380870**, iniciando sesión anónimamente. **No actualices mientras el servidor esté en ejecución.**
4. En el **primer arranque**, es preferible ejecutar manualmente el .bat para completar cualquier pregunta interactiva de contraseña administrador y revisar los ajustes de memoria de Java. Una vez configurado, el panel podrá lanzarlo y capturar los logs.
5. Los procesos lanzados fuera de la GUI no se detectan automáticamente. En **Windows Nativo**, «Detener por RCON» solicita un cierre con el comando `quit`; no hay terminación forzada. Los botones principales de Docker solo funcionan en modo Docker.
6. En **Perfiles**, guarda configuraciones por servidor. Los perfiles excluyen contraseña RCON y webhook; vuelve a ingresarlos al cambiar de servidor.

**Nota:** el controlador nativo requiere Windows. Se utiliza el lanzador .bat del servidor; no se gestionan servicios Windows, reinicios automáticos ni actualización del servidor vivo. El backup automático v1.2 sigue siendo **solo Docker**. Los backups manuales de un servidor nativo deben hacerse con el servidor detenido.

## Archivo EXE de Windows

En GitHub ve a **Actions → Build Windows EXE → Run workflow**. Si la compilación finaliza correctamente, descarga el artifact `PanelGUI_ProjectZomboid_Pro-Windows`. El EXE no está firmado digitalmente. No se genera una release automáticamente.

## Backup diario

En **Ajustes** puedes configurar `Backup diario` (true/false), `Hora backup diario` (0-23) y `Cantidad de copias a conservar` (1-365). El GUI debe permanecer abierto; el horario usa la hora local del equipo. Si el contenedor está ejecutándose, se omite el respaldo en ese intento (se volverá a intentar en otro ciclo). La retención elimina solo ZIP anteriores reconocidos como formato propio; guarda copias externas para recuperación ante fallas del disco.

**Limitaciones:** no hay servicio en segundo plano cuando se cierra el GUI, ni sincronización atómica con el proceso del juego; para backups en caliente será necesario un procedimiento especializado.

## Comparación y próximos desarrollos

Consulta [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) para una matriz de capacidades frente al proyecto original y un roadmap de entregas.

## Créditos

Inspiración funcional: [trongio/Zomboid_Server_Manager_Docker](https://github.com/trongio/Zomboid_Server_Manager_Docker) (AGPL-3.0). El código de este repositorio es una implementación independiente en Python; no se ha trasladado el código original.

## Arquitectura integrada

- `main.py`: punto de entrada GUI; integra backend Docker, RCON, controles y pestañas.
- `ui_enterprise.py`: navegación lateral, agrupación de TabPages, temas y DPI.
- `pz_paths.py`: detección local de rutas Zomboid e INI.
- `pz_native.py`: ejecución nativa Windows, argumentos SteamCMD y perfiles.
- `pz_backup.py`: backups verificados SHA-256/CRC, staging y retención.
- `pz_features.py`: moderación, validación de mods, auditoría SQLite y webhook Discord.
- `tests/`: pruebas unitarias y prueba de integración sin interfaz gráfica real.
- `.github/workflows/python.yml`: pruebas en Python 3.10 y 3.12.
- `.github/workflows/windows-exe.yml`: compilación manual del ejecutable Windows.

Esta es una **aplicación modular integrada**, no un único archivo Python monolítico: hay un solo punto de entrada (`main.py`) y módulos especializados mantenibles. La ejecución de ventanas reales, SteamCMD y un servidor conectado sigue requiriendo pruebas en Windows.
