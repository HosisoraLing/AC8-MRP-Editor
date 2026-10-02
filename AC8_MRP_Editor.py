"""Standalone offline campaign MRP editor. Uses only Python's standard library."""
from pathlib import Path
from datetime import datetime
import csv
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import tempfile
import tkinter as tk
import zlib

CRC_SEED = 0x41916EBD
DEFAULT_MRP = 2_000_000
MAX_MRP = 999_999_999
DEFAULT_ROOT = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'BANDAI NAMCO Entertainment' / 'ACE COMBAT 8' / 'Saved' / 'SaveGames'

class SaveError(Exception):
    pass

def require(condition, message):
    if not condition:
        raise SaveError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def field(data, name, kind, size):
    tag = (struct.pack('<i', len(name) + 1) + name.encode() + b'\0'
           + struct.pack('<i', len(kind) + 1) + kind.encode() + b'\0'
           + struct.pack('<II', 0, size) + b'\0')
    require(data.count(tag) == 1, '存档格式不兼容：无法唯一定位 ' + name)
    position = data.index(tag) + len(tag)
    require(position + size <= len(data), '存档字段不完整：' + name)
    return position

def parse_save(data):
    require(data.startswith(b'GVAS'), '文件不是支持的 GVAS 战役存档。')
    mrp = field(data, 'CurrentMRP', 'UInt64Property', 8)
    total = field(data, 'TotalMRP', 'UInt64Property', 8)
    checksum = field(data, 'Checksum', 'UInt32Property', 4)
    packed = data.find(b'PackedData\0')
    require(packed >= 0, '存档中没有 PackedData。')
    byte_tag = data.find(b'ByteProperty\0', packed)
    require(byte_tag >= 0, 'PackedData 类型不兼容。')
    count_at = byte_tag + 22
    require(count_at + 4 <= len(data), 'PackedData 长度字段不完整。')
    start = count_at + 4
    end = start + struct.unpack_from('<I', data, count_at)[0]
    require(end == data.find(b'Checksum\0') - 4 and end <= len(data), 'PackedData 边界不兼容。')
    require(start <= mrp and mrp + 8 <= end and start <= total and total + 8 <= end, 'MRP 字段边界不兼容。')
    require(zlib.crc32(data[start:end], CRC_SEED) == struct.unpack_from('<I', data, checksum)[0],
            '原存档校验码不匹配，已停止修改。请确认游戏已退出，且版本未改变存档格式。')
    return {'mrp': mrp, 'total': total, 'checksum': checksum, 'start': start, 'end': end,
            'value': struct.unpack_from('<Q', data, mrp)[0], 'total_value': struct.unpack_from('<Q', data, total)[0]}

def make_modified(original, amount):
    require(type(amount) is int and 0 <= amount <= MAX_MRP, 'MRP 必须是 0～999,999,999 的整数。')
    info = parse_save(original)
    modified = bytearray(original)
    struct.pack_into('<Q', modified, info['mrp'], amount)
    struct.pack_into('<I', modified, info['checksum'], zlib.crc32(modified[info['start']:info['end']], CRC_SEED))
    modified = bytes(modified)
    verified = parse_save(modified)
    require(verified['value'] == amount and verified['total_value'] == info['total_value'], '修改后的数值验证失败。')
    require(len(original) == len(modified), '修改后的文件长度改变。')
    changes = [i for i, (a, b) in enumerate(zip(original, modified)) if a != b]
    require(all(info['mrp'] <= i < info['mrp'] + 8 or info['checksum'] <= i < info['checksum'] + 4 for i in changes),
            '修改范围验证失败。')
    return modified, info, changes

def ensure_game_closed():
    try:
        result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True,
                                timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SaveError('无法检查游戏进程，已停止修改。') from exc
    require(result.returncode == 0, '无法检查游戏进程，已停止修改。')
    names = {row[0].lower() for row in csv.reader(io.StringIO(result.stdout.decode('utf-8', errors='replace'))) if row}
    require(not names.intersection({'acecombat8.exe', 'start_protected_game.exe'}),
            '请先正常退出《王牌空战8》，等待 Steam 同步完成，再点击修改。')

def list_files(root):
    files = {}
    for path in root.rglob('*'):
        require(not path.is_symlink(), '存档目录含符号链接，请选择普通的 SaveGames 目录。')
        if path.is_file():
            files[str(path.relative_to(root))] = path
    return files

def set_mrp(root, amount, progress=lambda text: None, guard=ensure_game_closed, backup_parent=None):
    root = Path(root).resolve()
    campaign = root / 'Campaign.sav'
    require(campaign.is_file(), '所选目录中找不到 Campaign.sav。')
    guard()
    original = campaign.read_bytes()
    modified, info, changes = make_modified(original, amount)
    progress('正在备份全部存档并核对 SHA-256…')
    backup_parent = Path(backup_parent) if backup_parent is not None else root.parent / 'MRP_Backups'
    backup_parent.mkdir(parents=True, exist_ok=True)
    backup = backup_parent / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir()
    try:
        source_files = list_files(root)
        shutil.copytree(root, backup / 'SaveGames')
        require(set(source_files) == set(list_files(root)), '备份期间存档文件发生变化，请重试。')
        manifest = []
        for name, path in source_files.items():
            live = path.read_bytes()
            require(live == (backup / 'SaveGames' / name).read_bytes(), '备份期间存档发生变化：' + name)
            manifest.append({'file': name, 'bytes': len(live), 'sha256': digest(live)})
        require((backup / 'SaveGames' / 'Campaign.sav').read_bytes() == original, '备份期间战役存档发生变化，请重试。')
        (backup / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        report = {'status': 'backed_up', 'save_file': str(campaign), 'backup_directory': str(backup),
                  'previous_MRP': info['value'], 'current_MRP': amount, 'unchanged_total_MRP': info['total_value'],
                  'changed_byte_count': len(changes), 'MRP_offset': hex(info['mrp']), 'checksum_offset': hex(info['checksum']),
                  'original_sha256': digest(original), 'modified_sha256': digest(modified)}
        report_file = backup / 'MRP-change-report.json'
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        progress('备份已核对，正在写入 MRP 和校验码…')
        guard()
        for record in manifest:
            require(digest((root / record['file']).read_bytes()) == record['sha256'], '写入前存档发生变化：' + record['file'])
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(prefix='Campaign-', suffix='.tmp', dir=root, delete=False) as temp:
                temp_name = Path(temp.name)
                temp.write(modified)
                temp.flush()
                os.fsync(temp.fileno())
            guard()
            require(campaign.read_bytes() == original, '写入前战役存档发生变化，请重试。')
            os.replace(temp_name, campaign)
            temp_name = None
        finally:
            if temp_name is not None:
                temp_name.unlink(missing_ok=True)
        progress('正在回读存档并验证校验码…')
        written = campaign.read_bytes()
        require(written == modified and parse_save(written)['value'] == amount, '写入后的存档验证失败。')
        for record in manifest:
            if record['file'] != 'Campaign.sav':
                require(digest((root / record['file']).read_bytes()) == record['sha256'], '其他存档在操作期间发生变化：' + record['file'])
        report['status'] = 'applied_and_verified'
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return report
    except Exception as exc:
        raise SaveError(str(exc) + '\n\n本次备份目录：\n' + str(backup)) from exc

from frontend import ModernApp

def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    window = tk.Tk()
    ModernApp(window, DEFAULT_ROOT, parse_save, set_mrp, SaveError)
    window.mainloop()

if __name__ == '__main__':
    main()
