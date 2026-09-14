"""Run python build_release.py from the source distribution on Windows."""
from pathlib import Path
import os
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent


def archives(executable=None):
    executable = Path(executable) if executable else ROOT / 'LaboratorioRobot.exe'
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    docs = ['README.txt', 'README.md', 'LICENZE.txt', 'Avvia_Robot.cmd']
    previews = ['screenshots/07-completa-il-numero.png', 'screenshots/11-risultato-da-correggere.png']
    with zipfile.ZipFile(output / 'LaboratorioRobot-Windows.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(executable, 'LaboratorioRobot.exe')
        for name in docs + previews:
            z.write(ROOT / name, name)
    sources = list(ROOT.glob('*.py')) + [ROOT / name for name in docs + ['requirements.txt', 'LaboratorioRobot.spec', 'PIANO.md', '.gitignore', '.gitattributes']]
    sources += list((ROOT / 'assets').glob('*')) + list((ROOT / 'tests').glob('*.py')) + list((ROOT / 'docs').rglob('*.md')) + list((ROOT / 'screenshots').glob('*.png'))
    with zipfile.ZipFile(output / 'LaboratorioRobot-Sorgenti.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sources:
            z.write(file, file.relative_to(ROOT))
    for path in output.glob('LaboratorioRobot-*.zip'):
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise RuntimeError('Archivio danneggiato: ' + str(path))
            assert 'progressi_cicli.json' not in z.namelist()
            for member in z.namelist():
                expected = executable if member == 'LaboratorioRobot.exe' else ROOT / member
                assert z.read(member) == expected.read_bytes(), member
        print('Verificato:', path.name)


if __name__ == '__main__':
    os.chdir(ROOT)
    os.environ['PYINSTALLER_CONFIG_DIR'] = str(ROOT / 'build' / 'cache')
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], check=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', '.', 'LaboratorioRobot.spec'], check=True)
    report = ROOT / 'build' / 'smoke-exe.json'
    report.unlink(missing_ok=True)
    subprocess.run([str(ROOT / 'LaboratorioRobot.exe'), '--smoke-test', str(report)], check=True, timeout=120, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    import json
    if json.loads(report.read_text(encoding='utf-8')).get('ok') is not True:
        raise RuntimeError('Verifica dell’eseguibile non riuscita.')
    archives()
    print('Pronti: LaboratorioRobot.exe e i due ZIP nella cartella dist.')
