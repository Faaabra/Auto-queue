import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autoqueue_core.storage import load_json, read_json, save_json, MAX_JSON_BYTES
from autoqueue_core.validation import normalize_address, validate_servers, validate_settings, is_newer_version


class ValidationTests(unittest.TestCase):
    def test_console_command_and_quotes(self):
        self.assertEqual(normalize_address(' CLIENT.CONNECT "EU.Example.com:28015" '), 'eu.example.com:28015')

    def test_plain_ip_and_default_port(self):
        self.assertEqual(normalize_address('127.0.0.1'), '127.0.0.1')
        self.assertEqual(normalize_address('localhost:00080'), 'localhost:80')

    def test_rejects_invalid_hosts_and_commands(self):
        for value in ('999.1.1.1', '-bad.com', 'bad-.com', 'a..com', 'x_y.com', 'host:0', 'host:65536', 'host:2:3', 'host&calc', 'host\ncalc', 'host:１２３', '', None, 'a' * 64 + '.com'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_address(value)

    def test_legacy_server_migration(self):
        self.assertEqual(validate_servers({'A': 'connect EU.Example.com:28015'}), {'A': {'ip': 'eu.example.com:28015', 'fav': False}})

    def test_import_validates_entire_document(self):
        for value in ([], {'': 'host'}, {'A': {}}, {'A': {'ip': 'host', 'fav': 'false'}}, {'A': None}, {'A': 'host', ' A ': 'host'}, {'A\nB': 'host'}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_servers(value)

    def test_server_limit(self):
        with self.assertRaises(ValueError):
            validate_servers({str(i): 'host' for i in range(1001)})

    def test_preserves_metadata(self):
        self.assertEqual(validate_servers({'A': {'ip': 'host', 'fav': True, 'note': 'hola'}})['A']['note'], 'hola')

    def test_settings_are_bounded(self):
        data = validate_settings({'delay': 900, 'reconnect_interval': -50, 'reduce_motion': 'false', 'active_steam_user': []})
        self.assertEqual(data['delay'], 300)
        self.assertEqual(data['reconnect_interval'], 5)
        self.assertFalse(data['reduce_motion'])
        self.assertNotIn('active_steam_user', data)

    def test_settings_invalid_values(self):
        for value in (None, 'abc', [], True, 2.5):
            self.assertEqual(validate_settings({'delay': value})['delay'], 10)
        self.assertIsNone(validate_settings({'wake_method': 'bad'})['wake_method'])

    def test_versions_cannot_downgrade(self):
        self.assertTrue(is_newer_version('v2.0.10', '2.0.7'))
        for candidate in ('2.0.6', '2.0.7', '2.0.8-beta', '', 'other'):
            self.assertFalse(is_newer_version(candidate, '2.0.7'))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'servers.json'
        self.old = {'Uno': {'ip': 'localhost:28015', 'fav': True}}
        self.new = {'Dos': {'ip': 'example.com:28015', 'fav': False}}

    def test_atomic_save_and_backup(self):
        save_json(self.path, self.old, validate_servers)
        save_json(self.path, self.new, validate_servers)
        self.assertEqual(read_json(self.path), self.new)
        self.assertEqual(read_json(str(self.path) + '.bak'), self.old)

    def test_recovery_from_corrupt_main(self):
        save_json(self.path, self.old, validate_servers)
        save_json(self.path, self.new, validate_servers)
        self.path.write_text('{bad', encoding='utf-8')
        notices = []
        self.assertEqual(load_json(self.path, validate_servers, dict, notices.append), self.old)
        self.assertTrue(notices)

    def test_bad_main_does_not_replace_good_backup(self):
        save_json(self.path, self.old, validate_servers)
        save_json(self.path, self.new, validate_servers)
        self.path.write_text('[]', encoding='utf-8')
        save_json(self.path, self.new, validate_servers)
        self.assertEqual(read_json(str(self.path) + '.bak'), self.old)

    def test_failed_replace_keeps_previous(self):
        save_json(self.path, self.old, validate_servers)
        with patch('autoqueue_core.storage.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                save_json(self.path, self.new, validate_servers)
        self.assertEqual(read_json(self.path), self.old)
        self.assertEqual(list(Path(self.tmp.name).glob('*.tmp')), [])

    def test_invalid_save_does_not_modify_file(self):
        save_json(self.path, self.old, validate_servers)
        with self.assertRaises(ValueError):
            save_json(self.path, {'bad': None}, validate_servers)
        self.assertEqual(read_json(self.path), self.old)

    def test_missing_configuration_defaults(self):
        self.assertEqual(load_json(self.path, validate_servers, dict), {})

    def test_rejects_oversized_import(self):
        self.path.write_bytes(b' ' * (MAX_JSON_BYTES + 1))
        with self.assertRaises(ValueError):
            read_json(self.path)

    def test_utf8_bom_supported(self):
        self.path.write_text(json.dumps(self.old), encoding='utf-8-sig')
        self.assertEqual(read_json(self.path), self.old)


if __name__ == '__main__':
    unittest.main()
