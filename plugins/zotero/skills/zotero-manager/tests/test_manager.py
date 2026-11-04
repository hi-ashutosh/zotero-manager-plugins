import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from zotero_manager import Client, ManagerError, private_json, parser, run


class FakeClient(Client):
    def __init__(self, state):
        super().__init__(state)
        self.server = 'test-server'
        self.item = {'key': 'ABCDEFGH', 'version': 12, 'data': {
            'key': 'ABCDEFGH', 'version': 12, 'itemType': 'journalArticle',
            'title': 'Before', 'collections': ['AAAAAAAA', 'BBBBBBBB'], 'DOI': 'unchanged'}}
        self.writes = []
        self.ignore_update = False

    def get(self, path):
        if path.startswith('/collections/'):
            return {'key': path.split('/')[-1], 'version': 1, 'data': {'name': 'Collection'}}
        return copy.deepcopy(self.item)

    def load_auth(self):
        pass

    def write(self, method, path, payload, headers):
        self.writes.append((method, path, payload, headers))
        if not self.ignore_update:
            self.item['data'].update(payload)


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = FakeClient(self.tmp.name)

    def test_preview_has_no_writes_or_backups(self):
        result = self.c.change('items', 'ABCDEFGH', {'title': 'After'})
        self.assertTrue(result['dry_run'])
        self.assertEqual(self.c.writes, [])
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_edit_preserves_other_fields_and_saves_snapshot(self):
        result = self.c.change('items', 'ABCDEFGH', {'title': 'After'}, True)
        self.assertTrue(result['verified'])
        self.assertEqual(result['data']['DOI'], 'unchanged')
        self.assertEqual(self.c.writes[0][3]['If-Unmodified-Since-Version'], '12')
        before = json.loads(Path(result['backup']).read_text())['before']
        self.assertEqual(before['title'], 'Before')
        self.assertEqual(Path(result['backup']).stat().st_mode & 0o777, 0o600)

    def test_move_preserves_unrelated_collection(self):
        result = self.c.membership('ABCDEFGH', ['CCCCCCCC'], ['BBBBBBBB'], True)
        self.assertEqual(result['data']['collections'], ['AAAAAAAA', 'CCCCCCCC'])
        self.assertEqual(len(self.c.writes), 1)

    def test_contradictory_membership_rejected(self):
        with self.assertRaises(ManagerError):
            self.c.membership('ABCDEFGH', ['AAAAAAAA'], ['AAAAAAAA'], True)
        self.assertEqual(self.c.writes, [])

    def test_readback_mismatch_is_not_reported_success(self):
        self.c.ignore_update = True
        with self.assertRaisesRegex(ManagerError, 'verification differed'):
            self.c.change('items', 'ABCDEFGH', {'title': 'After'}, True)
        self.assertEqual(len(self.c.writes), 1)

    def test_managed_fields_rejected(self):
        with self.assertRaises(ManagerError):
            self.c.change('items', 'ABCDEFGH', {'version': 99}, True)
        self.assertEqual(self.c.writes, [])

    def test_credentials_are_private_and_server_bound(self):
        real = Client(self.tmp.name)
        real.server = 'different-server'
        private_json(real.auth_path, {'key': 'secret', 'serverID': 'original-server', 'remember': True})
        with self.assertRaisesRegex(ManagerError, 'another Zotero database'):
            real.load_auth()

    def test_collection_readback_ignores_membership_order(self):
        Client.verify({'collections': ['B', 'A']}, {'collections': ['A', 'B']}, 'journal')

    def test_stale_write_is_not_retried(self):
        def reject(*args):
            self.c.writes.append(args)
            raise ManagerError('HTTP 412')
        self.c.write = reject
        with self.assertRaisesRegex(ManagerError, '412'):
            self.c.change('items', 'ABCDEFGH', {'title': 'After'}, True)
        self.assertEqual(len(self.c.writes), 1)

    def test_single_use_credential_discarded_after_failed_write(self):
        real = Client(self.tmp.name)
        real.server = 'test-server'
        private_json(real.auth_path, {'key': 'secret', 'serverID': real.server, 'remember': False})
        def reject(*args, **kwargs):
            raise ManagerError('HTTP 401')
        real.request = reject
        with self.assertRaisesRegex(ManagerError, '401'):
            real.write('PATCH', '/items/ABCDEFGH', {'title': 'After'}, {})
        self.assertFalse(real.auth_path.exists())
        self.assertIsNone(real.token)

    def test_create_checks_per_object_failure_and_journals_key(self):
        def fail(*args):
            return {'successful': {}, 'failed': {'0': {'code': 400, 'message': 'Invalid field'}}}
        self.c.write = fail
        with self.assertRaisesRegex(ManagerError, 'Create failed'):
            self.c.create('items', {'itemType': 'book', 'title': 'New'}, True)
        journals = list((Path(self.tmp.name) / 'backups').glob('*.json'))
        self.assertEqual(len(journals), 1)
        self.assertEqual(len(json.loads(journals[0].read_text())['key']), 8)

    def test_template_uses_local_schema_without_web_only_endpoint(self):
        def schema(method, path):
            self.assertEqual(method, 'GET')
            if path == '/itemTypeFields?itemType=book':
                return [{'field': 'title'}, {'field': 'ISBN'}], {}
            if path == '/itemTypeCreatorTypes?itemType=book':
                return [{'creatorType': 'author'}], {}
            self.fail('Unsupported local endpoint: ' + path)
        self.c.request = schema
        result = run(parser().parse_args(['template', 'book']), self.c)
        self.assertEqual(result['template']['ISBN'], '')
        self.assertEqual(result['allowedCreatorTypes'], ['author'])
        self.assertEqual(self.c.writes, [])

    def test_collection_rename_keeps_parent_and_uses_current_version(self):
        collection = {'key': 'BBBBBBBB', 'version': 7, 'data': {
            'key': 'BBBBBBBB', 'version': 7, 'name': 'Before', 'parentCollection': 'AAAAAAAA'}}
        self.c.get = lambda path: copy.deepcopy(collection)
        def save(method, path, payload, headers):
            self.c.writes.append((method, path, payload, headers))
            collection['data'].update(payload)
        self.c.write = save
        result = self.c.change('collections', 'BBBBBBBB', {'name': 'After'}, True)
        self.assertTrue(result['verified'])
        method, path, payload, headers = self.c.writes[0]
        self.assertEqual(method, 'PUT')
        self.assertEqual(payload['parentCollection'], 'AAAAAAAA')
        self.assertEqual(headers['If-Unmodified-Since-Version'], '7')

    def test_linked_pdf_preview_uses_original_path_without_copying(self):
        pdf = Path(self.tmp.name) / 'My Paper.pdf'
        pdf.write_bytes(b'%PDF-1.4\n% temporary path-only fixture\n')
        self.c.get = lambda path: [] if path.endswith('/children') else copy.deepcopy(self.c.item)
        result = self.c.link_file('ABCDEFGH', pdf)
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['data']['path'], str(pdf.resolve()))
        self.assertEqual(result['data']['linkMode'], 'linked_file')
        self.assertEqual(result['data']['parentItem'], 'ABCDEFGH')
        self.assertEqual(self.c.writes, [])
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [pdf])

    def test_existing_link_is_not_duplicated(self):
        pdf = Path(self.tmp.name) / 'My Paper.pdf'; pdf.touch()
        def read(path):
            if path.endswith('/children'):
                return [{'key': 'BBBBBBBB', 'data': {'linkMode': 'linked_file'}}]
            if path.endswith('/file/view/url'):
                return pdf.as_uri()
            return copy.deepcopy(self.c.item)
        self.c.get = read
        result = self.c.link_file('ABCDEFGH', pdf, apply=True)
        self.assertFalse(result['changed'])
        self.assertEqual(result['existing_attachment'], 'BBBBBBBB')
        self.assertEqual(self.c.writes, [])

    def test_attachment_parent_is_rejected_before_writing(self):
        pdf = Path(self.tmp.name) / 'paper.pdf'; pdf.touch()
        self.c.item['data']['itemType'] = 'attachment'
        with self.assertRaisesRegex(ManagerError, 'bibliographic parent'):
            self.c.link_file('ABCDEFGH', pdf, apply=True)
        self.assertEqual(self.c.writes, [])

    def test_missing_pdf_does_not_create_attachment(self):
        with self.assertRaises(FileNotFoundError):
            self.c.link_file('ABCDEFGH', Path(self.tmp.name) / 'missing.pdf', apply=True)
        self.assertEqual(self.c.writes, [])

    def test_create_link_verifies_resolved_url_when_zotero_uses_relative_path(self):
        pdf = Path(self.tmp.name) / 'paper.pdf'; pdf.touch()
        state = {}
        def save(method, path, payload, headers):
            state.update(payload[0])
            return {'successful': {'0': {'key': state['key']}}, 'failed': {}}
        def read(path):
            if path.endswith('/file/view/url'):
                return pdf.as_uri()
            return {'key': state['key'], 'data': {**state, 'path': 'attachments:paper.pdf'}}
        self.c.write = save
        self.c.get = read
        result = self.c.create('items', {'itemType': 'attachment', 'linkMode': 'linked_file',
                                       'path': str(pdf)}, True)
        self.assertTrue(result['verified'])
        self.assertEqual(result['data']['path'], 'attachments:paper.pdf')

    def test_wrong_resolved_file_is_not_reported_verified(self):
        pdf = Path(self.tmp.name) / 'paper.pdf'; pdf.touch()
        state = {}
        def save(method, path, payload, headers):
            state.update(payload[0])
            return {'successful': {'0': {'key': state['key']}}, 'failed': {}}
        self.c.write = save
        self.c.get = lambda path: ((Path(self.tmp.name) / 'wrong.pdf').as_uri()
            if path.endswith('/file/view/url') else {'key': state['key'], 'data': state})
        with self.assertRaisesRegex(ManagerError, 'file URL differs'):
            self.c.create('items', {'itemType': 'attachment', 'linkMode': 'linked_file',
                                    'path': str(pdf)}, True)


if __name__ == '__main__':
    unittest.main()
