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
from guidance import PREDICTIONS, first_gap, meaningful_code, writing_issue, writing_sections, misconceptions
from guided_ui import GuidedUI
import storage
from ui import SIZE, THEMES, Editor, board, font, lines, mix, palette, panel, robot, text, wrap

TITLE = 'Il laboratorio dei robot'


class App(GuidedUI):
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
        self.trace_editor = Editor()
        self.trace_return = None
        self.trace_only = False
        self.verification = None
        self.prediction_attempt = None
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
        self.verification = None
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
        self.prediction_attempt = None
        self.block_data = copy.deepcopy(self.state['blocks'].get(key, dict(count=3, condition=CONDITIONS[0], actions=[])))
        if self.mode == 'learn':
            self.editor.set(self.mission.solution(self.language))
        elif self.easy:
            self.editor.set(self.block_code())
        else:
            self.editor.set(self.state['drafts'].get(self.draft_key(), self.mission.starter(self.language, self.difficulty)))
        self.invalidate()
        self.persist()

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
        color = self.c['text'] if enabled or selected else self.c['muted']
        if selected and accent == self.c['mint'] and enabled:
            panel(self.canvas, r, mix(accent, self.c['text'], .12) if r.collidepoint(self.pointer) else accent, radius=12)
            color = self.c['bg']
        while font(size, True).size(label)[0] > r.width - 16 and size > 12:
            size -= 1
        text(self.canvas, label, r.center, size, color, True, 'center')

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
        if self.modal == 'writing':
            return 'Cosa fare con i blocchi' if self.easy else 'Cosa devo scrivere?', writing_sections(m, self.language, self.editor.value, self.easy)
        if self.modal == 'misconceptions':
            return 'Equivoci sui cicli', misconceptions(m)
        if self.modal == 'code':
            return 'Il codice da osservare', [('Il programma · ' + self.language, self.editor.value)]
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
            return 'Dall’idea al robot', [('Il tuo obiettivo', m.objective), ('Il ragionamento', m.concept), ('Il programma · ' + self.language, m.solution(self.language)), ('Mentre osservi', 'Segui la riga illuminata e leggi il riquadro sotto la griglia. Distingui una ripetizione completa da una singola azione. Il pulsante Un passaggio mostra anche i controlli: il robot si muove solo quando viene eseguito avanza().')]
        lesson = LESSONS[m.loop]
        return LOOPS[m.loop] + ' · ' + lesson['title'], [('Inizia da qui', lesson['intro'])] + list(lesson['sections'])

    def draw_modal(self):
        if self.modal == 'trace':
            self.draw_trace()
            return
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
                code = heading in ('Il programma · ' + self.language, 'Una possibile soluzione · ' + self.language, 'Esempio di forma · ' + self.language)
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
        self.trace_only = self.modal == 'trace'
        issue = writing_issue(self.mission, self.editor.value, self.language, self.easy) if self.mode == 'game' else ''
        if self.easy and not self.block_data['actions']:
            issue = 'Il corpo è vuoto. Aggiungi almeno un comando con i pulsanti +, poi controlla di nuovo i blocchi.'
        if issue:
            self.result.message = self.result.frames[-1].message = issue
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
            editor = self.trace_editor if self.modal == 'trace' else self.editor
            editor.scroll = max(0, frame.line - 3)
            editor.xscroll = 0

    def verify_program(self):
        self.run_program(False)
        self.verification = self.result
        self.frame_index = len(self.result.frames) - 1
        self.motion = 1
        if self.result.success:
            key = self.draft_key()
            if key not in self.state['completed']:
                self.state['completed'].append(key)
                self.persist()

    def focus_code(self):
        gap = first_gap(self.editor.value, self.language)
        self.playing = False
        self.editor.focus = True
        if gap:
            self.editor.anchor, self.editor.caret = gap.start, gap.end
        else:
            self.editor.anchor = self.editor.caret = len(self.editor.value)
            if self.editor.value and not meaningful_code(self.editor.value) and not self.editor.value.endswith('\n'):
                self.editor.replace('\n')
                self.invalidate()
        self.editor.reveal()
        pygame.key.start_text_input()

    def advance(self):
        if not self.result or self.frame_index >= len(self.result.frames) - 1:
            return
        self.frame_index += 1
        self.motion = 0
        self.follow_line()
        if self.frame_index == len(self.result.frames) - 1:
            self.playing = False
            if self.result.success and self.mode == 'game' and not self.trace_only:
                key = self.draft_key()
                if key not in self.state['completed']:
                    self.state['completed'].append(key)
                    self.persist()
                self.verification = self.result
            elif not self.result.success:
                self.shake = 1

    def action(self, key):
        if key == 'close':
            if self.modal == 'trace':
                self.result, self.frame_index, self.motion = self.trace_return
                self.trace_return = None
                self.trace_only = False
                self.playing = False
            self.modal = None
            self.key_focus = None
        elif key == 'focus_code':
            self.focus_code()
        elif key == 'verify':
            self.verify_program()
        elif key == 'trace':
            self.trace_return = (self.result, self.frame_index, self.motion)
            self.trace_editor.set(self.editor.value)
            self.open_modal('trace')
            self.run_program(False)
            self.trace_only = True
        elif key.startswith('predict:'):
            self.prediction_attempt = int(key.split(':')[1])
            self.invalidate()
        elif key == 'learn_start':
            if self.prediction_attempt == PREDICTIONS[self.mission.key].correct:
                self.run_program(True)
        elif key in ('writing', 'misconceptions', 'code'):
            self.open_modal(key)
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
                    index = min(len(actions), max(0, int((self.pointer[1] - self.body_rect.y - 8 + 19) // 38)) + self.body_scroll)
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
            if self.modal == 'trace' and self.trace_editor.rect.collidepoint(self.pointer):
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self.trace_editor.xscroll = max(0, self.trace_editor.xscroll - event.y * 4)
                else:
                    self.trace_editor.scroll = max(0, self.trace_editor.scroll - event.y * 3)
            elif self.modal:
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
                    self.action('close')
                elif self.page == 'settings':
                    self.navigate(self.return_page)
                elif self.editor.focus:
                    self.editor.focus = False
                    pygame.key.stop_text_input()
                elif self.page == 'lab':
                    self.navigate('catalog')
                else:
                    self.navigate('welcome')
            elif not self.modal and self.page == 'lab' and self.mode == 'game' and event.key == pygame.K_RETURN and event.mod & pygame.KMOD_CTRL:
                self.verify_program()
            elif self.modal == 'trace' and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.trace_editor.xscroll = max(0, self.trace_editor.xscroll + (-4 if event.key == pygame.K_LEFT else 4))
                else:
                    self.trace_editor.scroll = max(0, self.trace_editor.scroll + (-3 if event.key == pygame.K_UP else 3))
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
                if self.mode == 'learn' and self.prediction_attempt == PREDICTIONS[self.mission.key].correct:
                    self.action('run')

    def update(self, dt):
        self.time += dt
        if (not self.modal or self.modal == 'trace') and self.page == 'lab':
            self.motion = min(1, self.motion + dt * 4 * self.state['speed'])
            self.shake = max(0, self.shake - dt * 1.7)
            if self.playing:
                self.elapsed += dt
                if self.elapsed >= .85 / self.state['speed']:
                    self.elapsed = 0
                    self.advance()
        if self.dirty_at is not None and self.time - self.dirty_at > .7:
            self.persist()


def smoke(report, screenshots=None):
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
                app.prediction_attempt = PREDICTIONS[mission.key].correct
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
        for kind in ('guide', 'help', 'hint', 'objective', 'feedback', 'condition', 'reset', 'writing', 'misconceptions'):
            app.open_modal(kind)
            app.draw()
            app.modal_scroll = app.modal_max
            app.draw()
            app.modal = None
    if screenshots:
        folder = Path(screenshots)
        folder.mkdir(parents=True, exist_ok=True)
        app = App(screen, saving=False)
        app.state = storage.defaults()
        app.c = palette('Notte')
        def capture(name):
            app.pointer = (-100, -100)
            app.draw()
            pygame.image.save(app.canvas, folder / name)
        capture('01-home.png')
        app.navigate('catalog')
        capture('02-missioni.png')
        app.open_mission('for_batterie')
        capture('03-prevedi-i-giri.png')
        app.action('predict:0')
        capture('04-giri-diversi-dalle-azioni.png')
        app.open_mission('while_zero')
        app.action('predict:0')
        app.action('learn_start')
        while app.frame_index < len(app.result.frames) - 1:
            app.advance()
        capture('05-zero-passi-corretto.png')
        app.mode = 'game'
        app.state['difficulty'] = 'Facile'
        app.open_mission('for_batterie')
        app.action('add:avanza')
        app.action('add:raccogli')
        capture('06-costruisci-i-blocchi.png')
        app.set_difficulty('Medio')
        app.action('focus_code')
        capture('07-completa-il-numero.png')
        app.open_mission('do_segnale')
        app.action('focus_code')
        capture('08-completa-il-comando.png')
        app.set_difficulty('Difficile')
        capture('09-scrivi-qui.png')
        app.action('writing')
        app.modal_scroll = 250
        capture('10-guida-do-while-python.png')
        app.action('close')
        app.open_mission('for_pontile')
        app.editor.set('for i in range(4):\n    avanza()')
        app.action('verify')
        capture('11-risultato-da-correggere.png')
        app.action('trace')
        app.action('step')
        app.action('step')
        capture('12-esecuzione-passo-passo.png')
        app.action('close')
        app.action('misconceptions')
        capture('13-equivoci-da-evitare.png')
        app.action('close')
        app.editor.set(app.mission.solution(app.language))
        app.action('verify')
        capture('14-missione-completata.png')
    Path(report).write_text(json.dumps(dict(ok=True, solution_checks=count, languages=list(LANGUAGES), missions=len(MISSIONS), themes=len(THEMES))), encoding='utf-8')


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    pygame.key.set_repeat(450, 35)
    if '--smoke-test' in sys.argv:
        smoke(sys.argv[sys.argv.index('--smoke-test') + 1], sys.argv[sys.argv.index('--screenshots') + 1] if '--screenshots' in sys.argv else None)
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
