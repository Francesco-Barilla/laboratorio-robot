# Il laboratorio dei robot

Realizzato dal **Prof. Barillà Francesco**. Laboratorio offline per alunni di prima superiore: robot su una griglia, spiegazioni dei cicli ed esercizi in Python, JavaScript, C e Java.

## Avvio

Questo repository contiene i sorgenti del laboratorio. Puoi avviarli con Python oppure costruire localmente l?eseguibile Windows x64 seguendo la sezione Ricostruzione. Gli eseguibili e i progressi personali non sono inclusi nei file del repository. Il gioco funziona offline, senza account.

Per avviare i sorgenti con Python 3.10 o successivo:

```text
python -m pip install -r requirements.txt
python main.py
```

## Percorso didattico

- **Impara**: nove esempi con guida scorrevole, concetti, confronto tra cicli e codice nel linguaggio scelto. Esecuzione automatica, pausa, avanti e indietro. Aprire una spiegazione congela la simulazione fino alla chiusura.
- **Gioca**: nove missioni, tutte accessibili in tre difficoltà. Facile: blocchi trascinabili o aggiunti con un clic, riordinabili anche con frecce; Medio: completamento di codice; Difficile: scrittura del programma. La difficoltà cambia gli strumenti disponibili sulla stessa missione.
- **Feedback**: riga e blocco attivo, sensori, contatori, errori legati allo stato effettivo del robot, tremolio in caso di errore, suggerimenti progressivi e soluzione consultabile. La soluzione non compila il tentativo né assegna la vittoria.
- **Interfaccia**: card con bordo luminoso e cursore a mano, tre temi (Notte, Giorno, Contrasto), testo ingrandibile, F11, velocità da 0.5× a 3×, ridimensionamento proporzionale e firma in ogni schermata.

| Ciclo | Missioni | Concetti |
|---|---|---|
| for | Il pontile solare; La scorta di energia; Accendi la base | Limite escluso, più azioni per giro, ordine delle azioni |
| while | Il corridoio sicuro; Segui le batterie; Sei già arrivato | Sensori, controllo prima, zero esecuzioni |
| do while | Un messaggio dallo spazio; Partenza obbligatoria; Il controllo di conferma | Controllo dopo, almeno una esecuzione |

## Regole del gioco

L'obiettivo fisico da solo non basta. Il ciclo richiesto deve essere raggiunto e le azioni del robot devono avvenire al suo interno. Un ciclo inutilizzato, azioni eseguite manualmente fuori dal ciclo o un ciclo di altro tipo non superano la missione. Nei for è richiesta una ripetizione effettiva: un solo giro con tutte le azioni duplicate non basta. I cicli annidati dello stesso tipo sono supportati, ma non richiesti nelle missioni introduttive.

La missione del while con zero giri verifica che ci sia un comando avanza nel corpo e che la guardia distingua il traguardo da una posizione precedente: un while False vuoto non è una soluzione didattica. La missione di conferma richiede esattamente una scansione.

I controlli e le ripetizioni sono contatori didattici: non sono misure di prestazioni. Nel for Python il controllo rappresenta la disponibilità del prossimo valore di range. Nel do while equivalente in Python viene contato il controllo di uscita in fondo, senza contare la condizione costante True del contenitore while.

## Linguaggi: ambito dell'editor

È un **interprete didattico di frammenti**, non un IDE o un compilatore completo. Le istruzioni accettate sono mostrate nella scheda Comandi e codice. Lo studente scrive il frammento della missione senza import, definizioni, classi, main o accesso al sistema.

- Comandi senza argomenti: `avanza()`, `sinistra()`, `destra()`, `raccogli()`, `accendi()`, `scansiona()`.
- Sensori booleani: `strada_libera()`, `sulla_batteria()`, `sul_traguardo()`, `segnale_trovato()`.
- Contatori del robot in sola lettura: `passi`, `raccolte`, `accese`, `scansioni`.
- Variabili intere, assegnazioni, `+=`, `-=`, confronti, `+`, `-`, `*`, condizioni logiche, `if/else`, `break`, cicli. Interi limitati all'intervallo -10000…10000; non sono disponibili divisione, stringhe, array, funzioni o librerie esterne.
- Python: for su `range`, while, if con rientri. Il do while è mostrato come `while True` con controllo finale `if ...: break`. La condizione di uscita è il contrario di quella di ripetizione; si semplificano le doppie negazioni negli esempi.
- JavaScript, C, Java: blocchi con graffe obbligatorie, punto e virgola, for con contatore intero, confronto al limite e aggiornamento `++`, `--`, `+=`, `-=`. Dichiarazioni mostrate con `let` o `int`. Queste forme condividono un parser didattico: non vengono implementati tutti i sistemi di tipi, scope e conversioni dei linguaggi completi.

Le differenze del for sono rispettate: Python prepara range una volta e prende i valori successivi; il for classico ricontrolla il limite e aggiorna il contatore dopo il corpo. Cambiare il contatore nel corpo ha perciò effetti diversi. La traduzione automatica serve per i frammenti delle missioni: non garantisce equivalenza per tutti i programmi arbitrari, in particolare se cambiano limite o contatore nel corpo.

Il codice non viene passato a `eval`, `exec`, shell o runtime esterni. L'esecuzione è limitata a 1400 passaggi, 250 righe, 14000 caratteri e 12 livelli di annidamento. Superare il limite produce una pausa con diagnosi, non una dichiarazione automatica che il ciclo sia infinito.

## Salvataggi e tastiera

Preferenze, progressi e bozze vengono salvati atomicamente in `progressi_cicli.json`, accanto all'eseguibile (o al sorgente). I progressi distinguono missione, difficoltà e linguaggio; i blocchi sono condivisi tra i linguaggi. Ogni livello con editor ha la propria bozza per linguaggio. Se si cambia linguaggio, una bozza già esistente viene conservata; in sua assenza si traduce il codice valido. Un tentativo incompleto resta disponibile tornando al linguaggio precedente.

La modalità Impara non sovrascrive i tentativi del gioco. Le impostazioni conservano codice e posizione della simulazione. Per ricominciare un testo si usa il pulsante dedicato con conferma; Riparti ripristina solo la scena.

F11 per schermo intero; Esc chiude le schede; Tab ed Invio navigano tra i pulsanti. Nell'editor Tab inserisce quattro spazi, Ctrl+A/C/X/V selezionano e usano gli appunti, Ctrl+Z/Y annullano e ripristinano. Le frecce muovono il cursore; Shift estende la selezione. La rotella scorre verticalmente, Shift+rotella orizzontalmente. Le spiegazioni supportano anche Home, End e Pagina su/giù.

## Struttura e ricostruzione

- `main.py`: navigazione, missioni, simulazione e interazioni.
- `engine.py`: parser, rappresentazione dei cicli, generazione del codice e interprete con stato verificabile.
- `missions.py`: nove missioni, soluzioni e suggerimenti.
- `lessons.py`: testi originali delle spiegazioni.
- `ui.py`: disegno vettoriale del robot, griglia, temi, editor.
- `storage.py`: salvataggi validati.
- `tests/test_robot_lab.py`: verifiche del motore, delle regole e delle interazioni.

```text
python -m unittest discover -s tests -v
python main.py --smoke-test smoke.json
python -m pip install pyinstaller==6.20.0
python build_release.py
```

`build_release.py` esegue i test, costruisce LaboratorioRobot.exe, verifica l'eseguibile senza aprire finestre e produce i due ZIP in dist. Non include i progressi personali negli archivi. Chiudere il programma prima di ricostruire il suo eseguibile. Il file `LaboratorioRobot.spec` e l'icona originale sono inclusi nei sorgenti.

## Riferimenti per la didattica

Sintassi e differenze sono state confrontate con la [documentazione Python](https://docs.python.org/3/reference/compound_stmts.html), le [specifiche ECMAScript](https://tc39.es/ecma262/multipage/ecmascript-language-statements-and-declarations.html#sec-iteration-statements), la [Java Language Specification](https://docs.oracle.com/javase/specs/jls/se25/html/jls-14.html) e la [bozza pubblica C11 N1570, §6.8.5](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf). I testi del laboratorio e la grafica sono originali; le licenze dei componenti distribuiti sono in LICENZE.txt.
