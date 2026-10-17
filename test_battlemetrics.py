import urllib.request, json

server_id = '30643199'

def get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

# --- 1. Info basica del servidor (sin auth) ---
print('=== INFO DEL SERVIDOR ===')
try:
    data = get('https://api.battlemetrics.com/servers/' + server_id)
    attrs = data['data']['attributes']
    print('Nombre:', attrs['name'])
    print('IP:', attrs['ip'], ':', attrs['port'])
    print('Jugadores:', attrs['players'], '/', attrs['maxPlayers'])
    print('Status:', attrs['status'])
    details = attrs.get('details', {})
    print('Queue:', details.get('rust_queued_players', 'N/A'))
    print('Map size:', details.get('rust_world_size', 'N/A'))
    print('Last wipe:', details.get('rust_last_wipe', 'N/A'))
except Exception as e:
    print('Error info:', e)

print()

# --- 2. Lista de players activos (endpoint publico) ---
print('=== PLAYERS ACTIVOS ===')
try:
    data = get('https://api.battlemetrics.com/players?filter[servers]=' + server_id + '&filter[online]=true&page[size]=100&fields[player]=name')
    players = data.get('data', [])
    print('Total players recibidos:', len(players))
    for p in players[:20]:
        print('  -', p['attributes']['name'])
    if len(players) > 20:
        print('  ... y', len(players) - 20, 'mas')
    # Meta info
    meta = data.get('meta', {})
    print('Meta:', meta)
except Exception as e:
    print('Error players:', e)
