"""Path discovery must not open operator logs before smoke redirects paths."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_path_imports_do_not_initialize_logs_before_runtime_is_selected(tmp_path):
    source = Path(__file__).resolve().parents[1]
    copied = tmp_path / 'application'
    utilities = copied / 'src' / 'utils'
    utilities.mkdir(parents=True)
    (copied / 'src' / '__init__.py').write_text('')
    for name in ('__init__.py', 'path_manager.py', 'logger.py'):
        shutil.copy2(source / 'src' / 'utils' / name, utilities / name)
    runtime = tmp_path / 'smoke-runtime'
    runtime.mkdir()
    script = '''
import json, logging, sys
from pathlib import Path
from src.utils.path_manager import PathManager as QualifiedPaths
from utils.path_manager import PathManager as LegacyPaths
application, runtime = map(Path, sys.argv[1:])
assert not (application / 'logs').exists(), 'Path import opened operator logs'
for paths in (QualifiedPaths, LegacyPaths):
    paths.get_project_root = staticmethod(lambda: str(runtime))
from src.utils import get_logger
get_logger('smoke-isolation').info('synthetic smoke message')
logging.shutdown()
assert not (application / 'logs').exists()
assert 'synthetic smoke message' in (runtime / 'logs/app.log').read_text()
print(json.dumps({'isolated': True}))
'''
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join((str(copied), str(copied / 'src')))
    result = subprocess.run(
        [sys.executable, '-c', script, str(copied), str(runtime)],
        cwd=runtime, env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['isolated']
