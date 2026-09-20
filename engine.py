"""Bounded, deterministic interpreter for the robot classroom language.

Only the explicitly supported syntax is interpreted. Student code is never
passed to eval/exec, a shell, or an installed language runtime.
"""
from dataclasses import dataclass, field
import ast
import copy
import re
from native_io import output_message, output_statement

LANGUAGES = ('Python', 'JavaScript', 'C', 'Java')
COMMANDS = {'avanza': 'Avanza', 'sinistra': 'Gira a sinistra', 'destra': 'Gira a destra',
            'raccogli': 'Raccogli batteria', 'accendi': 'Accendi lampada', 'scansiona': 'Scansiona segnale'}
SENSORS = ('strada_libera', 'sulla_batteria', 'sul_traguardo', 'segnale_trovato')
READONLY = {'passi', 'raccolte', 'accese', 'scansioni'}


class CodeError(Exception):
    def __init__(self, message, line=1):
        super().__init__(message)
        self.line = line


@dataclass
class Node:
    kind: str
    line: int = 1
    value: str = ''
    name: str = ''
    body: list = field(default_factory=list)
    other: list = field(default_factory=list)
    start: str = '0'
    stop: str = '1'
    step: str = '1'
    endline: int = 1
    scoped: bool = True
    declares: bool = False


def expression(value):
    """Normalize only the common, documented expression subset."""
    value = re.sub(r'\btrue\b', 'True', value)
    value = re.sub(r'\bfalse\b', 'False', value)
    value = value.replace('&&', ' and ').replace('||', ' or ')
    value = re.sub(r'!(?!=)', ' not ', value)
    return value.strip()


def expr_tree(value, line=1):
    try:
        tree = ast.parse(expression(value), mode='eval').body
    except (SyntaxError, ValueError, RecursionError):
        raise CodeError('Controlla la condizione: usa un sensore oppure un confronto, per esempio i < 5.', line)
    allowed = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.Call, ast.UnaryOp,
               ast.Not, ast.USub, ast.UAdd, ast.BinOp, ast.Add, ast.Sub, ast.Mult,
               ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)
    for item in ast.walk(tree):
        if not isinstance(item, allowed):
            raise CodeError('Qui sono disponibili interi, sensori, +, -, *, confronti e condizioni logiche.', line)
        if isinstance(item, ast.Constant) and (type(item.value) not in (int, bool) or abs(item.value) > 10000):
            raise CodeError('Usa numeri interi tra -10000 e 10000 oppure valori vero/falso.', line)
        if isinstance(item, ast.Call):
            raise CodeError('Leggi prima il sensore in una variabile con input (o prompt, scanf, nextLine), poi confrontala con 0. Le vecchie funzioni sensore non esistono.', line)
    return tree


def check_name(name, line):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,23}', name) or name in COMMANDS:
        raise CodeError('Scegli un nome di variabile come i o contatore.', line)


def negate(value):
    tree = expr_tree(value)
    return ast.unparse(tree.operand) if isinstance(tree, ast.UnaryOp) and isinstance(tree.op, ast.Not) else 'not (' + ast.unparse(tree) + ')'


def python_nodes(items):
    out = []
    for item in items:
        line = item.lineno
        if isinstance(item, ast.Expr) and isinstance(item.value, ast.Call):
            try:
                message = output_message(ast.unparse(item.value), 'Python')
            except ValueError as err:
                raise CodeError(str(err), line) from None
            out.append(Node('command', line, name=message))
        elif isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
            value = ast.unparse(item.value)
            out.append(Node('read' if value == 'int(input())' else 'assign', line, value, item.targets[0].id))
        elif isinstance(item, ast.AugAssign) and isinstance(item.target, ast.Name) and isinstance(item.op, (ast.Add, ast.Sub)):
            op = '+' if isinstance(item.op, ast.Add) else '-'
            out.append(Node('assign', line, f'{item.target.id} {op} ({ast.unparse(item.value)})', item.target.id))
        elif isinstance(item, ast.While) and not item.orelse:
            body = item.body
            # Recognize the taught Python equivalent of a post-test loop.
            if (isinstance(item.test, ast.Constant) and item.test.value is True and body and
                isinstance(body[-1], ast.If) and not body[-1].orelse and
                len(body[-1].body) == 1 and isinstance(body[-1].body[0], ast.Break)):
                out.append(Node('do', line, negate(ast.unparse(body[-1].test)), body=python_nodes(body[:-1]), endline=body[-1].lineno))
            else:
                out.append(Node('while', line, ast.unparse(item.test), body=python_nodes(body)))
        elif isinstance(item, ast.For) and isinstance(item.target, ast.Name) and not item.orelse:
            call = item.iter
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != 'range' or not 1 <= len(call.args) <= 3 or call.keywords:
                raise CodeError('In questo laboratorio usa for i in range(inizio, fine, passo):. Puoi anche scrivere range(5).', line)
            args = [ast.unparse(x) for x in call.args]
            if len(args) == 1:
                args = ['0', args[0]]
            if len(args) == 2:
                args.append('1')
            out.append(Node('for', line, name=item.target.id, body=python_nodes(item.body), start=args[0], stop=args[1], step=args[2], scoped=False))
        elif isinstance(item, ast.If):
            out.append(Node('if', line, ast.unparse(item.test), body=python_nodes(item.body), other=python_nodes(item.orelse)))
        elif isinstance(item, ast.Break):
            out.append(Node('break', line))
        elif isinstance(item, ast.Pass):
            out.append(Node('pass', line))
        else:
            raise CodeError('Istruzione non disponibile. Usa cicli, if, variabili intere e i comandi del robot. Scrivi soltanto il corpo del programma.', line)
    return out


class BraceParser:
    def __init__(self, source, language):
        self.language = language
        # Consume quoted literals before comments, keeping contents and line numbers.
        source = re.sub(
            r'"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|/\*.*?\*/|//[^\n]*',
            lambda m: re.sub(r'[^\n]', ' ', m[0]) if m[0].startswith(('/*', '//')) else m[0],
            source, flags=re.S)
        self.tokens = [(m[0], source.count('\n', 0, m.start()) + 1) for m in re.finditer(r'"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|\+\+|--|\+=|-=|<=|>=|==|!=|&&|\|\||[A-Za-z_]\w*|\d+|[^\s]', source)]
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else ''

    def take(self, expected=None):
        if self.pos >= len(self.tokens):
            raise CodeError(f'Manca {expected or "una istruzione"} alla fine del programma.', self.tokens[-1][1] if self.tokens else 1)
        token, line = self.tokens[self.pos]
        if expected and token != expected:
            raise CodeError(f'Qui serve «{expected}», ma hai scritto «{token}». Controlla parentesi e punto e virgola.', line)
        self.pos += 1
        return token

    def until(self, marker):
        tokens, depth = [], 0
        while self.peek():
            if self.peek() == marker and depth == 0:
                self.take(marker)
                return ' '.join(tokens)
            t = self.take()
            depth += (t == '(') - (t == ')')
            tokens.append(t)
        raise CodeError(f'Manca «{marker}».', self.tokens[-1][1] if self.tokens else 1)

    def condition(self):
        self.take('(')
        return self.until(')')

    def block(self, depth=0):
        if depth > 12:
            raise CodeError('Ci sono troppi blocchi annidati: prova a semplificare il programma.')
        self.take('{')
        nodes = []
        while self.peek() != '}':
            nodes.append(self.statement(depth + 1))
        self.take('}')
        return nodes

    def statement(self, depth=0):
        if self.pos >= len(self.tokens):
            raise CodeError('Manca la parentesi graffa di chiusura }.')
        line = self.tokens[self.pos][1]
        token = self.peek()
        if token in ('while', 'if'):
            self.take()
            value = self.condition()
            node = Node(token, line, value, body=self.block(depth))
            if token == 'if' and self.peek() == 'else':
                self.take()
                node.other = self.block(depth)
            return node
        if token == 'do':
            self.take()
            body = self.block(depth)
            end = self.tokens[self.pos][1] if self.pos < len(self.tokens) else line
            self.take('while')
            value = self.condition()
            self.take(';')
            return Node('do', line, value, body=body, endline=end)
        if token == 'for':
            self.take()
            self.take('(')
            initial = self.until(';')
            condition = self.until(';')
            update = self.until(')')
            declaration = re.match(r'^(int|let|var)\s+', initial)
            if declaration and declaration[1] not in (('let', 'var') if self.language == 'JavaScript' else ('int',)):
                raise CodeError('Usa let nel for JavaScript oppure int nel for C/Java.', line)
            scoped = bool(re.match(r'^(int|let)\s+', initial))
            initial = re.sub(r'^(int|let|var)\s+', '', initial)
            match = re.fullmatch(r'(\w+)\s*=\s*(.+)', initial)
            if not match:
                raise CodeError('Inizializza il contatore: per esempio for (int i = 0; i < 5; i++).', line)
            name, start = match.groups()
            cmp = re.fullmatch(rf'{re.escape(name)}\s*(<=|>=|<|>)\s*(.+)', condition)
            inc = re.fullmatch(rf'{re.escape(name)}\s*(\+\+|--|\+=|-=)\s*(.*)', update)
            if not cmp or not inc:
                raise CodeError('Usa lo stesso contatore nelle tre parti del for: i = 0; i < 5; i++. Sono disponibili anche --, += e -=.', line)
            op, stop = cmp.groups()
            change, amount = inc.groups()
            if change in ('++', '--') and amount:
                raise CodeError('Dopo ++ o -- non serve un numero.', line)
            if change in ('+=', '-=') and not amount:
                raise CodeError('Dopo += o -= scrivi il passo del contatore.', line)
            step = '1' if change == '++' else '-1' if change == '--' else amount if change == '+=' else f'-({amount})'
            if op == '<=':
                stop = f'({stop}) + 1'
            elif op == '>=':
                stop = f'({stop}) - 1'
            return Node('for', line, name=name, start=start, stop=stop, step=step, body=self.block(depth), value=op[0], scoped=scoped, declares=bool(declaration))
        statement = self.until(';').strip()
        if statement in ('break', ''):
            return Node('break' if statement else 'pass', line)
        compact = re.sub(r'\s+', '', statement)
        if self.language == 'C':
            read = re.fullmatch(r'scanf\("%d",&(\w+)\)', compact)
            if read:
                return Node('read', line, name=read[1], scoped=False)
        read_pattern = r'(?:(let|var)\s+)?(\w+)\s*=\s*Number\s*\(\s*prompt\s*\(\s*\)\s*\)' if self.language == 'JavaScript' else r'(?:(int)\s+)?(\w+)\s*=\s*Integer\s*\.\s*parseInt\s*\(\s*input\s*\.\s*nextLine\s*\(\s*\)\s*\)' if self.language == 'Java' else r'(?!)'
        read = re.fullmatch(read_pattern, statement)
        if read:
            return Node('read', line, name=read[2], scoped=bool(read[1]))
        declaration = re.fullmatch(r'(int|let|var)\s+(\w+)', statement)
        if declaration:
            if declaration[1] not in (('let', 'var') if self.language == 'JavaScript' else ('int',)):
                raise CodeError('Usa la dichiarazione del linguaggio selezionato.', line)
            return Node('declare', line, name=declaration[2])
        if re.match(r'[\w. ]+\s*\(', statement):
            try:
                message = output_message(statement, self.language)
            except ValueError as err:
                raise CodeError(str(err), line) from None
            return Node('command', line, name=message)
        declaration = re.match(r'^(int|bool|boolean|let|var|const)\s+', statement)
        if declaration and declaration[1] not in (('let', 'var') if self.language == 'JavaScript' else ('int',)):
            raise CodeError('Usa let in JavaScript oppure int in C e Java.', line)
        statement = re.sub(r'^(int|bool|boolean|let|var|const)\s+', '', statement)
        assign = re.fullmatch(r'(\w+)\s*(=|\+=|-=|\+\+|--)\s*(.*)', statement)
        if assign:
            name, op, value = assign.groups()
            if op in ('++', '--'):
                value = f'{name} {op[0]} 1'
            elif op in ('+=', '-='):
                value = f'{name} {op[0]} ({value})'
            return Node('assign', line, value, name, scoped=bool(declaration))
        raise CodeError('Istruzione non riconosciuta. Usa output e input standard: apri «Comandi e codice» per la sintassi.', line)

    def parse(self):
        out = []
        while self.peek():
            out.append(self.statement())
        return out


def placeholder_index(source, language):
    """Find unfinished code, leaving comments and quoted text alone."""
    i = 0
    while i < len(source):
        if (language == 'Python' and source[i] == '#') or (language != 'Python' and source.startswith('//', i)):
            end = source.find('\n', i)
            i = len(source) if end < 0 else end + 1
        elif source[i] in ('"', "'"):
            quote = source[i]
            i += 1
            while i < len(source):
                if source[i] == '\\':
                    i += 2
                elif source[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
        elif source.startswith('???', i):
            return i
        else:
            i += 1
    return -1


def parse(source, language):
    if language not in LANGUAGES:
        raise CodeError('Linguaggio non disponibile.')
    if len(source) > 14000 or source.count('\n') > 250:
        raise CodeError('Il laboratorio accetta programmi fino a 250 righe e 14000 caratteri.')
    gap = placeholder_index(source, language)
    if gap >= 0:
        raise CodeError('Completa il punto indicato con ??? prima di eseguire.', source[:gap].count('\n') + 1)
    try:
        if language == 'Python':
            nodes = python_nodes(ast.parse(source).body)
        else:
            nodes = BraceParser(source, language).parse()
    except (SyntaxError, IndentationError) as err:
        raise CodeError('Controlla la sintassi e i rientri: dopo for, while o if serve «:» e il corpo va rientrato di quattro spazi.', err.lineno or 1)
    except RecursionError:
        raise CodeError('Il programma è troppo annidato: semplifica parentesi e blocchi.')

    def validate(nodes, loops=0, depth=0):
        if depth > 12:
            raise CodeError('Sono consentiti al massimo 12 blocchi annidati.')
        for node in nodes:
            if node.kind == 'command' and node.name not in COMMANDS:
                raise CodeError(f'«{node.name}» non è un comando del robot. Apri «Comandi e codice» per vedere quelli disponibili.', node.line)
            if node.kind in ('assign', 'for', 'read', 'declare'):
                check_name(node.name, node.line)
            if node.kind == 'read' and node.name not in SENSORS:
                raise CodeError('Il protocollo di questa simulazione fornisce input 0/1 soltanto a: ' + ', '.join(SENSORS) + '.', node.line)
            if node.kind in ('assign', 'while', 'do', 'if'):
                expr_tree(node.value, node.line)
            if node.kind == 'for':
                for value in (node.start, node.stop, node.step):
                    expr_tree(value, node.line)
            if node.kind == 'break' and not loops:
                raise CodeError('break può essere usato soltanto dentro un ciclo.', node.line)
            validate(node.body, loops + (node.kind in ('for', 'while', 'do')), depth + 1)
            validate(node.other, loops, depth + 1)
    validate(nodes)
    if language != 'Python':
        def integer(tree):
            return (isinstance(tree, ast.Constant) and type(tree.value) is int or
                    isinstance(tree, ast.Name) or
                    isinstance(tree, ast.UnaryOp) and isinstance(tree.op, (ast.USub, ast.UAdd)) and integer(tree.operand) or
                    isinstance(tree, ast.BinOp) and integer(tree.left) and integer(tree.right))

        def boolean(tree):
            return (isinstance(tree, ast.Compare) or
                    isinstance(tree, ast.Constant) and type(tree.value) is bool or
                    isinstance(tree, ast.UnaryOp) and isinstance(tree.op, ast.Not) and boolean(tree.operand) or
                    isinstance(tree, ast.BoolOp) and all(boolean(v) for v in tree.values))
        def names(items, outer):
            declared = set(outer)
            for n in items:
                if n.kind == 'for' and not n.declares and n.name not in declared:
                    raise CodeError('Dichiara prima ' + n.name + (' con let.' if language == 'JavaScript' else ' con int.'), n.line)
                if language == 'Java':
                    values = (n.value,) if n.kind == 'assign' else (n.start, n.stop, n.step) if n.kind == 'for' else ()
                    if any(not integer(expr_tree(value, n.line)) for value in values):
                        raise CodeError('Una variabile int richiede un valore intero. In Java true, false e i confronti sono booleani, non numeri 0 e 1.', n.line)
                if n.kind in ('declare', 'assign', 'read'):
                    if n.kind == 'declare' or n.scoped:
                        if n.name in declared:
                            raise CodeError('Variabile già dichiarata: usa una semplice assegnazione per aggiornarla.', n.line)
                        declared.add(n.name)
                    elif n.name not in declared:
                        raise CodeError('Dichiara prima ' + n.name + (' con let.' if language == 'JavaScript' else ' con int.'), n.line)
                if language == 'Java' and n.kind in ('while', 'do', 'if') and not boolean(expr_tree(n.value, n.line)):
                    raise CodeError('Java richiede una condizione booleana: confronta il sensore intero con 0, per esempio strada_libera != 0.', n.line)
                inner = declared | ({n.name} if n.kind == 'for' else set())
                names(n.body, inner)
                names(n.other, declared)
        names(nodes, set())
    return nodes


def format_expr(value, language):
    tree = expr_tree(value)
    if language == 'Python':
        return ast.unparse(tree)

    def render(e):
        if isinstance(e, ast.Constant):
            return str(e.value).lower()
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.Call):
            return e.func.id + '()'
        if isinstance(e, ast.UnaryOp):
            op = '!' if isinstance(e.op, ast.Not) else '-' if isinstance(e.op, ast.USub) else '+'
            return op + '(' + render(e.operand) + ')'
        if isinstance(e, ast.BinOp):
            op = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*'}[type(e.op)]
            return f'({render(e.left)} {op} {render(e.right)})'
        if isinstance(e, ast.BoolOp):
            return '(' + (' && ' if isinstance(e.op, ast.And) else ' || ').join(render(v) for v in e.values) + ')'
        ops = {ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>=', ast.Eq: '==', ast.NotEq: '!='}
        values = [e.left] + e.comparators
        return '(' + ' && '.join(f'{render(a)} {ops[type(op)]} {render(b)}' for a, op, b in zip(values, e.ops, values[1:])) + ')'
    return render(tree)


def generate(nodes, language):
    lines = []
    declared = set()
    py = language == 'Python'
    def input_names(items):
        for n in items:
            if n.kind in ('read', 'declare'):
                yield n.name
            yield from input_names(n.body)
            yield from input_names(n.other)
    if not py:
        for name in dict.fromkeys(input_names(nodes)):
            lines.append(('let ' if language == 'JavaScript' else 'int ') + name + ';')
            declared.add(name)

    def emit(items, level=0):
        prefix = '    ' * level
        if not items:
            lines.append(prefix + ('pass' if py else '// aggiungi un comando'))
        for n in items:
            n.line = len(lines) + 1
            ex = lambda value: format_expr(value, language)
            if n.kind == 'command':
                lines.append(prefix + output_statement(n.name, language))
            elif n.kind == 'declare':
                if not py and n.name not in declared:
                    lines.append(prefix + ('let ' if language == 'JavaScript' else 'int ') + n.name + ';')
                    declared.add(n.name)
            elif n.kind == 'read':
                if language == 'C':
                    if n.name not in declared:
                        lines.append(prefix + 'int ' + n.name + ';')
                    lines.append(prefix + 'scanf("%d", &' + n.name + ');')
                else:
                    declaration = '' if py or n.name in declared else 'let ' if language == 'JavaScript' else 'int '
                    call = {'Python': 'int(input())', 'JavaScript': 'Number(prompt())', 'Java': 'Integer.parseInt(input.nextLine())'}[language]
                    lines.append(prefix + declaration + n.name + ' = ' + call + ('' if py else ';'))
                declared.add(n.name)
            elif n.kind == 'assign':
                declaration = '' if py or n.name in declared else 'let ' if language == 'JavaScript' else 'int '
                declared.add(n.name)
                lines.append(prefix + declaration + n.name + ' = ' + ex(n.value) + ('' if py else ';'))
            elif n.kind in ('pass', 'break'):
                lines.append(prefix + (n.kind if py else ';' if n.kind == 'pass' else 'break;'))
            elif n.kind == 'for':
                if py:
                    lines.append(prefix + f'for {n.name} in range({ex(n.start)}, {ex(n.stop)}, {ex(n.step)}):')
                else:
                    negative = n.step.strip().startswith('-')
                    op = n.value or ('>' if negative else '<')
                    declaration = 'let' if language == 'JavaScript' else 'int'
                    lines.append(prefix + f'for ({declaration} {n.name} = {ex(n.start)}; {n.name} {op} {ex(n.stop)}; {n.name} += {ex(n.step)}) {{')
                emit(n.body, level + 1)
                if not py:
                    lines.append(prefix + '}')
            elif n.kind == 'do':
                lines.append(prefix + ('while True:' if py else 'do {'))
                emit(n.body, level + 1)
                n.endline = len(lines) + 1
                if py:
                    lines.append(prefix + '    if ' + ex(negate(n.value)) + ':')
                    lines.append(prefix + '        break')
                else:
                    lines.append(prefix + '} while (' + ex(n.value) + ');')
            else:
                lines.append(prefix + n.kind + (' ' + ex(n.value) + ':' if py else ' (' + ex(n.value) + ') {'))
                emit(n.body, level + 1)
                if not py:
                    lines.append(prefix + '}')
                if n.other:
                    lines.append(prefix + ('else:' if py else 'else {'))
                    emit(n.other, level + 1)
                    if not py:
                        lines.append(prefix + '}')
    emit(copy.deepcopy(nodes))
    return '\n'.join(lines) + '\n'


@dataclass
class World:
    x: int
    y: int
    direction: int = 0
    batteries: set = field(default_factory=set)
    lamps: set = field(default_factory=set)
    lit: set = field(default_factory=set)
    steps: int = 0
    collected: int = 0
    scans: int = 0


@dataclass
class Frame:
    world: World
    variables: dict
    line: int
    phase: str
    message: str
    iterations: int
    checks: int
    truth: object = None


@dataclass
class Result:
    frames: list
    success: bool
    goal: bool
    rule: bool
    message: str
    error_line: int = 0


class StopLoop(Exception):
    pass


class Interpreter:
    def __init__(self, mission, language, limit=1400):
        self.m = mission
        self.language = language
        self.world = World(*mission.start, batteries=set(mission.batteries), lamps=set(mission.lamps))
        self.variables = {}
        self.frames = []
        self.checks = self.iterations = 0
        self.limit = limit
        self.stack = []
        self.visited = set()
        self.covered = 0
        self.outside = 0
        self.trees = {}
        self.line = 1
        self.output = []
        self.reads = []

    def sensor(self, name):
        w = self.world
        dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[w.direction]
        pos = w.x + dx, w.y + dy
        return {'strada_libera': 0 <= pos[0] < self.m.width and 0 <= pos[1] < self.m.height and pos not in self.m.walls,
                'sulla_batteria': (w.x, w.y) in w.batteries,
                'sul_traguardo': (w.x, w.y) == self.m.goal,
                'segnale_trovato': w.scans >= self.m.signal_after}[name]

    def env(self):
        return dict(self.variables)

    def evaluate(self, value):
        if value not in self.trees:
            self.trees[value] = expr_tree(value, self.line)
        env = self.env()

        def visit(e):
            if isinstance(e, ast.Constant):
                return e.value
            if isinstance(e, ast.Name):
                if e.id not in env:
                    raise CodeError(f'La variabile {e.id} non ha ancora un valore. Inizializzala prima di usarla.', self.line)
                return env[e.id]
            if isinstance(e, ast.UnaryOp):
                v = visit(e.operand)
                return not v if isinstance(e.op, ast.Not) else -v if isinstance(e.op, ast.USub) else v
            if isinstance(e, ast.BoolOp):
                if isinstance(e.op, ast.And):
                    return all(visit(x) for x in e.values)
                return any(visit(x) for x in e.values)
            if isinstance(e, ast.BinOp):
                a, b = visit(e.left), visit(e.right)
                v = a + b if isinstance(e.op, ast.Add) else a - b if isinstance(e.op, ast.Sub) else a * b
                if abs(v) > 10000:
                    raise CodeError('Il contatore è uscito dall’intervallo del laboratorio (-10000…10000). Controlla l’aggiornamento.', self.line)
                return v
            values = [visit(e.left)]
            for op, rhs in zip(e.ops, e.comparators):
                b = visit(rhs)
                a = values[-1]
                ok = {ast.Lt: lambda: a < b, ast.LtE: lambda: a <= b, ast.Gt: lambda: a > b,
                      ast.GtE: lambda: a >= b, ast.Eq: lambda: a == b, ast.NotEq: lambda: a != b}[type(op)]()
                if not ok:
                    return False
                values.append(b)
            return True
        return visit(self.trees[value])

    def frame(self, phase, message, truth=None):
        if len(self.frames) >= self.limit:
            raise CodeError(f'Pausa di protezione dopo {self.limit} passaggi. Il programma non ha ancora terminato: controlla che contatore o sensore si avvicinino alla condizione di uscita.', self.line)
        self.frames.append(Frame(copy.deepcopy(self.world), self.env(), self.line, phase, message, self.iterations, self.checks, truth))

    def check(self, n):
        self.line = n.endline if n.kind == 'do' else n.line
        truth = bool(self.evaluate(n.value))
        self.checks += 1
        self.visited.add(n.kind)
        pretty = format_expr(n.value, self.language)
        observed = ', '.join(f'{name} = {value}' for name, value in self.env().items() if re.search(rf'\b{name}\b', n.value))
        details = observed
        if n.kind == 'do' and self.language == 'Python':
            self.frame('Controllo di uscita', f'if {format_expr(negate(n.value), self.language)}: {"FALSO, salta break e ripeti il corpo" if truth else "VERO, esegui break e termina"}. La condizione di ripetizione ({pretty}) vale {"vero" if truth else "falso"}. ' + details, not truth)
        else:
            self.frame('Condizione', f'{pretty}: {"VERO, esegui il corpo" if truth else "FALSO, esci dal ciclo"}. ' + details, truth)
        return truth

    def command(self, name):
        w = self.world
        if name == 'avanza':
            if not self.sensor('strada_libera'):
                raise CodeError('Il robot incontrerebbe un ostacolo o uscirebbe dalla griglia. Controlla quante volte avanza e quando il ciclo deve fermarsi.', self.line)
            dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[w.direction]
            w.x += dx
            w.y += dy
            w.steps += 1
            message = f'Il robot avanza di una casella. Passi compiuti: {w.steps}. Ora si trova nella colonna {w.x + 1}, riga {w.y + 1}.'
        elif name in ('sinistra', 'destra'):
            w.direction = (w.direction + (1 if name == 'destra' else -1)) % 4
            message = 'Il robot gira di 90 gradi ' + ('a destra' if name == 'destra' else 'a sinistra') + ', restando nella stessa casella.'
        elif name == 'raccogli':
            if (w.x, w.y) not in w.batteries:
                raise CodeError('In questa casella non c’è una batteria. Osserva se devi prima avanzare oppure leggere sulla_batteria con input e confrontarla con 0.', self.line)
            w.batteries.remove((w.x, w.y))
            w.collected += 1
            message = f'Batteria raccolta! Totale: {w.collected}. Rimaste sulla griglia: {len(w.batteries)}.'
        elif name == 'accendi':
            if (w.x, w.y) not in w.lamps or (w.x, w.y) in w.lit:
                raise CodeError('Qui non c’è una lampada spenta. Controlla l’ordine: accendi la lampada, poi avanza.', self.line)
            w.lit.add((w.x, w.y))
            message = f'Lampada accesa. Adesso sono accese {len(w.lit)} lampade su {len(w.lamps)}.'
        else:
            w.scans += 1
            message = f'Scansione {w.scans}: ' + ('segnale trovato!' if self.sensor('segnale_trovato') else 'segnale ancora assente. Il prossimo controllo deciderà se ripetere.')
        if self.m.loop in self.stack:
            self.covered += 1
        else:
            self.outside += 1
        self.frame('Azione', 'Output: "' + name + '". Il gioco interpreta il messaggio. ' + message)

    def execute(self, nodes):
        for n in nodes:
            self.line = n.line
            if n.kind == 'command':
                self.output.append(n.name)
                self.command(n.name)
            elif n.kind == 'declare':
                self.variables.pop(n.name, None)
                self.frame('Dichiarazione', f'{n.name}: variabile dichiarata, ancora senza valore.')
            elif n.kind == 'read':
                value = int(self.sensor(n.name))
                self.variables[n.name] = value
                self.reads.append((n.line, n.name, value))
                self.frame('Input', f'Leggi {value} dal simulatore in {n.name}. Il valore resta memorizzato fino alla prossima assegnazione o lettura.')
            elif n.kind == 'assign':
                self.variables[n.name] = self.evaluate(n.value)
                self.frame('Variabile', f'{n.name} ora vale {self.variables[n.name]}.')
            elif n.kind == 'break':
                self.frame('Uscita', 'break termina il ciclo più interno e prosegue dopo il suo corpo.')
                raise StopLoop()
            elif n.kind == 'pass':
                self.frame('Corpo vuoto', 'Nessuna azione: questo passaggio lascia tutto invariato.')
            elif n.kind == 'if':
                yes = bool(self.evaluate(n.value))
                self.frame('Scelta', f'La condizione di if è {"vera" if yes else "falsa"}.', yes)
                self.execute(n.body if yes else n.other)
            else:
                self.stack.append(n.kind)
                saved_counter = self.variables.get(n.name)
                had_counter = n.name in self.variables
                try:
                    if n.kind == 'for':
                        start, stop, step = (self.evaluate(v) for v in (n.start, n.stop, n.step))
                        if any(type(v) is not int for v in (start, stop, step)) or step == 0:
                            raise CodeError('Il for richiede inizio, fine e passo interi. Il passo deve essere diverso da zero.', n.line)
                        if n.value and ((n.value == '<' and step < 0) or (n.value == '>' and step > 0)):
                            raise CodeError('Il passo allontana il contatore dal limite. Correggi il segno del passo.', n.line)
                        python = self.language == 'Python'
                        current = start
                        if not python:
                            self.variables[n.name] = current
                        self.frame('Preparazione', f'{"range prepara i valori" if python else "Inizializza il contatore"}: da {start}, limite escluso {stop}, passo {step}.')
                        while True:
                            self.line = n.line
                            if not python:
                                current = self.variables[n.name]
                                stop = self.evaluate(n.stop)
                            truth = current < stop if step > 0 else current > stop
                            self.visited.add('for')
                            self.checks += 1
                            if python:
                                message = f'range offre il prossimo valore: {current}.' if truth else 'range non ha altri valori: il ciclo termina.'
                            else:
                                message = f'{n.name} = {current}; {current} {"<" if step > 0 else ">"} {stop} è {"VERO: esegui il corpo" if truth else "FALSO: esci"}.'
                            self.frame('Condizione', message, truth)
                            if not truth:
                                break
                            if python:
                                self.variables[n.name] = current
                            self.iterations += 1
                            self.frame('Corpo', f'Inizia la ripetizione {self.iterations}; {n.name} = {current}.')
                            self.execute(n.body)
                            self.line = n.line
                            if python:
                                current += step
                            else:
                                step_now = self.evaluate(n.step)
                                self.variables[n.name] += step_now
                                if abs(self.variables[n.name]) > 10000:
                                    raise CodeError('Il contatore è diventato troppo grande: controlla il passo.', n.line)
                                self.frame('Aggiornamento', f'Aggiorna {n.name}: ora vale {self.variables[n.name]}. Torna a controllare la condizione.')
                    else:
                        if n.kind == 'do':
                            self.visited.add('do')
                            self.frame('Ingresso', 'Il do while entra subito nel corpo: il primo controllo arriverà dopo la prima esecuzione.')
                        while n.kind == 'do' or self.check(n):
                            self.line = n.line
                            self.iterations += 1
                            self.frame('Corpo', f'Inizia la ripetizione {self.iterations}. Esegui le istruzioni del corpo nell’ordine indicato.')
                            self.execute(n.body)
                            if n.kind == 'do' and not self.check(n):
                                if self.language == 'Python':
                                    self.line = n.endline + 1
                                    self.frame('Uscita', 'break viene eseguito: termina il while True. Abbiamo ottenuto il comportamento del do while.')
                                break
                except StopLoop:
                    pass
                finally:
                    self.stack.pop()
                    if n.kind == 'for' and n.scoped and self.language != 'Python':
                        if had_counter:
                            self.variables[n.name] = saved_counter
                        else:
                            self.variables.pop(n.name, None)

    def run(self, source):
        self.frame('Pronto', 'Osserva il robot, poi segui un passaggio alla volta. Il programma parte dalla situazione iniziale.')
        error, error_line, nodes = '', 0, []
        try:
            nodes = parse(source, self.language)
            self.execute(nodes)
        except CodeError as err:
            error, error_line = str(err), err.line
        goal = ((self.world.x, self.world.y) == self.m.goal and not self.world.batteries and
                self.world.lit == self.world.lamps and self.world.scans >= self.m.required_scans and
                (self.m.exact_scans is None or self.world.scans == self.m.exact_scans))
        zero_rule = False
        if self.m.zero_case and self.covered == 0:
            # Re-run the actual input statements in an alternate initial world.
            # Constant-false guards and omitted input cannot pass this scenario.
            from dataclasses import replace
            alternate = replace(self.m, start=(self.m.start[0] - 1, self.m.start[1]), zero_case=False)
            if alternate.start[0] >= 0 and alternate.start not in alternate.walls:
                probe = Interpreter(alternate, self.language, self.limit)
                alternate_result = probe.run(source)
                zero_rule = alternate_result.success and probe.world.steps > 0
        mixed_loops = bool(self.visited - {self.m.loop})
        repeated = self.m.loop != 'for' or self.iterations > 1
        rule = self.m.loop in self.visited and not mixed_loops and repeated and self.outside == 0 and (self.covered > 0 or zero_rule)
        if error:
            message = error
        elif goal and rule:
            message = 'Missione completata! Hai raggiunto l’obiettivo e usato correttamente il ciclo richiesto.'
        elif mixed_loops:
            message = f'Questa missione allena soltanto il ciclo {"do while" if self.m.loop == "do" else self.m.loop}. Hai eseguito anche un altro tipo di ciclo: riscrivi la ripetizione usando quello richiesto.'
        elif not repeated:
            message = 'Il for deve ripetere il lavoro. Un solo giro che contiene tutte le azioni scritte una dopo l’altra non basta: individua il corpo da ripetere e aumenta il numero di giri.'
        elif not rule:
            message = f'Usa il ciclo {"do while" if self.m.loop == "do" else self.m.loop} per eseguire le azioni del robot. Il ciclo deve essere realmente raggiunto: un ciclo inutilizzato o azioni fuori dal ciclo non completano questa missione.'
        else:
            message = self.m.failure(self.world)
        self.line = error_line or self.line
        # One final diagnostic snapshot is retained even when the execution budget is exhausted.
        self.frames.append(Frame(copy.deepcopy(self.world), self.env(), self.line, 'Completata' if goal and rule and not error else 'Da rivedere', message, self.iterations, self.checks))
        return Result(self.frames, goal and rule and not error, goal, rule, message, error_line)
