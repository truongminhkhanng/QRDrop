"""Check embedded mobile JavaScript without platform-dependent shell quoting."""
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import MOBILE_HTML

script = MOBILE_HTML.split('<script nonce=')[1].split('>', 1)[1].split('</script>')[0]
script = script.replace('__SESSION_JSON__', '"syntax-check"')
with tempfile.TemporaryDirectory(prefix='phonedrop-js-') as directory:
    path = Path(directory) / 'mobile.js'
    path.write_text(script, encoding='utf-8')
    subprocess.run(['node', '--check', str(path)], check=True)
print('Embedded mobile JavaScript syntax: OK')
