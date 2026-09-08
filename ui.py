"""Resolution-independent interface, robot drawings and a small code editor."""
import math
from functools import lru_cache
import pygame

SIZE = (1440, 900)
THEMES = {
    'Notte': dict(bg='#0b1422', panel='#142438', card='#1c3047', border='#31485f', text='#f1f6fa', muted='#aabed0', accent='#ffd078', mint='#65dfc5', blue='#8bbfff', danger='#ff998c', grid='#1b2b40'),
    'Giorno': dict(bg='#edf3f6', panel='#ffffff', card='#e4edf2', border='#b9cbd6', text='#193044', muted='#47637a', accent='#975609', mint='#076b57', blue='#235f9f', danger='#b73128', grid='#d4e1e8'),
    'Contrasto': dict(bg='#000000', panel='#090909', card='#1b1b1b', border='#b8c5ce', text='#ffffff', muted='#eeeeee', accent='#ffff00', mint='#4bffc5', blue='#91c6ff', danger='#ff968b', grid='#323232'),
}


def palette(theme):
    return {k: pygame.Color(v) for k, v in THEMES.get(theme, THEMES['Notte']).items()}


@lru_cache(maxsize=100)
def font(size, bold=False, mono=False):
    return pygame.font.SysFont('consolas' if mono else 'segoeui', size, bold=bold)


def text(surface, value, pos, size, color, bold=False, anchor='topleft', mono=False):
    label = font(size, bold, mono).render(str(value), True, color)
    rect = label.get_rect(**{anchor: pos})
    surface.blit(label, rect)
    return rect


@lru_cache(maxsize=500)
def lines(value, width, size, bold=False):
    result = []
    f = font(size, bold)
    for paragraph in str(value).split('\n'):
        line = ''
        for word in paragraph.split():
            if f.size((line + ' ' + word).strip())[0] > width and line:
                result.append(line)
                line = ''
            while f.size(word)[0] > width and len(word) > 1:
                end = len(word) - 1
                while end > 1 and f.size(word[:end])[0] > width:
                    end -= 1
                result.append(word[:end])
                word = word[end:]
            line = (line + ' ' + word).strip()
        result.append(line)
    return tuple(result)


def wrap(surface, value, rect, size, color, bold=False):
    step = font(size, bold).get_linesize() + 4
    clip = surface.get_clip()
    surface.set_clip(rect.clip(clip))
    for i, line in enumerate(lines(str(value), rect.width, size, bold)):
        text(surface, line, (rect.x, rect.y + i * step), size, color, bold)
    surface.set_clip(clip)
    return len(lines(str(value), rect.width, size, bold)) * step


def panel(surface, rect, fill, border=None, radius=16):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, 1, border_radius=radius)


def mix(a, b, t):
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def robot(surface, center, scale, direction=0, tick=0, shake=0):
    """Original vector mascot: articulated wheels, expressive visor, antenna."""
    x, y = center
    x += math.sin(tick * 55) * shake
    def r(dx, dy, w, h):
        return pygame.Rect(round(x + dx * scale), round(y + dy * scale), max(1, round(w * scale)), max(1, round(h * scale)))
    pygame.draw.ellipse(surface, '#07111d', r(-27, 20, 56, 15))
    for dx in (-25, 14):
        panel(surface, r(dx, 1, 13, 28), '#263e55', '#66819a', max(2, int(5 * scale)))
        for dy in (7, 14, 21):
            pygame.draw.line(surface, '#07121f', r(dx + 2, dy, 1, 1).topleft, r(dx + 10, dy, 1, 1).topleft, max(1, round(scale * 2)))
    panel(surface, r(-21, -12, 42, 35), '#66ddc5', '#a0f5df', max(3, round(9 * scale)))
    panel(surface, r(-26, -32, 52, 33), '#d7e8f2', '#8ba8c1', max(3, round(10 * scale)))
    panel(surface, r(-21, -26, 42, 21), '#102439', '#3d647c', max(2, round(7 * scale)))
    blink = int(tick * 2) % 13 == 12
    for dx in (-12, 8):
        panel(surface, r(dx, -20, 6, 2 if blink else 9), '#7bfce0', radius=max(1, round(2 * scale)))
    pygame.draw.line(surface, '#b8d0df', r(0, -33, 1, 1).topleft, r(0, -43, 1, 1).topleft, max(1, round(3 * scale)))
    pygame.draw.circle(surface, '#ffd078', r(0, -44, 1, 1).topleft, max(2, round(4 * scale)))
    panel(surface, r(-11, 4, 22, 10), '#1d6e64', radius=max(1, round(3 * scale)))
    for dx in (-6, 0, 6):
        pygame.draw.circle(surface, '#adffe1', r(dx, 9, 1, 1).topleft, max(1, round(1.5 * scale)))
    # Direction is explicit rather than inferred from the front-facing mascot.
    dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[direction]
    tip = (x + dx * 37 * scale, y + dy * 37 * scale)
    base = (x + dx * 28 * scale, y + dy * 28 * scale)
    pygame.draw.polygon(surface, '#ffd078', [tip, (base[0] - dy * 5 * scale, base[1] + dx * 5 * scale), (base[0] + dy * 5 * scale, base[1] - dx * 5 * scale)])


def board(surface, rect, mission, world, colors, tick=0, previous=None, progress=1, shake=0):
    panel(surface, rect, colors['panel'], colors['border'], 20)
    cell = min((rect.width - 64) / mission.width, (rect.height - 56) / mission.height)
    ox = rect.centerx - cell * mission.width / 2
    oy = rect.centery - cell * mission.height / 2 + 4
    for y in range(mission.height):
        for x in range(mission.width):
            r = pygame.Rect(round(ox + x * cell + 3), round(oy + y * cell + 3), round(cell - 6), round(cell - 6))
            fill = colors['card'] if (x + y) % 2 == 0 else mix(colors['panel'], colors['card'], .5)
            if (x, y) == mission.goal:
                fill = mix(colors['panel'], colors['mint'], .28)
            panel(surface, r, fill, colors['mint'] if (x, y) == mission.goal else colors['border'], 8)
            if (x, y) == mission.goal:
                pygame.draw.rect(surface, colors['mint'], r.inflate(-12, -12), 2, border_radius=6)
            if (x, y) in mission.walls:
                panel(surface, r.inflate(-7, -7), '#667487', '#98a8bb', 6)
                for d in (12, 28, 44):
                    if d < r.width - 4:
                        pygame.draw.line(surface, '#364556', (r.x + d, r.y + 8), (r.x + d - 6, r.bottom - 8), 4)
            if (x, y) in world.batteries:
                battery = pygame.Rect(0, 0, max(14, round(cell * .27)), max(24, round(cell * .43)))
                battery.center = r.center
                panel(surface, battery, '#ffd078', '#fff1b6', 4)
                pygame.draw.rect(surface, '#ffe5a8', (battery.centerx - 4, battery.top - 4, 8, 4))
                text(surface, '+', battery.center, 21, '#785018', True, 'center')
            if (x, y) in world.lamps:
                lit = (x, y) in world.lit
                if lit:
                    pygame.draw.circle(surface, mix(colors['card'], colors['accent'], .27), r.center, int(cell * .35))
                pygame.draw.circle(surface, '#ffda7d' if lit else '#7c91a6', (r.centerx, r.centery - 4), max(6, round(cell * .17)))
                pygame.draw.line(surface, '#819aad', (r.centerx, r.centery + 7), (r.centerx, r.centery + 17), 5)
    for x in range(mission.width):
        text(surface, x + 1, (ox + (x + .5) * cell, oy - 15), 12, colors['muted'], anchor='center')
    for y in range(mission.height):
        text(surface, y + 1, (ox - 12, oy + (y + .5) * cell), 12, colors['muted'], anchor='center')
    rx, ry = world.x, world.y
    if previous and abs(previous.x - rx) + abs(previous.y - ry) == 1:
        t = max(0, min(1, progress))
        t = t * t * (3 - 2 * t)
        rx = previous.x * (1 - t) + rx * t
        ry = previous.y * (1 - t) + ry * t
    robot(surface, (ox + (rx + .5) * cell, oy + (ry + .5) * cell + cell * .1), cell / 86, world.direction, tick, shake)
    if mission.required_scans:
        pos = (rect.right - 26, rect.top + 25)
        for radius in (6, 12, 18):
            pygame.draw.circle(surface, colors['mint'] if world.scans >= mission.signal_after else colors['muted'], pos, radius, 1)
        if world.scans:
            for offset in (0, .5):
                pulse = (tick * .65 + offset) % 1
                color = mix(colors['panel'], colors['mint'] if world.scans >= mission.signal_after else colors['blue'], 1 - pulse)
                pygame.draw.circle(surface, color, (round(ox + (rx + .5) * cell), round(oy + (ry + .5) * cell)), round(cell * (.5 + pulse * .7)), 2)


class Editor:
    def __init__(self, value=''):
        self.value = value
        self.caret = len(value)
        self.anchor = self.caret
        self.scroll = 0
        self.xscroll = 0
        self.focus = False
        self.undo = []
        self.redo = []
        self.rect = pygame.Rect(0, 0, 1, 1)
        self.size = 19

    def set(self, value):
        self.value = value
        self.caret = min(self.caret, len(value))
        self.anchor = self.caret
        self.scroll = self.xscroll = 0
        self.undo.clear()
        self.redo.clear()

    def snapshot(self):
        return self.value, self.caret, self.anchor

    def replace(self, value):
        a, b = sorted((self.caret, self.anchor))
        new = self.value[:a] + value.replace('\r', '') + self.value[b:]
        if len(new) > 14000 or new.count('\n') > 250:
            return False
        self.undo.append(self.snapshot())
        self.undo = self.undo[-100:]
        self.redo.clear()
        self.value = new
        self.caret = a + len(value.replace('\r', ''))
        self.anchor = self.caret
        self.reveal()
        return True

    def reveal(self):
        row = self.value[:self.caret].count('\n')
        col = len(self.value[:self.caret].split('\n')[-1])
        lh = self.size + 8
        visible = max(1, (self.rect.height - 18) // lh)
        self.scroll = max(0, min(self.scroll, row))
        if row >= self.scroll + visible:
            self.scroll = row - visible + 1
        cw = font(self.size, mono=True).size('M')[0]
        visible_cols = max(1, (self.rect.width - 65) // cw)
        self.xscroll = max(0, min(self.xscroll, col))
        if col >= self.xscroll + visible_cols:
            self.xscroll = col - visible_cols + 1

    def click(self, pos, shift=False):
        all_lines = self.value.split('\n')
        row = min(len(all_lines) - 1, max(0, int((pos[1] - self.rect.y - 10) // (self.size + 8)) + self.scroll))
        cw = font(self.size, mono=True).size('M')[0]
        col = min(len(all_lines[row]), max(0, round((pos[0] - self.rect.x - 47) / cw) + self.xscroll))
        self.caret = sum(len(s) + 1 for s in all_lines[:row]) + col
        if not shift:
            self.anchor = self.caret
        self.focus = True

    def key(self, event):
        if not self.focus:
            return False
        ctrl = bool(event.mod & pygame.KMOD_CTRL)
        shift = bool(event.mod & pygame.KMOD_SHIFT)
        old = self.value
        if ctrl and event.key == pygame.K_a:
            self.anchor, self.caret = 0, len(self.value)
        elif ctrl and event.key in (pygame.K_z, pygame.K_y):
            src, dest = (self.undo, self.redo) if event.key == pygame.K_z else (self.redo, self.undo)
            if src:
                dest.append(self.snapshot())
                self.value, self.caret, self.anchor = src.pop()
        elif ctrl and event.key in (pygame.K_c, pygame.K_x, pygame.K_v):
            try:
                if not pygame.scrap.get_init():
                    pygame.scrap.init()
                if event.key == pygame.K_v:
                    data = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if data:
                        self.replace(data.rstrip(b'\x00').decode('utf-8', errors='replace'))
                else:
                    a, b = sorted((self.caret, self.anchor))
                    if a != b:
                        pygame.scrap.put(pygame.SCRAP_TEXT, self.value[a:b].encode('utf-8') + b'\0')
                        if event.key == pygame.K_x:
                            self.replace('')
            except pygame.error:
                pass
        elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
            if self.caret == self.anchor:
                if event.key == pygame.K_BACKSPACE:
                    self.anchor = max(0, self.caret - 1)
                else:
                    self.anchor = min(len(self.value), self.caret + 1)
            self.replace('')
        elif event.key == pygame.K_RETURN:
            previous = self.value[:self.caret].split('\n')[-1]
            indent = len(previous) - len(previous.lstrip())
            self.replace('\n' + ' ' * (indent + (4 if previous.rstrip().endswith((':', '{')) else 0)))
        elif event.key == pygame.K_TAB:
            self.replace('    ')
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_HOME, pygame.K_END, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            all_lines = self.value.split('\n')
            row = self.value[:self.caret].count('\n')
            col = len(self.value[:self.caret].split('\n')[-1])
            if event.key == pygame.K_LEFT:
                self.caret = max(0, self.caret - 1)
            elif event.key == pygame.K_RIGHT:
                self.caret = min(len(self.value), self.caret + 1)
            elif event.key == pygame.K_HOME:
                self.caret = 0 if ctrl else self.caret - col
            elif event.key == pygame.K_END:
                self.caret = len(self.value) if ctrl else self.caret - col + len(all_lines[row])
            else:
                delta = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -10, pygame.K_PAGEDOWN: 10}[event.key]
                row = min(len(all_lines) - 1, max(0, row + delta))
                self.caret = sum(len(s) + 1 for s in all_lines[:row]) + min(col, len(all_lines[row]))
            if not shift:
                self.anchor = self.caret
        self.reveal()
        return old != self.value

    def draw(self, surface, rect, colors, active=0, error=0, readonly=False, tick=0, size=19):
        self.rect = pygame.Rect(rect)
        self.size = size
        panel(surface, self.rect, colors['bg'], colors['accent'] if self.focus and not readonly else colors['border'], 10)
        clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-4, -4).clip(clip))
        cw = font(size, mono=True).size('M')[0]
        lh = size + 8
        offset = 0
        a, b = sorted((self.anchor, self.caret))
        all_lines = self.value.split('\n')
        visible = max(1, (rect.height - 16) // lh)
        self.scroll = min(max(0, self.scroll), max(0, len(all_lines) - visible))
        columns = max(1, (rect.width - 65) // cw)
        longest = max(map(len, all_lines), default=0)
        self.xscroll = min(max(0, self.xscroll), max(0, longest - columns))
        for row, line in enumerate(all_lines):
            y = rect.y + 10 + (row - self.scroll) * lh
            if y < rect.bottom and y + lh > rect.top:
                if row + 1 in (active, error):
                    color = colors['danger'] if row + 1 == error else colors['mint']
                    panel(surface, pygame.Rect(rect.x + 3, y - 2, rect.width - 6, lh), mix(colors['bg'], color, .2), radius=3)
                    pygame.draw.rect(surface, color, (rect.x + 3, y - 2, 3, lh))
                text(surface, row + 1, (rect.x + 34, y), size - 2, colors['muted'], anchor='topright', mono=True)
                start, end = max(0, a - offset), min(len(line), b - offset)
                if start < end and self.focus and not readonly:
                    pygame.draw.rect(surface, mix(colors['bg'], colors['blue'], .4), (rect.x + 47 + (start - self.xscroll) * cw, y, (end - start) * cw, lh))
                code_clip = surface.get_clip()
                surface.set_clip(pygame.Rect(rect.x + 44, rect.y + 4, rect.width - 48, rect.height - 8).clip(code_clip))
                color = colors['muted'] if line.lstrip().startswith(('#', '//')) else colors['accent'] if line.lstrip().startswith(('for ', 'while ', 'do ', 'if ', 'break', '} while')) else colors['text']
                text(surface, line, (rect.x + 47 - self.xscroll * cw, y), size, color, mono=True)
                if self.focus and not readonly and offset <= self.caret <= offset + len(line) and int(tick * 2) % 2 == 0:
                    x = rect.x + 47 + (self.caret - offset - self.xscroll) * cw
                    pygame.draw.line(surface, colors['text'], (x, y), (x, y + lh - 5), 2)
                surface.set_clip(code_clip)
            offset += len(line) + 1
        if len(all_lines) > visible:
            h = max(18, (rect.height - 12) * visible / len(all_lines))
            y = rect.y + 6 + (rect.height - 12 - h) * self.scroll / (len(all_lines) - visible)
            panel(surface, pygame.Rect(rect.right - 7, y, 3, h), colors['muted'], radius=1)
        if longest > columns:
            track = rect.width - 62
            width = max(30, track * columns / longest)
            x = rect.x + 47 + (track - width) * self.xscroll / (longest - columns)
            panel(surface, pygame.Rect(x, rect.bottom - 6, width, 3), colors['muted'], radius=1)
        surface.set_clip(clip)
