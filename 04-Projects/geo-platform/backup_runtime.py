"""Local operator backup with an isolated restore drill; never restores over live data."""
import hashlib
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def backup(runtime, destination=None):
    runtime = Path(runtime).resolve()
    source_db = runtime / 'geo.db'
    if not source_db.is_file(): raise RuntimeError('没有找到运行数据库')
    destination = Path(destination).resolve() if destination else runtime / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if destination.exists(): raise RuntimeError('备份目标已存在，拒绝覆盖')
    destination.mkdir(parents=True)
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'files': {}, 'counts': {}, 'restore_drill': False}
    # Freeze writers while taking both the database and its referenced files.
    with closing(sqlite3.connect(source_db, timeout=30)) as gate:
        gate.execute('BEGIN IMMEDIATE')
        with closing(sqlite3.connect(source_db, timeout=30)) as source, closing(sqlite3.connect(destination / 'geo.db')) as target:
            source.backup(target)
            for table in ('users', 'projects', 'members', 'resources', 'events'):
                manifest['counts'][table] = source.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
        for folder in ('assets', 'agents'):
            path = runtime / folder
            if path.exists(): shutil.copytree(path, destination / folder)
        if (runtime / 'connector.key').exists(): shutil.copy2(runtime / 'connector.key', destination / 'connector.key')
    for path in destination.rglob('*'):
        if path.is_file(): manifest['files'][path.relative_to(destination).as_posix()] = file_hash(path)
    with tempfile.TemporaryDirectory(prefix='geo-restore-drill-') as tmp:
        restored = Path(tmp) / 'restored'
        shutil.copytree(destination, restored)
        for name, digest in manifest['files'].items():
            if file_hash(restored / name) != digest: raise RuntimeError('备份文件校验失败')
        with closing(sqlite3.connect(restored / 'geo.db')) as c:
            if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise RuntimeError('数据库完整性校验失败')
            for table, count in manifest['counts'].items():
                if c.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] != count: raise RuntimeError('恢复记录数不一致')
            for row in c.execute('SELECT project_id,data FROM resources WHERE kind IN ("asset","quarantine_asset")'):
                data = json.loads(row[1])
                path = restored / 'assets' / row[0] / data['storage_key']
                if not path.is_file() or path.stat().st_size != data['size']: raise RuntimeError('引用素材文件缺失或不完整')
            encrypted = [json.loads(row[0]).get('encrypted_secret') for row in c.execute('SELECT data FROM resources WHERE kind="connector"')]
            if any(encrypted):
                from cryptography.fernet import Fernet
                key = Fernet((restored / 'connector.key').read_bytes())
                for token in encrypted:
                    if token: key.decrypt(token.encode())
    manifest['restore_drill'] = True
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'backup': str(destination), 'file_count': len(manifest['files']), 'integrity': 'ok', 'restore_drill': 'passed'}


if __name__ == '__main__':
    print(json.dumps(backup(Path(__file__).parent / '.runtime'), ensure_ascii=False))
