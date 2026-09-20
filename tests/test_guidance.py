from native_io import output_statement
"""Real beginner interactions: typing, checking, predicting and replaying."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import unittest
import pygame
import storage
from main import App
from engine import Interpreter, LANGUAGES, parse
from missions import MISSIONS


class GuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1440, 900))

    @classmethod
    def tearDownClass(cls):
        from ui import font
        font.cache_clear()
        pygame.quit()

    def app(self, mission='for_pontile', difficulty='Medio', language='Python', mode='game'):
        app = App(self.screen, saving=False)
        app.state = storage.defaults()
        app.mode = mode
        app.state.update(difficulty=difficulty, language=language)
        app.open_mission(mission)
        app.modal = None
        app.draw()
        return app

    def click(self, app, key):
        app.draw()
        self.assertIn(key, [k for k, _, enabled in app.buttons if enabled], 'The requested action must be visible and usable.')
        rect = next(r for k, r, enabled in app.buttons if k == key and enabled)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            app.event(pygame.event.Event(kind, button=1, pos=rect.center))

    def test_focus_replaces_only_gap_and_checks_in_all_languages(self):
        for language in LANGUAGES:
            for mission, answer in [('for_pontile', '5'), ('while_corridoio', output_statement('avanza', language).rstrip(';')), ('do_segnale', output_statement('scansiona', language).rstrip(';'))]:
                with self.subTest(language=language, mission=mission):
                    app = self.app(mission, language=language)
                    original = app.editor.value
                    self.click(app, 'focus_code')
                    a, b = sorted((app.editor.anchor, app.editor.caret))
                    self.assertEqual(app.editor.value[a:b], '???')
                    app.event(pygame.event.Event(pygame.TEXTINPUT, text=answer))
                    self.assertEqual(app.editor.value, original.replace('???', answer, 1))
                    self.click(app, 'verify')
                    self.assertTrue(app.verification.success)
                    self.assertIn(app.draft_key(), app.state['completed'])
                    self.assertFalse(app.playing)
                    self.assertIsNone(app.modal)

    def test_ctrl_enter_checks_without_adding_a_newline(self):
        app = self.app()
        app.editor.set('for i in range(5):\n    print("avanza")')
        app.editor.focus = True
        before = app.editor.value
        app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=pygame.KMOD_CTRL))
        self.assertEqual(app.editor.value, before)
        self.assertIsNotNone(getattr(app, 'verification', None))
        self.assertTrue(app.verification.success)

    def test_wrong_program_shows_final_state_then_edit_clears_verdict(self):
        app = self.app()
        app.editor.set('for i in range(4):\n    print("avanza")')
        app.action('verify')
        self.assertIsNotNone(getattr(app, 'verification', None))
        self.assertFalse(app.verification.success)
        self.assertEqual(app.current_frame().world.steps, 4)
        self.assertEqual(app.state['completed'], [])
        app.action('focus_code')
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='\n'))
        self.assertIsNone(app.verification)

    def test_empty_code_explains_how_to_start(self):
        app = self.app(difficulty='Difficile')
        app.editor.set('')
        app.action('verify')
        self.assertIsNotNone(getattr(app, 'verification', None))
        self.assertFalse(app.verification.success)
        self.assertIn('Scrivi qui', app.verification.message)

    def test_legacy_comment_does_not_swallow_first_typed_statement(self):
        for language, comment in [('Python', '# Vecchia bozza'), ('Java', '// Vecchia bozza')]:
            app = self.app(difficulty='Difficile', language=language)
            app.editor.set(comment)
            app.action('focus_code')
            app.event(pygame.event.Event(pygame.TEXTINPUT, text='print("avanza")'))
            self.assertEqual(app.editor.value, comment + '\nprint("avanza")')

    def test_trace_preserves_draft_and_selection_and_allows_horizontal_scroll(self):
        app = self.app('while_corridoio', difficulty='Difficile')
        app.editor.set('while ' + ' and '.join(['strada_libera()'] * 8) + ':\n    print("avanza")')
        app.editor.anchor, app.editor.caret = 3, 12
        before = app.editor.snapshot()
        app.action('trace')
        self.assertEqual(app.modal, 'trace')
        app.draw()
        app.action('step')
        self.assertEqual(app.editor.snapshot(), before)
        app.pointer = app.trace_editor.rect.center
        pygame.key.set_mods(pygame.KMOD_SHIFT)
        try:
            app.event(pygame.event.Event(pygame.MOUSEWHEEL, y=-4, x=0))
        finally:
            pygame.key.set_mods(0)
        self.assertGreater(app.trace_editor.xscroll, 0)
        app.action('close')
        self.assertEqual(app.editor.snapshot(), before)
        self.assertFalse(app.playing)
        self.assertEqual(app.state['completed'], [])

    def test_replaying_trace_never_awards_completion(self):
        app = self.app()
        app.editor.set('for i in range(5):\n    print("avanza")')
        app.action('trace')
        for replay in range(2):
            if replay:
                app.action('run')
            for _ in range(100):
                if app.frame_index == len(app.result.frames) - 1:
                    break
                app.advance()
            self.assertEqual(app.state['completed'], [])

    def test_unknown_command_can_open_the_referenced_help(self):
        app = self.app(difficulty='Difficile')
        app.editor.set('forward()')
        app.action('verify')
        self.assertFalse(app.verification.success)
        self.click(app, 'help')
        self.assertEqual(app.modal, 'help')
        app.draw()
        self.click(app, 'close')
        self.assertEqual(app.editor.value, 'forward()')

    def test_prediction_wrong_then_correct_zero_girs_stays_visible(self):
        app = self.app('while_zero', mode='learn')
        self.click(app, 'predict:1')
        self.assertEqual(app.prediction_attempt, 1)
        self.assertIsNone(app.result)
        self.click(app, 'predict:0')
        self.assertEqual(app.prediction_attempt, 0)
        self.click(app, 'learn_start')
        while app.frame_index < len(app.result.frames) - 1:
            app.advance()
        self.assertEqual(app.current_frame().iterations, 0)
        self.assertEqual(app.current_frame().world.steps, 0)
        self.assertEqual(app.prediction_attempt, 0)
        self.assertEqual(app.state['completed'], [])

    def test_learn_opens_with_question_and_game_keeps_its_own_draft(self):
        app = self.app(difficulty='Difficile')
        app.editor.set('for i in range(2):\n    print("avanza")')
        app.navigate('catalog')
        app.mode = 'learn'
        app.open_mission('for_pontile')
        self.assertIsNone(app.modal)
        app.action('try_game')
        self.assertEqual(app.editor.value, 'for i in range(2):\n    print("avanza")')

    def test_placeholder_in_comments_is_not_executable_code(self):
        for language in LANGUAGES:
            m = MISSIONS[0]
            comment = '# nota ???\n' if language == 'Python' else '// nota ???\n'
            result = Interpreter(m, language).run(comment + m.solution(language))
            self.assertTrue(result.success, result.message)

    def test_syntax_examples_are_executable_and_do_not_move_the_robot(self):
        from guidance import syntax_example
        for m in MISSIONS:
            for language in LANGUAGES:
                example = syntax_example(m, language)
                self.assertTrue(parse(example, language))
                result = Interpreter(m, language).run(example)
                self.assertEqual(result.error_line, 0, result.message)
                self.assertEqual(result.frames[-1].world.scans, 3 if m.loop == 'for' else 2)
                self.assertEqual(result.frames[-1].world.steps, 0)


if __name__ == '__main__':
    unittest.main()
