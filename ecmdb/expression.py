import copy
import functools
import importlib
import itertools
import logging
import math
import operator
import re

import gmpy2
import sympy

from pyparsing import (
    Literal,
    Word,
    Group,
    Forward,
    alphas,
    alphanums,
    Regex,
    ParseException,
    CaselessKeyword,
    Suppress,
    delimitedList,
    Optional,
    Keyword,
    PrecededBy,
    Combine
)

from pyparsing import pyparsing_common as ppc

_exprStack = []


def _push_first(toks):
    _exprStack.append(toks[0])


def _push_unary(toks):
    for t in toks:
        if t == "-":
            _exprStack.append("unary -")
        else:
            break


_bnf = None


def _BNF():
    """
    expop   :: '^'
    multop  :: '*' | '/'
    addop   :: '+' | '-'
    integer :: ['+' | '-'] '0'..'9'+
    atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
    factor  :: atom [ expop factor ]*
    term    :: factor [ multop factor ]*
    expr    :: term [ addop term ]*
    """
    global _bnf
    if not _bnf:
        # use CaselessKeyword for e and pi, to avoid accidentally matching
        # functions that start with 'e' or 'pi' (such as 'exp'); Keyword
        # and CaselessKeyword only match whole words
        e = CaselessKeyword("E")
        pi = CaselessKeyword("PI")
        # fnumber = Combine(Word("+-"+nums, nums) +
        #                    Optional("." + Optional(Word(nums))) +
        #                    Optional(e + Word("+-"+nums, nums)))
        # or use provided pyparsing_common.number, but convert back to str:
        # fnumber = ppc.number().addParseAction(lambda t: str(t[0]))
        fnumber = Regex(r"[+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?")
        # ident = Word(alphas, alphanums + "_$")
        ident = Regex(r'[a-zA-Z_](?:[a-zA-Z0-9_]*[a-zA-Z0-9])?')

        plus, minus, mult, div = map(Literal, "+-*/")
        lpar, rpar = map(Suppress, "()")
        lbrace, rbrace = map(Suppress, "{}")
        lbrack, rbrack = map(Suppress, "[]")
        comma = Suppress(",")
        addop = plus | minus
        multop = mult | div
        expop = Literal("^")
        fac, prim = map(Literal, "!#")
        unop = fac | prim

        expr = Forward()
        expr_list = delimitedList(Group(expr))
        # add parse action that replaces the function identifier with a (name, number of args) tuple
        def insert_fn_argcount_tuple(t):
            fn = t.pop(0)
            sub = t.pop(0)
            sup = t.pop(0)
            num_args = len(t[0])
            t.insert(0, (fn, num_args, sub, sup))

        def euclid_mullin_parse(t):
            _exprStack.append(t[1])
            _exprStack.append(t[2])

        def range_parse(t):
            fn = t.pop(0)
            identifier = t[1]
            start = t[2]
            end = t[3]
            t.insert(0, (fn, identifier, start, end))


        euclidmullin = (Literal("EuclidMullin") + Optional(lbrack + fnumber + rbrack, "2") + fnumber).setParseAction(
            euclid_mullin_parse
        )
        range_func = ((Literal("concat") | Literal("prod")) + lpar + Group(expr) + comma + ident + Suppress("=")
                      + ppc.signed_integer + Suppress("..")
                      + ppc.signed_integer + rpar).setParseAction(range_parse)

        fn_call = (ident + (Optional(Suppress("_") + lbrace + ppc.signed_integer + rbrace, None)
                   + Optional(Suppress("^") + lbrace + ppc.signed_integer + rbrace, None))
                   + lpar - Group(expr_list) + rpar).setParseAction(
            insert_fn_argcount_tuple
        )
        atom = (
            addop[...]
            + (
                (range_func | euclidmullin | fn_call | pi | e | fnumber | ident).setParseAction(_push_first)
                | Group(lpar + expr + rpar)
            ) + unop.setParseAction(_push_first)[...]
        ).setParseAction(_push_unary)

        # by defining exponentiation as "atom [ ^ factor ]..." instead of "atom [ ^ atom ]...", we get right-to-left
        # exponents, instead of left-to-right that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor <<= atom + (expop + factor).setParseAction(_push_first)[...]
        term = factor + (multop + factor).setParseAction(_push_first)[...]
        expr <<= term + (addop + term).setParseAction(_push_first)[...]
        _bnf = expr
    return _bnf


# map operator symbols to corresponding arithmetic operations
_epsilon = 1e-12
_opn = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.floordiv,
    "^": operator.pow,
}

_fn = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "abs": abs,
    "trunc": int,
    "round": round,
    "sgn": lambda a: -1 if a < -_epsilon else 1 if a > _epsilon else 0,
    # functions with multiple arguments
    "multiply": lambda a, b: a * b,
    "hypot": math.hypot,
    # functions with a variable number of arguments
    "all": lambda *a: all(a),
    "Fibonacci": gmpy2.fib,
    "fibonacci": gmpy2.fib,
    "F": gmpy2.fib,
    "Fib": gmpy2.fib,
    "fib": gmpy2.fib,
    "Lucas": gmpy2.lucas,
    "Euler": sympy.euler,
    "Pell": lambda n: gmpy2.lucasu(2, -1, n),
    "Phi": lambda n, x: sympy.polys.specialpolys.cyclotomic_poly(n, x),
    # "tens_complement_factorial": A110396,
    "Tribonacci": lambda n: sympy.tribonacci(n-1),
    # "Sylvester": A000058,
    # "Sm": lambda n: gmpy2.mpz(A007908(n)),
}


def _evaluate_stack(s, state=None):
    if not state:
        state = {}
    popped, num_args = s.pop(), 0
    op = popped
    if isinstance(op, tuple):
        if op[0] in ["concat", "prod"]:  # special range functions
            op = popped[0]
        elif len(op) == 4:
            op, num_args, sub, sup = op
        else:
            assert f"unusual tuple encountered {op}"
    if type(op) == int:
        return op
    if op == "EuclidMullin":
        term_index = _evaluate_stack(s, state)
        first_term = _evaluate_stack(s, state)
        # get the euclid mullen number to be factored
        raise ParseException("EuclidMullin not supported")
        # return euclid_mullin_product(first_term, term_index-1) + 1
    if op == "Phi":
        # note: args are pushed onto the stack in reverse order
        args = list(reversed([_evaluate_stack(s, state) for _ in range(num_args)]))
        return gmpy2.mpz(sympy.polys.specialpolys.cyclotomic_poly(sub, *args))
    elif op in ["prod", "concat"]:
        end_range_incl = popped[3]
        start_range_incl = popped[2]
        identifier = popped[1]
        expression = copy.deepcopy(s)
        values = [_evaluate_stack(copy.deepcopy(expression), state=state | {identifier: k}) for k in range(start_range_incl, end_range_incl + 1)]
        s.pop()
        s.pop()
        if op == "prod":
            return math.prod(values)
        elif op == "concat":
            return gmpy2.mpz("".join(map(str, values)))
    elif op == "unary -":
        return -_evaluate_stack(s, state)
    elif op == "!":
        return gmpy2.fac(_evaluate_stack(s, state))
    elif op == "#":
        return sympy.primorial(_evaluate_stack(s, state))
    elif op in "+-*/^":
        # note: operands are pushed onto the stack in reverse order
        op2 = _evaluate_stack(s, state)
        op1 = _evaluate_stack(s, state)
        return _opn[op](op1, op2)
    elif op == "PI":
        return math.pi  # 3.1415926535
    elif op == "E":
        return math.e  # 2.718281828
    elif op in _fn or re.match(r"A\d{6}", op):
        # note: args are pushed onto the stack in reverse order
        args = reversed([_evaluate_stack(s, state) for _ in range(num_args)])
        if re.match(r"A\d{6}", op):
            function = importlib.import_module(f"sequences.{op}")  # needs a replacement for oeis sequence composites
        else:
            function = _fn[op]
        if sup:  # apply function sup (superscript) times, e.g. A048985^{281}(2295)
            return functools.reduce(lambda total, _: gmpy2.mpz(function(total)), [None] * (sup - 1), gmpy2.mpz(function(*args)))
        return gmpy2.mpz(function(*args))
    elif op[0].isalpha():
        if op in state:
            return state[op]
        raise Exception("invalid identifier '%s'" % op)
    else:
        # try to evaluate as int first, then as float if int fails
        try:
            return gmpy2.mpz(op)
        except ValueError:
            return float(op)


def evaluate(s):
    if not s:
        return None
    _exprStack[:] = []
    results = _BNF().parseString(s, parseAll=True)
    val = _evaluate_stack(_exprStack[:])
    return val


def can_parse(s):
    if not s:
        return False
    _exprStack[:] = []
    try:
        _BNF().parseString(s, parseAll=True)
    except ParseException as pe:
        logging.debug(pe)
        return False
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def test(s, expected):
        _exprStack[:] = []
        try:
            results = _BNF().parseString(s, parseAll=True)
            val = _evaluate_stack(_exprStack[:])
        except ParseException as pe:
            print(s, "failed parse:", str(pe))
        except Exception as e:
            print(s, "failed eval:", str(e), _exprStack)
        else:
            if val == expected:
                print(s, "=", val, results, "=>", _exprStack)
            else:
                print(s + "!!!", val, "!=", expected, results, "=>", _exprStack)

    # TODO support all test cases nicely
    # test("prod(A057204(k),k=1..3)+1", 10812186008)
    # test("1+prod(A057204(k),k=1..3)", 10812186008)
    # test("A048985^{281}(2295)", 2212686725588660190846701777565322981741192119760405080395040470274676741341850761753500834257532037731919663954846125186454002551800699483997598384785995154171692759349610428638356492885427)
    # test("A037276^{118}(49)", 31591559896269666666598271323929987368130648086914375205708609469455240795758009093092999931626631706893838237446804628957426949545161439643850763983152977771070456646529606514514350669236880120878528179383004060084979184123521819930400481691041161410407051)
    # test("A037279^{6}(45)", 3892671338076267963305029515140142288038899150885453119088787848734147626843935726636354620244288053172572979899573149720435239786397718939698719449161305719359172289952110620103251187363409887168698563318603097535620902296613344284334156543954945215129395794858217656476927948910328530024696318648356453881873845746529694307838467306413057399324119901241465162257423813714264465874521)
    # test("concat(A096098(n),n=1..182)", 2137172159917311231614913913119331714893313989693097350956401900335673788279883089441874368101349387565144329514794708322449496611129187318115445779738875162190709978635216773353105931774129972074283243741173911727812075787378324999312471699177231631792344939321127431431091571232871678765761317431885993284310167360035080796986373547322110793237351594132031891335714335371291476091195370387301194117309293111094875399352277254491097922726362179086360119613807679012053208714609259163489113472773310673291416142779311192931536237937132096272511001805031245882596336066472939944538252112536340232517408717793279139793692531289149267631834515919681091863134719558940415713041943033312695034931194346912433233215517731531474615891712432237334915920124234119135727363756346346159225916140631352373950607328978723397710360542059415905008646558829120515833465267264969791563446331411004639194564199773144948794542507892997402567498103471057853892370914753907813696111707867888633718659000600692781584845032382558783999508242587307666076050268497431783395958351593212987417535334628170845947300973667321519947026395481495407161860303064607682815018818390412336833053721408080287457734580882837998969271155315289907696807323679484224920252246480630857766938642839937655999423556658561903731734583000681128249182118709989438483909962114094953262774793519320480607182210372192600620254714452263362689660672770359218888032822485785380879472115343751901553845211937257773891886542385167024093255540636600775198972618516952827648471579246991951701001622915118611577913750077576063667988327264981)
    # test("prod(A000946(k),k=1..14)+1", 110721465493002960453669737626182095929861002444217630084728101840814389517145776947757647185681033716504925247273515756720076434129863468366272908514227824139272687809696635619251625371039464763992521352908321920697230358329690909804157733806149260259095949192261207550664145547314786038676638526563069026548149264840040649770821659684890735628731429655066437369046403043)
    test("prod(k,k=1..8)", gmpy2.fac(8))
    # test("EuclidMullin52", 96829488818499592481168771836336683023181156945795350980834458372199490598743221067775290195641203125439681639536219726888871822435629511515837059837171813128663335953886175536897367740550240372528813404899458874513057418332695709006061299277468749241875966062032012477732299909160292749026996368849279816035027111164073836173908645011)
    # test("EuclidMullin[89]79", 11174617834364236795841009048233307300266825806821422768355693373365085032585044193459792474481968534214012129338582609223777313906676835876512016253134736446357244064548876600154122498493336254078690308702387774957116102193153114003470199116309299587255991548961775026348706644057280189730066638814807136216048503660514558885943442917252155683194807171395786420042916143788146664817225907035132966072525490126951084348500242420179655236405362096465417821955926267527178066851665196294594188032518202793351207396724701134942229850943352554573712322632224284217403442359968160098745805723478409060133345414496102693644080400204614617480555946617395294653880623668910385640647413239838375624590534991034996755408130348770236930183011337721064071)
    # test("EuclidMullin[8191]60", 8282089243446473211387684636969237867638878560572521325217278223996825743484686294904224706272288789954840578990605617587341463889169512704364420619434904332537477485387539288196099910681975906215779951603268145410370249046577878320501841985614222467391716530554622300331305118091323357851046588721123252761073612195879641026231)
    # test("EuclidMullin[11]56", 1462115955076312880461971028916830938531855923948487645486638771029731639617228168230757487217679296656161518044471471279730823624417566019435857915727335280250082384877479577893113821299744957891473317726865603494324569156457826991823271093527584262566919919934993248371302559556597773494345711715798437281437071)
    test("523#+1", 8709668761379269784034173446876636639594408083936553641753483991897255703964943107588335040121154680170867105541177741204814011615930342030904704147856733048115934632145172739949220591246493529224396454328521288726491)
    # test("tens_complement_factorial(112)-1", A110396(112)-1)
    test("Phi_{17}(5461881130856756498343881353355730200091930726446628652260883480575183173)", sympy.polys.specialpolys.cyclotomic_poly(17,5461881130856756498343881353355730200091930726446628652260883480575183173))
    # test("A007942(3)", gmpy2.mpz(32123))
    test("7^384-384", pow(gmpy2.mpz(7), 384) - 384)
    test("110!+7", gmpy2.fac(110) + 7)
    test("Fibonacci(1423)", gmpy2.fib(1423))
    test("2^1497-1", pow(gmpy2.mpz(2), 1497)-1)
    test("9", 9)
    test("-9", -9)
    test("--9", 9)
    test("-E", -math.e)
    test("9 + 3 + 6", 9 + 3 + 6)
    test("9 + 3 / 11", 9 + 3.0 // 11)
    test("(9 + 3)", (9 + 3))
    test("(9+3) / 11", (9 + 3.0) // 11)
    test("9 - 12 - 6", 9 - 12 - 6)
    test("9 - (12 - 6)", 9 - (12 - 6))
    test("2*3.14159", 2 * 3.14159)
    test("3.1415926535*3.1415926535 / 10", 3.1415926535 * 3.1415926535 // 10)
    test("PI * PI / 10", math.pi * math.pi // 10)
    test("PI*PI/10", math.pi * math.pi // 10)
    test("PI^2", math.pi ** 2)
    test("round(PI^2)", round(math.pi ** 2))
    test("6.02E23 * 8.048", 6.02e23 * 8.048)
    test("e / 3", math.e // 3)
    test("sin(PI/2)", math.sin(math.pi // 2))
    test("10+sin(PI/4)^2", 10 + math.sin(math.pi // 4) ** 2)
    test("trunc(E)", int(math.e))
    test("trunc(-E)", int(-math.e))
    test("round(E)", round(math.e))
    test("round(-E)", round(-math.e))
    test("E^PI", math.e ** math.pi)
    test("exp(0)", 1)
    test("exp(1)", math.e)
    test("2^3^2", 2 ** 3 ** 2)
    test("(2^3)^2", (2 ** 3) ** 2)
    test("2^3+2", 2 ** 3 + 2)
    test("2^3+5", 2 ** 3 + 5)
    test("2^9", 2 ** 9)
    test("sgn(-2)", -1)
    test("sgn(0)", 0)
    test("sgn(0.1)", 1)
    test("foo(0.1)", None)
    test("round(E, 3)", round(math.e, 3))
    test("round(PI^2, 3)", round(math.pi ** 2, 3))
    test("sgn(cos(PI/4))", 1)
    test("sgn(cos(PI/2))", 0)
    test("sgn(cos(PI*3/4))", -1)
    test("+(sgn(cos(PI/4)))", 1)
    test("-(sgn(cos(PI/4)))", -1)
    test("hypot(3, 4)", 5)
    test("multiply(3, 7)", 21)
    test("all(1,1,1)", True)
    test("all(1,1,1,1,1,0)", False)
