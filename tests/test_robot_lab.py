from native_io import output_statement
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from engine import CodeError, Interpreter, LANGUAGES, Node, generate, parse
from missions import BY_KEY, CONDITIONS, DIFFICULTIES, MISSIONS
import storage


class ExecutionTests(unittest.TestCase):
    def test_all_authored_solutions(self):
        for mission in MISSIONS:
            for language in LANGUAGES:
                with self.subTest(mission=mission.key, language=language):
                    result = Interpreter(mission, language).run(mission.solution(language))
                    self.assertTrue(result.success, result.message)
                    self.assertTrue(result.rule)
                    self.assertTrue(result.goal)

    def test_all_solution_translations(self):
        for mission in MISSIONS:
            for source in LANGUAGES:
                nodes = parse(mission.solution(source), source)
                for target in LANGUAGES:
                    code = generate(nodes, target)
                    self.assertTrue(Interpreter(mission, target).run(code).success, (mission.key, source, target, code))

    def test_medium_exercises_are_incomplete_in_every_language(self):
        for mission in MISSIONS:
            for language in LANGUAGES:
                code = mission.starter(language, 'Medio')
                self.assertIn('???', code)
                result = Interpreter(mission, language).run(code)
                self.assertFalse(result.success)
                self.assertIn('Completa', result.message)

    def test_while_and_do_condition_timing(self):
        for language in LANGUAGES:
            mission = BY_KEY['do_uno']
            after = Interpreter(mission, language).run(mission.solution(language))
            self.assertEqual(after.frames[-1].world.scans, 1)
            loop = Node('while', value='segnale_trovato == 0', body=[Node('command', name='scansiona')])
            before = Interpreter(mission, language).run(generate([Node('read', name='segnale_trovato'), loop], language))
            self.assertEqual(before.frames[-1].world.scans, 0)
            phases = [f.phase for f in after.frames]
            self.assertLess(phases.index('Azione'), phases.index('Controllo di uscita' if language == 'Python' else 'Condizione'))

    def test_zero_case_requires_a_meaningful_guard_and_body(self):
        mission = BY_KEY['while_zero']
        valid = Interpreter(mission, 'Python').run(mission.solution('Python'))
        self.assertTrue(valid.success)
        self.assertEqual(valid.frames[-1].iterations, 0)
        for code in ('', 'while False:\n    print("avanza")', 'while not sul_traguardo():\n    pass', 'print("avanza")'):
            self.assertFalse(Interpreter(mission, 'Python').run(code).success, code)

    def test_unused_loop_and_manual_commands_do_not_pass(self):
        mission = BY_KEY['for_pontile']
        manual = 'print("avanza")\n' * 5
        for code in (manual, 'for i in range(0):\n    print("avanza")\n' + manual,
                     'if False:\n    for i in range(5):\n        print("avanza")\n' + manual):
            result = Interpreter(mission, 'Python').run(code)
            self.assertTrue(result.goal)
            self.assertFalse(result.rule)
            self.assertFalse(result.success)

    def test_wrong_loop_reaches_goal_but_not_success(self):
        mission = BY_KEY['for_pontile']
        code = 'sul_traguardo = int(input())\nwhile sul_traguardo == 0:\n    print("avanza")\n    sul_traguardo = int(input())'
        result = Interpreter(mission, 'Python').run(code)
        self.assertTrue(result.goal)
        self.assertFalse(result.success)

    def test_single_dummy_for_and_mixed_loops_do_not_pass(self):
        mission = BY_KEY['for_pontile']
        for code in ('for i in range(1):\n' + '    print("avanza")\n' * 5,
                     'sul_traguardo = int(input())\nfor i in range(1):\n    while sul_traguardo == 0:\n        print("avanza")\n        sul_traguardo = int(input())'):
            result = Interpreter(mission, 'Python').run(code)
            self.assertTrue(result.goal)
            self.assertFalse(result.rule)

    def test_python_post_test_truth_matches_highlighted_if(self):
        m = BY_KEY['do_segnale']
        code = m.solution('Python')
        result = Interpreter(m, 'Python').run(code)
        checks = [f for f in result.frames if f.phase == 'Controllo di uscita']
        self.assertEqual([f.truth for f in checks], [False, False, True])
        self.assertTrue(all(code.splitlines()[f.line - 1].strip().startswith('if not segnale_trovato == 0') for f in checks))
        exit_frame = next(f for f in result.frames if f.phase == 'Uscita')
        self.assertEqual(code.splitlines()[exit_frame.line - 1].strip(), 'break')

    def test_wrong_order_reports_actual_missing_battery(self):
        m = BY_KEY['for_batterie']
        code = m.program('Python', 4, '', ['raccogli', 'avanza'])
        result = Interpreter(m, 'Python').run(code)
        self.assertFalse(result.success)
        self.assertIn('non c’è una batteria', result.message)
        self.assertEqual(result.frames[-1].world.collected, 0)

    def test_collision_stops_before_moving_through_wall(self):
        m = BY_KEY['for_pontile']
        result = Interpreter(m, 'Python').run(m.program('Python', 8, '', ['avanza']))
        self.assertFalse(result.success)
        self.assertEqual(result.frames[-1].world.x, 5)
        self.assertIn('ostacolo', result.message)

    def test_budget_bounds_empty_and_changing_loops(self):
        for code in ('while True:\n    pass', 'i = 0\nwhile True:\n    i += 1'):
            result = Interpreter(MISSIONS[0], 'Python', limit=70).run(code)
            self.assertLessEqual(len(result.frames), 71)
            self.assertFalse(result.success)
            self.assertIn('Pausa di protezione', result.message)

    def test_native_for_counter_behavior(self):
        mission = replace(MISSIONS[0], goal=(3, 2))
        py = Interpreter(mission, 'Python').run('for i in range(3):\n    print("avanza")\n    i = 10')
        self.assertEqual(py.frames[-1].world.steps, 3)
        self.assertEqual(py.frames[-1].variables['i'], 10)
        js = Interpreter(mission, 'JavaScript').run('for (let i = 0; i < 3; i++) { console.log("avanza"); i = 10; }')
        self.assertEqual(js.frames[-1].world.steps, 1)
        self.assertNotIn('i', js.frames[-1].variables)

    def test_for_descending_and_inclusive_limits(self):
        m = BY_KEY['for_pontile']
        for language in LANGUAGES:
            code = 'for i in range(4, -1, -1):\n    print("avanza")' if language == 'Python' else 'for (' + ('let' if language == 'JavaScript' else 'int') + ' i = 4; i >= 0; i--) { ' + output_statement('avanza', language) + ' }'
            self.assertTrue(Interpreter(m, language).run(code).success)
            translated = generate(parse(code, language), language)
            self.assertTrue(Interpreter(m, language).run(translated).success, translated)
        self.assertTrue(Interpreter(m, 'C').run('for (int i = 0; i <= 4; i++) { ' + output_statement('avanza', 'C') + ' }').success)

    def test_range_bounds_evaluated_once_but_classic_for_rechecks(self):
        m = MISSIONS[0]
        py = Interpreter(m, 'Python').run('n = 5\nfor i in range(n):\n    print("avanza")\n    n = 1')
        js = Interpreter(m, 'JavaScript').run('let n = 5; for (let i = 0; i < n; i++) { console.log("avanza"); n = 1; }')
        self.assertEqual(py.frames[-1].world.steps, 5)
        self.assertEqual(js.frames[-1].world.steps, 1)

    def test_nested_loops_break_and_sensor_conditions(self):
        m = replace(MISSIONS[0], goal=(4, 2))
        code = 'for i in range(2):\n    for j in range(8):\n        print("avanza")\n        if j == 1:\n            break'
        self.assertTrue(Interpreter(m, 'Python').run(code).success)
        code = 'strada_libera = int(input())\nsul_traguardo = int(input())\nwhile strada_libera != 0 and sul_traguardo == 0:\n    print("avanza")\n    strada_libera = int(input())\n    sul_traguardo = int(input())'
        self.assertTrue(Interpreter(replace(m, loop='while'), 'Python').run(code).success)

    def test_student_code_cannot_call_host_or_modify_sensors(self):
        code_samples = ('import os', '__import__("os")', 'open("file")', 'x = (1).__class__',
                        'while True:\n    eval()', 'x = [1] * 9999', 'break', 'x = 10 ** 999')
        for code in code_samples:
            with self.subTest(code=code):
                result = Interpreter(MISSIONS[0], 'Python').run(code)
                self.assertFalse(result.success)
                self.assertNotEqual(result.error_line, 0)
        for code in ('system();', 'while (true) {', 'for (;;) {}', 'int i = ;'):
            self.assertFalse(Interpreter(MISSIONS[0], 'C').run(code).success)

    def test_counters_checks_and_snapshot_independence(self):
        m = BY_KEY['while_traccia']
        result = Interpreter(m, 'Python').run(m.solution('Python'))
        first, last = result.frames[0], result.frames[-1]
        self.assertEqual(first.world.batteries, set(m.batteries))
        self.assertEqual(last.world.batteries, set())
        self.assertEqual(last.iterations, 4)
        self.assertEqual(last.checks, 5)
        self.assertEqual(last.world.steps, 4)


class PersistenceTests(unittest.TestCase):
    def test_roundtrip_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            state = storage.defaults()
            state['drafts']['example'] = 'while ???\n'
            state['completed'] = ['for_pontile|Facile|Python']
            state['blocks']['for_pontile'] = dict(count=5, condition=CONDITIONS[0], actions=['avanza'])
            self.assertEqual(storage.save(state, path), '')
            self.assertEqual(storage.load(path)[0], state)
            path.write_text('{broken', encoding='utf-8')
            self.assertTrue(storage.load(path)[1])
            path.write_text(json.dumps({'size': 900, 'language': None, 'blocks': {'x': {'count': -1}}, 'completed': [3, 'ok']}), encoding='utf-8')
            loaded, _ = storage.load(path)
            self.assertEqual(loaded['size'], 19)
            self.assertEqual(loaded['completed'], ['ok'])
            self.assertEqual(loaded['blocks'], {})


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pygame
        pygame.init()
        cls.pygame = pygame
        cls.screen = pygame.display.set_mode((1440, 900))

    @classmethod
    def tearDownClass(cls):
        cls.pygame.quit()

    def app(self):
        from main import App
        app = App(self.screen, saving=False)
        app.state = storage.defaults()
        return app

    def test_settings_keeps_incomplete_code_and_simulation(self):
        app = self.app()
        app.mode = 'game'
        app.state['difficulty'] = 'Difficile'
        app.open_mission('while_corridoio')
        app.editor.set('while ???\n')
        app.action('settings')
        app.action('settings')
        app.action('theme:Giorno')
        app.action('return')
        self.assertEqual(app.page, 'lab')
        self.assertEqual(app.editor.value, 'while ???\n')

    def test_difficulty_drafts_are_separate(self):
        app = self.app()
        app.mode = 'game'
        app.state['difficulty'] = 'Medio'
        app.open_mission('for_pontile')
        app.editor.set('my medium draft')
        app.set_difficulty('Difficile')
        app.editor.set('my difficult draft')
        app.set_difficulty('Facile')
        app.action('add:avanza')
        app.set_difficulty('Medio')
        self.assertEqual(app.editor.value, 'my medium draft')
        app.set_difficulty('Difficile')
        self.assertEqual(app.editor.value, 'my difficult draft')
        app.set_difficulty('Facile')
        self.assertEqual(app.block_data['actions'], ['avanza'])

    def test_switch_from_learn_does_not_fill_game_with_solution(self):
        app = self.app()
        app.state['difficulty'] = 'Difficile'
        app.open_mission('for_pontile')
        app.modal = None
        app.action('try_game')
        self.assertNotEqual(app.editor.value, app.mission.solution(app.language))
        self.assertEqual(app.editor.value, '')
        app.action('focus_code')
        app.event(self.pygame.event.Event(self.pygame.TEXTINPUT, text='print("avanza")'))
        self.assertEqual(app.editor.value, 'print("avanza")')

    def test_language_translation_and_incomplete_draft_preservation(self):
        app = self.app()
        app.mode = 'game'
        app.state['difficulty'] = 'Difficile'
        app.open_mission('for_pontile')
        app.editor.set(app.mission.solution('Python'))
        app.set_language('Java')
        self.assertIn('for (int', app.editor.value)
        self.assertTrue(Interpreter(app.mission, 'Java').run(app.editor.value).success)
        app.editor.set('for (???')
        app.set_language('Python')
        self.assertEqual(app.editor.value, app.mission.solution('Python'))
        app.set_language('Java')
        self.assertEqual(app.editor.value, 'for (???')

    def test_modal_pauses_playback_and_keyboard_scrolls(self):
        app = self.app()
        app.open_mission('do_segnale')
        app.modal = None
        app.run_program(True)
        app.advance()
        app.open_modal('guide')
        app.draw()
        self.assertGreater(app.modal_max, 0)
        before = app.frame_index
        app.update(5)
        self.assertEqual(app.frame_index, before)
        app.event(self.pygame.event.Event(self.pygame.KEYDOWN, key=self.pygame.K_END, mod=0))
        self.assertEqual(app.modal_scroll, app.modal_max)
        app.action('close')
        app.update(1)
        self.assertGreater(app.frame_index, before)

    def test_completion_is_awarded_only_at_end_of_playback(self):
        app = self.app()
        app.mode = 'game'
        app.open_mission('for_pontile')
        app.block_data = dict(count=5, condition=CONDITIONS[0], actions=['avanza'])
        app.sync_blocks()
        app.run_program(False)
        self.assertEqual(app.state['completed'], [])
        while app.frame_index < len(app.result.frames) - 1:
            app.advance()
        self.assertEqual(app.state['completed'], [app.draft_key()])
        app.action('back')
        self.assertEqual(len(app.state['completed']), 1)

    def test_drag_to_add_and_reorder_blocks(self):
        app = self.app()
        app.mode = 'game'
        app.open_mission('for_batterie')
        app.draw()
        def drag(key, target):
            app.draw()
            rect = next(r for k, r, enabled in app.buttons if k == key)
            app.event(self.pygame.event.Event(self.pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
            app.event(self.pygame.event.Event(self.pygame.MOUSEMOTION, pos=target, rel=(0, 0), buttons=(1, 0, 0)))
            app.event(self.pygame.event.Event(self.pygame.MOUSEBUTTONUP, button=1, pos=target))
        drag('add:avanza', (app.body_rect.centerx, app.body_rect.y + 18))
        drag('add:raccogli', (app.body_rect.centerx, app.body_rect.y + 60))
        self.assertEqual(app.block_data['actions'], ['avanza', 'raccogli'])
        drag('body:1', (app.body_rect.centerx, app.body_rect.y + 2))
        self.assertEqual(app.block_data['actions'], ['raccogli', 'avanza'])

    def test_editor_undo_and_multiline_navigation(self):
        from ui import Editor
        e = Editor('print("avanza")\n')
        e.focus = True
        e.replace('print("raccogli")')
        e.key(self.pygame.event.Event(self.pygame.KEYDOWN, key=self.pygame.K_z, mod=self.pygame.KMOD_CTRL))
        self.assertEqual(e.value, 'print("avanza")\n')
        e.key(self.pygame.event.Event(self.pygame.KEYDOWN, key=self.pygame.K_y, mod=self.pygame.KMOD_CTRL))
        self.assertIn('print("raccogli")', e.value)
        e.key(self.pygame.event.Event(self.pygame.KEYDOWN, key=self.pygame.K_a, mod=self.pygame.KMOD_CTRL))
        e.replace('while strada_libera():\n    print("avanza")')
        self.assertEqual(e.value.count('\n'), 1)

    def test_hover_all_enabled_controls_and_modal_isolation(self):
        from ui import palette, THEMES
        app = self.app()
        checked = 0
        for theme in THEMES:
            app.c = palette(theme)
            for page in ('welcome', 'catalog', 'settings', 'lab'):
                app.page = page
                if page == 'lab':
                    app.mode = 'game'
                    app.open_mission('for_pontile')
                    app.action('add:avanza')
                app.modal = None
                app.pointer = (-10, -10)
                app.draw()
                controls = list(app.buttons)
                before = app.canvas.copy()
                for key, rect, enabled in controls:
                    if not enabled:
                        continue
                    app.pointer = rect.center
                    app.draw()
                    self.assertEqual(app.cursor, self.pygame.SYSTEM_CURSOR_HAND, key)
                    self.assertNotEqual(app.canvas.get_at((rect.x + 5, rect.centery)), before.get_at((rect.x + 5, rect.centery)), key)
                    checked += 1
            app.open_modal('guide')
            app.draw()
            self.assertFalse(any(key == 'home' for key, _, _ in app.buttons))
        self.assertGreater(checked, 170)


if __name__ == '__main__':
    unittest.main()
