import socket
import struct

IP = '195.60.166.217'

# --- PASO 1: A2S_INFO para confirmar nombre del server ---
print('=== A2S_INFO ===')
def a2s_info(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    try:
        query = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"
        sock.sendto(query, (ip, port))
        data, _ = sock.recvfrom(4096)
        # Manejar challenge
        if data[4] == 0x41:
            challenge = data[5:9]
            sock.sendto(query + challenge, (ip, port))
            data, _ = sock.recvfrom(4096)
        if data[4] == 0x49:
            offset = 5
            # Leer strings hasta llegar a los datos numericos
            strings = []
            for _ in range(5):  # name, map, folder, game, appid_str
                end = data.index(b'\x00', offset)
                strings.append(data[offset:end].decode('utf-8', errors='ignore'))
                offset = end + 1
            app_id = struct.unpack_from('<H', data, offset)[0]; offset += 2
            players = data[offset]; offset += 1
            max_players = data[offset]; offset += 1
            bots = data[offset]; offset += 1
            return strings[0], players, max_players
    except Exception as e:
        return None, 0, 0
    finally:
        sock.close()

for port in [28015, 28016, 28017]:
    name, players, max_p = a2s_info(IP, port)
    if name:
        print(f'  Puerto {port}: "{name}" - {players}/{max_p}')
    else:
        print(f'  Puerto {port}: sin respuesta')

print()

# --- PASO 2: A2S_PLAYER en varios puertos con timeout mas alto ---
print('=== A2S_PLAYER (intentos extendidos) ===')
for port in [28015, 28016, 28017, 28018, 27015]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5.0)  # timeout mas alto
    try:
        # Enviar peticion inicial para obtener challenge
        sock.sendto(b'\xFF\xFF\xFF\xFF\x55\xFF\xFF\xFF\xFF', (IP, port))
        data, _ = sock.recvfrom(4096)
        header = data[4]
        print(f'Puerto {port}: respuesta inicial -> 0x{header:02X}')

        if header == 0x41:
            challenge = data[5:9]
            print(f'  Challenge recibido: {challenge.hex()}')
            # Re-enviar con challenge
            sock.sendto(b'\xFF\xFF\xFF\xFF\x55' + challenge, (IP, port))
            try:
                data2, _ = sock.recvfrom(65535)
                header2 = data2[4]
                print(f'  Respuesta con challenge -> 0x{header2:02X}, bytes={len(data2)}')
                if header2 == 0x44:
                    num = data2[5]
                    print(f'  PLAYERS ACTIVOS: {num}')
                    offset = 6
                    for i in range(min(num, 30)):
                        try:
                            offset += 1  # index
                            end = data2.index(b'\x00', offset)
                            name = data2[offset:end].decode('utf-8', errors='ignore')
                            offset = end + 1 + 8  # +score(4) +duration(4)
                            print(f'    [{i+1}] {name}')
                        except:
                            break
                else:
                    print(f'  Header inesperado: 0x{header2:02X}')
            except socket.timeout:
                print(f'  Timeout esperando respuesta con challenge (query bloqueada)')
        elif header == 0x44:
            num = data[5]
            print(f'  PLAYERS directos: {num}')
    except socket.timeout:
        print(f'Puerto {port}: timeout total')
    except Exception as e:
        print(f'Puerto {port}: error -> {e}')
    finally:
        sock.close()
