#!/usr/bin/env python3
"""Small Zotero 10 local-API manager. No third-party dependencies."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = 'http://127.0.0.1:23119/api'
PREFIX = '/users/0'
DEFAULT_STATE = Path.home() / '.local/state/zotero-manager'


class ManagerError(Exception):
    pass


def key(value):
    if not re.fullmatch(r'[A-Z0-9]{8}', value):
        raise ManagerError('Expected an eight-character Zotero item/collection key')
    return value


def tag_name(value):
    value = value.strip()
    if not value:
        raise ManagerError('Tag names cannot be blank')
    return value


def pdf_path(value):
    file = Path(value).expanduser().resolve(strict=True)
    if not file.is_file() or file.suffix.lower() != '.pdf':
        raise ManagerError('Choose an existing PDF file')
    return file


def private_json(path, data):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation avoids overwriting an existing backup or following a symlink.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    return str(path)


class Client:
    def __init__(self, state_dir=DEFAULT_STATE):
        self.state = Path(state_dir).expanduser()
        self.auth_path = self.state / 'auth.json'
        self.server = None
        self.token = None
        self.remember = False

    def request(self, method, path, data=None, headers=None, timeout=15):
        hdr = {'Zotero-API-Version': '3', **(headers or {})}
        if self.server:
            hdr['Zotero-Server-ID'] = self.server
        body = None if data is None else json.dumps(data).encode()
        if body is not None:
            hdr['Content-Type'] = 'application/json'
        try:
            req = urllib.request.Request(BASE + path, data=body, headers=hdr, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode()
                result = json.loads(raw) if raw and 'json' in response.headers.get('Content-Type', '') else raw
                return result, response.headers
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors='replace')[:800]
            hints = {401: 'Run authorize again; key expired or was single-use.',
                     412: 'Server or object changed. Re-read and preview again; no automatic retry.',
                     403: 'Access denied. Check Zotero settings or authorization.',
                     429: 'Authorization rate limited; wait before trying again.'}
            raise ManagerError(f'HTTP {e.code}: {detail}. {hints.get(e.code, "")}') from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ManagerError(f'Local Zotero request failed: {e}. If this was a write, inspect its result before retrying.') from None

    def connect(self):
        _, headers = self.request('GET', '/')
        self.server = headers.get('Zotero-Server-ID')
        if not self.server:
            raise ManagerError('Zotero 10+ with Zotero-Server-ID is required')

    def get(self, path):
        return self.request('GET', PREFIX + path)[0]

    def authorize(self):
        result, _ = self.request('POST', '/local/authorize', {'appName': 'Zotero Manager'}, timeout=180)
        if not isinstance(result, dict) or not result.get('key'):
            raise ManagerError('Zotero did not grant an authorization key')
        # Save only our key, never read Zotero profile credentials.
        self.auth_path.unlink(missing_ok=True)
        private_json(self.auth_path, {**result, 'serverID': self.server})
        return {'authorized': True, 'remember': result.get('remember', False), 'credential_file': str(self.auth_path)}

    def load_auth(self):
        if self.token:
            return
        if not self.auth_path.exists():
            raise ManagerError('No local authorization. Run authorize when the user authorizes writes.')
        if self.auth_path.stat().st_mode & 0o077:
            raise ManagerError('Credential file must have permissions 0600')
        data = json.loads(self.auth_path.read_text())
        if data.get('serverID') != self.server:
            raise ManagerError('Credential belongs to another Zotero database; authorize again')
        self.token = data['key']
        self.remember = bool(data.get('remember'))

    def write(self, method, path, payload, headers):
        self.load_auth()
        try:
            return self.request(method, PREFIX + path, payload,
                                {**headers, 'Zotero-API-Key': self.token})[0]
        finally:
            if not self.remember:
                self.auth_path.unlink(missing_ok=True)
                self.token = None

    def journal(self, data):
        return private_json(self.state / 'backups' / (uuid.uuid4().hex + '.json'),
                            {'serverID': self.server, **data})

    def change(self, kind, object_key, changes, apply=False, current=None):
        path = f'/{kind}/{key(object_key)}'
        current = current or self.get(path)
        before = current['data']
        changes = {k: v for k, v in changes.items() if before.get(k) != v}
        if not changes:
            return {'changed': False, 'key': object_key}
        forbidden = {'key', 'version', 'dateAdded', 'dateModified'} & changes.keys()
        if forbidden:
            raise ManagerError(f'Cannot edit managed fields: {sorted(forbidden)}')
        plan = {'operation': 'update', 'kind': kind, 'key': object_key,
                'before': before, 'changes': changes}
        if not apply:
            return {'dry_run': True, **plan}
        self.load_auth()
        backup = self.journal(plan)
        # Collections have a documented PUT route. Preserve the full downloaded data.
        method = 'PUT' if kind == 'collections' else 'PATCH'
        payload = {**before, **changes} if method == 'PUT' else changes
        self.write(method, path, payload, {'If-Unmodified-Since-Version': str(current['version'])})
        actual = self.get(path)
        expected = dict(changes)
        result = {'verified': True, 'key': object_key, 'data': actual['data'], 'backup': backup}
        if before.get('linkMode') == 'linked_file' and 'path' in expected:
            result['file_url'] = self.verify_file_path(object_key, expected.pop('path'), backup)
        self.verify(actual['data'], expected, backup)
        return result

    def verify_file_path(self, attachment_key, file, journal):
        url = self.get(f'/items/{attachment_key}/file/view/url')
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'file' or Path(urllib.parse.unquote(parsed.path)).resolve() != Path(file).resolve():
            raise ManagerError(f'Attachment file URL differs; inspect before retrying. Journal: {journal}')
        return url

    @staticmethod
    def verify(actual, expected, journal):
        mismatch = {}
        for k, v in expected.items():
            if k == 'collections':
                equal = set(actual.get(k, [])) == set(v)
            elif k == 'tags':
                # Zotero can sort tags and omit the default manual-tag type (0).
                canonical = lambda tags: {(t['tag'], t.get('type', 0)) for t in tags}
                equal = canonical(actual.get(k, [])) == canonical(v)
            else:
                equal = actual.get(k) == v
            if not equal:
                mismatch[k] = {'expected': v, 'actual': actual.get(k)}
        if mismatch:
            raise ManagerError(f'Write completed but verification differed: {json.dumps(mismatch)}. Journal: {journal}. Inspect before retrying.')

    def create(self, kind, data, apply=False):
        if {'key', 'version'} & data.keys():
            raise ManagerError('New records must not contain key or version')
        if not apply:
            return {'dry_run': True, 'operation': 'create', 'kind': kind, 'data': data}
        self.load_auth()
        # Persist the intended key and write token BEFORE sending, for recovery after timeout.
        alphabet = '23456789ABCDEFGHIJKLMNPQRSTUVWXYZ'
        import secrets
        object_key = ''.join(secrets.choice(alphabet) for _ in range(8))
        token = uuid.uuid4().hex
        # A client-assigned key requires a version precondition, even for creates.
        payload = {**data, 'key': object_key, 'version': 0}
        journal = self.journal({'operation': 'create', 'kind': kind, 'key': object_key,
                                'writeToken': token, 'data': payload})
        result = self.write('POST', f'/{kind}', [payload], {'Zotero-Write-Token': token})
        if not isinstance(result, dict) or result.get('failed'):
            raise ManagerError(f'Create failed: {json.dumps(result)}. Journal: {journal}')
        successful = result.get('successful', {}).get('0')
        returned_key = successful.get('key') if isinstance(successful, dict) else None
        returned_key = returned_key or result.get('success', {}).get('0') or result.get('unchanged', {}).get('0')
        if returned_key != object_key:
            raise ManagerError(f'Unexpected create response; inspect before retrying. Journal: {journal}')
        actual = self.get(f'/{kind}/{object_key}')
        expected = dict(data)
        if data.get('linkMode') == 'linked_file' and 'path' in data:
            # Zotero may store an absolute path relative to its attachment base directory.
            expected.pop('path')
            self.verify_file_path(object_key, data['path'], journal)
        self.verify(actual['data'], expected, journal)
        return {'verified': True, 'key': object_key, 'data': actual['data'], 'journal': journal}

    def membership(self, item_key, add, remove, apply=False):
        if set(add) & set(remove):
            raise ManagerError('A collection cannot be both added and removed')
        current = self.get(f'/items/{key(item_key)}')
        if current['data'].get('parentItem'):
            raise ManagerError('Change collection membership on the parent reference')
        for collection in set(add + remove):
            self.get(f'/collections/{key(collection)}')
        memberships = [c for c in current['data'].get('collections', []) if c not in remove]
        memberships.extend(c for c in add if c not in memberships)
        return self.change('items', item_key, {'collections': memberships}, apply, current)

    def link_file(self, parent, file, title=None, apply=False):
        file = pdf_path(file)
        item = self.get(f'/items/{key(parent)}')['data']
        if item.get('itemType') in ('attachment', 'note', 'annotation'):
            raise ManagerError('Choose a bibliographic parent reference')
        for child in self.get(f'/items/{parent}/children'):
            data = child['data']
            if data.get('linkMode') != 'linked_file':
                continue
            url = self.get(f'/items/{child["key"]}/file/view/url')
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme == 'file' and Path(urllib.parse.unquote(parsed.path)).resolve() == file:
                return {'changed': False, 'existing_attachment': child['key'], 'path': str(file)}
        result = self.create('items', {'itemType': 'attachment', 'parentItem': parent,
            'linkMode': 'linked_file', 'title': title or file.name, 'contentType': 'application/pdf',
            'path': str(file), 'tags': [], 'collections': [], 'relations': {}}, apply)
        if apply:
            url = self.get(f'/items/{result["key"]}/file/view/url')
            if Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).resolve() != file:
                raise ManagerError(f'Attachment created but file URL differs: {url}; inspect before retrying')
            result['file_url'] = url
        return result

    def update_tags(self, item_key, add, remove, apply=False):
        add = [tag_name(t) for t in add]
        remove = [tag_name(t) for t in remove]
        if not add and not remove:
            raise ManagerError('Provide at least one tag to add or remove')
        if set(add) & set(remove):
            raise ManagerError('A tag cannot be both added and removed')
        current = self.get(f'/items/{key(item_key)}')
        tags = [dict(t) for t in current['data'].get('tags', []) if t['tag'] not in remove]
        present = {t['tag'] for t in tags}
        for name in add:
            if name not in present:
                tags.append({'tag': name})
                present.add(name)
        return self.change('items', item_key, {'tags': tags}, apply, current)

    def relink_file(self, attachment_key, file, apply=False):
        file = pdf_path(file)
        current = self.get(f'/items/{key(attachment_key)}')
        data = current['data']
        if data.get('itemType') != 'attachment' or data.get('linkMode') != 'linked_file':
            raise ManagerError('Choose an existing linked-file attachment key, not a parent or stored copy')
        if data.get('contentType') != 'application/pdf' and not data.get('path', '').lower().endswith('.pdf'):
            raise ManagerError('Choose an existing linked PDF attachment')
        result = self.change('items', attachment_key, {'path': str(file)}, apply, current)
        if apply and 'file_url' not in result:
            result['file_url'] = self.verify_file_path(attachment_key, file, 'no change')
        return result


def json_object(value):
    result = json.loads(value)
    if not isinstance(result, dict) or not result:
        raise argparse.ArgumentTypeError('Expected a nonempty JSON object')
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir', type=Path, default=DEFAULT_STATE,
                   help='Private credentials and pre-write recovery journals')
    subs = p.add_subparsers(dest='command', required=True)
    subs.add_parser('authorize', help='Request Zotero’s own write-authorization dialog')
    get = subs.add_parser('get', help='Read complete item or collection JSON')
    get.add_argument('kind', choices=['items', 'collections']); get.add_argument('key', type=key)
    template = subs.add_parser('template', help='Read a new-item template')
    template.add_argument('item_type')
    for command in ('create-item', 'edit-item', 'create-collection', 'edit-collection', 'membership', 'link-file', 'edit-tags', 'relink-file'):
        s = subs.add_parser(command)
        s.add_argument('--apply', action='store_true', help='Execute the write; otherwise preview only')
        if command in ('edit-item', 'edit-collection', 'membership', 'link-file', 'edit-tags', 'relink-file'):
            s.add_argument('key', type=key)
        if command in ('create-item', 'edit-item'):
            s.add_argument('--json', required=True, type=json_object, dest='data')
        if command in ('create-collection', 'edit-collection'):
            s.add_argument('--name', required=command == 'create-collection')
            s.add_argument('--parent', help='Parent collection key, or none to use library root')
        if command == 'membership':
            s.add_argument('--add', action='append', default=[], type=key)
            s.add_argument('--remove', action='append', default=[], type=key)
        if command == 'edit-tags':
            s.add_argument('--add', action='append', default=[], type=tag_name)
            s.add_argument('--remove', action='append', default=[], type=tag_name)
        if command == 'link-file':
            s.add_argument('file', type=Path); s.add_argument('--title')
        if command == 'relink-file':
            s.add_argument('file', type=Path)
    return p


def run(args, client):
    c = client
    cmd = args.command
    if cmd == 'authorize': return c.authorize()
    if cmd == 'get': return c.get(f'/{args.kind}/{args.key}')
    if cmd == 'template':
        query = urllib.parse.urlencode({'itemType': args.item_type})
        fields, _ = c.request('GET', '/itemTypeFields?' + query)
        creators, _ = c.request('GET', '/itemTypeCreatorTypes?' + query)
        data = {field['field']: '' for field in fields}
        data.update({'itemType': args.item_type, 'creators': [], 'tags': [],
                     'collections': [], 'relations': {}})
        return {'template': data, 'allowedCreatorTypes': [t['creatorType'] for t in creators]}
    if cmd == 'create-item':
        if not args.data.get('itemType'): raise ManagerError('itemType is required')
        data = {'tags': [], 'collections': [], 'relations': {}, **args.data}
        return c.create('items', data, args.apply)
    if cmd == 'edit-item': return c.change('items', args.key, args.data, args.apply)
    if cmd in ('create-collection', 'edit-collection'):
        data = {}
        if args.name is not None:
            if not args.name.strip(): raise ManagerError('Collection name cannot be blank')
            data['name'] = args.name
        if args.parent is not None:
            data['parentCollection'] = False if args.parent == 'none' else key(args.parent)
            if args.parent != 'none': c.get(f'/collections/{args.parent}')
        if cmd == 'create-collection':
            data.setdefault('parentCollection', False)
            return c.create('collections', data, args.apply)
        if not data: raise ManagerError('Provide --name or --parent')
        return c.change('collections', args.key, data, args.apply)
    if cmd == 'membership':
        if not args.add and not args.remove: raise ManagerError('Provide --add or --remove')
        return c.membership(args.key, args.add, args.remove, args.apply)
    if cmd == 'link-file': return c.link_file(args.key, args.file, args.title, args.apply)
    if cmd == 'edit-tags': return c.update_tags(args.key, args.add, args.remove, args.apply)
    if cmd == 'relink-file': return c.relink_file(args.key, args.file, args.apply)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    # Existing search/export/citation/import commands remain available without rewriting them.
    legacy_commands = {'status', 'enable', 'disable', 'restart', 'probe', 'inventory', 'collections',
        'tags', 'groups', 'search', 'export-bibtex', 'sync-bib', 'citations', 'children', 'fulltext',
        'file-url', 'cite', 'selected-target', 'import-bibtex', 'import-ris'}
    if argv and argv[0] in legacy_commands:
        import zotero_legacy
        return zotero_legacy.main(argv)
    try:
        args = parser().parse_args(argv)
        client = Client(args.state_dir)
        client.connect()
        print(json.dumps(run(args, client), indent=2))
        return 0
    except (ManagerError, OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
