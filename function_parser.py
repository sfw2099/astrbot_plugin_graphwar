import re
import math as _math


class FunctionToken:
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    POW = 5
    LPAREN = 6
    RPAREN = 7
    SQRT = 8
    LOG = 9
    LN = 10
    ABS = 11
    SIN = 12
    COS = 13
    TAN = 14
    EXP = 15
    VAR_X = 16
    VAR_Y = 17
    VAR_YP = 18
    VALUE = 19
    CONST_E = 20
    CONST_PI = 21
    NEG = 22

    _NAMES = {
        ADD: "+", SUB: "-", MUL: "*", DIV: "/", POW: "^",
        SQRT: "sqrt", LOG: "log", LN: "ln", ABS: "abs",
        SIN: "sin", COS: "cos", TAN: "tan", EXP: "exp",
        VAR_X: "x", VAR_Y: "y", VAR_YP: "y'", NEG: "neg",
    }

    _PRECEDENCE = {
        ADD: 1, SUB: 1, MUL: 2, DIV: 2, POW: 3,
    }

    _UNARY_FUNCS = {
        SQRT: _math.sqrt, LOG: _math.log10, LN: _math.log,
        ABS: abs, SIN: _math.sin, COS: _math.cos,
        TAN: _math.tan, EXP: _math.exp,
        NEG: lambda x: -x,
    }

    @classmethod
    def is_operator(cls, t):
        return t in (cls.ADD, cls.SUB, cls.MUL, cls.DIV, cls.POW)

    @classmethod
    def is_unary_func(cls, t):
        return t in cls._UNARY_FUNCS or t == cls.NEG

    @classmethod
    def is_variable(cls, t):
        return t in (cls.VAR_X, cls.VAR_Y, cls.VAR_YP)

    @classmethod
    def is_value(cls, t):
        return t in (cls.VALUE, cls.CONST_E, cls.CONST_PI, cls.VAR_X, cls.VAR_Y, cls.VAR_YP)


class ValueToken:
    def __init__(self, value):
        self.type = FunctionToken.VALUE
        self.value = float(value)

    def __repr__(self):
        return f"Value({self.value})"


_TOKEN_RE = re.compile(
    r"(?P<num>\d+\.?\d*|\.\d+)"
    r"|(?P<yp>y'')"
    r"|(?P<yp1>y')"
    r"|(?P<neg>neg)"
    r"|(?P<func>sqrt|log|ln|abs|sin|cos|tan|exp)"
    r"|(?P<const>e|pi)"
    r"|(?P<var>[xy])"
    r"|(?P<op>[-+*/^()])",
    re.IGNORECASE,
)

_FUNC_MAP = {
    "sqrt": FunctionToken.SQRT, "log": FunctionToken.LOG,
    "ln": FunctionToken.LN, "abs": FunctionToken.ABS,
    "sin": FunctionToken.SIN, "cos": FunctionToken.COS,
    "tan": FunctionToken.TAN, "exp": FunctionToken.EXP,
}

_CONST_MAP = {
    "e": FunctionToken.CONST_E,
    "pi": FunctionToken.CONST_PI,
}


def tokenize(expr):
    expr = expr.lower().replace(" ", "").replace("\t", "")
    if expr.startswith("y="):
        expr = expr[2:]
    elif expr.startswith("y'="):
        expr = expr[3:]
    elif expr.startswith("y''="):
        expr = expr[4:]

    expr = expr.replace("exp(", "e^(")

    tokens = []
    pos = 0
    while pos < len(expr):
        m = _TOKEN_RE.match(expr, pos)
        if not m:
            raise ValueError(f"无法解析: '{expr[pos:]}' 在位置 {pos}")
        pos = m.end()

        if m.group("num"):
            tokens.append(ValueToken(m.group("num")))
        elif m.group("yp"):
            tokens.append(FunctionToken.VAR_YP)
        elif m.group("yp1"):
            tokens.append(FunctionToken.VAR_YP)
        elif m.group("neg"):
            tokens.append(FunctionToken.NEG)
        elif m.group("func"):
            tokens.append(_FUNC_MAP[m.group("func").lower()])
        elif m.group("const"):
            tokens.append(_CONST_MAP[m.group("const").lower()])
        elif m.group("var"):
            v = m.group("var")
            tokens.append(FunctionToken.VAR_X if v == "x" else FunctionToken.VAR_Y)
        elif m.group("op"):
            op = m.group("op")
            if op == "-":
                prev_op = tokens[-1] if tokens else None
                if prev_op is None or prev_op in (
                    FunctionToken.LPAREN, FunctionToken.POW,
                    FunctionToken.MUL, FunctionToken.DIV, FunctionToken.ADD, FunctionToken.SUB,
                ):
                    tokens.append(FunctionToken.NEG)
                else:
                    tokens.append(FunctionToken.SUB)
            else:
                op_map = {
                    "+": FunctionToken.ADD, "*": FunctionToken.MUL,
                    "/": FunctionToken.DIV, "^": FunctionToken.POW,
                    "(": FunctionToken.LPAREN, ")": FunctionToken.RPAREN,
                }
                tokens.append(op_map[op])

    if not tokens:
        raise ValueError("空表达式")

    # Fix: wrap e^... after NEG: -e^(x+2) → -(e^(x+2))
    for i in range(len(tokens) - 2):
        if (tokens[i] == FunctionToken.NEG and tokens[i+1] == FunctionToken.CONST_E
                and i + 2 < len(tokens) and tokens[i+2] == FunctionToken.POW):
            j = i + 3
            depth = 0
            while j < len(tokens):
                if tokens[j] == FunctionToken.LPAREN:
                    depth += 1
                elif tokens[j] == FunctionToken.RPAREN:
                    if depth == 0:
                        j += 1
                        break
                    depth -= 1
                elif depth == 0 and FunctionToken.is_operator(tokens[j]):
                    break
                j += 1
            tokens.insert(j, FunctionToken.RPAREN)
            tokens.insert(i + 1, FunctionToken.LPAREN)
            break

    return tokens


def _insert_implicit_mul(tokens):
    result = []
    for t in tokens:
        if result:
            prev = result[-1]
            prev_is_value = (
                isinstance(prev, ValueToken)
                or prev in (FunctionToken.VAR_X, FunctionToken.VAR_Y, FunctionToken.VAR_YP,
                           FunctionToken.CONST_E, FunctionToken.CONST_PI)
                or prev == FunctionToken.RPAREN
            )
            curr_is_value_or_func = (
                isinstance(t, ValueToken)
                or t in (FunctionToken.VAR_X, FunctionToken.VAR_Y, FunctionToken.VAR_YP,
                        FunctionToken.CONST_E, FunctionToken.CONST_PI)
                or FunctionToken.is_unary_func(t)
                or t == FunctionToken.LPAREN
            )
            if prev_is_value and curr_is_value_or_func:
                result.append(FunctionToken.MUL)
        result.append(t)
    return result


def _to_prefix(tokens):
    if not tokens:
        raise ValueError("空 token 列表")

    if len(tokens) == 1:
        t = tokens[0]
        if FunctionToken.is_operator(t) or FunctionToken.is_unary_func(t) or t in (FunctionToken.LPAREN, FunctionToken.RPAREN):
            raise ValueError("单个 token 不能是运算符或括号")
        return [t]

    min_prec = 999
    min_idx = -1
    depth = 0
    for i, t in enumerate(tokens):
        if t == FunctionToken.LPAREN:
            depth += 1
        elif t == FunctionToken.RPAREN:
            depth -= 1
        elif depth == 0 and FunctionToken.is_operator(t):
            prec = FunctionToken._PRECEDENCE[t]
            if prec <= min_prec:
                min_prec = prec
                min_idx = i

    if min_idx >= 0:
        op = tokens[min_idx]
        left = _to_prefix(tokens[:min_idx])
        right = _to_prefix(tokens[min_idx + 1:])
        return [op] + left + right

    if tokens[0] == FunctionToken.LPAREN and tokens[-1] == FunctionToken.RPAREN:
        return _to_prefix(tokens[1:-1])

    if FunctionToken.is_unary_func(tokens[0]):
        inner = _to_prefix(tokens[1:])
        return [tokens[0]] + inner

    raise ValueError("无法解析表达式结构")


def _evaluate(prefix_tokens, x, y, yp):
    stack = list(reversed(prefix_tokens))

    def _eval():
        if not stack:
            raise ValueError("表达式不完整")
        t = stack.pop()

        if isinstance(t, ValueToken):
            return t.value
        if t == FunctionToken.CONST_E:
            return _math.e
        if t == FunctionToken.CONST_PI:
            return _math.pi
        if t == FunctionToken.VAR_X:
            return x
        if t == FunctionToken.VAR_Y:
            return y
        if t == FunctionToken.VAR_YP:
            return yp

        if FunctionToken.is_operator(t):
            a = _eval()
            b = _eval()
            if t == FunctionToken.ADD:
                return a + b
            if t == FunctionToken.SUB:
                return a - b
            if t == FunctionToken.MUL:
                return a * b
            if t == FunctionToken.DIV:
                return a / b if b != 0 else float("nan")
            if t == FunctionToken.POW:
                try:
                    return a ** b
                except (ValueError, OverflowError, TypeError):
                    return float("nan")

        if FunctionToken.is_unary_func(t):
            v = _eval()
            func = FunctionToken._UNARY_FUNCS[t]
            try:
                return func(v)
            except (ValueError, OverflowError):
                return float("nan")

        raise ValueError(f"未知 token: {t}")

    return _eval()


class CompiledFunction:
    def __init__(self, expr_str):
        self.expr_str = expr_str
        tokens = tokenize(expr_str)
        tokens = _insert_implicit_mul(tokens)
        self.prefix = _to_prefix(tokens)

    def evaluate(self, x=0.0, y=0.0, yp=0.0):
        try:
            return _evaluate(self.prefix, x, y, yp)
        except (ValueError, ZeroDivisionError, OverflowError):
            return float("nan")

    def __repr__(self):
        return f"CompiledFunction('{self.expr_str}')"
