# Comparación funcional con trongio/Zomboid_Server_Manager_Docker

Fecha de revisión: 2026-11-11. Referencia: [README upstream](https://github.com/trongio/Zomboid_Server_Manager_Docker/blob/main/README.md).

> No confundir implementación independiente de escritorio con clon 1:1 del sistema web. Los servicios Laravel/PostgreSQL/Redis, web pública y Lua bridge **no** están incluidos aquí.

## Matriz de cobertura

| Capacidad | Estado PanelGUI | Pendiente |
|---|---|---|
| Docker start/stop/restart e inspect | Básico | Gestión de imágenes y updates |
| Docker logs | Filtros, recarga y exportación | Auto-refresh independiente de estado y rotación de archivos |
| Docker CPU/RAM | Bajo demanda | Gráficos y muestreo histórico |
| RCON / consola | Básico | Historia persistente, autocompletado y tolerancia multipaquete |
| Moderación (kick/ban/unban/access level) | Controles RCON | Confirmar sintaxis con versión del juego |
| Entrega de objetos | Comando RCON | Registro fiable de entrega |
| Jugadores en línea | Comando RCON sin parser | Tabla, perfiles, estadísticas, filtros |
| Mods Workshop | Edición pareada y validación | Catálogo Steam, reordenamiento y metadatos |
| server.ini | Editor, backup antes de guardar | Formularios categorizados, validación por versión |
| Sandbox Lua | Ausente | Editor y validación |
| Respaldos | ZIP SHA256/CRC, programación diaria en GUI, retención y restauración en carpeta separada | Backup en caliente coherente y rollback atómico |
| SQLite | Auditoría local | Whitelist, métricas históricas y estadísticas |
| Discord | Webhook de prueba manual | Alertas por evento, switches, reintentos y cuotas |
| Whitelist | Ausente | Acceso seguro a serverPZ.db y migraciones |
| Auto-restart | Ausente | Horarios, avisos y coordinación con jugadores |
| Inventario | Ausente | Puente Lua y lecturas confiables |
| Mapa | Ausente | Mosaicos, coordenadas, marcadores |
| Safe zones, PvP, respawn | Ausente | Bridge Lua verificado, eventos y mitigaciones |
| Rankings y estadísticas | Ausente | Origen seguro de datos, persistencia |
| Item shop, wallet, promo codes | Ausente | Modelo contable transaccional y reglas de entrega |
| Portal web, 2FA, API tokens, traducciones | No aplicable a app local | Requiere backend/web si se desea ese alcance |

## Restricciones y seguridad

- **No enviar RCON por Internet abierta**. Usar localhost, red confiable o túnel privado.
- El archivo local `config.json` guarda la contraseña RCON y el webhook **sin cifrar**: se debe migrar a keyring/DPAPI antes de producción.
- No manipular `serverPZ.db` del proceso vivo desde el GUI sin protocolo de bloqueo, backup y pruebas de esquema.
- La restauración de ZIP solo prepara una carpeta nueva; no sustituye el mundo activo ni es rollback automático.
- El nombre de contenedor en Docker es configurable, pero los volúmenes montados NO son automáticamente rutas en Windows.
- No borrar mapas/mundos ni actualizar imágenes Docker automáticamente hasta disponer de backup íntegro verificado.
- Comandos RCON de PZ y soporte de mods cambian según build del juego. Probar en servidor de pruebas antes de producción.
- Funciones de tienda y zonas seguras exigen **validación server-side** y un puente Lua autenticado; no simularlas en el cliente.

## Plan de entregas

1. **v1.1**: GUI de moderación, editor WorkshopItems/Mods, auditoría SQLite, Discord de prueba y recursos Docker. Implementado en código; pendiente prueba real.
2. **v1.2**: monitoreo básico periódico, filtros/exportación logs, backups SHA-256 con staging y retención, programación diaria mientras GUI abierta. Implementado en código. **Pendiente**: secretos con DPAPI/keyring y tests de RCON mock.
3. **v1.3**: controlador de arranque Windows nativo, solicitud de parada por RCON, comandos de SteamCMD, perfiles múltiples sin secretos y workflow manual de empaquetado EXE. Implementado en código; sin pruebas de ejecución Windows real.
4. **v1.4**: whitelist SQLite en offline/snapshot y restauración con verificación de estados.
5. **v2.x**: sandbox config, estadísticas, programador, Discord eventos y mods metadata.
6. **v3.x**: diseño puente Lua opcional, mapa e inventario; estudiar tienda solo con modelo transaccional estable.

## Licencia / atribución

Inspiración funcional: [trongio/Zomboid_Server_Manager_Docker](https://github.com/trongio/Zomboid_Server_Manager_Docker) (AGPL-3.0). Esta implementación es independiente y no copia código de ese repositorio. Si posteriormente incorporamos código original, cumpliremos las condiciones de su licencia.

## v1.3: nota de seguridad

El panel nativo solo supervisa el proceso iniciado en la sesión actual, y no descubre servidores ejecutados por separado. Los scripts StartServer64.bat son archivos locales ejecutables y deben provenir de una instalación confiable. SteamCMD actualiza archivos del servidor: detener previamente también los procesos no gestionados por la GUI. La primera ejecución del juego puede pedir la contraseña del administrador en consola; completar ese inicio manual antes de usar el panel.
