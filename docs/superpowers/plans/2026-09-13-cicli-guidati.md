# Cicli guidati: piano di implementazione

> Esecuzione inline con executing-plans, revisione indipendente prima della pubblicazione.

**Obiettivo:** rendere espliciti osservazione, scrittura e risultato nel laboratorio dei cicli.
**Architettura:** guidance.py per le consegne; guided_ui.py per i pannelli; main.py per le interazioni. Conservare il parser e l'interprete esistenti.
**Tecnologie:** Python, Pygame e PyInstaller già presenti, nessuna nuova dipendenza.

## Vincoli globali
Nove missioni, Python/JavaScript/C/Java, Facile/Medio/Difficile, Notte/Giorno/Contrasto, salvataggi e bozze separati. EXE e ZIP offline completi. Aggiornare soltanto robot_e_cicli dopo la verifica della copia di lavoro.

## Passi
- [x] Creare tests/test_guidance.py. Provare selezione e sostituzione dei segnaposti, Ctrl+Invio senza newline, conferma immediata del risultato, invalidazione dopo modifica, traccia senza alterare cursore o bozza, previsioni corrette/errate e passaggio da Impara al gioco. Eseguire `python -m unittest discover -s tests -p test_guidance.py -q` prima e dopo l'implementazione.
- [x] Implementare `first_gap(code, language)`, `writing_task(mission, code, language)`, `writing_sections(mission, language, code, easy)` ed esempi validi. Ignorare segnaposti nei commenti e preservare rientri/punteggiatura. Verificare tutti i 36 esempi nel parser.
- [x] Implementare `GuidedUI` con programma a sinistra e griglia/risultato a destra; adattare coordinate di trascinamento, selezione automatica, verifica diretta e traccia in un editor separato. Il risultato della verifica resta leggibile durante la correzione finché il programma non cambia.
- [x] Aggiungere nove previsioni con tre scelte, spiegazione specifica e pulsante di esecuzione. Rendere disponibili gli equivoci da Impara e Gioca. Controllare zero giri, azioni senza spostamento, rientri Python e condizione finale inversa del do while.
- [x] Eseguire suite completa, controllo automatico di impaginazione, schermate a 1440 e 960 pixel, revisione indipendente. Aggiornare README e catture incluse nelle distribuzioni.
- [ ] Ricostruire con `python build_release.py`, estrarre e provare l'EXE. Copiare solo i file verificati, salvare una copia dei precedenti, preservare progressi_cicli.json. Commit, push e confronto dei blob GitHub col commit locale.

## Verifiche del 14 settembre 2026
40 test superati. Controllo automatico di 10.854 schermate nei tre temi, quattro linguaggi e tre dimensioni: nessun testo fuori area, nessuna sintesi accorciata e nessuna sovrapposizione dei controlli. Revisione indipendente di 108 combinazioni missione/linguaggio/difficoltà; riproduzioni ripetute della traccia, salvataggi e passaggio Impara/Gioca verificati. Corretto e coperto da test il rimando alla scheda Comandi e codice.
