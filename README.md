# PanelGUI Project Zomboid PRO

Administrador de escritorio para **Project Zomboid** escrito en Python 3.10+ y Tkinter, pensado para Windows y contenedores Docker Linux.

## Primer release - v1.0

- Dashboard de estado del contenedor Docker.
- Arranque, parada y reinicio del contenedor (con confirmación).
- Consulta de logs Docker.
- Consola Source RCON con autenticación y comandos básicos.
- Editor de `server.ini` y de entradas `WorkshopItems` / `Mods` con copia de seguridad antes de guardar.
- Respaldo manual ZIP del directorio local de datos.
- Ajustes persistentes en `%APPDATA%/PanelGUI_ProjectZomboid_Pro/config.json`.
- Interfaz oscura; operaciones de red y Docker fuera del hilo visual.

## Ejecutar

En Windows, instalar Python 3.10 o superior y ejecutar `start.bat` o:

```powershell
py -3 main.py
```

Docker CLI y el motor Docker deben estar instalados y funcionando. Configurar **Ajustes** antes de administrar el servidor. Para usar RCON, debe estar habilitado y accesible mediante red confiable o túnel privado. Los archivos de volumen Docker no son necesariamente accesibles como directorios normales de Windows: el editor y los backups necesitan rutas locales válidas.

## Importante

**No se verificó la ejecución contra un servidor real**. Los comandos y respuestas RCON pueden variar entre versiones. Las credenciales se guardan sin cifrado en el perfil local: no compartir `config.json`. No abrir RCON a Internet. El backup es más seguro con el servidor detenido. No existe restauración automática en esta entrega.

## Próximos módulos

Soporte nativo Windows sin Docker; almacenamiento seguro de credenciales; módulo de jugadores, moderación, whitelist, mods Steam Workshop, respaldos programados/restauración verificada, estadísticas SQLite, alertas Discord, y puente Lua para funciones avanzadas de juego.

## Crédito

Inspiración funcional: [trongio/Zomboid_Server_Manager_Docker](https://github.com/trongio/Zomboid_Server_Manager_Docker). Implementación independiente en Python; **no incorpora código de aquel repositorio**. Si se reutiliza código original, hay que cumplir AGPL-3.0.
