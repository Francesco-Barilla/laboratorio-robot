import unittest
from engine import Interpreter, LANGUAGES, parse, CodeError
from missions import BY_KEY, MISSIONS


class NativeIOTests(unittest.TestCase):
    def test_python_print_is_output_and_input_updates_memory(self):
        runner = Interpreter(BY_KEY['while_corridoio'], 'Python')
        result = runner.run('strada_libera = int(input())\nwhile strada_libera != 0:\n    print("avanza")\n    strada_libera = int(input())')
        self.assertTrue(result.success, result.message)
        self.assertEqual(runner.output, ['avanza'] * 4)
        self.assertEqual([event[2] for event in runner.reads], [1, 1, 1, 1, 0])

    def test_omitted_reread_keeps_old_sensor_value(self):
        runner = Interpreter(BY_KEY['while_corridoio'], 'Python')
        result = runner.run('strada_libera = int(input())\nwhile strada_libera != 0:\n    print("avanza")')
        self.assertFalse(result.success)
        self.assertEqual(result.frames[-1].world.steps, 4)
        self.assertEqual(result.frames[-1].variables['strada_libera'], 1)
        self.assertEqual(len(runner.reads), 1)

    def test_old_calls_are_rejected_with_native_help(self):
        for language in LANGUAGES:
            with self.assertRaisesRegex(CodeError, 'standard'):
                parse('avanza()' + ('' if language == 'Python' else ';'), language)
        with self.assertRaisesRegex(CodeError, 'input'):
            parse('while strada_libera():\n    print("avanza")', 'Python')

    def test_java_and_javascript_reject_adjacent_output_string_literals(self):
        invalid = {
            'JavaScript': 'console.log("avan" "za");',
            'Java': 'System.out.println("avan" "za");',
        }
        for language, source in invalid.items():
            with self.subTest(language=language), self.assertRaisesRegex(CodeError, 'virgolette'):
                parse(source, language)

    def test_java_rejects_python_only_hex_escape_in_output_literal(self):
        with self.assertRaisesRegex(CodeError, 'virgolette'):
            parse(r'System.out.println("\x61vanza");', 'Java')

    def test_world_counters_are_not_injected(self):
        result = Interpreter(MISSIONS[0], 'Python').run('x = scansioni')
        self.assertNotEqual(result.error_line, 0)
        self.assertNotIn('scansioni', result.frames[-1].variables)

    def test_sensor_reads_and_post_tests_point_to_source_lines(self):
        for mission in MISSIONS:
            for language in LANGUAGES:
                with self.subTest(mission=mission.key, language=language):
                    source = mission.solution(language)
                    runner = Interpreter(mission, language)
                    result = runner.run(source)
                    lines = source.splitlines()
                    for line, name, value in runner.reads:
                        self.assertIn(name, lines[line - 1])
                        self.assertTrue(any(call in lines[line - 1] for call in ('input()', 'prompt()', 'scanf(', 'nextLine()')))
                        self.assertIn(value, (0, 1))
                    if mission.loop == 'do':
                        phases = [frame.phase for frame in result.frames]
                        self.assertLess(phases.index('Azione'), phases.index('Input'))
                        checks = [frame for frame in result.frames if frame.phase in ('Condizione', 'Controllo di uscita')]
                        for frame in checks:
                            self.assertIn('if ' if language == 'Python' else 'while ', lines[frame.line - 1])

    def test_reference_context_teaches_io_without_revealing_mission_solution(self):
        from native_context import native_sections, standalone
        for mission in MISSIONS:
            for language in LANGUAGES:
                sections = native_sections(mission, language)
                complete = next(value for title, value in sections if title.startswith('Il programma completo'))
                self.assertNotEqual(complete, standalone(mission.solution(language), language))
                self.assertTrue(any(title.startswith('Lettura esplicita') for title, _ in sections))

    def test_all_solutions_use_print_and_explicit_reads(self):
        for mission in MISSIONS:
            for language in LANGUAGES:
                runner = Interpreter(mission, language)
                result = runner.run(mission.solution(language))
                self.assertTrue(result.success, (mission.key, language, result.message))
                self.assertTrue(runner.output or mission.zero_case)
                self.assertEqual(bool(runner.reads), mission.loop != 'for')

    def test_native_input_requires_declarations_and_boolean_conditions(self):
        invalid = [('C', 'scanf("%d", &strada_libera);'),
                   ('Java', 'strada_libera = Integer.parseInt(input.nextLine());'),
                   ('Java', 'int strada_libera = 1; while (strada_libera) {}'),
                   ('JavaScript', 'for (int i = 0; i < 2; i++) {}')]
        for language, source in invalid:
            with self.subTest(language=language, source=source):
                with self.assertRaises(CodeError):
                    parse(source, language)

    def test_comments_inside_output_literals_are_not_removed(self):
        from native_io import output_statement
        for language in ('JavaScript', 'C', 'Java'):
            for message in ('avan/*comment*/za', 'avan//comment'):
                with self.subTest(language=language, message=message):
                    source = BY_KEY['for_pontile'].solution(language).replace(
                        output_statement('avanza', language), output_statement(message, language))
                    result = Interpreter(BY_KEY['for_pontile'], language).run(source)
                    self.assertFalse(result.success)
                    self.assertNotEqual(result.error_line, 0)

    def test_comment_removal_preserves_error_line_and_token_boundaries(self):
        source = '/* prima\nseconda */\nfor (int i = 0; i < 5; i++) {\nSystem.out.println("avan/*test*/za");\n}'
        with self.assertRaises(CodeError) as caught:
            parse(source, 'Java')
        self.assertEqual(caught.exception.line, 4)
        with self.assertRaises(CodeError):
            parse('int/**/n = 0; int/**/n = 1;', 'Java')
        self.assertEqual(parse('int/**/n = 0;', 'Java')[0].name, 'n')

    def test_for_assignment_requires_an_existing_counter(self):
        from native_io import output_statement
        for language in ('C', 'Java'):
            source = 'for (i = 0; i < 5; i++) { ' + output_statement('avanza', language) + ' }'
            with self.subTest(language=language):
                with self.assertRaisesRegex(CodeError, 'Dichiara'):
                    parse(source, language)
                result = Interpreter(BY_KEY['for_pontile'], language).run('int i; ' + source)
                self.assertTrue(result.success, result.message)

    def test_java_integer_values_reject_boolean_expressions(self):
        solution = BY_KEY['for_pontile'].solution('Java')
        for value in ('true', '1 < 2', '!false', '(1 < 2) + 1'):
            for prefix in ('int n = ' + value + ';', 'int n; n = ' + value + ';'):
                with self.subTest(prefix=prefix):
                    result = Interpreter(BY_KEY['for_pontile'], 'Java').run(prefix + solution)
                    self.assertFalse(result.success)
                    self.assertNotEqual(result.error_line, 0)
        for source in ('for (int i = true; i < 5; i++) {}',
                       'for (int i = 0; i < true; i++) {}',
                       'for (int i = 0; i < 5; i += true) {}'):
            with self.subTest(source=source), self.assertRaises(CodeError):
                parse(source, 'Java')
        self.assertTrue(Interpreter(BY_KEY['for_pontile'], 'Java').run('int n = (2 + 3) * 1; ' + solution).success)
        self.assertEqual(parse('int n = (1 < 2);', 'C')[0].name, 'n')
