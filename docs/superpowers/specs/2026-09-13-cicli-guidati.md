# Cicli: capire, programmare, verificare

La richiesta è applicare al laboratorio dei robot la chiarezza già approvata per Stazione delle scelte e Officina dei dati. La revisione conserva nove missioni, quattro linguaggi, tre difficoltà, temi, progressi e distribuzione offline.

## Scelta progettuale

Due pannelli numerati rendono visibili il compito e il suo risultato. La sola riscrittura delle etichette lascerebbe ambiguo il rapporto tra verifica ed esecuzione; una riscrittura completa del gioco eliminerebbe attività già valide. Si aggiorna quindi l'interfaccia esistente e si conserva il motore verificato.

Gioca: a sinistra si costruisce il programma; a destra si vedono griglia, stato iniziale o finale e risultato. Facile distingue numero/condizione e comandi del corpo, con clic e trascinamento. Medio spiega se manca un numero o un comando e seleziona solo il segnaposto. Difficile parte da un editor vuoto; gli aiuti mostrano frammenti validi, senza main o definizioni dei comandi. Ctrl+Invio verifica. Il controllo presenta subito successo o errore, criteri raggiunti e mancanti; la successiva traccia è separata e non modifica il tentativo.

Impara: si osserva la scena e il codice, si risponde a una domanda specifica e si segue l'esecuzione. L'errore resta visibile e permette un nuovo tentativo. La correttezza non dipende dal movimento: il while può fare zero giri, una scansione non sposta il robot. La spiegazione evidenzia controllo, corpo, aggiornamento e uscita.

Gli equivoci diventano espliciti: limite escluso, contatore che parte da zero, giri diversi dalle azioni, ordine del corpo, sensori diversi dai comandi, condizione di ripetizione e di uscita, almeno un giro del do while, possibilità di un ciclo che non termina. In Python il do while resta un equivalente con controllo finale e break.

## Architettura e verifica

`guidance.py` contiene consegne, domande ed esempi; `guided_ui.py` disegna le nuove attività e la traccia; `main.py` gestisce focus, verifica e navigazione. L'interprete conserva limiti e criteri didattici. Si controllano interazioni reali, traduzioni, risultato prima/dopo correzione, salvataggi separati e geometria delle schermate nei tre temi e dimensioni di testo. L'EXE viene provato anche estratto dallo ZIP. Pubblicazione su Francesco-Barilla/laboratorio-robot con confronto completo dei file e conservazione del salvataggio locale.
