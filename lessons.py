"""Original Italian teaching notes, organized into scrollable reading sections."""
LESSONS = {
    'for': {
        'tag': 'RIPETIZIONI CONTATE',
        'title': 'Un giro per ogni valore.',
        'intro': 'Usa un for quando vuoi ripetere un’azione seguendo una sequenza di valori. Per esempio: fai cinque passi, raccogli quattro batterie o accendi una fila di lampade.',
        'sections': (
            ('L’idea', 'Immagina di numerare i giri del robot. Il contatore ti dice a quale giro sei arrivato; il corpo contiene le azioni da ripetere. Un giro può contenere una sola istruzione oppure più istruzioni, eseguite nell’ordine in cui le hai scritte.'),
            ('JavaScript, C e Java: tre parti', 'Nel for classico trovi inizializzazione, condizione e aggiornamento. L’inizializzazione avviene una sola volta. Poi controlli la condizione: se è vera esegui tutto il corpo. Alla fine aggiorni il contatore e ricontrolli. Quando la condizione è falsa, esci senza eseguire un altro giro.'),
            ('Python: i valori di range', 'In Python il for prende un valore alla volta da range. range(0, 5, 1) offre 0, 1, 2, 3, 4: il limite 5 è escluso. Il contatore riceve ciascuno di questi valori. Quando non ci sono altri valori il ciclo termina. Non devi scrivere i++: Python passa al valore successivo. Il for di Python può anche attraversare altri insiemi di elementi; qui partiamo dagli interi di range.'),
            ('Esempio: cinque passi', 'Parti da 0 e usa il limite escluso 5. Il robot avanza con i = 0, poi con 1, 2, 3 e 4. Ha fatto cinque passi. Scrivere i < 4 produrrebbe soltanto quattro giri. Il contatore identifica il giro: il primo valore 0 non indica che il robot sia fermo.'),
            ('Un caso importante: zero giri', 'Se l’inizio è già fuori dall’intervallo, il corpo può non partire. Per esempio range(5, 5) è vuoto; nel for classico i = 5 con condizione i < 5 fa fallire subito il controllo.'),
            ('Controlla il passo', 'Con un passo positivo i valori crescono; con uno negativo diminuiscono. Da 4 a 0, incluso, puoi usare range(4, -1, -1). Se il contatore non cambia nella direzione corretta, il programma può non terminare. In questo laboratorio il for usa un contatore intero con limite escluso e passo non nullo.'),
        ),
    },
    'while': {
        'tag': 'CONTROLLO PRIMA',
        'title': 'Prima chiedi. Poi agisci.',
        'intro': 'Il while ripete il corpo mentre una condizione è vera. È utile quando la decisione dipende da ciò che il robot osserva, per esempio una strada libera o una batteria nella casella attuale.',
        'sections': (
            ('Che cosa è una condizione?', 'È una domanda con risposta vero o falso. strada_libera != 0 confronta con 0 l’ultimo intero letto: 1 significa strada libera, 0 ostacolo. i < 5 confronta la variabile i con 5. La condizione non legge nuovi dati e non muove il robot: decide se eseguire il corpo.'),
            ('L’ordine dei passaggi', '1. Controlla la condizione. 2. Se è vera, esegui tutto il corpo. 3. Torna al controllo. Se la condizione è falsa, passa all’istruzione dopo il ciclo. Il controllo avviene anche prima della prima ripetizione.'),
            ('Esempio: un corridoio', 'Prima del while leggi strada_libera con l’input standard del linguaggio. Se il valore è diverso da 0, stampa avanza: il gioco anima il messaggio. Rileggi strada_libera alla fine del corpo. Davanti all’ostacolo ricevi 0 e il ciclo termina. Senza rilettura la variabile conserva il vecchio valore.'),
            ('Può eseguire zero giri', 'Se il robot è già sul traguardo, la condizione «non sono sul traguardo» è falsa fin dall’inizio. Il corpo viene saltato. Nella missione Sei già arrivato il risultato corretto è proprio zero passi.'),
            ('Qualcosa deve cambiare', 'Una condizione sempre vera rischia di continuare senza fine. Se controlli i < 5, aggiorna i nel corpo. Se controlli un dato della scena, le azioni possono cambiare il mondo ma devi eseguire una nuova lettura per aggiornare la variabile.'),
            ('Mentre, non fino a', 'while strada_libera != 0 significa «ripeti mentre l’ultimo dato letto indica strada libera». Per continuare fino al traguardo confronta sul_traguardo == 0. Questi confronti producono condizioni booleane valide anche in Java, dove non puoi usare direttamente un intero come condizione.'),
        ),
    },
    'do': {
        'tag': 'CONTROLLO DOPO',
        'title': 'Un tentativo è garantito.',
        'intro': 'Nel do while il robot esegue il corpo prima di controllare se deve ripeterlo. Per questo almeno una esecuzione è garantita, anche quando la condizione di ripetizione è già falsa.',
        'sections': (
            ('L’ordine dei passaggi', '1. Esegui il corpo. 2. Controlla la condizione. 3. Se è vera torna al corpo; se è falsa esci. Il controllo è in fondo: questa posizione cambia il comportamento rispetto al while.'),
            ('Esempio: cercare un segnale', 'Stampa scansiona, poi leggi segnale_trovato con l’input standard. Controlla segnale_trovato == 0: se è vero ripeti, altrimenti termina. Nella missione Un messaggio dallo spazio il dato letto vale 1 dopo la terza scansione. La lettura va dopo l’output e prima del controllo finale.'),
            ('Se il segnale è già presente', 'Nella missione Il controllo di conferma il sensore è già vero all’inizio. Il do while esegue comunque una scansione e poi termina, perché «segnale non trovato» è falso. Un while con lo stesso controllo iniziale farebbe zero scansioni.'),
            ('JavaScript, C e Java', 'Scrivi do, il corpo tra parentesi graffe e poi while (condizione);. Non dimenticare il punto e virgola finale. La condizione indica quando RIPETERE: finché il segnale manca, la condizione deve essere vera.'),
            ('Python: comportamento equivalente', 'Python non ha una istruzione do while nativa. Usiamo while True: con il corpo seguito da if e break. Dopo l’output leggi segnale_trovato = int(input()). Il controllo di uscita è il contrario di segnale_trovato == 0: if not (segnale_trovato == 0): seguito da break. Il laboratorio riconosce questa forma come equivalente del do while.'),
            ('Che cosa significa break?', 'break termina immediatamente il ciclo più interno. Nel modello Python viene eseguito solo quando non devi più ripetere. Il while True non continua per sempre perché il controllo in fondo può raggiungere break.'),
        ),
    },
}

COMPARISON = (
    ('La stessa domanda, in momenti diversi', 'while e do while possono avere lo stesso corpo e la stessa condizione. Il while controlla prima; il do while controlla dopo. Guarda la missione Sei già arrivato e confrontala con Il controllo di conferma: la prima può fare zero azioni, la seconda ne deve fare almeno una.'),
    ('for e while possono esprimere lo stesso percorso', 'Cinque passi possono essere descritti da un for con cinque valori oppure da un while con un contatore inizializzato prima e aggiornato nel corpo. Il for rende vicini i dettagli del conteggio; il while rende evidente la condizione da osservare.'),
    ('Quando la condizione è falsa all’inizio', 'while: zero esecuzioni del corpo. do while: una esecuzione, poi il controllo può fermarlo. for: può fare zero esecuzioni se l’intervallo è vuoto o la prima condizione è falsa. Non scegliere il ciclo soltanto dal numero di righe: ragiona su quando deve avvenire il controllo.'),
    ('Non confondere azioni, giri e controlli', 'Un giro può contenere due azioni, per esempio avanza e raccogli. Quattro giri producono allora otto azioni. Anche i controlli hanno un loro conteggio: un while che fa quattro giri normalmente controlla cinque volte, perché l’ultimo controllo falso lo fa uscire.'),
)

from native_context import INPUT_PROTOCOL

HELP = (
    ('Il programma del robot', 'Il frammento usa le funzioni standard di output e input del linguaggio. Le funzioni stampano testo nel terminale; il gioco interpreta i messaggi e anima il robot. Il contesto completo qui sopra mostra import, main e Scanner dove necessari.'),
    ('Messaggi e azioni', 'I testi avanza, sinistra, destra, raccogli, accendi e scansiona sono il protocollo del gioco. Stampa uno di questi messaggi per riga con la funzione standard del linguaggio.'),
    ('Input e memoria', INPUT_PROTOCOL),
    ('Sintassi disponibile', 'Puoi usare for con contatore e passo, while, do while (equivalente in Python), if/else e break. Le espressioni supportano interi, +, -, *, <, <=, >, >=, ==, != e condizioni logiche. Python usa and, or, not; gli altri linguaggi &&, ||, !. Il for con graffe usa ++, --, += oppure -= per aggiornare il contatore. Le graffe sono obbligatorie per rendere evidente il corpo.'),
    ('Scrivere e correggere', 'Completa i ??? seleziona la parte mancante; Scrivi qui attiva il cursore in fondo alla bozza. Puoi anche cliccare una riga. Invio va a capo; Ctrl+Invio controlla il programma. Tab inserisce quattro spazi. Ctrl+A seleziona tutto; Ctrl+C, Ctrl+X e Ctrl+V copiano, tagliano e incollano; Ctrl+Z annulla e Ctrl+Y ripristina. Rotella e Shift+rotella scorrono il codice, anche nella traccia. Una modifica azzera la verifica precedente, conservando il testo.'),
    ('Un laboratorio guidato', 'L’editor comprende il sottoinsieme di istruzioni descritto qui, con numeri interi tra -10000 e 10000. Non è un ambiente completo per eseguire qualsiasi programma nei quattro linguaggi. Le stesse missioni funzionano offline e non richiedono compilatori installati.'),
)
