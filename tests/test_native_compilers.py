"""Independent native output oracle for trusted authored solutions only."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from engine import Interpreter
from missions import MISSIONS
from native_context import standalone


CASES = {
    'for_pontile': ([], ['avanza'] * 5),
    'for_batterie': ([], ['avanza', 'raccogli'] * 4),
    'for_luci': ([], ['accendi', 'avanza'] * 4),
    'while_corridoio': ([1, 1, 1, 1, 0], ['avanza'] * 4),
    'while_traccia': ([1, 1, 1, 1, 0], ['raccogli', 'avanza'] * 4),
    'while_zero': ([1], []),
    'do_segnale': ([0, 0, 1], ['scansiona'] * 3),
    'do_partenza': ([0, 0, 0, 1], ['avanza'] * 4),
    'do_uno': ([1], ['scansiona']),
}


class NativeCompilerTests(unittest.TestCase):
    def test_all_solutions_and_false_block_match_native_io(self):
        for language in ('Python', 'JavaScript', 'C', 'Java'):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                snippets, inputs, expected = [], [], []
                for mission in MISSIONS:
                    source = mission.solution(language)
                    values, messages = CASES[mission.key]
                    runner = Interpreter(mission, language)
                    result = runner.run(source)
                    self.assertTrue(result.success, result.message)
                    self.assertEqual(runner.output, messages)
                    self.assertEqual([v for _, _, v in runner.reads], values)
                    self.assertNotRegex(source, r'\b(?:avanza|scansiona|raccogli|accendi|strada_libera|sul_traguardo|sulla_batteria|segnale_trovato)\(\)')
                    snippets.append(source if language == 'Python' else '{\n' + source + '\n}')
                    inputs.extend(map(str, values))
                    expected.extend(messages)
                # Use a variable: Java rejects a compile-time while(false) body.
                declaration = {'Python': 'controllo = 0\n', 'JavaScript': 'let controllo = 0;\n',
                               'C': 'int controllo = 0;\n', 'Java': 'int controllo = 0;\n'}[language]
                source = declaration + MISSIONS[3].program(language, 3, 'controllo != 0', ('avanza',))
                runner = Interpreter(MISSIONS[3], language)
                self.assertEqual(runner.run(source).error_line, 0)
                self.assertEqual(runner.output, [])
                self.assertEqual(runner.reads, [])
                snippets.append(source if language == 'Python' else '{\n' + source + '\n}')
                body = '\n'.join(snippets)
                root = Path(directory)
                program = standalone(body, language)
                if language == 'C':
                    compiler = shutil.which('gcc')
                    if not compiler:
                        self.skipTest('GCC unavailable')
                    path = root/'main.c'
                    path.write_text(program, encoding='utf-8')
                    result = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(root/'main.exe')], capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    command = [str(root/'main.exe')]
                elif language == 'Java':
                    compiler, runtime = shutil.which('javac'), shutil.which('java')
                    if not compiler or not runtime:
                        self.skipTest('Java unavailable')
                    path = root/'Main.java'
                    path.write_text(program, encoding='utf-8')
                    result = subprocess.run([compiler, '-encoding', 'UTF-8', str(path)], capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    command = [runtime, '-cp', str(root), 'Main']
                elif language == 'JavaScript':
                    runtime = shutil.which('node')
                    if not runtime:
                        self.skipTest('Node unavailable')
                    path = root/'main.js'
                    path.write_text('const inputs = ' + json.dumps(inputs) + ';\nconst prompt = () => inputs.shift();\n' + program, encoding='utf-8')
                    command = [runtime, str(path)]
                else:
                    path = root/'main.py'
                    path.write_text(program, encoding='utf-8')
                    command = [sys.executable, str(path)]
                result = subprocess.run(command, input='\n'.join(inputs)+'\n', capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), expected)


if __name__ == '__main__':
    unittest.main()
