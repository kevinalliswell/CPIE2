"""The real entry point must tolerate Chinese dependency output on Windows."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('mode', ['legacy_encoding', 'no_console', 'captured'])
def test_entry_point_prepares_streams_before_loading_application(mode, tmp_path):
    project = Path(__file__).resolve().parents[1]
    script = '''
import io, sys, types
from pathlib import Path
from src.app import main
mode = sys.argv[1]
buffers = [io.BytesIO(), io.BytesIO()]
if mode == 'legacy_encoding':
    streams = [io.TextIOWrapper(buffer, encoding='cp1252', errors='strict')
               for buffer in buffers]
elif mode == 'no_console':
    streams = [None, None]
else:
    streams = [io.StringIO(), io.StringIO()]
sys.stdout, sys.stderr = streams
message = '配置已加载：中文路径 ✓'
def startup(output):
    # This is where application/dependency imports start in smoke mode.
    assert sys.stdout is not None and sys.stderr is not None
    from flamekit.config import ConfigManager
    config = Path('中文配置.json')
    config.write_text('{"camera_id": 7}', encoding='utf-8')
    assert ConfigManager(str(config)).config['camera_id'] == 7
    for stream in (sys.stdout, sys.stderr):
        print(message, file=stream, flush=True)
    return 0
module = types.ModuleType('scripts.smoke_check')
module.application_smoke = startup
sys.modules['scripts.smoke_check'] = module
sys.argv = ['app.py', '--smoke-test', '--smoke-output', 'unused.json']
assert main() == 0
if mode == 'legacy_encoding':
    assert all(message in buffer.getvalue().decode('utf-8') for buffer in buffers)
    assert '配置已加载: 中文配置.json' in buffers[0].getvalue().decode('utf-8')
elif mode == 'captured':
    assert sys.stdout is streams[0] and sys.stderr is streams[1]
    assert all(message in stream.getvalue() for stream in streams)
else:
    assert sys.stdout.encoding == sys.stderr.encoding == 'utf-8'
'''
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project)
    result = subprocess.run(
        [sys.executable, '-c', script, mode], cwd=tmp_path, env=env,
        capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
