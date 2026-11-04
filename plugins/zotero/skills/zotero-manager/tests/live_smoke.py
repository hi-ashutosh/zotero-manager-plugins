#!/usr/bin/env python3
"""Opt-in local Zotero smoke test. Creates and removes only uniquely marked fixtures."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import urllib.parse
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from zotero_manager import Client, DEFAULT_STATE, ManagerError


def make_pdf(path):
    """Write a tiny valid PDF fixture without extra packages or existing documents."""
    stream = b'BT /F1 16 Tf 40 100 Td (Zotero Manager temporary test) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    pdf = bytearray(b'%PDF-1.4\n'); offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf)); pdf.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(pdf)
    pdf.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]: pdf.extend(f'{offset:010} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    path.write_bytes(pdf)


class FixtureClient(Client):
    def __init__(self, state, marker, report_file):
        super().__init__(state)
        self.marker = marker
        self.report_file = report_file
        self.fixtures = []
        self.authorization_failed = False

    def persist(self):
        self.report_file.write_text(json.dumps({'marker': self.marker, 'fixtures': self.fixtures}, indent=2))

    def load_auth(self):
        if self.authorization_failed:
            raise ManagerError('Authorization failed; no further dialogs will be requested in this run')
        if not self.token and not self.auth_path.exists():
            print('Zotero needs authorization for the next test write. Please use its dialog.', flush=True)
            try:
                self.authorize()
            except ManagerError:
                self.authorization_failed = True
                raise
        return super().load_auth()

    def write(self, method, path, payload, headers):
        if method == 'POST' and path in ('/items', '/collections'):
            for data in payload:
                label = data.get('title', data.get('name', ''))
                if not label.startswith(self.marker):
                    raise ManagerError('Test attempted to create an unmarked object')
                self.fixtures.append({'kind': path[1:], 'key': data['key']})
            # Persist intended keys before requests, including verification-failure cases.
            self.persist()
        return super().write(method, path, payload, headers)

    def cleanup(self):
        errors = []
        # Children are created after parents, so reverse order removes them first.
        for fixture in reversed(self.fixtures):
            path = f'/{fixture["kind"]}/{fixture["key"]}'
            try:
                try:
                    current = self.get(path)
                except ManagerError as e:
                    if str(e).startswith('HTTP 404:'): continue
                    raise
                data = current['data']
                label = data.get('title', data.get('name', ''))
                if not label.startswith(self.marker):
                    raise ManagerError('Refusing to remove an object without this run’s marker')
                self.write('DELETE', path, None, {'If-Unmodified-Since-Version': str(current['version'])})
                try:
                    self.get(path)
                except ManagerError as e:
                    if str(e).startswith('HTTP 404:'): continue
                    raise
                raise ManagerError('Deleted fixture is still readable')
            except Exception as e:
                errors.append({**fixture, 'error': str(e)})
        return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true', help='Required to run actual temporary-record writes')
    p.add_argument('--state-dir', type=Path, default=DEFAULT_STATE)
    args = p.parse_args()
    if not args.apply:
        print('No writes. Use --apply only when temporary-record testing is authorized.')
        return 0
    directory = Path(tempfile.mkdtemp(prefix='zotero-manager-live-'))
    marker = '__ZOTERO_MANAGER_TEST_' + uuid.uuid4().hex[:10] + '__'
    report_file = directory / 'fixtures.json'
    c = FixtureClient(args.state_dir, marker, report_file)
    passed = []
    errors = []
    pdf = directory / 'Linked test paper.pdf'
    def check(name, condition):
        if not condition: raise AssertionError(name)
        passed.append(name); print('PASS:', name, flush=True)
    try:
        c.connect(); c.load_auth()
        root = c.create('collections', {'name': marker + ' Root', 'parentCollection': False}, True)['key']
        source = c.create('collections', {'name': marker + ' Source', 'parentCollection': root}, True)['key']
        target = c.create('collections', {'name': marker + ' Target', 'parentCollection': root}, True)['key']
        check('create root and nested collections', c.get(f'/collections/{source}')['data']['parentCollection'] == root)
        renamed = c.change('collections', target, {'name': marker + ' Renamed target'}, True)
        check('rename preserves collection parent', renamed['data']['parentCollection'] == root)
        data = {'itemType': 'journalArticle', 'title': marker + ' Paper', 'date': '2010',
                'creators': [{'creatorType': 'author', 'firstName': 'Test', 'lastName': 'Researcher'}],
                'tags': [], 'collections': [root, source], 'relations': {}}
        item = c.create('items', data, True)['key']
        check('create structured reference', c.get(f'/items/{item}')['data']['title'] == data['title'])
        preview = c.change('items', item, {'title': marker + ' Preview only'})
        check('preview leaves record unchanged', preview['dry_run'] and c.get(f'/items/{item}')['data']['title'] == data['title'])
        edit = c.change('items', item, {'title': marker + ' Corrected paper', 'date': '2011',
             'DOI': '10.0000/zotero-manager-test', 'creators': [{'creatorType': 'author', 'firstName': 'Updated', 'lastName': 'Researcher'}]}, True)
        check('edit title, date, DOI and author', edit['verified'])
        check('edit preserves collection membership', set(edit['data']['collections']) == {root, source})
        moved = c.membership(item, [target], [source], True)
        check('move preserves unrelated membership', set(moved['data']['collections']) == {root, target})
        removed = c.membership(item, [], [target], True)
        check('remove membership keeps library item', removed['data']['collections'] == [root])
        added = c.membership(item, [target], [], True)
        check('add membership', set(added['data']['collections']) == {root, target})
        make_pdf(pdf); original = pdf.read_bytes()
        attached = c.link_file(item, pdf, title=marker + ' Linked PDF', apply=True)
        linked_path = Path(urllib.parse.unquote(urllib.parse.urlparse(attached['file_url']).path))
        check('create linked PDF and resolve original path', attached.get('verified') and linked_path.resolve() == pdf.resolve())
        duplicate = c.link_file(item, pdf, apply=True)
        check('duplicate linked PDF is not recreated', duplicate.get('existing_attachment') == attached['key'] and not duplicate['changed'])
        check('PDF contents remain unchanged', pdf.read_bytes() == original)
    except Exception as e:
        errors.append(str(e)); print('TEST ERROR:', e, flush=True)
    finally:
        cleanup_errors = c.cleanup()
        # Keep the test PDF available if an attachment could not be removed.
        if not cleanup_errors: pdf.unlink(missing_ok=True)
        report = {'marker': marker, 'passed': passed, 'errors': errors,
                  'cleanup_errors': cleanup_errors, 'fixtures': c.fixtures,
                  'pdf_removed': not pdf.exists(), 'report_path': str(directory / 'result.json')}
        (directory / 'result.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)
    return 1 if errors or cleanup_errors else 0


if __name__ == '__main__':
    sys.exit(main())
