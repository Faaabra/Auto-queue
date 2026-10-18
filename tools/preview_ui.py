"""Local design preview with sample data and no system or network operations."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['APPDATA'] = str(ROOT / '.preview-data')
import main

main.App.check_for_updates = lambda self: None
main.App._check_steam_installed = lambda self: None
main.App.check_status = lambda self: None
main.App._populate_active_ip = lambda self: None
main.App.load_servers = lambda self: {
    'Rustoria EU Main': {'ip': 'eu.rustoria.co:28015', 'fav': True},
    'Rustafied EU Long': {'ip': 'eulong.rustafied.com:28015', 'fav': True},
    'Atlas · Monthly': {'ip': '2xmonthlyquad.atlasrust.uk:28015', 'fav': False}}
main.App.load_settings = lambda self: main.validate_settings({})
main.App.save_settings = lambda self: True
main.App.save_servers = lambda self: True
def sample_query(self, ip, subtitle, status, players, ping, wipe, avatar):
    for widget in (subtitle, players, ping, wipe):
        self._unregister_skeleton(widget)
        widget.configure(fg_color='transparent')
    subtitle.configure(text='Servidor de ejemplo · Vista de diseño', text_color='#a9a39b')
    status.configure(text='  Ejemplo  ', text_color='#8eb9a3')
    players.configure(text='184 / 250 jugadores', text_color='#d0ccc5')
    ping.configure(text='32 ms', text_color='#d0ccc5')
    wipe.configure(text='Wipe semanal', text_color='#a9a39b')
main.App._fetch_server_data_async = sample_query
def demo_action(self, *args):
    main.ToastNotification.show(self, 'Vista de diseño · No se realizan acciones del sistema', 'info')
for method in ('activate_auto_queue', 'deactivate_auto_queue', 'test_connection', 'test_windows_password',
               '_toggle_snipe', 'create_wake_task', 'cancel_wake_task', 'set_wake_method',
               'on_steam_user_changed', 'run_system_diagnostic', '_on_reconnect_toggle'):
    setattr(main.App, method, demo_action)
main.winreg.SetValueEx = lambda *args: (_ for _ in ()).throw(RuntimeError('Registry writes disabled in preview'))
app = main.App()
app.title('Auto-Queue · Vista de diseño')
app.mainloop()
