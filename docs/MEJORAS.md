# Revisión y mejoras — 18 de octubre de 2026

## Interfaz 2.1.0

- Inicio reorganizado en tres pasos, con tarjetas y una acción principal clara.
- Tema oscuro unificado, acento óxido, texto sin fondos decorativos y mayor legibilidad.
- Marca con el icono de Rust del proyecto y título que cabe en la barra lateral.
- La aplicación y la vista de diseño leen las cuentas reales de Steam. Se prioriza la cuenta elegida en las preferencias y después la última utilizada. Las pruebas usan cuentas ficticias aisladas.
- Pantallas de Servidores y Wipe en vivo extraídas a componentes de presentación independientes.
- Navegación con desplazamiento de 14 píxeles y duración de 160 ms. Notificaciones discretas, una a la vez, con cierre manual.
- Radar estático en reposo y en movimiento reducido; efectos decorativos de Comunidad eliminados.
- Retraso de arranque validado en el rango de 5 a 300 segundos, coherente con el deslizador existente.
- Recursos del tema incluidos en la compilación.

Comprobaciones añadidas: lectura de dos cuentas desde un archivo VDF de prueba, selección de la última utilizada, fondo transparente de etiquetas y título sin recortes en ventanas de 960 y 1160 píxeles. Se inspeccionó la pantalla Inicio real con el icono y una cuenta local de Steam. Las demás integraciones de Windows y Rust siguen pendientes de una prueba funcional real.

## Decisión técnica

Mantener Python y CustomTkinter. La aplicación depende de Windows (registro, Steam, suspensión y tareas programadas). Reescribirla a otro lenguaje no resuelve por sí mismo sus problemas observados y obligaría a verificar de nuevo esas integraciones. La refactorización puede hacerse por etapas conservando el funcionamiento.

## Cambios de la versión 2.0.7

- Página de Ajustes funcional: movimiento reducido en navegación, reconexión, intervalo, carpeta de datos y diagnóstico.
- Búsqueda por alias o dirección, filtro de favoritos, contador de resultados y acceso con Ctrl+F.
- Enter avanza desde el alias a la dirección y permite añadir desde la dirección.
- Ventana redimensionable horizontal y verticalmente. La navegación deja de restablecer continuamente la altura elegida.
- Cancelación de animaciones de navegación obsoletas al cambiar rápidamente de página.
- Las consultas antiguas del servidor de Inicio no repintan la selección nueva.
- Hasta seis consultas de servidores simultáneas. Las consultas pendientes se cancelan al volver a filtrar la lista.
- Validación única para añadir, editar, importar y lanzar conexiones: IPv4, dominios y puertos 1–65535, incluyendo comandos `connect` y `client.connect` pegados.
- Los alias existentes no se sobrescriben al añadir ni al renombrar.
- Importaciones completas validadas antes de mezclar datos; no sustituyen alias existentes. Límite de 2 MB y 1.000 servidores.
- Guardado mediante archivo temporal, sincronización y sustitución atómica. Copia de la configuración anterior válida y recuperación desde `.bak` con aviso.
- Errores de guardado visibles. Las operaciones de servidores restauran el estado anterior si falla la escritura.
- Guardado del cambio pendiente del deslizador al cerrar.
- Registros con rotación: archivo de 2 MB y tres copias.
- Las actualizaciones se comparan numéricamente para evitar ofrecer una versión anterior. Descarga con timeout y comprobación de tamaño y cabecera de ejecutable.
- Núcleo independiente de Tk para almacenamiento y validación, con pruebas automatizadas.
- Una receta de compilación, dependencias declaradas, entorno virtual y errores de compilación visibles. El script deja de cerrar procesos por la fuerza.
- Workflow de GitHub para pruebas y compilación en Windows, preparado localmente; no se ha subido ni ejecutado en GitHub.
- Limpieza recuperable con manifiesto. Se conservan los recursos, la web, Git y la configuración de herramientas.

## Validación realizada

18 pruebas unitarias de migración, validación, versiones, recuperación y fallos de escritura. Prueba de interfaz con widgets reales de Tk: arranque, Ajustes, añadir un servidor, buscar, filtrar favoritos, navegación rápida y guardar al cerrar. Se usan archivos temporales y se bloquean las acciones de escritura al registro y lanzamiento de procesos.

Compilación Windows mediante PyInstaller 6.16.0, Python 3.12.14, CustomTkinter 5.2.2 y Pillow 12.3.0. El entorno aislado de pruebas emite un aviso de carga de la fuente de CustomTkinter; usa su alternativa de dibujo. Los recursos de CustomTkinter se incluyen explícitamente en el ejecutable.

No se ha hecho una prueba real de encendido, suspensión, inicio automático de Windows, conexión a Rust ni instalación de una actualización. Tampoco se ha evaluado visualmente la aplicación en distintos monitores o escalas DPI. Son verificaciones pendientes antes de distribuir públicamente esta versión.

## Prioridades siguientes

1. **Privilegios y credenciales.** El código actual escribe `DefaultPassword` como texto en Winlogon y la aplicación completa se eleva como administrador. Separar las operaciones privilegiadas de la interfaz y estudiar una integración de AutoLogon que no almacene esa contraseña en texto en Winlogon. Probar migración, desactivación y restauración antes de sustituir el mecanismo. La versión 2.0.7 conserva este comportamiento existente.
2. **Restauración del sistema.** Registrar el estado previo de políticas de bloqueo, energía y selección de cuenta de Steam para restaurar exactamente los valores originales. Ahora hay rutas que imponen valores al desactivar.
3. **Servicios y estado explícito.** Extraer del archivo principal servicios de Steam, tareas, registro, actualizaciones y consultas de servidores. Modelar estados como desactivado, programado, esperando y conectando; distinguir datos confirmados de inferencias. Un ping no confirma que un servidor de Rust esté disponible y la reconexión actual no confirma si estás en cola.
4. **Actualizaciones verificadas.** Firmar ejecutables y verificar integridad y origen antes de sustituirlos; añadir rollback y pruebas de descarga incompleta. La comprobación `MZ` añadida detecta formatos incorrectos, pero no autentica una actualización.
5. **Experiencia de primera configuración.** Asistente breve con servidor, Steam, método de despertar y resumen verificable; mostrar la próxima ejecución y permitir cancelarla claramente. Unificar etiquetas en español y revisar foco, contraste y escalado a 125/150/200 %.
6. **Animación y rendimiento.** Extender movimiento reducido al radar, toasts y animaciones decorativas, pausar efectos en páginas ocultas y usar una cola única para comunicaciones desde trabajadores a Tk. Actualmente el ajuste afecta a las transiciones de navegación.

## Limpieza y recuperación

Antes de aplicar los cambios se guardan los archivos sustituidos bajo `_archive/before-2.0.7-<fecha>/`. La limpieza mueve compilaciones, ejecutables históricos, recetas antiguas y experimentos a `_archive/<fecha>/`, y deja un `manifest.json` con sus rutas originales.

La inspección encontró 121 ejecutables en `releases` (2,35 GB) y 2,88 GB de compilaciones intermedias. Archivar dentro del proyecto ordena las carpetas, pero **no libera espacio en disco**. Se conservan el ejecutable canónico y `RustAutoQueue_v122.exe`. Las copias archivadas se pueden retirar más adelante, tras verificar la nueva versión.

La configuración personal continúa en `%APPDATA%/RustAutoQueue`. No se han modificado tus credenciales, el registro, tareas programadas ni el arranque durante estas verificaciones.
