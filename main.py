"""Il laboratorio dei robot — an offline school application about loops."""
import copy
import json
import math
import os
from pathlib import Path
import sys

if '--smoke-test' in sys.argv:
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from engine import COMMANDS, LANGUAGES, CodeError, Interpreter, World, generate, parse
from lessons import COMPARISON, HELP, LESSONS
from missions import BY_KEY, CONDITIONS, DIFFICULTIES, LOOPS, MISSIONS
import storage
from ui import SIZE, THEMES, Editor, board, font, lines, mix, palette, panel, robot, text, wrap

TITLE = 'Il laboratorio dei robot'


class App:
    def __init__(self, screen, state_path=None, saving=True):
        self.screen = screen
        self.canvas = pygame.Surface(SIZE)
        self.state_path = state_path
        self.saving = saving
        self.state, self.notice = storage.load(state_path)
        self.c = palette(self.state['theme'])
        self.page = 'welcome'
        self.return_page = 'welcome'
        self.mode = 'learn'
        self.filter = 'Tutti'
        self.mission = BY_KEY.get(self.state['mission'], MISSIONS[0])
        self.editor = Editor()
        self.block_data = dict(count=3, condition=CONDITIONS[0], actions=[])
        self.body_rect = pygame.Rect(808, 423, 568, 169)
        self.body_scroll = 0
        self.buttons = []
        self.pointer = (-100, -100)
        self.pressed = None
        self.press_pos = (0, 0)
        self.drag = None
        self.key_focus = None
        self.modal = None
        self.modal_tab = 'Spiegazione'
        self.modal_scroll = 0
        self.modal_max = 0
        self.drawing_modal = False
        self.cursor = None
        self.result = None
        self.frame_index = 0
        self.playing = False
        self.elapsed = 0
        self.motion = 1
        self.shake = 0
        self.hint_level = 0
        self.fullscreen = False
        self.window_size = screen.get_size()
        self.time = 0
        self.alive = True
        self.dirty_at = None

    @property
    def language(self):
        return self.state['language']

    @property
    def difficulty(self):
        return self.state['difficulty']

    @property
    def easy(self):
        return self.mode == 'game' and self.difficulty == 'Facile'

    def draft_key(self, language=None, difficulty=None):
        return '|'.join((self.mission.key, difficulty or self.difficulty, language or self.language))

    def persist(self):
        if self.page == 'lab' or (self.page == 'settings' and self.return_page == 'lab'):
            self.remember()
        if self.saving:
            warning = storage.save(self.state, self.state_path)
            if warning:
                self.notice = warning
        self.dirty_at = None

    def remember(self):
        if self.mode == 'game':
            if self.easy:
                self.state['blocks'][self.mission.key] = copy.deepcopy(self.block_data)
            else:
                self.state['drafts'][self.draft_key()] = self.editor.value

    def invalidate(self):
        self.result = None
        self.frame_index = 0
        self.playing = False
        self.elapsed = 0
        self.motion = 1
        self.shake = 0
        self.dirty_at = self.time

    def block_code(self):
        return self.mission.program(self.language, **self.block_data)

    def sync_blocks(self):
        self.editor.set(self.block_code())
        self.invalidate()

    def open_mission(self, key, remember=True):
        if remember and self.page == 'lab':
            self.remember()
        self.mission = BY_KEY[key]
        self.state['mission'] = key
        self.page = 'lab'
        self.editor.focus = False
        self.hint_level = self.body_scroll = 0
        self.block_data = copy.deepcopy(self.state['blocks'].get(key, dict(count=3, condition=CONDITIONS[0], actions=[])))
        if self.mode == 'learn':
            self.editor.set(self.mission.solution(self.language))
        elif self.easy:
            self.editor.set(self.block_code())
        else:
            self.editor.set(self.state['drafts'].get(self.draft_key(), self.mission.starter(self.language, self.difficulty)))
        self.invalidate()
        self.persist()
        if self.mode == 'learn':
            self.open_modal('guide')

    def set_language(self, language):
        if language == self.language:
            return
        self.remember()
        converted = None
        in_lab = self.page == 'lab'
        if in_lab and self.mode == 'game' and not self.easy:
            try:
                converted = generate(parse(self.editor.value, self.language), language)
            except CodeError:
                self.notice = 'La bozza incompleta è conservata nel linguaggio precedente. Completa il codice per poterlo tradurre.'
        self.state['language'] = language
        if in_lab:
            if self.mode == 'learn':
                self.editor.set(self.mission.solution(language))
            elif self.easy:
                self.editor.set(self.block_code())
            else:
                # An existing draft takes precedence over an automatic translation.
                self.editor.set(self.state['drafts'].get(self.draft_key(), converted if converted is not None else self.mission.starter(language, self.difficulty)))
            self.invalidate()
        self.persist()

    def set_difficulty(self, difficulty):
        if difficulty == self.difficulty:
            return
        self.remember()
        self.state['difficulty'] = difficulty
        if self.page == 'lab':
            key = self.mission.key
            self.open_mission(key, remember=False)
        self.persist()

    def navigate(self, page):
        self.persist()
        self.page = page
        self.playing = False
        self.editor.focus = False
        pygame.key.stop_text_input()
        self.key_focus = None

    def open_modal(self, kind):
        self.modal = kind
        self.modal_tab = 'Spiegazione'
        self.modal_scroll = self.modal_max = 0
        self.key_focus = None
        self.editor.focus = False
        pygame.key.stop_text_input()

    def logical(self, pos):
        w, h = self.screen.get_size()
        scale = min(w / SIZE[0], h / SIZE[1])
        return ((pos[0] - (w - SIZE[0] * scale) / 2) / scale, (pos[1] - (h - SIZE[1] * scale) / 2) / scale)

    def card(self, key, rect, accent=None, selected=False, enabled=True):
        c = self.c
        rect = pygame.Rect(rect)
        accent = accent or c['mint']
        active = (not self.modal or self.drawing_modal) and enabled
        hover = active and (rect.collidepoint(self.pointer) or key == self.key_focus)
        fill = c['card'] if selected else c['panel']
        border = accent if selected else c['border']
        if hover:
            glow = pygame.Surface((rect.width + 14, rect.height + 14), pygame.SRCALPHA)
            for spread, alpha in ((6, 18), (3, 45), (1, 80)):
                pygame.draw.rect(glow, (*accent[:3], alpha), (7 - spread, 7 - spread, rect.width + spread * 2, rect.height + spread * 2), 2, border_radius=15 + spread)
            self.canvas.blit(glow, (rect.x - 7, rect.y - 7))
            fill, border = mix(fill, accent, .14), accent
        panel(self.canvas, rect, fill, border, 13)
        if hover:
            pygame.draw.rect(self.canvas, accent, rect, 2, border_radius=13)
        self.buttons.append((key, rect, enabled))
        return rect

    def button(self, key, label, rect, selected=False, accent=None, enabled=True, size=17):
        r = self.card(key, rect, accent, selected, enabled)
        while font(size, True).size(label)[0] > r.width - 16 and size > 12:
            size -= 1
        text(self.canvas, label, r.center, size, self.c['text'] if enabled else self.c['muted'], True, 'center')

    def header(self):
        c, s = self.c, self.canvas
        robot(s, (62, 47), .57, tick=self.time)
        text(s, 'LABORATORIO', (104, 22), 22, c['text'], True)
        text(s, 'DEI ROBOT  /  IMPARA I CICLI', (105, 51), 12, c['mint'], True)
        if self.page != 'welcome':
            self.button('home', 'Inizio', (939, 25, 91, 40), size=15)
        self.button('settings', 'Impostazioni', (1042, 25, 156, 40), size=15)
        self.button('fullscreen', 'Finestra' if self.fullscreen else 'Schermo intero', (1210, 25, 190, 40), size=15)
        pygame.draw.line(s, c['border'], (40, 88), (1400, 88))

    def welcome(self):
        s, c = self.canvas, self.c
        panel(s, pygame.Rect(48, 130, 269, 31), c['card'], c['border'], 15)
        text(s, 'MISSIONE: IMPARARE A RIPETERE', (182, 145), 12, c['mint'], True, 'center')
        text(s, 'Piccoli robot.', (47, 186), 62, c['text'], True)
        text(s, 'Grandi ragionamenti.', (47, 263), 55, c['mint'], True)
        wrap(s, 'Un passo, un controllo, un nuovo tentativo. Scopri come i cicli trasformano poche istruzioni in una missione completa.', pygame.Rect(51, 352, 586, 112), 24, c['muted'])
        for x, label in ((51, '3 cicli'), (203, '4 linguaggi'), (389, 'Anche offline')):
            text(s, '• ' + label, (x, 493), 18, c['accent'])
        hero = pygame.Rect(724, 128, 675, 418)
        panel(s, hero, c['panel'], c['border'], 24)
        for row in range(4):
            for col in range(7):
                tile = pygame.Rect(750 + col * 89, 162 + row * 83, 76, 71)
                panel(s, tile, mix(c['panel'], c['mint'], .12 if row == 2 else .03), c['border'], 9)
        for col in range(3, 6):
            text(s, '›', (788 + col * 89, 365), 39, c['mint'], True, 'center')
        robot(s, (908 + math.sin(self.time) * 6, 345), 2.7, tick=self.time)
        panel(s, pygame.Rect(1121, 196, 220, 67), c['card'], c['mint'], 13)
        text(s, 'RIPETI  →  OSSERVA', (1231, 218), 14, c['mint'], True, 'center')
        text(s, 'Il prossimo passo è tuo.', (1231, 243), 13, c['text'], anchor='center')
        for index, (mode, title, subtitle, desc, color) in enumerate((
            ('learn', 'Impara', 'Prima capisci come funziona.', 'Spiegazioni, esempi e robot da osservare un passaggio alla volta.', 'accent'),
            ('game', 'Gioca', 'Adesso programma tu.', 'Missioni pronte. Scegli Facile, Medio o Difficile e guida il robot.', 'mint'))):
            r = self.card('mode:' + mode, (48 + index * 683, 590, 667, 207), c[color])
            text(s, f'0{index + 1}', (r.x + 25, r.y + 21), 15, c[color], True)
            text(s, title, (r.x + 25, r.y + 50), 34, c['text'], True)
            text(s, '↗', (r.right - 36, r.y + 21), 30, c[color], anchor='topright')
            text(s, subtitle, (r.x + 25, r.y + 105), 20, c[color], True)
            wrap(s, desc, pygame.Rect(r.x + 25, r.y + 143, r.width - 50, 56), 19, c['muted'])
        text(s, 'Scegli il tuo livello. Osserva gli errori. Prova ancora.', (49, 836), 16, c['muted'])
        text(s, f'{len(set(self.state["completed"]))} missioni completate tra livelli e linguaggi', (1397, 836), 15, c['mint'], anchor='topright')

    def selectors(self, y=215, compact=False):
        for i, lang in enumerate(LANGUAGES):
            self.button('lang:' + lang, lang, (40 + i * 146, y, 136, 39), self.language == lang, size=16)
        if self.mode == 'game':
            for i, diff in enumerate(DIFFICULTIES):
                self.button('diff:' + diff, diff, (950 + i * 153, y, 143, 39), self.difficulty == diff, size=16)
        else:
            text(self.canvas, 'Spiegazioni complete, al tuo ritmo.', (1398, y + 19), 17, self.c['muted'], anchor='midright')

    def catalog(self):
        s, c = self.canvas, self.c
        text(s, 'Scegli la tua prossima missione.', (40, 111), 38, c['text'], True)
        text(s, ('IMPARA  /  Guarda e ragiona' if self.mode == 'learn' else 'GIOCA  /  Usa il ciclo richiesto per completare la missione'), (42, 162), 17, c['mint'])
        text(s, 'LINGUAGGIO', (42, 191), 12, c['muted'], True)
        if self.mode == 'game':
            text(s, 'DIFFICOLTÀ LIBERA', (952, 191), 12, c['muted'], True)
        self.selectors()
        for i, (key, title) in enumerate((('Tutti', 'Tutti i cicli'), ('for', 'for'), ('while', 'while'), ('do', 'do while'))):
            self.button('filter:' + key, title, (40 + i * 150, 277, 139, 37), self.filter == key, size=16)
        text(s, '9 missioni · 3 difficoltà · nessun livello bloccato', (1398, 295), 16, c['muted'], anchor='midright')
        entries = [m for m in MISSIONS if self.filter == 'Tutti' or m.loop == self.filter]
        for i, m in enumerate(entries):
            r = self.card('mission:' + m.key, (40 + (i % 3) * 458, 338 + (i // 3) * 158, 444, 145), c['mint'])
            completed = '|'.join((m.key, self.difficulty, self.language)) in self.state['completed']
            text(s, LOOPS[m.loop].upper(), (r.x + 19, r.y + 16), 12, c['accent'], True)
            text(s, '✓ completata' if completed else 'Apri →', (r.right - 18, r.y + 16), 13, c['mint'], True, 'topright')
            text(s, m.title, (r.x + 19, r.y + 43), 23, c['text'], True)
            wrap(s, m.subtitle, pygame.Rect(r.x + 19, r.y + 84, r.width - 38, 50), 18, c['muted'])
        if self.mode == 'game':
            summary = {'Facile': 'FACILE  ·  Costruisci il corpo con i blocchi e osserva il codice generato.', 'Medio': 'MEDIO  ·  Completa i punti segnati con ??? e controlla il risultato.', 'Difficile': 'DIFFICILE  ·  Scrivi il programma con i comandi del robot. Gli aiuti restano disponibili.'}[self.difficulty]
            text(s, summary, (42, 836), 17, c['muted'])
        else:
            text(s, 'Ogni esempio ha una spiegazione, un confronto tra cicli e i comandi del robot.', (42, 836), 17, c['muted'])

    def current_frame(self):
        return self.result.frames[self.frame_index] if self.result else None

    def initial_world(self):
        return World(*self.mission.start, batteries=set(self.mission.batteries), lamps=set(self.mission.lamps))

    def lab(self):
        s, c, m = self.canvas, self.c, self.mission
        self.button('catalog', '← Missioni', (40, 112, 137, 41), size=16)
        text(s, m.title, (194, 111), 34, c['text'], True)
        self.button('guide', 'Spiegazione', (1052, 111, 163, 41), accent=c['accent'])
        self.button('help', 'Comandi e codice', (1228, 111, 172, 41), size=15)
        self.card('objective', (40, 170, 1360, 52), c['blue'])
        text(s, f'{"IMPARA" if self.mode == "learn" else self.difficulty.upper()}  ·  CICLO {LOOPS[m.loop].upper()}', (56, 185), 14, c['accent'], True)
        label = m.objective
        while font(16).size(label)[0] > 1010 and len(label) > 1:
            label = label[:-1]
        if label != m.objective:
            label = label.rstrip() + '…'
        text(s, label, (340, 185), 16, c['text'])
        text(s, '↗', (1381, 183), 22, c['blue'], anchor='topright')
        frame = self.current_frame()
        world = frame.world if frame else self.initial_world()
        previous = self.result.frames[self.frame_index - 1].world if self.result and self.frame_index > 0 else None
        board(s, pygame.Rect(40, 238, 720, 376), m, world, c, self.time, previous, self.motion, self.shake * 5)
        text(s, '↗ direzione  ·  piattaforma verde = traguardo', (61, 591), 13, c['muted'])
        panel(s, pygame.Rect(40, 628, 720, 159), c['panel'], c['border'])
        text(s, frame.phase.upper() if frame else 'PRONTO ALLA MISSIONE', (59, 644), 13, c['danger'] if frame and frame.phase == 'Da rivedere' else c['mint'], True)
        truth = '' if not frame or frame.truth is None else 'CONDIZIONE: VERA' if frame.truth else 'CONDIZIONE: FALSA'
        text(s, truth, (740, 644), 13, c['mint'] if not frame or frame.truth else c['accent'], True, 'topright')
        vars_label = f'Giri: {frame.iterations if frame else 0}    Controlli: {frame.checks if frame else 0}    Passi: {world.steps}    Batterie: {world.collected}'
        text(s, vars_label, (59, 670), 17, c['text'], True)
        user_vars = '   '.join(f'{k} = {v}' for k, v in (frame.variables.items() if frame else []) if k not in ('passi', 'raccolte', 'accese', 'scansioni'))
        text(s, user_vars or f'Lampade accese: {len(world.lit)}    Scansioni: {world.scans}', (59, 697), 16, c['blue'])
        message = frame.message if frame else ('Premi Esegui o Un passo per osservare il programma.' if self.mode == 'learn' else 'Costruisci il programma, poi premi Esegui. Puoi chiedere un suggerimento in qualsiasi momento.')
        brief = lines(message, 492, 16)
        text(s, brief[0] + ('…' if len(brief) > 1 else ''), (59, 744), 16, c['muted'])
        self.button('feedback', 'Leggi tutto →', (571, 733, 169, 36), size=14, accent=c['blue'])
        panel(s, pygame.Rect(783, 238, 617, 549), c['panel'], c['border'])
        for i, lang in enumerate(LANGUAGES):
            self.button('lang:' + lang, lang, (802 + i * 145, 252, 137, 35), self.language == lang, size=15)
        if self.easy:
            self.blocks()
            text(s, 'IL CODICE DEI TUOI BLOCCHI', (808, 606), 12, c['muted'], True)
            self.editor.draw(s, pygame.Rect(808, 628, 568, 141), c, frame.line if frame else 0, readonly=True, tick=self.time, size=16)
        else:
            text(s, 'OSSERVA IL CODICE' if self.mode == 'learn' else 'COMPLETA ???' if self.difficulty == 'Medio' else 'SCRIVI IL PROGRAMMA', (808, 306), 13, c['mint'], True)
            if self.mode == 'game':
                self.button('reset_code', 'Ricomincia il codice', (1180, 300, 196, 32), size=14)
            self.editor.draw(s, pygame.Rect(808, 345, 568, 422), c, frame.line if frame else 0,
                             self.result.error_line if self.result and self.frame_index == len(self.result.frames) - 1 else 0,
                             self.mode == 'learn', self.time, self.state['size'])
        self.button('run', 'Pausa' if self.playing else 'Continua' if self.result and self.frame_index < len(self.result.frames) - 1 else 'Esegui', (40, 805, 132, 44), selected=True, accent=c['mint'])
        self.button('back', '← Indietro', (183, 805, 125, 44), enabled=bool(self.result and self.frame_index > 0), size=16)
        self.button('step', 'Un passo →', (319, 805, 137, 44), enabled=not self.result or self.frame_index < len(self.result.frames) - 1, size=16)
        self.button('restart', 'Riparti', (467, 805, 108, 44), size=16)
        self.button('speed', f'{self.state["speed"]:g}×', (586, 805, 73, 44), size=16)
        if self.mode == 'game':
            self.button('hint', 'Suggerimento', (674, 805, 161, 44), accent=c['accent'], size=16)
            for i, diff in enumerate(DIFFICULTIES):
                self.button('diff:' + diff, diff, (970 + i * 146, 805, 138, 44), self.difficulty == diff, size=15)
        else:
            self.button('comparison', 'Confronta i cicli', (680, 805, 196, 44), accent=c['blue'], size=16)
            self.button('try_game', 'Prova questa missione →', (1090, 805, 310, 44), accent=c['mint'], size=17)
        if self.drag:
            name = self.drag[1] if self.drag[0] == 'add' else self.block_data['actions'][self.drag[1]]
            r = pygame.Rect(self.pointer[0] + 12, self.pointer[1] - 20, 211, 37)
            panel(s, r, c['card'], c['mint'], 9)
            text(s, COMMANDS[name], r.center, 15, c['text'], True, 'center')

    def blocks(self):
        c, s, m = self.c, self.canvas, self.mission
        if m.loop == 'for':
            text(s, 'RIPETI', (809, 306), 14, c['accent'], True)
            self.button('count:-1', '−', (888, 296, 43, 36), enabled=self.block_data['count'] > 0, size=24)
            text(s, self.block_data['count'], (966, 314), 23, c['text'], True, 'center')
            self.button('count:1', '+', (1003, 296, 43, 36), enabled=self.block_data['count'] < 20, size=24)
            text(s, 'VOLTE', (1062, 307), 14, c['muted'], True)
        else:
            text(s, 'MENTRE' if m.loop == 'while' else 'RIPETI DOPO SE', (809, 307), 13, c['accent'], True)
            from engine import format_expr
            self.button('condition', format_expr(self.block_data['condition'], self.language) + ' ▾', (948, 296, 428, 36), size=16)
        for i, (name, label) in enumerate(COMMANDS.items()):
            self.button('add:' + name, '+ ' + label, (808 + (i % 3) * 191, 345 + (i // 3) * 37, 183, 31), enabled=len(self.block_data['actions']) < 12, size=13)
        panel(s, self.body_rect, c['bg'], c['mint'] if self.drag and self.body_rect.collidepoint(self.pointer) else c['border'], 10)
        actions = self.block_data['actions']
        active_block = -1
        frame = self.current_frame()
        if frame and frame.phase == 'Azione':
            nodes = parse(self.editor.value, self.language)
            if nodes:
                active_block = next((i for i, node in enumerate(nodes[0].body) if node.line == frame.line), -1)
        self.body_scroll = min(self.body_scroll, max(0, len(actions) - 4))
        if not actions:
            wrap(s, 'Trascina qui i comandi, oppure cliccali per aggiungerli. Questo è il corpo che verrà ripetuto.', self.body_rect.inflate(-38, -40), 18, c['muted'])
        for i in range(self.body_scroll, min(len(actions), self.body_scroll + 4)):
            y = 432 + (i - self.body_scroll) * 38
            self.button('body:' + str(i), f'{i + 1}.  {COMMANDS[actions[i]]}', (819, y, 391, 32), selected=i == active_block, accent=c['mint'], size=15)
            self.button('up:' + str(i), '↑', (1218, y, 42, 32), enabled=i > 0, size=18)
            self.button('down:' + str(i), '↓', (1267, y, 42, 32), enabled=i < len(actions) - 1, size=18)
            self.button('remove:' + str(i), '×', (1316, y, 45, 32), size=20)
        if self.drag and self.body_rect.collidepoint(self.pointer):
            row = min(4, max(0, int((self.pointer[1] - 430 + 19) // 38)))
            y = min(585, 430 + row * 38)
            pygame.draw.line(s, c['mint'], (821, y), (1360, y), 3)
        if len(actions) > 4:
            text(s, f'{self.body_scroll + 1}–{min(len(actions), self.body_scroll + 4)} / {len(actions)} · rotella per scorrere', (1374, 605), 11, c['muted'], anchor='topright')

    def settings(self):
        s, c = self.canvas, self.c
        text(s, 'Il laboratorio, come piace a te.', (48, 121), 38, c['text'], True)
        text(s, 'Le tue scelte e i tuoi programmi vengono conservati.', (50, 175), 20, c['muted'])
        groups = [('Aspetto', 'Un tema leggibile sulla lavagna e sul tuo schermo.', list(THEMES), 'theme', self.state['theme']),
                  ('Dimensione del testo', 'Ingrandisci codice e spiegazioni. Puoi sempre scorrere il contenuto.', ['Compatto', 'Grande', 'Proiezione'], 'size', {17: 'Compatto', 19: 'Grande', 21: 'Proiezione'}[self.state['size']]),
                  ('Velocità di esecuzione', 'Rallenta per osservare il controllo e ogni singola azione.', ['0.5×', '1×', '2×', '3×'], 'velocity', f'{self.state["speed"]:g}×')]
        for i, (title, desc, values, key, selected) in enumerate(groups):
            r = pygame.Rect(49, 230 + i * 171, 1349, 149)
            panel(s, r, c['panel'], c['border'])
            text(s, title, (r.x + 24, r.y + 21), 25, c['text'], True)
            text(s, desc, (r.x + 24, r.y + 62), 17, c['muted'])
            for j, value in enumerate(values):
                self.button(key + ':' + value, value, (750 + j * 152, r.y + 55, 139, 44), value == selected, size=16)
        self.button('return', '← Torna all’attività', (50, 790, 273, 49), accent=c['mint'])
        text(s, 'F11: schermo intero  ·  Nessun account, nessuna connessione richiesta.', (1397, 815), 16, c['muted'], anchor='midright')

    def modal_content(self):
        m = self.mission
        if self.modal == 'condition':
            return 'Scegli quando ripetere', []
        if self.modal == 'reset':
            return 'Ricominciare il codice?', [('Una nuova bozza', 'La missione e i progressi completati rimangono disponibili. Il programma attuale sarà sostituito dal modello iniziale di questo livello.')]
        if self.modal == 'notice':
            return 'Informazione', [('Da sapere', self.notice)]
        if self.modal == 'success':
            frame = self.current_frame()
            return 'Missione compiuta!', [('Obiettivo raggiunto', m.objective), ('Hai usato il ciclo giusto', f'Hai completato la missione con {LOOPS[m.loop]}, in {self.language}, al livello {self.difficulty}.'), ('Il lavoro del robot', f'Ripetizioni: {frame.iterations}. Controlli: {frame.checks}. Passi: {frame.world.steps}. Batterie raccolte: {frame.world.collected}.'), ('Porta con te questa idea', m.concept)]
        if self.modal == 'help':
            return 'Comandi e codice', HELP
        if self.modal == 'objective':
            return m.title, [('Obiettivo', m.objective), ('Ciclo richiesto', LOOPS[m.loop] + ': le azioni del robot devono essere nel corpo del ciclo, che deve essere effettivamente raggiunto.'), ('Che cosa impari', m.concept), ('Come affrontare la missione', 'Osserva la posizione iniziale, la freccia di direzione, gli oggetti e la piattaforma verde. Prima di eseguire, prova a prevedere quante ripetizioni serviranno. Puoi leggere le coordinate sopra e a sinistra della griglia.')]
        if self.modal in ('feedback', 'hint'):
            frame = self.current_frame()
            parts = [('La missione', m.objective)]
            if frame:
                parts.append((f'Passaggio {self.frame_index + 1} · {frame.phase}', frame.message))
            if self.modal == 'hint' or (self.easy and frame and frame.phase == 'Da rivedere'):
                level = max(1, self.hint_level)
                parts.extend((f'Suggerimento {i + 1}', hint) for i, hint in enumerate(m.hints[:level]))
                parts.append(('Il concetto da ricordare', m.concept))
            if self.modal == 'hint' and self.hint_level >= 4:
                parts.append(('Una possibile soluzione · ' + self.language, m.solution(self.language)))
                parts.append(('Ora ricostruiscila', 'Leggi la soluzione e confrontala con il tuo programma. Chiudi questa scheda e correggi il tuo tentativo: la soluzione non viene inserita automaticamente e la missione non viene segnata come completata.'))
            if frame:
                parts.append(('Tutte le variabili', '\n'.join(f'{key} = {value}' for key, value in frame.variables.items())))
            return 'Un aiuto per ragionare' if self.modal == 'hint' else 'Osserva questo passaggio', parts
        if self.modal_tab == 'Confronto':
            return 'Tre cicli, tre modi di ripetere', COMPARISON
        if self.modal_tab == 'La missione':
            return 'Dall’idea al robot', [('Il tuo obiettivo', m.objective), ('Il ragionamento', m.concept), ('Il programma · ' + self.language, m.solution(self.language)), ('Mentre osservi', 'Segui la riga illuminata e leggi il riquadro sotto la griglia. Distingui una ripetizione completa da una singola azione. Il pulsante Un passo mostra anche i controlli: il robot si muove solo quando viene eseguito avanza().')]
        lesson = LESSONS[m.loop]
        return LOOPS[m.loop] + ' · ' + lesson['title'], [('Inizia da qui', lesson['intro'])] + list(lesson['sections'])

    def draw_modal(self):
        overlay = pygame.Surface(SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.canvas.blit(overlay, (0, 0))
        self.buttons = []
        self.drawing_modal = True
        s, c = self.canvas, self.c
        panel(s, pygame.Rect(180, 105, 1080, 710), c['panel'], c['border'], 22)
        title, sections = self.modal_content()
        text(s, title, (213, 130), 29, c['text'], True)
        self.button('close', 'Chiudi ×', (1092, 130, 137, 40), size=16)
        text(s, 'Leggi con calma: durante la lettura il robot resta fermo.', (215, 181), 17, c['muted'])
        if self.modal == 'guide':
            for i, tab in enumerate(('Spiegazione', 'La missione', 'Confronto')):
                self.button('tab:' + tab, tab, (214 + i * 236, 216, 223, 40), self.modal_tab == tab, size=17)
        if self.modal == 'condition':
            from engine import format_expr
            for i, cond in enumerate(CONDITIONS):
                label = format_expr(cond, self.language)
                self.button('choose_condition:' + str(i), label, (218 + (i % 2) * 506, 246 + (i // 2) * 94, 488, 74), self.block_data['condition'] == cond, size=20)
            text(s, 'La condizione deve essere vera quando vuoi RIPETERE il corpo.', (219, 682), 20, c['accent'], True)
        else:
            viewport = pygame.Rect(214, 280 if self.modal == 'guide' else 226, 961, 443 if self.modal == 'guide' else 497)
            size = self.state['size'] + 1
            layout, total = [], 0
            for heading, value in sections:
                layout.append((total, heading, True, False, 23))
                total += 38
                code = heading in ('Il programma · ' + self.language, 'Una possibile soluzione · ' + self.language)
                row_size = size
                if code:
                    while row_size > 14 and any(font(row_size, mono=True).size(row)[0] > viewport.width - 12 for row in value.splitlines()):
                        row_size -= 1
                content_lines = value.splitlines() if code else lines(value, viewport.width - 12, size)
                for line in content_lines:
                    layout.append((total, line, False, code, row_size))
                    total += font(row_size, mono=code).get_linesize() + 6
                total += 27
            self.modal_max = max(0, total - viewport.height)
            self.modal_scroll = max(0, min(self.modal_scroll, self.modal_max))
            clip = s.get_clip()
            s.set_clip(viewport)
            for y, value, heading, code, row_size in layout:
                pos = viewport.y + y - self.modal_scroll
                if viewport.y - 45 < pos < viewport.bottom:
                    text(s, value, (viewport.x, pos), row_size, c['mint'] if heading else c['accent'] if code else c['text'], heading, mono=code)
            s.set_clip(clip)
            if self.modal_max:
                track = pygame.Rect(1205, viewport.y + 54, 5, viewport.height - 108)
                panel(s, track, c['card'], radius=2)
                thumb = max(30, track.height * viewport.height / total)
                y = track.y + (track.height - thumb) * self.modal_scroll / self.modal_max
                panel(s, pygame.Rect(track.x, y, 5, thumb), c['mint'], radius=2)
                self.button('scroll:-200', '↑', (1188, viewport.y, 39, 36), enabled=self.modal_scroll > 0, size=21)
                self.button('scroll:200', '↓', (1188, viewport.bottom - 36, 39, 36), enabled=self.modal_scroll < self.modal_max, size=21)
        text(s, 'Rotella o ↑ ↓ per scorrere  ·  Esc per tornare', (215, 778), 14, c['muted'])
        if self.modal == 'hint':
            self.button('more_hint', 'Mostra soluzione' if self.hint_level == 3 else 'Altro suggerimento', (960, 756, 268, 40), enabled=self.hint_level < 4, accent=c['accent'], size=16)
        elif self.modal == 'reset':
            self.button('confirm_reset', 'Sì, ricomincia il codice', (944, 756, 285, 40), accent=c['danger'])
        elif self.modal == 'success':
            self.button('next_mission', 'Prossima missione →', (952, 756, 276, 40), accent=c['mint'])
        self.drawing_modal = False

    def draw(self):
        s, c = self.canvas, self.c
        s.fill(c['bg'])
        for x in range(25, SIZE[0], 40):
            for y in range(108, SIZE[1], 40):
                pygame.draw.circle(s, c['grid'], (x, y), 1)
        self.buttons = []
        self.header()
        {'welcome': self.welcome, 'catalog': self.catalog, 'lab': self.lab, 'settings': self.settings}[self.page]()
        if self.notice and not self.modal:
            self.button('notice', 'Informazione sul salvataggio o sulla bozza', (466, 857, 508, 25), accent=c['danger'], size=12)
        if self.modal:
            self.draw_modal()
        text(s, 'Realizzato dal Prof. Barillà Francesco', (720, 889), 13, c['muted'], anchor='center')
        w, h = self.screen.get_size()
        scale = min(w / SIZE[0], h / SIZE[1])
        target = (round(SIZE[0] * scale), round(SIZE[1] * scale))
        self.screen.fill('#000000')
        self.screen.blit(pygame.transform.smoothscale(s, target), ((w - target[0]) // 2, (h - target[1]) // 2))
        kind = pygame.SYSTEM_CURSOR_ARROW
        if any(enabled and rect.collidepoint(self.pointer) for _, rect, enabled in self.buttons):
            kind = pygame.SYSTEM_CURSOR_HAND
        elif self.page == 'lab' and not self.modal and self.mode == 'game' and not self.easy and self.editor.rect.collidepoint(self.pointer):
            kind = pygame.SYSTEM_CURSOR_IBEAM
        if kind != self.cursor:
            try:
                pygame.mouse.set_cursor(kind)
            except pygame.error:
                pass
            self.cursor = kind

    def run_program(self, playing=True):
        self.editor.focus = False
        self.persist()
        self.result = Interpreter(self.mission, self.language).run(self.editor.value)
        self.frame_index = 0
        self.playing = playing
        self.elapsed = 0
        self.motion = 1
        if self.result.error_line and len(self.result.frames) <= 2:
            self.frame_index = len(self.result.frames) - 1
            self.playing = False
            self.shake = 1
            self.follow_line()

    def follow_line(self):
        frame = self.current_frame()
        if frame:
            self.editor.scroll = max(0, frame.line - 3)
            self.editor.xscroll = 0

    def advance(self):
        if not self.result or self.frame_index >= len(self.result.frames) - 1:
            return
        self.frame_index += 1
        self.motion = 0
        self.follow_line()
        if self.frame_index == len(self.result.frames) - 1:
            self.playing = False
            if self.result.success and self.mode == 'game':
                key = self.draft_key()
                if key not in self.state['completed']:
                    self.state['completed'].append(key)
                    self.persist()
                self.open_modal('success')
            elif not self.result.success:
                self.shake = 1

    def action(self, key):
        if key == 'close':
            self.modal = None
            self.key_focus = None
        elif key.startswith('scroll:'):
            self.modal_scroll = max(0, min(self.modal_max, self.modal_scroll + int(key.split(':')[1])))
        elif key.startswith('tab:'):
            self.modal_tab = key.split(':')[1]
            self.modal_scroll = 0
        elif key.startswith('choose_condition:'):
            self.block_data['condition'] = CONDITIONS[int(key.split(':')[1])]
            self.modal = None
            self.sync_blocks()
        elif key == 'more_hint':
            self.hint_level = min(4, self.hint_level + 1)
            self.modal_scroll = 0
        elif key == 'confirm_reset':
            self.editor.set(self.mission.starter(self.language, self.difficulty))
            self.invalidate()
            self.modal = None
            self.persist()
        elif key == 'next_mission':
            self.modal = None
            index = MISSIONS.index(self.mission)
            if index + 1 < len(MISSIONS):
                self.open_mission(MISSIONS[index + 1].key)
            else:
                self.navigate('catalog')
        elif key in ('guide', 'help', 'objective', 'feedback', 'condition', 'notice'):
            self.open_modal(key)
        elif key == 'comparison':
            self.open_modal('guide')
            self.modal_tab = 'Confronto'
        elif key == 'reset_code':
            self.open_modal('reset')
        elif key == 'hint':
            self.hint_level = max(1, self.hint_level)
            self.open_modal('hint')
        elif key == 'settings':
            if self.page != 'settings':
                self.return_page = self.page
                self.navigate('settings')
        elif key == 'return':
            self.navigate(self.return_page)
        elif key == 'home':
            self.navigate('welcome')
        elif key == 'catalog':
            self.navigate('catalog')
        elif key.startswith('mode:'):
            self.mode = key.split(':')[1]
            self.navigate('catalog')
        elif key.startswith('filter:'):
            self.filter = key.split(':')[1]
        elif key.startswith('mission:'):
            self.open_mission(key.split(':')[1])
        elif key.startswith('lang:'):
            self.set_language(key.split(':')[1])
        elif key.startswith('diff:'):
            self.set_difficulty(key.split(':')[1])
        elif key.startswith('theme:'):
            self.state['theme'] = key.split(':')[1]
            self.c = palette(self.state['theme'])
            self.persist()
        elif key.startswith('size:'):
            self.state['size'] = {'Compatto': 17, 'Grande': 19, 'Proiezione': 21}[key.split(':')[1]]
            self.persist()
        elif key.startswith('velocity:'):
            self.state['speed'] = float(key.split(':')[1].rstrip('×'))
            self.persist()
        elif key == 'speed':
            values = (.5, 1, 2, 3)
            self.state['speed'] = values[(values.index(self.state['speed']) + 1) % len(values)]
            self.persist()
        elif key == 'fullscreen':
            if not self.fullscreen:
                self.window_size = self.screen.get_size()
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
            self.fullscreen = not self.fullscreen
        elif key == 'try_game':
            self.navigate('catalog')
            self.mode = 'game'
            self.open_mission(self.mission.key)
        elif key == 'run':
            if self.playing:
                self.playing = False
            elif self.result and self.frame_index < len(self.result.frames) - 1:
                self.playing = True
            else:
                self.run_program()
        elif key == 'step':
            self.playing = False
            if not self.result:
                self.run_program(False)
            self.advance()
        elif key == 'back':
            if self.result:
                self.playing = False
                self.frame_index = max(0, self.frame_index - 1)
                self.motion = 1
                self.follow_line()
        elif key == 'restart':
            self.invalidate()
        elif key.startswith('count:'):
            self.block_data['count'] = max(0, min(20, self.block_data['count'] + int(key.split(':')[1])))
            self.sync_blocks()
        elif key.startswith('add:'):
            if len(self.block_data['actions']) < 12:
                self.block_data['actions'].append(key.split(':')[1])
                self.body_scroll = max(0, len(self.block_data['actions']) - 4)
                self.sync_blocks()
        elif key.startswith(('up:', 'down:', 'remove:')):
            operation, index = key.split(':')
            index = int(index)
            actions = self.block_data['actions']
            if operation == 'remove':
                actions.pop(index)
            else:
                other = index + (-1 if operation == 'up' else 1)
                if 0 <= other < len(actions):
                    actions[index], actions[other] = actions[other], actions[index]
            self.sync_blocks()

    def event(self, event):
        if event.type == pygame.QUIT:
            self.persist()
            self.alive = False
            return
        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.screen = pygame.display.set_mode((max(960, event.w), max(600, event.h)), pygame.RESIZABLE)
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.pointer = self.logical(event.pos)
        if event.type == pygame.MOUSEMOTION and self.pressed and self.easy and not self.modal:
            if self.pressed.startswith(('add:', 'body:')) and math.dist(self.pointer, self.press_pos) > 7:
                kind, value = self.pressed.split(':')
                self.drag = ('add', value) if kind == 'add' else ('move', int(value))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.key_focus = None
            self.pressed = next((key for key, r, enabled in reversed(self.buttons) if enabled and r.collidepoint(self.pointer)), None)
            self.press_pos = self.pointer
            if not self.modal and self.page == 'lab':
                self.editor.focus = not self.easy and self.mode == 'game' and self.editor.rect.collidepoint(self.pointer)
                if self.editor.focus:
                    self.playing = False
                    self.editor.click(self.pointer, bool(pygame.key.get_mods() & pygame.KMOD_SHIFT))
                    pygame.key.start_text_input()
                else:
                    pygame.key.stop_text_input()
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag:
                if self.body_rect.collidepoint(self.pointer):
                    actions = self.block_data['actions']
                    index = min(len(actions), max(0, int((self.pointer[1] - 430 + 19) // 38)) + self.body_scroll)
                    kind, value = self.drag
                    if kind == 'move':
                        name = actions.pop(value)
                        if index > value:
                            index -= 1
                        actions.insert(index, name)
                    elif len(actions) < 12:
                        actions.insert(index, value)
                    self.sync_blocks()
                self.drag = None
            elif self.pressed:
                if any(key == self.pressed and enabled and r.collidepoint(self.pointer) for key, r, enabled in self.buttons):
                    self.action(self.pressed)
            self.pressed = None
        if event.type == pygame.MOUSEWHEEL:
            if self.modal:
                self.modal_scroll = max(0, min(self.modal_max, self.modal_scroll - event.y * 70))
            elif self.page == 'lab':
                if self.easy and self.body_rect.collidepoint(self.pointer):
                    self.body_scroll = max(0, min(max(0, len(self.block_data['actions']) - 4), self.body_scroll - event.y))
                elif self.editor.rect.collidepoint(self.pointer):
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        self.editor.xscroll = max(0, self.editor.xscroll - event.y * 4)
                    else:
                        self.editor.scroll = max(0, self.editor.scroll - event.y * 3)
        if event.type == pygame.TEXTINPUT and self.page == 'lab' and self.editor.focus and not self.modal:
            if self.editor.replace(event.text):
                self.invalidate()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.action('fullscreen')
            elif event.key == pygame.K_ESCAPE:
                if self.modal:
                    self.modal = None
                elif self.page == 'settings':
                    self.navigate(self.return_page)
                elif self.editor.focus:
                    self.editor.focus = False
                    pygame.key.stop_text_input()
                elif self.page == 'lab':
                    self.navigate('catalog')
                else:
                    self.navigate('welcome')
            elif self.modal and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END):
                change = {pygame.K_UP: -50, pygame.K_DOWN: 50, pygame.K_PAGEUP: -380, pygame.K_PAGEDOWN: 380, pygame.K_HOME: -100000, pygame.K_END: 100000}[event.key]
                self.modal_scroll = max(0, min(self.modal_max, self.modal_scroll + change))
            elif self.page == 'lab' and self.editor.focus and not self.modal:
                if self.editor.key(event):
                    self.invalidate()
            elif event.key == pygame.K_TAB:
                enabled = [key for key, _, active in self.buttons if active]
                if enabled:
                    i = enabled.index(self.key_focus) if self.key_focus in enabled else -1
                    self.key_focus = enabled[(i + (-1 if event.mod & pygame.KMOD_SHIFT else 1)) % len(enabled)]
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.key_focus:
                if any(key == self.key_focus and enabled for key, _, enabled in self.buttons):
                    self.action(self.key_focus)
            elif event.key == pygame.K_SPACE and self.page == 'lab' and not self.modal:
                self.action('run')

    def update(self, dt):
        self.time += dt
        if not self.modal and self.page == 'lab':
            self.motion = min(1, self.motion + dt * 4 * self.state['speed'])
            self.shake = max(0, self.shake - dt * 1.7)
            if self.playing:
                self.elapsed += dt
                if self.elapsed >= .85 / self.state['speed']:
                    self.elapsed = 0
                    self.advance()
        if self.dirty_at is not None and self.time - self.dirty_at > .7:
            self.persist()


def smoke(report):
    screen = pygame.display.set_mode(SIZE)
    app = App(screen, saving=False)
    count = 0
    for theme in THEMES:
        app.state['theme'] = theme
        app.c = palette(theme)
        for page in ('welcome', 'catalog', 'settings'):
            app.page = page
            app.draw()
        for lang in LANGUAGES:
            app.state['language'] = lang
            for mission in MISSIONS:
                app.mode = 'learn'
                app.open_mission(mission.key)
                app.draw()
                app.modal = None
                app.run_program(False)
                assert app.result.success, (lang, mission.key, app.result.message)
                app.frame_index = len(app.result.frames) - 1
                app.draw()
                count += 1
                for difficulty in DIFFICULTIES:
                    app.mode = 'game'
                    app.state['difficulty'] = difficulty
                    app.open_mission(mission.key)
                    app.draw()
        for kind in ('guide', 'help', 'hint', 'objective', 'feedback', 'condition', 'reset'):
            app.open_modal(kind)
            app.draw()
            app.modal_scroll = app.modal_max
            app.draw()
            app.modal = None
    Path(report).write_text(json.dumps(dict(ok=True, solution_checks=count, languages=list(LANGUAGES), missions=len(MISSIONS), themes=len(THEMES))), encoding='utf-8')


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    pygame.key.set_repeat(450, 35)
    if '--smoke-test' in sys.argv:
        smoke(sys.argv[sys.argv.index('--smoke-test') + 1])
        pygame.quit()
        return
    screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    icon = pygame.Surface((64, 64), pygame.SRCALPHA)
    robot(icon, (32, 36), .7)
    pygame.display.set_icon(icon)
    app = App(screen)
    clock = pygame.time.Clock()
    while app.alive:
        dt = min(.1, clock.tick(60) / 1000)
        app.pointer = app.logical(pygame.mouse.get_pos())
        app.draw()
        for event in pygame.event.get():
            app.event(event)
        app.update(dt)
        pygame.display.flip()
    pygame.quit()


if __name__ == '__main__':
    main()
