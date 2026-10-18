"""Exercise real Tk widgets with isolated files and all system/network actions stubbed."""
import os
import logging
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
    os.environ['APPDATA'] = directory
    import main
    errors = []
    main.styled_showerror = lambda *args, **kwargs: errors.append(args[1:])
    main.styled_showwarning = lambda *args, **kwargs: errors.append(args[1:])
    def unexpected_system_action(*args, **kwargs):
        raise AssertionError('Unexpected system action')
    steam_root = Path(directory) / 'Steam'
    (steam_root / 'config').mkdir(parents=True)
    (steam_root / 'config' / 'loginusers.vdf').write_text('''"users" {
        "76561198000000001" { "AccountName" "account_one" "PersonaName" "Cuenta uno" "MostRecent" "0" }
        "76561198000000002" { "AccountName" "account_two" "PersonaName" "Cuenta dos" "MostRecent" "1" }
    }''', encoding='utf-8')
    with patch.object(main.winreg, 'OpenKey', return_value=object()), \
         patch.object(main.winreg, 'QueryValueEx', return_value=(str(steam_root), 1)), \
         patch.object(main.winreg, 'CloseKey'):
        accounts = main.App.load_steam_accounts(object())
    assert [account['account_name'] for account in accounts] == ['account_one', 'account_two']
    with patch.object(main.App, 'check_for_updates'), patch.object(main.App, '_check_steam_installed'), \
         patch.object(main.App, 'load_steam_accounts', return_value=accounts), \
         patch.object(main.App, 'check_status'), patch.object(main.App, '_populate_active_ip'), \
         patch.object(main.App, '_fetch_server_data_async'), \
         patch.object(main.winreg, 'SetValueEx', side_effect=unexpected_system_action), \
         patch.object(main.subprocess, 'Popen', side_effect=unexpected_system_action):
        app = main.App()
        app.withdraw()
        def pump(seconds=0.1):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                app.update()
                time.sleep(0.01)
        pump()
        assert 'settings' in app.pages
        assert app.steam_dropdown.cget('values') == ['Cuenta uno (account_one)', 'Cuenta dos (account_two)']
        assert app.steam_dropdown.get() == 'Cuenta dos (account_two)'
        assert main.ctk.ThemeManager.theme['CTkLabel']['fg_color'] == 'transparent'
        for width in (960, 1160):
            app.geometry(f'{width}x800')
            pump()
            assert app.brand_title.winfo_x() + app.brand_title.winfo_reqwidth() <= app.brand_title.master.winfo_width()
        app.settings['reduce_motion'] = True
        app.switch_page('settings')
        pump()
        assert app.active_page == 'settings'
        app.switch_page('servers')
        app.new_alias_entry.insert(0, 'EU')
        app.new_ip_entry.insert(0, 'CLIENT.CONNECT example.com:28015')
        app.add_new_server_inline()
        assert app.servers_data['EU']['ip'] == 'example.com:28015'
        app.server_search_var.set('missing')
        pump(0.4)
        assert app.lbl_server_count.cget('text') == '0 / 1 servidores'
        app.server_search_var.set('EU')
        pump(0.4)
        assert app.lbl_server_count.cget('text') == '1 / 1 servidores'
        app.favorites_only_var.set(True)
        app._apply_server_filter()
        assert app.lbl_server_count.cget('text') == '0 / 1 servidores'
        app.settings['reduce_motion'] = False
        for page in ('home', 'logs', 'servers', 'settings'):
            app.switch_page(page)
            pump(0.03)
        pump(1.0)
        assert app.active_page == 'settings'
        managers = {key: getattr(page, '_parent_frame', page).winfo_manager() for key, page in app.pages.items()}
        print('Navigation managers:', managers, 'errors:', errors)
        logging.shutdown()
        assert all(manager == '' for key, manager in managers.items() if key != 'settings')
        app.update_delay_label(42)
        app._on_close()
        assert main.read_json(main.SETTINGS_FILE)['delay'] == 42
        assert errors == [], errors
        print('UI smoke OK: pages, search, favorites, add, rapid navigation, pending save on close; no system actions.')
        logging.shutdown()
