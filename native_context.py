"""Copyable native program context; no robot-specific host functions."""
from native_io import output_explanation, output_statement

INPUT_PROTOCOL = ('Ogni lettura riceve un intero: 1 significa sì, 0 significa no. '
    'Nel simulatore il nome della variabile identifica il dato: strada_libera guarda davanti, '
    'sulla_batteria guarda sotto il robot, sul_traguardo indica la piattaforma, segnale_trovato il segnale. '
    'Il gioco fornisce il valore attuale solo quando esegui una lettura. Nel programma esterno inserisci '
    'tu gli stessi numeri, nello stesso ordine. Il nome non crea un sensore nel linguaggio. '
    'Nel while leggi prima del controllo iniziale e di nuovo alla fine del corpo; nel do while leggi '
    'dopo le azioni, prima del controllo finale. Omettere la lettura lascia il valore precedente. '
    'I contatori della scena non sono variabili automatiche: inizializza e aggiorna i tuoi contatori.')


def standalone(source, language):
    if language in ('Python', 'JavaScript'):
        return source
    body = '\n'.join('    ' + row for row in source.splitlines())
    if language == 'C':
        return '#include <stdio.h>\n#include <stdbool.h>\n\nint main(void) {\n' + body + '\n    return 0;\n}\n'
    body = '\n'.join('    ' + row for row in body.splitlines())
    return ('import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n'
            '        Scanner input = new Scanner(System.in);\n' + body + '\n    }\n}\n')


def native_sections(mission, language):
    from engine import Node, generate
    from guidance import syntax_example
    return [('Output standard', output_explanation(language)),
            ('Input 0/1: protocollo della simulazione', INPUT_PROTOCOL),
            ('Lettura esplicita · ' + language, generate([Node('read', name='strada_libera')], language)),
            ('Messaggi riconosciuti', '\n'.join(output_statement(n, language) for n in ('avanza', 'sinistra', 'destra', 'raccogli', 'accendi', 'scansiona'))),
            ('Contesto esterno', 'Nel laboratorio scrivi il corpo. Questo esempio completo stampa scansiona e conta i tentativi; adattalo alla missione. ' +
             ('JavaScript usa prompt nel browser: incolla nella console del browser e rispondi alle finestre di input.' if language == 'JavaScript' else
              'Python legge dal terminale.' if language == 'Python' else
              'C richiede stdio.h e main.' if language == 'C' else 'Java richiede Scanner; salva come Main.java.')),
            ('Il programma completo · ' + language, standalone(syntax_example(mission, language), language))]
