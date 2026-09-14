"""Nine authored missions, each playable with three scaffolding levels."""
from dataclasses import dataclass
from engine import Node, generate

LOOPS = {'for': 'for', 'while': 'while', 'do': 'do while'}
DIFFICULTIES = ('Facile', 'Medio', 'Difficile')
CONDITIONS = ('strada_libera()', 'sulla_batteria()', 'not sul_traguardo()',
              'not segnale_trovato()', 'passi < 5', 'scansioni < 3', 'False')


@dataclass(frozen=True)
class Mission:
    key: str
    loop: str
    title: str
    subtitle: str
    objective: str
    concept: str
    start: tuple = (0, 2)
    goal: tuple = (5, 2)
    width: int = 7
    height: int = 5
    walls: tuple = ()
    batteries: tuple = ()
    lamps: tuple = ()
    signal_after: int = 999
    required_scans: int = 0
    exact_scans: object = None
    count: int = 5
    condition: str = 'strada_libera()'
    actions: tuple = ('avanza',)
    zero_case: bool = False
    hints: tuple = ()

    def solution(self, language):
        return self.program(language, self.count, self.condition, self.actions)

    def program(self, language, count, condition, actions):
        return generate([Node(self.loop, value=condition if self.loop != 'for' else '', name='i', stop=str(count),
                              body=[Node('command', name=name) for name in actions])], language)

    def starter(self, language, difficulty):
        if difficulty == 'Difficile':
            return ''
        code = self.solution(language)
        if self.loop == 'for':
            return code.replace(f', {self.count},', ', ???,', 1) if language == 'Python' else code.replace(f'< {self.count};', '< ???;', 1)
        return code.replace(self.actions[0] + '()', '???', 1)

    def failure(self, world):
        if self.exact_scans is not None and world.scans != self.exact_scans:
            return f'Servono esattamente {self.exact_scans} scansioni; ne hai eseguite {world.scans}. Nel do while il corpo viene eseguito prima del controllo.'
        if world.batteries:
            return f'Mancano {len(world.batteries)} batterie. Controlla il numero di ripetizioni e l’ordine tra avanza() e raccogli().'
        if world.lamps - world.lit:
            return f'Mancano {len(world.lamps - world.lit)} lampade da accendere. Il robot deve accendere prima di lasciare la loro casella.'
        if world.scans < self.required_scans:
            return f'Il segnale non è ancora arrivato: hai eseguito {world.scans} scansioni. Il sensore va ricontrollato dopo ogni tentativo.'
        return f'Il robot è nella colonna {world.x + 1}, riga {world.y + 1}. Il traguardo è nella colonna {self.goal[0] + 1}, riga {self.goal[1] + 1}. Controlla quando il ciclo termina.'


MISSIONS = (
    Mission('for_pontile', 'for', 'Il pontile solare', 'Cinque passi, un solo ciclo.',
        'Raggiungi la piattaforma verde avanzando di cinque caselle con un for.',
        'Un contatore che parte da 0 e resta minore di 5 assume i valori 0, 1, 2, 3, 4: sono cinque ripetizioni.',
        walls=((6, 2),), hints=('Conta gli spostamenti tra la casella del robot e il traguardo: le caselle di arrivo sono cinque.',
        'Il corpo deve contenere avanza(). Il contatore parte da 0 e il limite escluso è 5.', 'Attenzione: partire da 0 non significa fare un giro in meno. Da 0 a 4 ci sono cinque valori.')),
    Mission('for_batterie', 'for', 'La scorta di energia', 'Due azioni in ogni giro.',
        'Raccogli le quattro batterie e fermati sulla piattaforma dell’ultima batteria. Usa un for.',
        'Un giro può contenere più istruzioni: prima avanza, poi raccogli. Il corpo completo viene ripetuto quattro volte.',
        goal=(4, 2), walls=((5, 2),), batteries=tuple((x, 2) for x in range(1, 5)), count=4, actions=('avanza', 'raccogli'),
        hints=('La prima batteria è davanti al robot, non sotto di lui.', 'Metti avanza() prima di raccogli() dentro il ciclo.', 'Ripeti la coppia di istruzioni quattro volte: non servono otto giri.')),
    Mission('for_luci', 'for', 'Accendi la base', 'Prima agisci, poi ti sposti.',
        'Accendi le quattro lampade e raggiungi il traguardo usando un for.',
        'L’ordine delle istruzioni conta: il robot parte sopra una lampada e deve accenderla prima di avanzare.',
        goal=(4, 2), walls=((5, 2),), lamps=tuple((x, 2) for x in range(4)), count=4, actions=('accendi', 'avanza'),
        hints=('Guarda la casella iniziale: contiene già una lampada.', 'Il corpo deve essere accendi(), poi avanza().', 'Ci sono quattro lampade: il limite escluso del contatore che parte da 0 è 4.')),
    Mission('while_corridoio', 'while', 'Il corridoio sicuro', 'Lascia decidere al sensore.',
        'Avanza mentre la strada è libera. Fermati sulla piattaforma prima dell’ostacolo usando un while.',
        'Il controllo avviene prima di ogni passo. Quando strada_libera() diventa falso, il robot non deve avanzare ancora.',
        goal=(4, 2), walls=((5, 2),),
        hints=('Non serve conoscere in anticipo la lunghezza del corridoio.', 'Il sensore strada_libera() guarda la casella davanti al robot.', 'Usa strada_libera() come condizione e avanza() come corpo: il sensore cambia quando arrivi davanti all’ostacolo.')),
    Mission('while_traccia', 'while', 'Segui le batterie', 'Ripeti finché trovi energia.',
        'Raccogli le batterie della fila e fermati sulla prima casella vuota usando un while.',
        'Il sensore sulla_batteria() osserva la casella attuale. Dopo la raccolta il robot avanza e controlla la nuova casella.',
        goal=(4, 2), batteries=tuple((x, 2) for x in range(4)), condition='sulla_batteria()', actions=('raccogli', 'avanza'),
        hints=('Il robot parte sopra una batteria: può raccoglierla subito.', 'La condizione è sulla_batteria(). Nel corpo raccogli, poi avanza.', 'Alla prima casella senza batteria la condizione è falsa e il corpo non viene eseguito.')),
    Mission('while_zero', 'while', 'Sei già arrivato', 'Anche zero giri è corretto.',
        'Il robot è già sul traguardo. Scrivi un while che avanzi soltanto quando non è sul traguardo.',
        'Il while può saltare completamente il corpo: la prima condizione è già falsa. Questo è un comportamento corretto, non un errore.',
        start=(2, 2), goal=(2, 2), walls=((3, 2),), condition='not sul_traguardo()', zero_case=True,
        hints=('Il robot è già sulla piattaforma: non deve fare nemmeno un passo.', 'sul_traguardo() vale vero. Per ripetere soltanto quando non sei arrivato, nega il sensore.', 'Usa not sul_traguardo() in Python oppure !sul_traguardo() negli altri linguaggi. Avanza resta nel corpo ma non viene eseguito.')),
    Mission('do_segnale', 'do', 'Un messaggio dallo spazio', 'Un tentativo prima del controllo.',
        'Esegui scansioni fino a trovare il segnale, che arriva alla terza scansione. Usa un do while.',
        'Prima scansiona, poi chiedi se serve ripetere. Il segnale viene controllato dopo ogni tentativo.',
        start=(3, 2), goal=(3, 2), signal_after=3, required_scans=3, condition='not segnale_trovato()', actions=('scansiona',),
        hints=('La prima azione deve essere una scansione.', 'Ripeti mentre il segnale NON è stato trovato.', 'Il corpo contiene scansiona(). La condizione è not segnale_trovato() in Python, !segnale_trovato() negli altri linguaggi.')),
    Mission('do_partenza', 'do', 'Partenza obbligatoria', 'Muoviti e poi controlla.',
        'Raggiungi la piattaforma a quattro passi: esegui un passo, poi controlla se devi ripetere. Usa un do while.',
        'Il primo passo è garantito. Dopo ciascun passo il sensore sul_traguardo() decide se il ciclo deve continuare.',
        goal=(4, 2), walls=((5, 2),), condition='not sul_traguardo()', actions=('avanza',),
        hints=('Qui il robot parte lontano dal traguardo: il primo passo è necessario.', 'Avanza nel corpo, poi controlla se NON sei sul traguardo.', 'Quando il robot arriva, sul_traguardo() è vero e la sua negazione è falsa: il ciclo termina.')),
    Mission('do_uno', 'do', 'Il controllo di conferma', 'Il segnale c’è già: fai un controllo.',
        'Il segnale è già disponibile. Esegui esattamente una scansione di conferma usando un do while.',
        'Anche se la condizione di ripetizione sarebbe falsa fin dall’inizio, il do while esegue il corpo almeno una volta.',
        start=(3, 2), goal=(3, 2), signal_after=0, required_scans=1, exact_scans=1, condition='not segnale_trovato()', actions=('scansiona',),
        hints=('Il sensore rileva già il segnale, ma la missione richiede una scansione di conferma.', 'Il controllo viene dopo scansiona(): questa è la differenza rispetto al while.', 'Dopo la prima scansione, NON segnale_trovato() è falso: esci senza eseguire una seconda scansione.')),
)
BY_KEY = {m.key: m for m in MISSIONS}
