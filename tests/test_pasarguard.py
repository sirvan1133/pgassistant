import ast
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from Function import admins, create, db, keyboards, myfeatures
from setup_pasarguard import initialize_database

ROOT = Path(__file__).resolve().parents[1]


def response(status=200, data=None):
    return Mock(status_code=status, json=Mock(return_value=data), text=json.dumps(data))


class GroupTests(unittest.TestCase):
    def test_group_defaults_skip_disabled_and_notice_groups(self):
        groups = [dict(id=4, name='Normal', inbound_tags=['vless']),
                  dict(id=8, name='Notice', inbound_tags=['Holderbot']),
                  dict(id=9, name='Disabled', inbound_tags=[], is_disabled=True)]
        with patch.object(create, 'DEF_GET_GROUPS', return_value=groups):
            _, selected = create.DEF_GET_GROUP_SELECTION(123)
        self.assertEqual(selected, {4: True, 8: False, 9: False})

    def test_group_payload_deduplicates_ids(self):
        self.assertEqual(create.DEF_GROUP_TEMPLATE_PAYLOAD([8, 4, 4]),
                         {'__group_ids__': [4, 8]})

    def test_legacy_inbounds_resolve_groups(self):
        groups = [dict(id=7, inbound_tags=['a', 'b']), dict(id=3, inbound_tags=['c'])]
        with patch.object(db, 'DEF_GET_GROUPS', return_value=groups):
            self.assertEqual(db.DEF_GROUP_IDS_FOR_INBOUNDS(123, {'vmess': ['a', 'b']}), [7])

    def test_legacy_empty_selection_does_not_enable_a_group(self):
        self.assertEqual(db.DEF_GROUP_IDS_FOR_INBOUNDS(123, {}), [])

    def test_holderbot_group_is_discovered_not_hardcoded(self):
        with patch.object(db, 'DEF_GET_GROUPS', return_value=[dict(id=87, inbound_tags=['Holderbot'])]):
            self.assertEqual(db.DEF_HOLDERBOT_GROUP_ID(123), 87)

    def test_absolute_and_relative_subscription_urls(self):
        self.assertEqual(db.DEF_ABSOLUTE_SUBSCRIPTION_URL('https://panel.example/', '/sub/test'),
                         'https://panel.example/sub/test')
        self.assertEqual(db.DEF_ABSOLUTE_SUBSCRIPTION_URL('https://panel.example', 'https://other.example/sub/test'),
                         'https://other.example/sub/test')

    @patch.object(create, 'DEF_PANEL_ACCESS', return_value={'Authorization': 'Bearer test-only'})
    @patch.object(create, 'DEF_IMPORT_DATA', return_value=('admin', 'test-only', 'https://panel.example'))
    def test_create_201_uses_group_ids_and_relative_subscription(self, *_):
        with patch.object(create.requests, 'post', return_value=response(201, {})) as post, \
             patch.object(create.requests, 'get', return_value=response(200, {'subscription_url': '/sub/test'})):
            result = create.DEF_CREATE_USER(123, 'example_user', 40, 30, {}, {'__group_ids__': [7]})
        payload = json.loads(post.call_args.kwargs['data'])
        self.assertEqual(payload['group_ids'], [7])
        self.assertEqual(payload['data_limit'], 40 * 1024 ** 3)
        self.assertNotIn('proxies', payload)
        self.assertTrue(post.call_args.kwargs['verify'])
        self.assertEqual(result, 'https://panel.example/sub/test')

    @patch.object(create, 'DEF_PANEL_ACCESS', return_value={})
    @patch.object(create, 'DEF_IMPORT_DATA', return_value=('admin', 'test-only', 'https://panel.example'))
    def test_no_groups_never_posts_a_user(self, *_):
        with patch.object(create.requests, 'post') as post:
            result = create.DEF_CREATE_USER(123, 'example_user', 40, 30, {}, [])
        post.assert_not_called()
        self.assertIn('no matching PasarGuard group', result)

    def test_protocol_menu_is_hidden(self):
        buttons = [button.text for row in keyboards.KEYBOARD_HOME.keyboard for button in row]
        self.assertFalse(any('Protocol' in text for text in buttons))


class AdminTests(unittest.TestCase):
    @patch.object(admins, 'DEF_PANEL_ACCESS', return_value={})
    @patch.object(admins, 'DEF_IMPORT_DATA', return_value=('admin', 'test-only', 'https://panel.example'))
    def test_role_change_uses_role_id(self, *_):
        with patch.object(admins.requests, 'put', return_value=response()) as put:
            admins.DEF_CHANGE_ROLE(123, 'example_admin', '4')
        self.assertEqual(json.loads(put.call_args.kwargs['data']), {'role_id': 4})

    @patch.object(admins, 'DEF_PANEL_ACCESS', return_value={})
    @patch.object(admins, 'DEF_IMPORT_DATA', return_value=('admin', 'test-only', 'https://panel.example'))
    def test_admin_create_accepts_201(self, *_):
        with patch.object(admins.requests, 'post', return_value=response(201)) as post:
            result = admins.DEF_ADD_ADMIN(123, 'example_admin', 'test-only', '4')
        self.assertEqual(json.loads(post.call_args.kwargs['data'])['role_id'], 4)
        self.assertIn('Admin is added', result)

    @patch.object(admins, 'DEF_PANEL_ACCESS', return_value={})
    @patch.object(admins, 'DEF_IMPORT_DATA', return_value=('admin', 'test-only', 'https://panel.example'))
    def test_delete_accepts_204(self, *_):
        with patch.object(admins.requests, 'delete', return_value=response(204)):
            self.assertIn('Admin is deleted', admins.DEF_DELETE_ADMIN(123, 'example_admin'))


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.temp.name)
        myfeatures.DEF_FEATURES_INIT()

    def tearDown(self):
        os.chdir(self.previous)
        self.temp.cleanup()

    def test_billing_separates_unlimited_from_finite_quotas(self):
        gib = 1024 ** 3
        users = [dict(username='finite', data_limit=40*gib, used_traffic=30*gib),
                 dict(username='unlimited', data_limit=0, used_traffic=90*gib),
                 dict(username='legacy', data_limit=1024**5, used_traffic=10*gib)]
        with patch.object(myfeatures, 'DEF_BILLING_USERS', return_value=users):
            result = myfeatures.DEF_BILLING_CALC(123, 'example_admin', 'finite')
        self.assertEqual(result['allocated_gb'], 40)
        self.assertEqual(result['used_gb'], 30)
        self.assertEqual(result['unlimited_used_gb'], 100)
        self.assertEqual(result['unlimited_count'], 2)
        self.assertEqual(myfeatures.DEF_BILLING_LAST(123, 'example_admin'), (2, 'legacy'))

    def test_user_pagination_fetches_every_page(self):
        session = Mock()
        session.get.side_effect = [response(data={'users': [{'username': str(i)} for i in range(500)]}),
                                   response(data={'users': [{'username': 'last'}]})]
        result = myfeatures._get_all_users('https://panel.example', {}, session=session, admin='example_admin')
        self.assertEqual(len(result), 501)
        self.assertIn('offset=500', session.get.call_args.args[0])


class ResetStateTests(unittest.TestCase):
    """Load only pure helpers; do not construct Telegram clients or run pollers."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        tree = ast.parse((ROOT / 'reseter.py').read_text(encoding='utf8'))
        helpers = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
        self.scope = {'sqlite3': sqlite3, 'RESET_DB': str(Path(self.temp.name) / 'reset.db')}
        exec(compile(helpers, 'reseter-helpers', 'exec'), self.scope)

    def tearDown(self):
        self.temp.cleanup()

    def test_old_reset_database_gets_silent_baseline(self):
        with closing(sqlite3.connect(self.scope['RESET_DB'])) as conn, conn:
            conn.execute('CREATE TABLE reset_state (username TEXT PRIMARY KEY, used_traffic INTEGER)')
            conn.execute("INSERT INTO reset_state VALUES ('example_user', 100)")
        self.scope['init_reset_db']()
        self.assertEqual(self.scope['load_all_states']()['example_user'], (100, None, None, 0))

    def test_initialized_states_and_events_are_persisted(self):
        self.scope['init_reset_db']()
        self.scope['save_all_states']([('example_user', 10, 100, 'example_admin')])
        self.assertEqual(self.scope['load_all_states']()['example_user'], (10, 100, 'example_admin', 1))
        self.scope['save_events']([('quota_change', 'example_user', 'example_admin', 'example_admin',
                                    10, 100, 200, '2026-01-01T00:00:00+00:00')])
        with closing(sqlite3.connect(self.scope['RESET_DB'])) as conn, conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM user_change_events').fetchone()[0], 1)

    def test_owner_handles_string_and_dictionary(self):
        self.assertEqual(self.scope['get_owner']({'admin': 'example_admin'}), 'example_admin')
        self.assertEqual(self.scope['get_owner']({'admin': {'username': 'example_admin'}}), 'example_admin')
        self.assertEqual(self.scope['get_owner']({}), '?')

    def test_unlimited_quota_formatting(self):
        self.assertEqual(self.scope['format_quota'](None), 'Unlimited')
        self.assertEqual(self.scope['format_quota'](0), 'Unlimited')
        self.assertEqual(self.scope['format_quota'](30*1024**3), '30.0 GB')


class SetupTests(unittest.TestCase):
    def test_parameterized_credentials_and_existing_database_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'holder.db'
            args = dict(chat_id=123, nickname="name's", username='example_admin',
                        password="test'quoted", domain='https://panel.example/', token='test-only')
            initialize_database(path, **args)
            with self.assertRaises(FileExistsError):
                initialize_database(path, **args)
            with closing(sqlite3.connect(path)) as conn, conn:
                record = conn.execute('SELECT name, password, domain FROM users').fetchone()
            self.assertEqual(record, ("name's", "test'quoted", 'https://panel.example'))


if __name__ == '__main__':
    unittest.main()
