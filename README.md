# Rust Auto-Queue Launcher

Aplicación de escritorio para Windows que programa el lanzamiento de Rust, gestiona servidores y configura opciones de despertar e inicio de sesión. Versión **2.1.0**.

Interfaz renovada con tarjetas para servidor, arranque e inicio de Windows, icono de Rust, cuentas locales reales de Steam, búsqueda y favoritos. Las transiciones son breves y las animaciones se pueden reducir desde Ajustes.

## Uso

Abre `releases/RustAutoQueue.exe`. Windows solicitará permisos de administrador porque la aplicación integra tareas programadas y cambios del registro.

- **Inicio:** servidor, retraso de lanzamiento, cuenta de Steam y modo de una sola noche.
- **Servidores:** añadir, editar, favoritos, búsqueda por nombre/dirección e importar/exportar JSON. Ctrl+F abre el buscador. Se aceptan direcciones y comandos `connect host:puerto` o `client.connect host:puerto`.
- **Auto-despertar:** instrucciones para enchufe inteligente y BIOS, o programación desde suspensión/hibernación. Una tarea de Windows no enciende por sí misma un equipo completamente apagado.
- **Ajustes:** movimiento reducido en navegación, vigilante de reconexión, intervalo, carpeta de datos y diagnóstico.
- **Actividad:** registro de acciones y errores.

La reconexión envía periódicamente una petición de conexión si Rust está abierto; no confirma el estado de la cola ni la entrada al servidor.

## Datos y recuperación

Los servidores, preferencias y registros se guardan en `%APPDATA%/RustAutoQueue`.

El guardado de JSON es atómico. Se conserva una copia `.bak` de la versión anterior válida y se intenta recuperarla si falla la lectura del archivo principal. La aplicación avisa cuando detecta un problema. Las importaciones se validan antes de incorporarse y omiten alias existentes.

**AutoLogon:** el mecanismo actual almacena la contraseña como texto en `DefaultPassword` del registro Winlogon. No está cifrada por esta aplicación. Revisa el aviso de la app antes de activarlo y utiliza «Desactivar y Borrar» para retirar esa configuración. Las mejoras de 2.0.7 conservan este mecanismo existente.

## Desarrollo

Windows 10/11, Python 3.12 o posterior, Steam y Rust para probar las integraciones reales.

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe main.py
```

El acceso al registro y la creación de tareas requieren elevación al ejecutar la aplicación. Importar el módulo para pruebas no solicita UAC.

## Pruebas

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tests\smoke_ui.py
```

Las pruebas de interfaz utilizan datos temporales y sustituyen las acciones de sistema y red. No verifican un despertar real, la entrada a Rust ni una actualización instalada.

## Compilación

Ejecuta `compilar_app.bat`. Prepara `.venv`, instala dependencias, ejecuta las pruebas unitarias y compila usando la única receta `RustAutoQueue.spec`. Si un paso falla, muestra el error. No cierra procesos por la fuerza.

```powershell
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath releases RustAutoQueue.spec
```

El resultado es `releases/RustAutoQueue.exe`, con iconos, fuentes y recursos incluidos.

## Ordenar archivos antiguos

```powershell
powershell -NoProfile -File tools\clean_project.ps1 -WhatIf
powershell -NoProfile -File tools\clean_project.ps1
```

La limpieza archiva archivos conocidos bajo `_archive/<fecha>/` y escribe un manifiesto. No borra las copias ni libera espacio hasta retirarlas posteriormente. Conserva la versión canónica, `RustAutoQueue_v122.exe`, los recursos, la web y Git. Los scripts `test_*.py` originales eran experimentos manuales y se archivan; la suite nueva está en `tests/`.

Consulta [docs/MEJORAS.md](docs/MEJORAS.md) para ver los cambios, límites de las verificaciones y prioridades siguientes.

Desarrollado por [faabra](https://github.com/Faaabra). [Repositorio](https://github.com/Faaabra/Auto-queue).
