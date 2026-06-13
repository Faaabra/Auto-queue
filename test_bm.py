import urllib.request, json, socket
bm_ip = '195.60.166.217'
url = f'https://api.battlemetrics.com/servers?filter[search]={bm_ip}'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
res = urllib.request.urlopen(req)
bm_data = json.loads(res.read())

for srv in bm_data.get('data', []):
    attrs = srv.get('attributes', {})
    if attrs.get('ip') == bm_ip:
        print(f"Status: {attrs.get('status')} | Name: {attrs.get('name')}")
