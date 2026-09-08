"""Validated preferences and drafts, saved independently of the previous app."""
import json
import os
from pathlib import Path
import sys
from engine import LANGUAGES


def data_path():
    return (Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent) / 'progressi_cicli.json'


def defaults():
    return dict(language='Python', difficulty='Facile', theme='Notte', size=19, speed=1.0, completed=[], drafts={}, blocks={}, mission='for_pontile')


def load(path=None):
    state = defaults()
    path = Path(path) if path else data_path()
    try:
        incoming = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(incoming, dict):
            raise ValueError('Formato non valido')
        for key, choices in (('language', LANGUAGES), ('difficulty', ('Facile', 'Medio', 'Difficile')), ('theme', ('Notte', 'Giorno', 'Contrasto')), ('size', (17, 19, 21))):
            if incoming.get(key) in choices:
                state[key] = incoming[key]
        if type(incoming.get('speed')) in (int, float) and incoming['speed'] in (.5, 1, 2, 3):
            state['speed'] = incoming['speed']
        if isinstance(incoming.get('mission'), str):
            state['mission'] = incoming['mission']
        if isinstance(incoming.get('completed'), list):
            state['completed'] = [x for x in incoming['completed'][:1000] if isinstance(x, str)]
        if isinstance(incoming.get('drafts'), dict):
            state['drafts'] = {k: v for k, v in list(incoming['drafts'].items())[:400] if isinstance(k, str) and isinstance(v, str) and len(v) <= 14000}
        if isinstance(incoming.get('blocks'), dict):
            from missions import CONDITIONS
            from engine import COMMANDS
            for key, value in list(incoming['blocks'].items())[:100]:
                if (isinstance(value, dict) and type(value.get('count')) is int and 0 <= value['count'] <= 20 and
                    value.get('condition') in CONDITIONS and isinstance(value.get('actions'), list) and
                    len(value['actions']) <= 12 and all(x in COMMANDS for x in value['actions'])):
                    state['blocks'][key] = value
        return state, ''
    except FileNotFoundError:
        return state, ''
    except (OSError, ValueError, TypeError):
        return state, 'Il salvataggio non è leggibile. Puoi continuare con le impostazioni iniziali.'


def save(state, path=None):
    path = Path(path) if path else data_path()
    temp = path.with_suffix('.tmp')
    try:
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, path)
        return ''
    except OSError:
        return 'Non riesco a salvare in questa cartella. Estrai lo ZIP in una cartella personale scrivibile. I progressi restano disponibili durante questa sessione.'
