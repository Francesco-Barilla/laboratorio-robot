IL LABORATORIO DEI ROBOT
Realizzato dal Prof. Barillà Francesco

AVVIO
Fai doppio clic su LaboratorioRobot.exe, accanto a questo file.
In alternativa usa Avvia_Robot.cmd.
Per distribuirlo: usa dist/LaboratorioRobot-Windows.zip e fai estrarre
tutto lo ZIP in una cartella personale prima di avviare il programma.
La versione Windows non richiede Python o compilatori installati.

IMPARA
Scegli un linguaggio e una missione. Leggi il codice e la scena, poi
scegli A, B o C. La spiegazione ti aiuta a correggere la previsione.
Dopo la risposta corretta, premi Osserva l'esecuzione.
Spiegami il ciclo apre la guida; Equivoci da evitare chiarisce gli errori
più comuni. Zero passi possono essere corretti: osserva giri e controlli.

GIOCA
Scegli liberamente Facile, Medio o Difficile:
- Facile: scegli ripetizioni o condizione, poi aggiungi i comandi con +.
  Le frecce cambiano l'ordine nel corpo; puoi anche trascinare i blocchi.
- Medio: premi Completa i ??? e digita soltanto il numero o comando
  richiesto. Mantieni il resto del codice già presente.
- Difficile: premi Scrivi qui e scrivi il ciclo. Cosa devo scrivere?
  mostra un esempio completo nel linguaggio scelto.
Controlla i blocchi o Controlla il mio programma verifica subito l'esito.
Il pannello destro confronta ciò che è richiesto con ciò che è successo.
Passo passo apre la traccia da osservare, senza cambiare il tentativo.
Devi raggiungere l'obiettivo usando il ciclo richiesto.
I suggerimenti sono sempre disponibili; la soluzione si legge soltanto
su richiesta e non completa automaticamente la missione.

9 missioni, 3 cicli (for, while, do while), 4 linguaggi
(Python, JavaScript, C, Java), 3 difficoltà.
L'editor didattico supporta le istruzioni elencate in Comandi e codice;
non sostituisce un ambiente di sviluppo completo.
Python mostra un equivalente del do while con while True, if e break.

F11: schermo intero. Esc: chiudi scheda o torna indietro.
Codice: Invio va a capo, Ctrl+Invio controlla. Ctrl+A/C/X/V, Ctrl+Z/Y,
Tab per rientrare; Shift+rotella per righe lunghe anche nella traccia.
Bozze, scelte e progressi sono salvati in progressi_cicli.json.
Il salvataggio appartiene a questa copia locale dell'app, senza account.

Dettagli tecnici, limiti e istruzioni per ricostruire: README.md.

Le vecchie bozze con funzioni del gioco vengono conservate: il controllo spiega come correggerle usando output e input standard.


PROGRESSI E REPORT PER IL DOCENTE
Il pulsante Progressi e report è sempre in basso. Mostra missioni Gioca
completate, risposte corrette, errori e percentuale di errore:
errori / risposte effettivamente controllate x 100. Senza risposte compare —.
Impara, Gioca e Quiz sono distinti. Ogni verifica del programma conta come
un tentativo, non come un tentativo per ciascun caso automatico.
Ripetere lo stesso controllo senza cambiare risposta non aggiunge tentativi;
una risposta modificata viene contata. Rivedere una traccia non conta.
Sono visibili anche aiuti e soluzioni consultati. I vecchi completamenti
restano; non vengono inventati tentativi o errori antecedenti all'aggiornamento.
Inserisci facoltativamente un nome/codice: identifica l'intero storico di
questa copia. Esporta report CSV crea un file nella cartella report accanto
ai progressi, con tutti i linguaggi/livelli e dettaglio delle attività.
Il registro è locale e modificabile, non sincronizzato né una prova
antimanomissione. Per il controllo in classe, raccogli i CSV degli studenti.
