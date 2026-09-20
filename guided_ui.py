"""Clear working areas for programming, prediction and execution."""
import pygame
from engine import COMMANDS, LANGUAGES, format_expr, parse
from guidance import PREDICTIONS, first_gap, result_rows, writing_task
from missions import DIFFICULTIES, LOOPS
from ui import SIZE, board, font, lines, mix, panel, text, wrap


class GuidedUI:
    def brief(self, value, rect, size=18, color=None, bold=False):
        """Keep a summary readable; long details remain in the explanation sheet."""
        rect = pygame.Rect(rect)
        rows = lines(value, rect.width, size, bold)
        while size > 16 and len(rows) * (font(size, bold).get_linesize() + 4) > rect.height:
            size -= 1
            rows = lines(value, rect.width, size, bold)
        limit = max(1, rect.height // (font(size, bold).get_linesize() + 4))
        if len(rows) > limit:
            rows = list(rows[:limit])
            rows[-1] = rows[-1].rstrip(' .') + '…'
        wrap(self.canvas, '\n'.join(rows), rect, size, color or self.c['text'], bold)

    def lab_header(self):
        s, c, m = self.canvas, self.c, self.mission
        self.button('catalog', '← Missioni', (40, 108, 145, 40), size=16)
        text(s, m.title, (202, 107), 31, c['text'], True)
        text(s, 'CICLO ' + LOOPS[m.loop].upper(), (1400, 120), 16, c['accent'], True, 'topright')
        self.brief(m.objective, (42, 162, 1356, 49), 19)
        for i, language in enumerate(LANGUAGES):
            self.button('lang:' + language, language, (40 + i * 143, 220, 132, 37), self.language == language, size=16)
        self.button('help', 'Comandi e codice', (619, 220, 174, 37), size=15)
        if self.mode == 'game':
            for i, difficulty in enumerate(DIFFICULTIES):
                label = difficulty + ' · ' + ('blocchi', 'completa', 'scrivi')[i]
                self.button('diff:' + difficulty, label, (805 + i * 202, 220, 192, 37), self.difficulty == difficulty, size=16)
        else:
            text(s, 'Leggi → scegli una risposta → osserva il perché', (1400, 230), 18, c['muted'], anchor='topright')

    def lab(self):
        self.lab_header()
        panel(self.canvas, pygame.Rect(40, 276, 790, 574), self.c['panel'])
        panel(self.canvas, pygame.Rect(850, 276, 550, 574), self.c['panel'])
        if self.mode == 'learn':
            self.learn_lab()
        else:
            self.game_lab()
        if self.drag:
            name = self.drag[1] if self.drag[0] == 'add' else self.block_data['actions'][self.drag[1]]
            r = pygame.Rect(self.pointer[0] + 12, self.pointer[1] - 20, 211, 37)
            panel(self.canvas, r, self.c['card'], self.c['mint'], 9)
            text(self.canvas, COMMANDS[name], r.center, 15, self.c['text'], True, 'center')

    def game_lab(self):
        s, c = self.canvas, self.c
        title = 'COSTRUISCI IL PROGRAMMA' if self.easy else 'COMPLETA IL CODICE' if self.difficulty == 'Medio' else 'SCRIVI IL PROGRAMMA'
        text(s, '1  ' + title, (58, 295), 19, c['mint'], True)
        if self.easy:
            self.brief('Scegli quante volte ripetere, poi aggiungi i messaggi da stampare.' if self.mission.loop == 'for' else 'Scegli la condizione e i messaggi. Le letture sono incluse: Codice dei blocchi le mostra.', (58, 338, 750, 50), 19)
            self.blocks()
        else:
            gap = first_gap(self.editor.value, self.language)
            self.button('focus_code', 'Completa i ???' if gap else 'Scrivi qui', (583, 285, 228, 41), True, c['mint'], size=18)
            task, instruction = writing_task(self.mission, self.editor.value, self.language)
            self.brief(task, (58, 343, 750, 52), 19)
            self.brief(instruction, (58, 398, 750, 43), 17, c['muted'])
            self.editor.draw(s, pygame.Rect(58, 454, 754, 248), c, error=self.verification.error_line if self.verification else 0, tick=self.time, size=self.state['size'])
            if not self.editor.value:
                text(s, 'Clicca qui e scrivi il ciclo della missione…', (109, 470), 18, c['muted'])
            text(s, 'Stai scrivendo' if self.editor.focus else 'Premi il pulsante in alto per iniziare a scrivere', (58, 714), 16, c['accent'])
            text(s, 'Invio: nuova riga · Tab: rientro · Ctrl+Invio: controlla', (58, 741), 16, c['muted'])
            self.button('reset_code', 'Ricomincia', (681, 732, 131, 34), size=15)
        self.button('writing', 'Come uso i blocchi?' if self.easy else 'Cosa devo scrivere?', (58, 793, 240, 39), size=16)
        self.button('code' if self.easy else 'hint', 'Codice dei blocchi' if self.easy else 'Suggerimento', (311, 793, 244, 39), size=16)
        self.button('misconceptions', 'Equivoci da evitare', (568, 793, 244, 39), size=16)
        self.game_result()

    def blocks(self):
        c, s, m = self.c, self.canvas, self.mission
        if m.loop == 'for':
            text(s, 'RIPETI IL CORPO', (58, 411), 16, c['accent'], True)
            self.button('count:-1', '−', (314, 400, 48, 38), enabled=self.block_data['count'] > 0, size=24)
            text(s, self.block_data['count'], (413, 419), 25, c['text'], True, 'center')
            self.button('count:1', '+', (464, 400, 48, 38), enabled=self.block_data['count'] < 20, size=24)
            text(s, 'VOLTE', (534, 411), 16, c['muted'], True)
        else:
            text(s, 'RIPETI MENTRE', (58, 411), 16, c['accent'], True)
            self.button('condition', format_expr(self.block_data['condition'], self.language) + ' ▾', (264, 400, 548, 38), size=18)
        text(s, 'FAI CLIC SU + PER AGGIUNGERE UN COMANDO', (58, 456), 15, c['muted'], True)
        for i, (name, label) in enumerate(COMMANDS.items()):
            self.button('add:' + name, '+ ' + label, (58 + (i % 3) * 254, 485 + (i // 3) * 38, 245, 33), enabled=len(self.block_data['actions']) < 12, size=16)
        self.body_rect = pygame.Rect(58, 574, 754, 174)
        panel(s, self.body_rect, c['bg'], c['mint'] if self.drag and self.body_rect.collidepoint(self.pointer) else c['border'], 10)
        actions = self.block_data['actions']
        self.body_scroll = min(self.body_scroll, max(0, len(actions) - 4))
        if not actions:
            self.brief('Il corpo è ancora vuoto. Aggiungi qui le azioni da ripetere a ogni giro, nell’ordine giusto. Puoi cliccare i pulsanti + oppure trascinarli qui.', (80, 599, 708, 116), 20, c['muted'])
        for i in range(self.body_scroll, min(len(actions), self.body_scroll + 4)):
            y = self.body_rect.y + 8 + (i - self.body_scroll) * 38
            self.button('body:' + str(i), f'{i + 1}.  {COMMANDS[actions[i]]}', (70, y, 543, 32), size=17)
            self.button('up:' + str(i), '↑', (623, y, 49, 32), enabled=i > 0, size=20)
            self.button('down:' + str(i), '↓', (680, y, 49, 32), enabled=i < len(actions) - 1, size=20)
            self.button('remove:' + str(i), '×', (738, y, 61, 32), size=21)
        if self.drag and self.body_rect.collidepoint(self.pointer):
            row = min(4, max(0, int((self.pointer[1] - self.body_rect.y - 8 + 19) // 38)))
            y = min(self.body_rect.bottom - 5, self.body_rect.y + 8 + row * 38)
            pygame.draw.line(s, c['mint'], (72, y), (797, y), 3)
        text(s, 'Ordine: dall’alto in basso · ↑ ↓ spostano · × elimina' if len(actions) <= 4 else f'{self.body_scroll + 1}–{min(len(actions), self.body_scroll + 4)} di {len(actions)} · rotella per scorrere il corpo', (58, 758), 16, c['muted'])

    def scene(self, label):
        frame = self.current_frame()
        world = frame.world if frame else self.initial_world()
        previous = self.result.frames[self.frame_index - 1].world if self.result and self.frame_index > 0 else None
        text(self.canvas, label, (868, 332), 16, self.c['muted'])
        board(self.canvas, pygame.Rect(868, 362, 514, 200), self.mission, world, self.c, self.time, previous, self.motion, self.shake * 5, focus=True)

    def game_result(self):
        s, c, result = self.canvas, self.c, self.verification
        text(s, '2  CONTROLLA IL RISULTATO', (868, 295), 19, c['mint'], True)
        if self.easy:
            self.button('hint', 'Aiuto', (1278, 286, 104, 36), accent=c['accent'], size=16)
        self.scene(f'Finale · Giri {result.frames[-1].iterations} · Passi {result.frames[-1].world.steps}' if result else 'Partenza · verde = traguardo')
        if result:
            color = c['mint'] if result.success else c['danger']
            text(s, 'Missione completata' if result.success else 'Da correggere', (868, 577), 25, color, True)
            self.button('feedback', 'Perché? →', (1248, 574, 133, 36), accent=color, size=16)
            self.brief(result.message, (868, 619, 514, 55), 18)
            for i, (required, actual, ok) in enumerate(result_rows(self.mission, result)):
                self.brief(required, (868, 683 + i * 30, 327, 26), 16, c['muted'])
                self.brief(('OK · ' if ok else 'NO · ') + actual, (1198, 683 + i * 30, 184, 26), 16, c['mint'] if ok else c['danger'], True)
        else:
            text(s, 'Il robot aspetta il tuo programma', (868, 583), 22, c['text'], True)
            self.brief('Lavora nel pannello 1. Il pulsante qui sotto prova il programma e ti dice subito se la missione è riuscita.', (868, 624, 514, 86), 19)
            self.brief('Ogni controllo riparte dalla scena iniziale. Per seguire ogni riga usa Passo passo.', (868, 718, 514, 63), 17, c['muted'])
        self.button('verify', 'Controlla i blocchi' if self.easy else 'Controlla il mio programma', (868, 797, 331, 39), True, c['mint'], size=17)
        self.button('trace', 'Passo passo →', (1210, 797, 172, 39), size=16)

    def learn_lab(self):
        s, c, m = self.canvas, self.c, self.mission
        question = PREDICTIONS[m.key]
        text(s, '1  LEGGI IL CODICE E PREVEDI', (58, 295), 19, c['mint'], True)
        text(s, 'Il codice è già pronto. Leggilo, poi scegli una risposta sotto.', (58, 336), 18, c['muted'])
        frame = self.current_frame()
        self.editor.draw(s, pygame.Rect(58, 371, 754, 187), c, frame.line if frame else 0, readonly=True, tick=self.time, size=self.state['size'])
        self.brief(question.question, (58, 578, 752, 48), 23, bold=True)
        for i, choice in enumerate(question.choices):
            selected = self.prediction_attempt == i
            color = c['mint'] if selected and i == question.correct else c['danger'] if selected else c['blue']
            self.button('predict:' + str(i), chr(65 + i) + ' · ' + choice, (58, 633 + i * 45, 754, 39), selected, color, size=19)
        self.button('guide', 'Spiegami il ciclo', (58, 793, 237, 39), size=16)
        self.button('misconceptions', 'Equivoci da evitare', (307, 793, 242, 39), size=16)
        self.button('try_game', 'Ora programma tu →', (561, 793, 251, 39), size=16)
        text(s, '2  OSSERVA IL PERCHÉ', (868, 295), 19, c['mint'], True)
        self.scene('La riga evidenziata è in esecuzione' if frame else 'Scena iniziale · verde = traguardo')
        correct = self.prediction_attempt == question.correct
        title = 'Previsione corretta' if correct else 'Da rivedere: prova ancora' if self.prediction_attempt is not None else 'Prima scegli una risposta'
        text(s, title, (868, 581), 23, c['mint'] if correct else c['danger'] if self.prediction_attempt is not None else c['text'], True)
        if frame:
            self.brief(f'{frame.phase} · Giri {frame.iterations} · Passi {frame.world.steps} · Scansioni {frame.world.scans}', (868, 620, 514, 48), 17, c['accent'], True)
            self.brief(frame.message, (868, 672, 514, 96), 18)
            self.button('run', 'Pausa' if self.playing else 'Riprendi' if self.frame_index < len(self.result.frames) - 1 else 'Riguarda', (868, 797, 171, 39), True, c['mint'], size=17)
            self.button('step', 'Un passaggio →', (1047, 797, 173, 39), enabled=self.frame_index < len(self.result.frames) - 1, size=16)
            self.button('next_mission' if self.frame_index == len(self.result.frames) - 1 else 'back', 'Prossima →' if self.frame_index == len(self.result.frames) - 1 else '← Indietro', (1229, 797, 153, 39), enabled=self.frame_index > 0, size=16)
        else:
            message = question.explanation if self.prediction_attempt is not None else 'Scegli A, B o C nel pannello 1. Il robot aspetta: prima prova a immaginare cosa farà.'
            self.brief(message, (868, 626, 514, 114), 20)
            self.button('learn_start', 'Osserva l’esecuzione →' if correct else 'Scegli la risposta per proseguire', (868, 797, 514, 39), correct, c['mint'], enabled=correct, size=18)

    def draw_trace(self):
        s, c = self.canvas, self.c
        overlay = pygame.Surface(SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        s.blit(overlay, (0, 0))
        panel(s, pygame.Rect(40, 110, 1360, 742), c['panel'], c['border'], 20)
        self.buttons = []
        self.drawing_modal = True
        text(s, 'Osserva un passaggio alla volta', (60, 131), 30, c['text'], True)
        self.button('close', 'Torna al programma ×', (1118, 132, 262, 41), size=17)
        text(s, 'Qui leggi il codice. Per modificarlo, torna al programma.', (61, 190), 18, c['muted'])
        frame = self.current_frame()
        self.trace_editor.draw(s, pygame.Rect(60, 231, 737, 467), c, frame.line if frame else 0, self.result.error_line if self.result and self.frame_index == len(self.result.frames) - 1 else 0, readonly=True, tick=self.time, size=self.state['size'])
        world = frame.world if frame else self.initial_world()
        previous = self.result.frames[self.frame_index - 1].world if self.result and self.frame_index else None
        board(s, pygame.Rect(818, 231, 562, 295), self.mission, world, c, self.time, previous, self.motion, focus=True)
        if frame:
            text(s, frame.phase.upper(), (836, 547), 20, c['danger'] if frame.phase == 'Da rivedere' else c['mint'], True)
            text(s, f'Giri: {frame.iterations} · Controlli: {frame.checks} · Passi: {world.steps}', (836, 580), 18, c['text'], True)
            self.brief(frame.message, (836, 619, 524, 123), 19)
        text(s, 'Rotella: scorri il codice · Shift+rotella: righe lunghe', (61, 715), 16, c['muted'])
        text(s, 'Un passaggio può essere un controllo: il robot non si muove a ogni riga.', (61, 748), 18, c['accent'])
        self.button('run', 'Pausa' if self.playing else 'Riproduci', (60, 794, 218, 40), True, c['mint'], size=18)
        self.button('back', '← Indietro', (293, 794, 195, 40), enabled=bool(self.result and self.frame_index > 0), size=18)
        self.button('step', 'Un passaggio →', (503, 794, 224, 40), enabled=bool(self.result and self.frame_index < len(self.result.frames) - 1), size=18)
        self.button('speed', f'Velocità {self.state["speed"]:g}×', (742, 794, 188, 40), size=17)
        self.drawing_modal = False
