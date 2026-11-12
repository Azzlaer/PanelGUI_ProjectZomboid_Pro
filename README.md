# PanelGUI Project Zomboid PRO

Administrador de escritorio para **Project Zomboid** desarrollado en Python 3.10+ (Tkinter), diseñado para Windows con acceso a Docker y RCON.

## v1.3.1 — fusión e integración de módulos

- Dashboard: inspección de estado del contenedor y operaciones de inicio, apagado y reinicio.
- Métricas Docker a demanda: CPU, RAM y tráfico de red.
- Consola RCON: comandos manuales, jugadores, guardado y ayuda.
- Moderación: kick, ban, unban, nivel de acceso y entrega de ítems con validación de argumentos y confirmaciones.
- Editor `server.ini` con respaldo local previo.
- Gestor visual básico de `WorkshopItems` y `Mods`: validación de parejas, edición y respaldo del INI.
- Backups ZIP con manifiesto SHA-256 y verificación CRC/archivos. Escritura temporal y publicación al terminar.
- Preparación segura de restauración en carpeta nueva y separada: **no sobrescribe el mundo activo**.
- Backups programados diariamente (requieren GUI abierta; solo se ejecutan cuando el contenedor Docker está detenido).
- Rotación manual o posterior a backup diario; conserva número configurable de copias del formato propio.
- Pestaña de logs Docker con filtro de texto, recarga y exportación a TXT.
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
py -3 -m compileall -q main.py pz_features.py pz_backup.py pz_native.py
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
- `pz_native.py`: ejecución nativa Windows, argumentos SteamCMD y perfiles.
- `pz_backup.py`: backups verificados SHA-256/CRC, staging y retención.
- `pz_features.py`: moderación, validación de mods, auditoría SQLite y webhook Discord.
- `tests/`: pruebas unitarias y prueba de integración sin interfaz gráfica real.
- `.github/workflows/python.yml`: pruebas en Python 3.10 y 3.12.
- `.github/workflows/windows-exe.yml`: compilación manual del ejecutable Windows.

Esta es una **aplicación modular integrada**, no un único archivo Python monolítico: hay un solo punto de entrada (`main.py`) y módulos especializados mantenibles. La ejecución de ventanas reales, SteamCMD y un servidor conectado sigue requiriendo pruebas en Windows.
