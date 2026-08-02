# 🧈 Plan de Implementación: Sistema "Smooth" Completo

## Objetivo
Transformar la aplicación desde una experiencia rígida y estática a una fluida, moderna y con animaciones suaves en cada interacción, navegación y carga de datos.

## Archivos que se tocarán
- `main.py` (principal, ~80% de los cambios)
- `roadmap.md` (actualización del plan existente)

---

## 1. TRANSICIONES DE PÁGINA (Slide + Fade)

**Qué hace:** Al hacer clic en cualquier ítem del sidebar, la nueva página se desliza desde la derecha con easing cúbico mientras la anterior se oculta. Sin cortes secos.

**Dónde:** Clase `App`, método `switch_page()` (línea ~2829)

**Lógica a implementar:**
1. Posicionar la nueva página fuera de la vista (`relx=1.0`)
2. Animar con `after()` en 20 pasos (duración total ~320ms)
3. Usar curva ease-out cúbica: `f(t) = 1 - (1-t)^3`
4. Al finalizar, quitar la página vieja con `place_forget()`
5. Si es la primera carga (sin página anterior), mostrar directamente sin animación

**Especificaciones:**
- Número de pasos: 20
- Duración por paso: 16ms (~60 FPS)
- La animación NO debe bloquear el resto de la UI

---

## 2. TOAST NOTIFICATIONS (No bloqueantes)

**Qué hace:** Reemplazar TODOS los `styled_showinfo`, `styled_showwarning` y feedback de "Guardado ✓" por notificaciones flotantes que aparecen, flotan 3 segundos y se desvanecen con fade-out. Sin bloquear al usuario.

**Dónde:** Nueva clase `Toast` en `main.py` + modificar todas las llamadas existentes a `styled_showinfo`

**Clase Toast (nueva):**
1. Ventana `tk.Toplevel` con `overrideredirect(True)` y `attributes('-topmost', True)`
2. Posición: esquina superior derecha de la ventana principal
3. Fondo: `#1a1a1c` con `corner_radius=10` en `CTkFrame`
4. Fade-in: de opacidad 0.0 a 1.0 en 5 pasos de 50ms
5. Esperar `duration` ms (por defecto 3000)
6. Fade-out: de 1.0 a 0.0 en 10 pasos de 50ms, luego destruir

**Tipos de toast:**
- `success`: borde/accent verde `#28a745` (guardado, copiado, activado)
- `info`: borde/accent azul `#4db8ff` (información general)
- `error`: borde/accent rojo `#ce422b` (fallos)
- `warning`: borde/accent amarillo `#ffcc00` (avisos)

**Métodos:**
- `Toast(parent, message, toast_type="success", duration=3000)`
- `toast.show()` — lanza la animación
- `toast.fade_in(step)` — interna
- `toast.fade_out()` — interna

**Puntos de reemplazo en `main.py` (buscar y sustituir lógica):**
- `_show_saved_feedback()` → llamar a `Toast(self, "✓ Guardado")`
- `activate_auto_queue()` al final → `Toast(self, "Auto-Cola activada")`
- `deactivate_auto_queue()` al final → `Toast(self, "Auto-Cola desactivada")`
- `add_new_server_inline()` → `Toast(self, "Servidor añadido")`
- `_export_servers()` → `Toast(self, "Servidores exportados")`
- `_import_servers()` → `Toast(self, "Servidores importados")`
- `copy_cmd()` en `refresh_server_list` → `Toast(self, "IP copiada")`
- `test_windows_password()` en éxito → `Toast(self, "Contraseña verificada")`
- `create_wake_task()` → `Toast(self, "Despertador programado")`
- `cancel_wake_task()` → `Toast(self, "Despertador cancelado")`

---

## 3. SKELETON LOADING (Estados de carga)

**Qué hace:** Mientras se consultan los datos A2S de los servidores (ping, jugadores, nombre), mostrar placeholders rectangulares con animación de brillo/pulso, en lugar de texto estático "COMPROBANDO..." o "--/-- PLAYERS".

**Dónde:** `refresh_server_list()` y `_fetch_server_data_async()`

**Lógica:**
1. Crear 3-4 tarjetas "esqueleto" dentro de `self.scroll_servers` al iniciar la carga
2. Cada esqueleto: frame oscuro con 3 rectángulos grises (título, subtítulo, badge)
3. Animación cíclica: cada 400ms cambiar el color de los rectángulos entre `#1b1b1d` y `#2a2a2c`
4. Cuando `_fetch_server_data_async` termina para TODOS los servidores, destruir los esqueletos y mostrar las tarjetas reales con fade-in

**También aplicar en:**
- `on_home_server_selected()` (home_card): mostrar skeleton hasta que llegue la respuesta A2S
- Wipe-Spam: mientras se espera conexión inicial, mostrar skeleton en el radar frame

---

## 4. MICRO-INTERACCIONES EN BOTONES

**Qué hace:** Todos los botones deben tener hover visual, cursor pointer y un sutil "presionado" (scale 0.97 por 80ms).

**Dónde:** Todos los `ctk.CTkButton` existentes

**Lógica:**
1. Bind evento `<Button-1>` en cada botón → reducir tamaño visual momentáneamente
2. No es necesario modificar CustomTkinter directamente
3. Crear helper `_add_press_effect(btn)` que:
   - Guarda el `fg_color` original
   - En `<ButtonPress>`: oscurecer color un 20%
   - En `<ButtonRelease>`: restaurar color (si sigue en hover, restaurar al hover_color original)

---

## 5. RADAR / SPINNER EN WIPE-SPAM

**Qué hace:** El área de estado en la página Wipe-Spam pasa de ser texto plano a un componente visual circular con arco giratorio que indica las fases de escaneo.

**Dónde:** `create_snipe_page()`, dentro del `radar_frame`

**Lógica:**
1. Crear un `tk.Canvas` de ~100x100px con fondo `#0a0a0c`
2. Dibujar círculo exterior fijo (gris oscuro)
3. Dibujar arco móvil (color variable según fase: gris → amarillo → verde)
4. Animar rotación con `after()`: girar 10° cada 30ms (360° en ~1s)
5. Fases visuales:
   - **Esperando:** arco gris, rotación lenta (1 vuelta cada 3s)
   - **Wipe detectado:** arco amarillo, rotación rápida (1 vuelta cada 800ms)
   - **Servidor online:** arco verde, sin rotación, círculo completo fijo
6. Texto de estado debajo del radar (conservar lbl_status existente)

---

## 6. SCROLL SUAVE EN LISTAS

**Qué hace:** Las listas de servidores y logs deben tener scrollbars estilizadas y el scroll debe sentirse fluido.

**Dónde:** `create_servers_page()` y `create_logs_page()`

**Lógica:**
1. Configurar `CTkScrollableFrame` con `scrollbar_button_color="#333"` y `scrollbar_button_hover_color="#555"`
2. Scrollbar width: 6px (más fina = más moderna)
3. En macOS/Windows 11, los frames scrolleables deben tener `corner_radius=0` o muy bajo para no verse forzados
4. Los `CTkTextbox` de logs deben activar scrollbars siempre visibles con estilo minimalista

---

## 7. ESTADO VACÍO MEJORADO (Empty State Premium)

**Qué hace:** Cuando no hay servidores guardados, en lugar de un texto gris plano, mostrar un diseño atractivo con icono grande, texto guía y botón de acción.

**Dónde:** `refresh_server_list()` cuando `not self.servers_data`

**Lógica:**
1. Contenedor centrado verticalmente con fade-in desde opacidad 0
2. Emoji/icono grande: `📭` o `🦀` tamaño 48px
3. Título: "Sin servidores guardados"
4. Subtítulo: "Añade tu primer servidor usando el formulario superior o explora los servidores destacados."
5. Botón: "🔍 Explorar Servidores Destacados" (llama a `open_featured_servers_modal`)
6. Animación de entrada: opacidad 0→1 en 400ms

---

## 8. PASSWORD TOGGLE (Mostrar/Ocultar)

**Qué hace:** Botón dentro del campo de contraseña que alterna entre ocultar y mostrar.

**Dónde:** `create_home_page()`, sección del `pw_entry`

**Lógica:**
1. Añadir botón pequeño `👁` a la derecha del entry
2. Estado 1 (oculto): `show="*"`, botón muestra `👁` (ojo abierto)
3. Estado 2 (visible): `show=""`, botón muestra `👁‍🗨` (ojo tachado)
4. No añadir tooltip al botón, es autoexplicativo

---

## 9. EFECTO GLOW EN TARJETAS DE SERVIDOR

**Qué hace:** Al pasar el ratón sobre una tarjeta de servidor, el borde brilla en rojo óxido y la tarjeta se eleva sutilmente.

**Dónde:** `refresh_server_list()`, en la creación de cada `card`

**Lógica:**
1. Bind `<Enter>`: cambiar `border_color` a `COLOR_RUST_RED` y `fg_color` a `#1f1f23`
2. Bind `<Leave>`: restaurar `border_color` a `#2b2b2f` y `fg_color` a `#18181A`
3. Transición suave: usar `after()` para interpolar el cambio de color en 4 pasos de 50ms
4. NO escalar la tarjeta (puede causar problemas de layout en Tkinter)

---

## 10. DIAGNÓSTICO PREVENTIVO DEL SISTEMA

**Qué hace:** Botón que verifica el estado completo de la configuración de auto-queue y muestra resultados con iconos visuales.

**Dónde:** Nueva función en `App`, botón en `create_home_page()` (columna derecha)

**Lógica:**
1. Botón "🔍 DIAGNOSTICAR SISTEMA" con icono y borde azul
2. Al pulsar, ejecutar en hilo separado las siguientes comprobaciones:
   - ✅/❌ Permisos de administrador
   - ✅/❌ Archivo `.bat` en startup (existe y tiene contenido válido)
   - ✅/❌ Registro Winlogon configurado (AutoAdminLogon = 1)
   - ✅/❌ Steam detectado en el sistema
   - ✅/❌ Cuenta de Steam activa seleccionada
   - ✅/❌ IP del servidor válida y con ping
3. Mostrar resultado en un modal con iconos:
   - ✅ Verde para checks exitosos
   - ❌ Rojo para fallos con sugerencia de solución
   - ⚠️ Amarillo para advertencias (ej: sin contraseña guardada)

**Modal de resultado:**
- Usar `ctk.CTkToplevel` (NO `tk.Toplevel`)
- Lista vertical de checks con iconos y textos
- Botón "Cerrar" al final
- Ancho: 450px, alto: variable según resultados

---

## 11. PÁGINA DISCORD CON GRADIENTE ANIMADO

**Qué hace:** La página de Discord deja de ser texto plano estático y pasa a tener un fondo con gradiente animado y efecto typewriter.

**Dónde:** `create_discord_page()`

**Lógica:**
1. Canvas de fondo que ocupa toda la página
2. Gradiente radial que se mueve lentamente (usar `after()` para recalcular posición)
3. Título "PRÓXIMAMENTE" con animación typewriter (aparece letra a letra, 80ms entre letras)
4. Subtítulo con fade-in después de completar el título
5. Icono de Discord grande en el centro con pulso de opacidad (0.7 ↔ 1.0 cada 2s)

---

## 12. FEATURED SERVERS MODAL → CTK

**Qué hace:** El modal de servidores destacados usa `tk.Toplevel` nativo, hay que pasarlo a `ctk.CTkToplevel`.

**Dónde:** `open_featured_servers_modal()`

**Lógica:**
1. Cambiar `tk.Toplevel` por `ctk.CTkToplevel`
2. Eliminar `modal.configure(bg="#121212")` (CTk usa `fg_color`)
3. Añadir `w.transient(self)` y `w.grab_set()`
4. Añadir botón de cerrar (X) en esquina superior derecha
5. Aplicar icono `rust.ico` igual que en otros modales con el truco del `withdraw` + `after`

---

## ORDEN DE IMPLEMENTACIÓN RECOMENDADO

Seguir este orden para ver resultados incrementales:

| Paso | Tarea | Impacto | Dificultad |
|:---|:---|:---|:---|
| **1** | Transiciones de página | 🔥 Muy alto | Baja |
| **2** | Toast notifications | 🔥 Muy alto | Media |
| **3** | Password toggle | ⚡ Medio | Baja |
| **4** | Glow en tarjetas | ⚡ Medio | Baja |
| **5** | Empty state premium | ⚡ Medio | Baja |
| **6** | Featured modal → CTk | ⚡ Medio | Baja |
| **7** | Skeleton loading | ⚡ Medio | Media |
| **8** | Radar / Spinner | 💎 Alto | Alta |
| **9** | Diagnóstico preventivo | 💎 Alto | Alta |
| **10** | Discord gradient | 💎 Alto | Media |
| **11** | Scroll suave | 💎 Alto | Media |
| **12** | Micro-interacciones | 🔧 Detalle | Media |

---

## NOTAS PARA EL DESARROLLADOR (IDE CON IA)

1. **Nunca usar `sleep()` en el hilo principal:** Toda animación debe usar `after()`.
2. **Respetar los colores existentes:** `COLOR_RUST_RED`, `COLOR_BLUE`, `COLOR_GREEN`, etc.
3. **Iconos Unicode:** Usar los ya definidos en `btn_data` (línea 430) para mantener consistencia.
4. **No romper funcionalidad:** Las mejoras son visuales y de UX, NO cambian la lógica de negocio (Winlogon, .bat, Steam, A2S).
5. **Hilos para tareas pesadas:** Toda consulta A2S, ping, registro de Windows o petición HTTP debe ejecutarse en `threading.Thread` con `daemon=True`.
6. **Usar `self.after(0, callback)` para actualizar UI desde hilos:** Nunca modificar widgets desde un hilo secundario.
7. **No reinventar diálogos:** Para confirmaciones y errores críticos, seguir usando `styled_askyesno` y `styled_showerror`. Los toasts son solo para feedback no crítico.