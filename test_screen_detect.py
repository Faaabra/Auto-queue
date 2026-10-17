"""
Test de detección de estado de Rust por análisis de pantalla.
Ejecuta esto mientras tienes Rust abierto (en cola o dentro del servidor)
para ver qué valores de píxeles capturamos.
"""
import subprocess
import time

# Verificar que PIL está disponible
try:
    from PIL import ImageGrab, Image
    import ctypes
    print("PIL disponible OK")
except ImportError:
    print("Instalando Pillow...")
    subprocess.run(['pip', 'install', 'Pillow'], capture_output=True)
    from PIL import ImageGrab, Image

def get_rust_window():
    """Obtiene la posición y tamaño de la ventana de Rust."""
    import ctypes
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "Rust")
    if not hwnd:
        return None
    
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom

def analyze_screen():
    """Captura la pantalla y analiza regiones clave para detectar el estado."""
    rust_win = get_rust_window()
    
    if rust_win:
        left, top, right, bottom = rust_win
        w = right - left
        h = bottom - top
        print(f"Ventana Rust encontrada: {w}x{h} en ({left},{top})")
    else:
        print("Ventana Rust NO encontrada, usando pantalla completa")
        import ctypes
        left, top = 0, 0
        w = ctypes.windll.user32.GetSystemMetrics(0)
        h = ctypes.windll.user32.GetSystemMetrics(1)
        right, bottom = w, h
        print(f"Pantalla: {w}x{h}")

    # Capturar la ventana/pantalla
    screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
    screenshot.save("rust_screenshot.png")
    print("Screenshot guardado: rust_screenshot.png")
    
    # Analizar regiones clave
    # -------------------------------------------------------
    # REGION 1: Centro-abajo (donde está la barra de inventario en-game)
    inv_region = screenshot.crop((
        int(w * 0.3),   # 30% desde izq
        int(h * 0.85),  # 85% desde arriba (parte baja)
        int(w * 0.7),   # 70% desde izq
        int(h * 0.98)   # 98% desde arriba
    ))
    inv_pixels = list(inv_region.getdata())
    inv_avg = tuple(sum(c) // len(inv_pixels) for c in zip(*inv_pixels))
    inv_brightness = sum(inv_avg[:3]) // 3
    
    # REGION 2: Centro de pantalla (oscuro en cola, colorido en-game)
    center_region = screenshot.crop((
        int(w * 0.35),
        int(h * 0.35),
        int(w * 0.65),
        int(h * 0.65)
    ))
    center_pixels = list(center_region.getdata())
    center_avg = tuple(sum(c) // len(center_pixels) for c in zip(*center_pixels))
    center_brightness = sum(center_avg[:3]) // 3
    
    # Varianza de colores en el centro (alta = en juego, baja = menú/cola)
    r_vals = [p[0] for p in center_pixels]
    variance = sum((x - center_brightness)**2 for x in r_vals) // len(r_vals)
    
    # REGION 3: Esquina inferior-izquierda (barra de salud en-game)
    health_region = screenshot.crop((
        int(w * 0.01),
        int(h * 0.88),
        int(w * 0.15),
        int(h * 0.98)
    ))
    health_pixels = list(health_region.getdata())
    health_avg = tuple(sum(c) // len(health_pixels) for c in zip(*health_pixels))
    
    print("\n--- ANÁLISIS ---")
    print(f"Región INVENTARIO (abajo-centro):")
    print(f"  Color promedio RGB: {inv_avg[:3]}")
    print(f"  Brillo: {inv_brightness}/255")
    
    print(f"\nRegión CENTRO:")
    print(f"  Color promedio RGB: {center_avg[:3]}")
    print(f"  Brillo: {center_brightness}/255")
    print(f"  Varianza de color: {variance}")
    
    print(f"\nRegión SALUD (abajo-izquierda):")
    print(f"  Color promedio RGB: {health_avg[:3]}")
    
    print("\n--- DIAGNÓSTICO ---")
    if center_brightness < 30 and variance < 500:
        print("ESTADO PROBABLE: COLA o MENÚ (pantalla muy oscura y uniforme)")
    elif center_brightness > 60 or variance > 1000:
        print("ESTADO PROBABLE: DENTRO DEL SERVIDOR (pantalla colorida/brillante)")
    else:
        print(f"ESTADO INDETERMINADO (brillo={center_brightness}, varianza={variance})")
    
    # Guardar regiones para inspección visual
    inv_region.save("region_inventario.png")
    center_region.save("region_centro.png")
    health_region.save("region_salud.png")
    print("\nRegiones guardadas como PNG para inspección.")

if __name__ == "__main__":
    print("Ejecutando análisis de pantalla...")
    print("(Asegúrate de tener Rust visible en pantalla)")
    print()
    analyze_screen()
    input("\nPulsa Enter para salir...")
