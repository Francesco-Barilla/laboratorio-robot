"""Task-specific prompts, executable examples and misconceptions about loops."""
from dataclasses import dataclass
from engine import COMMANDS, Node, generate, placeholder_index
from missions import LOOPS


@dataclass(frozen=True)
class Prediction:
    question: str
    choices: tuple
    correct: int
    explanation: str
    misconception: str


PREDICTIONS = {
    'for_pontile': Prediction('Quanti passi farà questo for?', ('4 passi', '5 passi', '6 passi'), 1,
        'I valori sono 0, 1, 2, 3, 4: cinque valori, quindi cinque giri. Ogni giro contiene un passo.',
        'Partire da 0 non toglie un giro. Il limite 5 è escluso: non è l’ultimo valore usato.'),
    'for_batterie': Prediction('Quanti giri servono per quattro batterie?', ('8 giri', '2 giri', '4 giri'), 2,
        'In ogni giro il robot avanza e raccoglie. Quattro giri producono otto azioni, due per batteria.',
        'Giri e azioni non sono la stessa cosa: il corpo intero viene ripetuto, non una sola riga.'),
    'for_luci': Prediction('Quale azione deve venire prima in ogni giro?', ('Accendi, poi avanza', 'Avanza, poi accendi', 'Avanza due volte'), 0,
        'Il robot parte su una lampada. Deve accenderla prima di lasciare la casella; poi ripete sulla successiva.',
        'Il ciclo conserva l’ordine delle istruzioni. Scambiarle cambia ciò che succede, anche con lo stesso numero di giri.'),
    'while_corridoio': Prediction('Davanti al muro, che cosa farà il while?', ('Avanza un’ultima volta', 'Esce senza avanzare', 'Gira da solo'), 1,
        'strada_libera() è falso davanti al muro. Il controllo precede il corpo, quindi avanza() viene saltato.',
        'Leggere un sensore non sposta il robot. Il movimento avviene soltanto quando viene eseguito avanza().'),
    'while_traccia': Prediction('Sulla prima casella vuota, cosa succede?', ('Raccoglie lo stesso', 'Torna indietro', 'Esce dal ciclo'), 2,
        'sulla_batteria() osserva la casella attuale. Sulla prima casella vuota è falso: il corpo non riparte.',
        'sulla_batteria() guarda sotto il robot; strada_libera() guarda davanti. I sensori rispondono a domande diverse.'),
    'while_zero': Prediction('È già sul traguardo: quanti passi farà?', ('0 passi', '1 passo', '2 passi'), 0,
        'Il primo controllo è già falso: non sono sul traguardo è falso. Il corpo viene saltato; restare fermo è corretto.',
        'Un while può fare zero giri. Il corpo deve comunque contenere il lavoro da svolgere se la condizione fosse vera.'),
    'do_segnale': Prediction('Quando controlla se è arrivato il segnale?', ('Solo prima di iniziare', 'Dopo ogni scansione', 'Dopo cinque scansioni'), 1,
        'Il corpo esegue una scansione, poi controlla. Alla terza il segnale arriva e il ciclo termina, senza spostare il robot.',
        'La condizione del do while dice quando RIPETERE. Nel modello Python l’if in fondo dice invece quando USCIRE con break.'),
    'do_partenza': Prediction('Che cosa avviene per primo?', ('Il controllo finale', 'Un giro a vuoto', 'Il primo passo'), 2,
        'Il do while esegue prima il corpo. Dopo il passo controlla se deve continuare verso il traguardo.',
        'Spostare il controllo prima del corpo cambia il ciclo: un do while garantisce almeno un giro.'),
    'do_uno': Prediction('Segnale già presente: quante scansioni farà?', ('1 scansione', '0 scansioni', '2 scansioni'), 0,
        'La scansione di conferma avviene prima del controllo finale. Poi il ciclo esce: il segnale era già disponibile.',
        'Una condizione di ripetizione falsa non annulla il primo giro del do while. Con un while iniziale avresti zero scansioni.'),
}


@dataclass(frozen=True)
class Gap:
    start: int
    end: int
    line: int
    kind: str


def first_gap(code, language):
    start = placeholder_index(code, language)
    if start < 0:
        return None
    line = code[:start].count('\n') + 1
    prefix = code[:start].split('\n')[-1].strip()
    kind = 'number' if prefix.startswith('for ') else 'action' if not prefix else 'condition'
    return Gap(start, start + 3, line, kind)


def meaningful_code(code):
    return any(row.strip() and not row.lstrip().startswith(('#', '//')) for row in code.splitlines())


def writing_task(mission, code, language):
    gap = first_gap(code, language)
    if gap and gap.kind == 'number':
        return ('Scrivi un numero intero al posto di ???.',
                'È il limite escluso del for: con partenza 0 e passo 1 indica quanti giri fare.')
    if gap and gap.kind == 'action':
        return ('Scrivi un comando del robot con le parentesi: per esempio avanza().',
                'Sostituisci solo ???. Mantieni il rientro' + (' e il ; già presente.' if language != 'Python' else ' già presente.'))
    if gap:
        return ('Scrivi la condizione al posto di ???.', 'La condizione è un controllo vero/falso. Conserva la punteggiatura già scritta.')
    if not meaningful_code(code):
        return (f'Scrivi il programma usando {LOOPS[mission.loop]}.',
                'Premi Scrivi qui e usa la tastiera. Robot, comandi e sensori sono già preparati.')
    return ('Modifica il programma, poi premi Controlla il mio programma.',
            'Clicca la riga da correggere. Scrivi qui porta il cursore in fondo alla bozza.')


def writing_issue(mission, code, language, easy):
    if easy and not meaningful_code(code):
        return 'Aggiungi almeno un comando al corpo del ciclo con i pulsanti +.'
    if not meaningful_code(code):
        return 'Il programma è vuoto. Premi Scrivi qui e scrivi il ciclo; Cosa devo scrivere? mostra un esempio completo.'
    gap = first_gap(code, language)
    if gap:
        label = {'number': 'il numero limite', 'action': 'un comando con le parentesi', 'condition': 'la condizione'}[gap.kind]
        return f'Riga {gap.line}: manca {label}. Premi Completa i ???, poi digita solo la parte mancante.'
    return ''


def syntax_example(mission, language):
    condition = 'not (scansioni >= 2)' if mission.loop == 'do' and language == 'Python' else 'scansioni < 2'
    node = Node(mission.loop, name='i', stop='3', value='' if mission.loop == 'for' else condition, body=[Node('command', name='scansiona')])
    return generate([node], language)


def writing_sections(mission, language, code, easy=False):
    title, instruction = writing_task(mission, code, language)
    sections = [('Cosa fare adesso', 'Scegli il numero o la condizione, poi aggiungi i comandi con +. Il corpo è l’elenco ripetuto a ogni giro. Le frecce cambiano l’ordine; × elimina un comando.' if easy else title + '\n' + instruction),
                ('La missione', mission.objective),
                ('Come leggere il ciclo', {'for': 'Il contatore parte da 0. Il limite è escluso. A ogni giro esegui tutto il corpo, poi passa al valore successivo.',
                 'while': 'Controlla prima: vero → esegui tutto il corpo e ricontrolla; falso → esci. Il corpo può essere saltato fin dall’inizio.',
                 'do': 'Esegui il corpo, poi controlla se ripetere. Almeno un giro è garantito. In Python si usa while True con if e break in fondo; quel controllo indica quando uscire.'}[mission.loop]),
                ('Esempio di forma · ' + language, syntax_example(mission, language)),
                ('Adatta l’esempio alla missione', 'L’esempio fa scansioni per mostrare la sintassi. Scegli numero, sensori e azioni adatti all’obiettivo qui sopra. I comandi esistono già: non scrivere main, classi o definizioni di funzioni.'),
                ('Comandi utili qui', '\n'.join(name + '()' + ('' if language == 'Python' else ';') + ' = ' + COMMANDS[name] for name in mission.actions)),
                ('Sensori e contatori', 'strada_libera(): guarda davanti. sulla_batteria(): guarda sotto il robot. sul_traguardo(): sei sulla piattaforma? segnale_trovato(): è arrivato il segnale?\nI sensori restituiscono vero/falso (1/0) e non muovono il robot. passi, raccolte, accese, scansioni sono contatori già aggiornati dal gioco.'),
                ('Punteggiatura e rientri', 'Invio va a capo; Tab inserisce quattro spazi. Il corpo è rientrato rispetto a for o while; il corpo di if richiede un altro rientro.' if language == 'Python' else 'Le graffe racchiudono il corpo. I comandi terminano con ;. Il do while termina con while (condizione);, compreso il punto e virgola finale.'),
                ('Controlla e osserva', 'Controlla i blocchi verifica subito il risultato. Osserva passo passo mostra poi come è stato ottenuto.' if easy else 'Controlla il mio programma (anche Ctrl+Invio) verifica subito il risultato. Osserva passo passo mostra come è stato ottenuto; leggere una soluzione non completa la missione.'),
                ('Equivoco da evitare', PREDICTIONS[mission.key].misconception)]
    return sections


def misconceptions(mission):
    return [('In questa missione', PREDICTIONS[mission.key].misconception),
            ('Un passo del programma non è un passo del robot', 'La traccia mostra anche i controlli e gli aggiornamenti. Solo avanza() cambia casella; scansiona() cerca un segnale restando fermo.'),
            ('Giri, azioni e controlli', 'Con due comandi nel corpo, quattro giri eseguono otto azioni. Un while di quattro giri controlla normalmente cinque volte: l’ultimo falso lo fa uscire.'),
            ('Vero significa ripeti', 'while condizione ripete mentre è vera. Per continuare fino al traguardo serve non sul_traguardo(). In Python not, negli altri linguaggi !. Nell’if finale del do while Python, invece, vero esegue break e termina.'),
            ('Il ciclo non si ferma da solo', 'Se il corpo non cambia ciò che controlli, la condizione può rimanere vera. Il laboratorio mette in pausa dopo 1400 passaggi: controlla contatori e sensori; il limite non dimostra da solo un ciclo infinito.'),
            ('Arrivare non basta a usare un ciclo', 'Le azioni richieste devono essere dentro il ciclo indicato. Scrivere i passi uno per uno fuori dal ciclo non allena la ripetizione.')]


def result_rows(mission, result):
    world = result.frames[-1].world
    rows = [(f'Traguardo: col. {mission.goal[0] + 1}, riga {mission.goal[1] + 1}',
             f'col. {world.x + 1}, riga {world.y + 1}', (world.x, world.y) == mission.goal)]
    if mission.batteries:
        rows.append((f'Batterie: {len(mission.batteries)}', str(world.collected), not world.batteries))
    if mission.lamps:
        rows.append((f'Lampade: {len(mission.lamps)}', str(len(world.lit)), world.lit == world.lamps))
    if mission.required_scans:
        target = ('esattamente ' + str(mission.exact_scans)) if mission.exact_scans is not None else ('almeno ' + str(mission.required_scans))
        rows.append(('Scansioni: ' + target, str(world.scans), world.scans >= mission.required_scans and (mission.exact_scans is None or world.scans == mission.exact_scans)))
    rows.append(('Ciclo ' + LOOPS[mission.loop] + ' usato nel modo richiesto', 'sì' if result.rule else 'da correggere', result.rule))
    return rows
