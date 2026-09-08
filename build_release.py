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
    with zipfile.ZipFile(output / 'LaboratorioRobot-Windows.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(executable, 'LaboratorioRobot.exe')
        for name in docs:
            z.write(ROOT / name, name)
    sources = list(ROOT.glob('*.py')) + [ROOT / name for name in docs + ['requirements.txt', 'LaboratorioRobot.spec', 'PIANO.md', 'assets/robot.ico', 'tests/test_robot_lab.py']]
    with zipfile.ZipFile(output / 'LaboratorioRobot-Sorgenti.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sources:
            z.write(file, file.relative_to(ROOT))
    for path in output.glob('LaboratorioRobot-*.zip'):
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise RuntimeError('Archivio danneggiato: ' + str(path))


if __name__ == '__main__':
    os.chdir(ROOT)
    os.environ['PYINSTALLER_CONFIG_DIR'] = str(ROOT / 'build' / 'cache')
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], check=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', '.', 'LaboratorioRobot.spec'], check=True)
    report = ROOT / 'build' / 'smoke-exe.json'
    subprocess.run([str(ROOT / 'LaboratorioRobot.exe'), '--smoke-test', str(report)], check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    import json
    if json.loads(report.read_text(encoding='utf-8')).get('ok') is not True:
        raise RuntimeError('Verifica dell’eseguibile non riuscita.')
    archives()
    print('Pronti: LaboratorioRobot.exe e i due ZIP nella cartella dist.')
