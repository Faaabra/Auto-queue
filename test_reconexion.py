"""
Script de diagnóstico del modo reconexión.
Ejecutar con: py test_reconexion.py
"""

import os
import subprocess
import socket

# ============================================================
# CONFIG - Cambia esto a la IP de tu servidor
# ============================================================
SERVER_IP = "2xmonthlyquad.atlasrust.uk:28015"
# ============================================================

def check_rust_running():
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq RustClient.exe', '/NH'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        running = 'rustclient.exe' in result.stdout.lower()
        print(f"[RUST CORRIENDO]: {'✅ SÍ' if running else '❌ NO'}")
        return running
    except Exception as e:
        print(f"[ERROR tasklist]: {e}")
        return False

def check_log():
    rust_log_paths = [
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'LocalLow', 'Facepunch Studios LTD', 'Rust', 'Player.log'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'LocalLow', 'Facepunch Studios LTD', 'Rust', 'output_log.txt'),
    ]

    for log_path in rust_log_paths:
        print(f"\n[LOG PATH]: {log_path}")
        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            print(f"  ✅ Existe - Tamaño: {size / 1024 / 1024:.1f} MB")

            # Leer últimos 50KB
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(max(0, size - 51200))
                content = f.read()

            lines = content.splitlines()
            print(f"  Últimas {len(lines)} líneas leídas (50KB)")

            # Buscar palabras clave
            keywords = ['connect', 'disconnect', 'timeout', 'kicked', 'joining', 'leaving', 
                       'network', 'server', 'client', 'steam', 'host', 'peer']
            
            found_lines = []
            for line in lines:
                low = line.lower()
                for kw in keywords:
                    if kw in low:
                        found_lines.append(line.strip())
                        break
            
            if found_lines:
                print(f"\n  🔍 Líneas relevantes encontradas ({len(found_lines)}):")
                for l in found_lines[-20:]:  # últimas 20
                    print(f"    >> {l}")
            else:
                print(f"\n  ⚠️  NINGUNA línea relevante encontrada en los últimos 50KB")
                print(f"  Las últimas 5 líneas del log son:")
                for l in lines[-5:]:
                    print(f"    {l}")
        else:
            print(f"  ❌ No existe")

def check_net_connection():
    host = SERVER_IP.split(":")[0]
    port = int(SERVER_IP.split(":")[1]) if ":" in SERVER_IP else 28015
    
    print(f"\n[RESOLVING]: {host}")
    try:
        ip = socket.gethostbyname(host)
        print(f"  ✅ Resuelto: {ip}")
    except Exception as e:
        print(f"  ❌ Error DNS: {e}")
        return

    print(f"\n[NETSTAT UDP]:")
    try:
        result = subprocess.run(['netstat', '-n', '-p', 'UDP'], capture_output=True, text=True, creationflags=0x08000000)
        udp_lines = [l for l in result.stdout.splitlines() if ip in l]
        if udp_lines:
            print(f"  ✅ Conexión UDP a {ip} detectada!")
            for l in udp_lines:
                print(f"    {l}")
        else:
            print(f"  ❌ Sin UDP a {ip} (Rust usa RakNet/SteamNetworking, no UDP estándar)")
    except Exception as e:
        print(f"  Error: {e}")

    print(f"\n[NETSTAT TCP]:")
    try:
        result = subprocess.run(['netstat', '-n', '-p', 'TCP'], capture_output=True, text=True, creationflags=0x08000000)
        tcp_lines = [l for l in result.stdout.splitlines() if ip in l]
        if tcp_lines:
            print(f"  ✅ Conexión TCP a {ip} detectada!")
            for l in tcp_lines:
                print(f"    {l}")
        else:
            print(f"  ❌ Sin TCP ESTABLISHED a {ip}")
    except Exception as e:
        print(f"  Error: {e}")

def test_reconnect_url():
    print(f"\n[TEST URL RECONEXIÓN]:")
    ip = SERVER_IP
    import time
    rust_args_url = f"+connect%20{ip}%20+aq%20{int(time.time())}"
    url = f"steam://run/252490//{rust_args_url}"
    print(f"  URL que se lanzaría: {url}")
    resp = input("  ¿Quieres lanzar esta URL ahora para probar? (s/n): ").strip().lower()
    if resp == 's':
        subprocess.Popen(['explorer.exe', url])
        print("  ✅ URL lanzada. Mira si Rust conecta.")

if __name__ == "__main__":
    print("=" * 60)
    print("  DIAGNÓSTICO MODO RECONEXIÓN - Rust Auto-Queue")
    print("=" * 60)
    
    check_rust_running()
    check_log()
    check_net_connection()
    test_reconnect_url()
    
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO COMPLETO")
    input("Pulsa Enter para salir...")
