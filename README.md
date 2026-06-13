# 🦀 Rust Auto-Queue Launcher V2

[![Versión](https://img.shields.io/badge/Versi%C3%B3n-2.0.5-brightgreen.svg)](https://github.com/Faaabra/Auto-queue)
[![Desarrollador](https://img.shields.io/badge/Desarrollador-faabra-blue.svg)](https://github.com/Faaabra)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Plataforma](https://img.shields.io/badge/Plataforma-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

**Rust Auto-Queue Launcher** es una aplicación de escritorio diseñada para automatizar el encendido de tu ordenador y la conexión a servidores de Rust, permitiéndote saltarte las largas colas de espera mientras duermes, trabajas o estás fuera de casa.

Esta herramienta configura el inicio automático seguro de sesión de Windows (AutoLogon) y programa el lanzamiento de Steam y de Rust con la dirección IP/dominio de tu elección de forma automatizada tras el encendido.

---

## 🚀 Características Principales

*   **⚡ Inicio Automático de Windows (AutoLogon)**: Registra temporal y de forma segura la contraseña en el sistema para que Windows inicie sesión por sí solo cuando el PC se despierte o encienda.
*   **⏰ Modos de Auto-Despertar**:
    *   **Enchufe Inteligente (Recomendado)**: Configura la BIOS en modo *"Restore on AC Power Loss"* para encender el ordenador mandándole corriente a distancia.
    *   **BIOS RTC**: Configura alarmas en la placa base para encender el PC físicamente a una hora exacta.
    *   **Software (Programador de Tareas)**: Genera tareas en Windows para despertar el PC si está suspendido o hibernando.
*   **📚 Gestor de Servidores**:
    *   Guarda una lista de tus servidores favoritos con alias personalizados.
    *   Botón para copiar la dirección directamente al portapapeles.
    *   **Importar / Exportar**: Permite guardar copias de seguridad de tu lista de servidores o compartirla mediante archivos JSON.
*   **📋 Copia y Pega Inteligente**: Limpia automáticamente prefijos como `connect` o `client.connect` al pegar comandos copiados de la consola F1 de Rust.
*   **🌙 Modo una Sola Noche**: Si solo vas a usar la cola para una ocasión, el archivo de arranque automático se auto-eliminará después del primer lanzamiento.
*   **⚙️ Retraso Configurable**: Control deslizante de 0 a 120 segundos para retrasar el inicio de Rust y permitir que el sistema se inicie y conecte a internet correctamente.
*   **🛠️ Seguridad y Estabilidad**:
    *   Ejecución segura mediante `subprocess.Popen` sin inyecciones de comandos shell.
    *   Avisos de seguridad explícitos sobre el almacenamiento de credenciales en el registro local.
    *   Verificación automática de que Steam está instalado en rutas estándar o de registro.
*   **📡 Actualizaciones Automáticas**: La app comprueba en cada inicio si hay una versión más nueva en GitHub y ofrece descargarla e instalarla con un solo clic.

---

## 🛠️ Requisitos de Ejecución

*   **Sistema Operativo**: Windows 10 u 11 (con permisos de Administrador para manipular el registro y las tareas programadas).
*   **Videojuego**: Steam y Rust instalados.
*   **Dependencias de desarrollo** (si ejecutas desde el código fuente):
    *   Python 3.12 o superior.
    *   Librerías indicadas en la sección de instalación.

---

## 📦 Instalación y Ejecución (Código Fuente)

Si quieres ejecutar el script de desarrollo directamente:

1.  **Clona el repositorio** o descarga los archivos.
2.  **Instala los requisitos** de Python:
    ```bash
    pip install customtkinter pillow
    ```
3.  **Ejecuta la aplicación**:
    ```bash
    py main.py
    ```

*Nota: La aplicación requiere ejecutarse con privilegios de Administrador para realizar cambios en el registro (`Winlogon`) y crear tareas en `schtasks`. Si no se inicia como Administrador, solicitará elevación UAC automáticamente.*

---

## 🔨 Compilar a `.exe`

El proyecto incluye un script listo para compilar la aplicación a un único ejecutable autónomo (`.exe`):

1.  Asegúrate de tener instalado `pyinstaller`:
    ```bash
    pip install pyinstaller
    ```
2.  Haz doble clic sobre el script automatizado:
    ```cmd
    compilar_app.bat
    ```
3.  Busca tu ejecutable compilado en la carpeta `dist/` resultante.

El comando de compilación interna utilizado es:
```bash
py -m PyInstaller --noconsole --uac-admin --onefile --name="RustAutoQueue" --icon="rust.ico" --add-data="rust.ico;." --clean main.py
```

---

## 📖 Guía de Configuración del Auto-Despertar

Para lograr que tu ordenador se encienda solo y entre en la cola antes de que te sientes a jugar:

### Opción A: Enchufe Inteligente (Recomendado)
Esta opción permite encender el PC de forma física desde cualquier lugar mediante un enchufe inteligente (Alexa, Google Home, Tapo, etc.):
1.  Entra en la BIOS de tu ordenador (pulsa `F2` o `Supr` al encender).
2.  Busca la configuración de energía (suele llamarse **Power Management**, **APM** o **Advanced**).
3.  Localiza la opción **Restore on AC Power Loss** (o *AC Back*) y configúrala como **Power On** (o *Always On*).
4.  Apaga el PC por completo por la noche.
5.  Programa en la app móvil de tu enchufe inteligente que este se encienda a la hora deseada (por ejemplo, a las 9:00 AM).
6.  *¡Al recibir corriente, el PC detectará la entrada de electricidad y se encenderá solo!*

### Opción B: BIOS RTC (Despertador por Placa Base)
Si prefieres no usar hardware externo, puedes programar la placa base para que despierte el ordenador:
1.  Accede a la BIOS al arrancar tu ordenador.
2.  Ve a **Advanced** -> **APM Configuration** o **Power Management**.
3.  Activa la opción **Power On By RTC** o **RTC Alarm**.
4.  Configura la hora y los minutos exactos en los que deseas que el PC arranque físicamente.
5.  Guarda los cambios y apaga el PC de manera normal.

### Opción C: Tareas por Software (Suspender/Hibernar)
Si no deseas cambiar nada de la BIOS:
1.  Abre el menú **⏰ Modo Auto-Despertar** en la app.
2.  En la pestaña **Software (Beta)**, selecciona la hora deseada y pulsa **Programar Despertador**.
3.  En lugar de apagar tu ordenador, ponlo en estado de **Suspender** o **Hibernar** (puedes pulsar el botón directo de la aplicación *"Suspender el PC ahora"*).
4.  Windows iniciará el temporizador interno de la placa para despertar el PC en la hora fijada.

---

## 🔒 Notas de Seguridad

> [!WARNING]
> Para habilitar el inicio automático de sesión de Windows (**AutoLogon**), la aplicación debe guardar las credenciales (nombre de usuario, dominio y contraseña cifrada) en la ruta del registro de Windows `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`.
> Esto es el funcionamiento nativo oficial de Windows para esta característica. Sin embargo, significa que **cualquier persona con acceso físico administrativo a tu ordenador podría llegar a leer esta contraseña**. Úsala con discreción y, si vas a dejar de usar la aplicación, pulsa siempre el botón **"Desactivar y Borrar"** para limpiar de forma segura el registro del sistema.

---

## 📝 Registro de Cambios Recientes (v2.0.5)

*   **Soporte de dominios**: Admite conectar usando nombres de dominio complejos (ej. `2xmonthlyquad.atlasrust.uk`) sin necesidad de resolver la IP manualmente.
*   **Limpieza Inteligente**: Extracción automática del host y puerto si se pega la línea de comando `connect` o `client.connect` entera.
*   **Debounce en Slider**: Optimización de escritura a disco. El delay solo se guarda tras 500ms de inactividad del deslizador, reduciendo las operaciones de I/O de disco.
*   **Seguridad Mejorada**: Ejecución libre de inyecciones de comandos usando `subprocess` y advertencia al guardar credenciales en local.
*   **Exportación/Importación de Servidores**: Comparte y guarda tu listado de servidores favoritos cómodamente.

---

## 👥 Créditos

Desarrollado por [faabra](https://github.com/Faaabra). Si tienes alguna sugerencia o error, puedes abrir una issue en el repositorio oficial de GitHub.
