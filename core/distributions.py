"""
Validacion de Conversiones Estadisticas (Generacion de Variables Aleatorias)
============================================================================
Toma la secuencia de numeros pseudoaleatorios r_i en [0, 1) producida por
cualquiera de los 5 generadores de la aplicacion y la convierte a cinco
distribuciones de probabilidad:

  1. Uniforme entre A y B
  2. Normal (mu, sigma)
  3. Erlang (k, lambda)
  4. Poisson (lambda)
  5. Binomial (n, p)

Para cada distribucion se ofrecen dos formulas de conversion:
  - Transformada inversa  (1 r_i -> 1 valor)                 [por defecto]
  - Metodo clasico del libro (Coss Bu, Cap. 3): suma de 12 r_i (Normal),
    producto de k r_i (Erlang), metodo multiplicativo (Poisson) y suma de
    ensayos de Bernoulli (Binomial).

Validacion (la "prueba de fuego"):
  Paso 1  Generacion:  r_1 ... r_N
  Paso 2  Conversion:  x_i = F^-1(r_i)   (o el metodo clasico)
  Paso 3  Conteo:      P_sim = #{x_i que cumplen la condicion} / n
          para tres casos: "menor que", "mayor que" y "entre a y b".
  Paso 4  Validacion:  se calcula la probabilidad teorica P_teo con la
          formula de la distribucion y se comparan. Como la simulacion
          nunca da EXACTAMENTE el mismo numero, se aceptan como iguales si
          |P_sim - P_teo| <= Z_(alpha/2) * sqrt(P_teo (1 - P_teo) / n)
          (margen de error de una proporcion al nivel de confianza 1-alpha).

Solo usa la libreria estandar de Python.
"""

import bisect
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

from .random_tests import z_alpha_2


DIST_ORDER = ["uniforme", "normal", "erlang", "poisson", "binomial"]

DIST_META = {
    "uniforme": {"name": "Uniforme entre A y B", "short": "Uniforme (A, B)", "discrete": False},
    "normal": {"name": "Distribución Normal", "short": "Normal (μ, σ)", "discrete": False},
    "erlang": {"name": "Distribución Erlang", "short": "Erlang (k, λ)", "discrete": False},
    "poisson": {"name": "Distribución de Poisson", "short": "Poisson (λ)", "discrete": True},
    "binomial": {"name": "Distribución Binomial", "short": "Binomial (n, p)", "discrete": True},
}

# Metodos de conversion disponibles por distribucion (el primero es el de defecto)
DIST_METHODS = {
    "uniforme": ["inversa"],
    "normal": ["inversa", "tlc"],
    "erlang": ["inversa", "convolucion"],
    "poisson": ["inversa", "multiplicativo"],
    "binomial": ["inversa", "bernoulli"],
}

METHOD_LABELS = {
    ("uniforme", "inversa"): "Transformada inversa",
    ("normal", "inversa"): "Transformada inversa",
    ("normal", "tlc"): "Suma de 12 rᵢ (Teorema del Límite Central)",
    ("erlang", "inversa"): "Transformada inversa (numérica)",
    ("erlang", "convolucion"): "Convolución: producto de k rᵢ",
    ("poisson", "inversa"): "Transformada inversa (tabla acumulada)",
    ("poisson", "multiplicativo"): "Método multiplicativo (Π rᵢ < e^(−λ))",
    ("binomial", "inversa"): "Transformada inversa (tabla acumulada)",
    ("binomial", "bernoulli"): "Suma de n ensayos de Bernoulli",
}

DEFAULT_CONFIG = {
    "uniforme": {"method": "inversa", "params": {"a": 5, "b": 15},
                 "cases": {"menor": {"op": "<", "x": 8}, "mayor": {"op": ">", "x": 12}, "rango": {"a": 7, "b": 11}}},
    "normal": {"method": "inversa", "params": {"mu": 50, "sigma": 10},
               "cases": {"menor": {"op": "<", "x": 45}, "mayor": {"op": ">", "x": 60}, "rango": {"a": 40, "b": 55}}},
    "erlang": {"method": "inversa", "params": {"k": 3, "lam": 0.5},
               "cases": {"menor": {"op": "<", "x": 4}, "mayor": {"op": ">", "x": 8}, "rango": {"a": 3, "b": 7}}},
    "poisson": {"method": "inversa", "params": {"lam": 4},
                "cases": {"menor": {"op": "<", "x": 3}, "mayor": {"op": ">", "x": 5}, "rango": {"a": 2, "b": 6}}},
    "binomial": {"method": "inversa", "params": {"n": 10, "p": 0.3},
                 "cases": {"menor": {"op": "<", "x": 3}, "mayor": {"op": ">", "x": 4}, "rango": {"a": 2, "b": 5}}},
}

CASE_ORDER = ["menor", "mayor", "rango"]
CASE_LABELS = {"menor": "Menor que", "mayor": "Mayor que", "rango": "Entre a y b (rango)"}

MIN_VALUES = 10          # por debajo de esto la validacion no es concluyente
RECOMMENDED_VALUES = 1000

POISSON_MAX_LAMBDA = 100.0
BINOMIAL_MAX_N = 200
ERLANG_MAX_K = 50


# =========================================================================
# FORMATO
# =========================================================================
def fmt(v: float, d: int = 6) -> str:
    """Numero con hasta d decimales, sin ceros sobrantes (para las formulas)."""
    if v is None:
        return "—"
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return str(v)
    if float(v).is_integer():
        return str(int(v))
    s = f"{v:.{d}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def fmt_p(v: float) -> str:
    """Probabilidad siempre con 6 decimales."""
    return f"{v:.6f}"


def _num(value, fallback: float) -> float:
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return float(fallback)
        return v
    except (TypeError, ValueError):
        return float(fallback)


# =========================================================================
# NORMALIZACION DE LA CONFIGURACION (compartida con el exportador de Excel)
# =========================================================================
def normalize_config(config: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Completa la configuracion recibida con los valores por defecto y
    sanea tipos / operadores. No valida rangos de parametros (eso lo hace
    `_param_errors`, para poder informar el error en pantalla)."""
    config = config if isinstance(config, dict) else {}
    out: Dict[str, Dict[str, Any]] = {}
    for dist in DIST_ORDER:
        base = DEFAULT_CONFIG[dist]
        user = config.get(dist) if isinstance(config.get(dist), dict) else {}

        method = str(user.get("method", base["method"]) or base["method"]).lower().strip()
        if method not in DIST_METHODS[dist]:
            method = base["method"]

        u_params = user.get("params") if isinstance(user.get("params"), dict) else {}
        params = {k: _num(u_params.get(k, v), v) for k, v in base["params"].items()}

        u_cases = user.get("cases") if isinstance(user.get("cases"), dict) else {}
        cases = {}
        for cid in CASE_ORDER:
            bc = base["cases"][cid]
            uc = u_cases.get(cid) if isinstance(u_cases.get(cid), dict) else {}
            if cid == "rango":
                a = _num(uc.get("a", bc["a"]), bc["a"])
                b = _num(uc.get("b", bc["b"]), bc["b"])
                if a > b:
                    a, b = b, a
                cases[cid] = {"a": a, "b": b}
            else:
                op = str(uc.get("op", bc["op"]) or bc["op"]).strip()
                op = op.replace("≤", "<=").replace("≥", ">=")
                allowed = ["<", "<="] if cid == "menor" else [">", ">="]
                if op not in allowed:
                    op = bc["op"]
                cases[cid] = {"op": op, "x": _num(uc.get("x", bc["x"]), bc["x"])}

        out[dist] = {"method": method, "params": params, "cases": cases}
    return out


def _param_errors(dist: str, p: Dict[str, float]) -> List[str]:
    errs = []
    if dist == "uniforme":
        if not p["a"] < p["b"]:
            errs.append("Se requiere A < B.")
    elif dist == "normal":
        if not p["sigma"] > 0:
            errs.append("La desviación estándar σ debe ser mayor que 0.")
    elif dist == "erlang":
        if not float(p["k"]).is_integer() or not (1 <= p["k"] <= ERLANG_MAX_K):
            errs.append(f"k debe ser un entero entre 1 y {ERLANG_MAX_K}.")
        if not p["lam"] > 0:
            errs.append("λ debe ser mayor que 0.")
    elif dist == "poisson":
        if not (0 < p["lam"] <= POISSON_MAX_LAMBDA):
            errs.append(f"λ debe estar entre 0 y {fmt(POISSON_MAX_LAMBDA)}.")
    elif dist == "binomial":
        if not float(p["n"]).is_integer() or not (1 <= p["n"] <= BINOMIAL_MAX_N):
            errs.append(f"n debe ser un entero entre 1 y {BINOMIAL_MAX_N}.")
        if not (0 < p["p"] < 1):
            errs.append("p debe estar entre 0 y 1 (sin incluirlos).")
    return errs


# =========================================================================
# FUNCIONES DE DISTRIBUCION (CDF, PMF, INVERSAS)
# =========================================================================
def uniform_cdf(x: float, a: float, b: float) -> float:
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    return (x - a) / (b - a)


def normal_cdf(x: float, mu: float, sigma: float) -> float:
    return statistics.NormalDist(mu, sigma).cdf(x)


def erlang_cdf(x: float, k: int, lam: float) -> float:
    """F(x) = 1 - sum_{n=0}^{k-1} e^(-lam x) (lam x)^n / n!"""
    if x <= 0:
        return 0.0
    lx = lam * x
    term = math.exp(-lx)
    total = term
    for n in range(1, int(k)):
        term *= lx / n
        total += term
    return min(1.0, max(0.0, 1.0 - total))


def erlang_inv(r: float, k: int, lam: float) -> float:
    """x tal que F(x) = r (biseccion; F es continua y creciente)."""
    if r <= 0:
        return 0.0
    lo, hi = 0.0, max(1.0, k / lam)
    while erlang_cdf(hi, k, lam) < r:
        hi *= 2.0
        if hi > 1e12:
            break
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if erlang_cdf(mid, k, lam) < r:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1e-13 * max(1.0, hi):
            break
    return (lo + hi) / 2.0


def poisson_pmf(t: int, lam: float) -> float:
    if t < 0:
        return 0.0
    return math.exp(-lam + t * math.log(lam) - math.lgamma(t + 1))


def poisson_cdf(t: int, lam: float) -> float:
    if t < 0:
        return 0.0
    upper = int(lam + 40 * math.sqrt(lam) + 60)
    if t > upper:
        return 1.0
    term = math.exp(-lam)
    total = term
    for j in range(1, int(t) + 1):
        term *= lam / j
        total += term
    return min(1.0, total)


def binomial_pmf(t: int, n: int, p: float) -> float:
    if t < 0 or t > n:
        return 0.0
    return math.comb(n, t) * (p ** t) * ((1 - p) ** (n - t))


def binomial_cdf(t: int, n: int, p: float) -> float:
    if t < 0:
        return 0.0
    if t >= n:
        return 1.0
    return min(1.0, sum(binomial_pmf(j, n, p) for j in range(0, int(t) + 1)))


def poisson_table_size(lam: float) -> int:
    """Cantidad de filas t = 0..T-1 de la tabla acumulada para la inversa discreta
    (compartida con el Excel para que ambos usen exactamente la misma tabla)."""
    return int(math.ceil(lam + 12 * math.sqrt(lam) + 15))


def _discrete_inverse(r: float, cum: List[float]) -> int:
    """Transformada inversa discreta: x tal que F(x-1) <= r < F(x).
    `cum` = [F(0), F(1), ..., F(T-1)]. Equivale en Excel a
    COINCIDIR(r; {F(-1)=0, F(0), ..., F(T-2)}; 1) - 1."""
    t = bisect.bisect_right(cum, r)
    return min(t, len(cum) - 1)


# =========================================================================
# CONVERSION rᵢ -> xᵢ
# =========================================================================
_SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _sub(i: int) -> str:
    return "r" + str(i).translate(_SUBSCRIPTS)


def convert(dist: str, method: str, p: Dict[str, float], numbers: List[float]) -> Dict[str, Any]:
    """Convierte la secuencia `numbers` a la distribucion indicada.
    Devuelve los valores xᵢ, la traza (para la tabla) y los descartados."""
    values: List[float] = []
    trace: List[Dict[str, Any]] = []   # {"used": "r5" | "r1…r12", "aux": float|None, "r": float|None}
    discarded = 0
    N = len(numbers)

    if dist == "uniforme":
        a, b = p["a"], p["b"]
        for i, r in enumerate(numbers, start=1):
            x = a + (b - a) * r
            values.append(x)
            trace.append({"used": _sub(i), "r": r, "aux": None})

    elif dist == "normal":
        mu, sigma = p["mu"], p["sigma"]
        if method == "tlc":
            g = 12
            for j in range(N // g):
                block = numbers[j * g:(j + 1) * g]
                s = sum(block)
                values.append(mu + sigma * (s - 6.0))
                trace.append({"used": f"{_sub(j * g + 1)}…{_sub((j + 1) * g)}", "r": None, "aux": s})
        else:
            nd = statistics.NormalDist(0.0, 1.0)
            for i, r in enumerate(numbers, start=1):
                if r <= 0.0 or r >= 1.0:
                    discarded += 1
                    continue
                values.append(mu + sigma * nd.inv_cdf(r))
                trace.append({"used": _sub(i), "r": r, "aux": None})

    elif dist == "erlang":
        k, lam = int(p["k"]), p["lam"]
        if method == "convolucion":
            for j in range(N // k):
                block = numbers[j * k:(j + 1) * k]
                prod = 1.0
                for r in block:
                    prod *= r
                if prod <= 0.0:
                    discarded += 1
                    continue
                values.append(-(1.0 / lam) * math.log(prod))
                trace.append({"used": _sub(j * k + 1) if k == 1 else f"{_sub(j * k + 1)}…{_sub((j + 1) * k)}",
                              "r": None, "aux": prod})
        else:
            for i, r in enumerate(numbers, start=1):
                values.append(erlang_inv(r, k, lam))
                trace.append({"used": _sub(i), "r": r, "aux": None})

    elif dist == "poisson":
        lam = p["lam"]
        if method == "multiplicativo":
            limit = math.exp(-lam)
            prod, cnt, start = 1.0, 0, 1
            for i, r in enumerate(numbers, start=1):
                prod *= r
                cnt += 1
                if prod < limit:
                    values.append(float(cnt - 1))
                    trace.append({"used": _sub(start) if cnt == 1 else f"{_sub(start)}…{_sub(i)}",
                                  "r": None, "aux": prod})
                    prod, cnt, start = 1.0, 0, i + 1
            if cnt > 0:
                discarded += 1  # grupo final incompleto
        else:
            T = poisson_table_size(lam)
            cum = [poisson_cdf(t, lam) for t in range(T)]
            for i, r in enumerate(numbers, start=1):
                values.append(float(_discrete_inverse(r, cum)))
                trace.append({"used": _sub(i), "r": r, "aux": None})

    elif dist == "binomial":
        n, pp = int(p["n"]), p["p"]
        if method == "bernoulli":
            for j in range(N // n):
                block = numbers[j * n:(j + 1) * n]
                exitos = sum(1 for r in block if r < pp)
                values.append(float(exitos))
                trace.append({"used": _sub(j * n + 1) if n == 1 else f"{_sub(j * n + 1)}…{_sub((j + 1) * n)}",
                              "r": None, "aux": float(exitos)})
        else:
            cum = [binomial_cdf(t, n, pp) for t in range(n + 1)]
            for i, r in enumerate(numbers, start=1):
                values.append(float(_discrete_inverse(r, cum)))
                trace.append({"used": _sub(i), "r": r, "aux": None})

    return {"values": values, "trace": trace, "discarded": discarded}


def conversion_formula(dist: str, method: str, p: Dict[str, float]) -> Tuple[str, str, str]:
    """(formula general, formula con parametros, rᵢ consumidos por valor)"""
    if dist == "uniforme":
        return ("x = A + (B − A)·r",
                f"x = {fmt(p['a'])} + ({fmt(p['b'])} − {fmt(p['a'])})·r",
                "1")
    if dist == "normal":
        if method == "tlc":
            return ("x = μ + σ·(Σ₁¹² rⱼ − 6)",
                    f"x = {fmt(p['mu'])} + {fmt(p['sigma'])}·(Σ₁¹² rⱼ − 6)",
                    "12")
        return ("x = μ + σ·Φ⁻¹(r)",
                f"x = {fmt(p['mu'])} + {fmt(p['sigma'])}·Φ⁻¹(r)   [Excel: INV.NORM(r; μ; σ)]",
                "1")
    if dist == "erlang":
        k = int(p["k"])
        if method == "convolucion":
            return ("x = −(1/λ)·ln(Π₁ᵏ rⱼ)",
                    f"x = −(1/{fmt(p['lam'])})·ln(r₁·r₂·…·r{k})",
                    str(k))
        return ("x = F⁻¹(r),  F(x) = 1 − Σₙ₌₀^(k−1) e^(−λx)(λx)ⁿ/n!",
                f"x = F⁻¹(r) con k = {k}, λ = {fmt(p['lam'])}   [Excel: INV.GAMMA(r; k; 1/λ)]",
                "1")
    if dist == "poisson":
        if method == "multiplicativo":
            return ("x = n  tal que  Π₁ⁿ rⱼ ≥ e^(−λ) > Π₁ⁿ⁺¹ rⱼ",
                    f"x = n  tal que  Π₁ⁿ rⱼ ≥ e^(−{fmt(p['lam'])}) = {fmt(math.exp(-p['lam']))} > Π₁ⁿ⁺¹ rⱼ",
                    "variable (x + 1)")
        return ("x tal que F(x − 1) ≤ r < F(x),  F(x) = Σⱼ₌₀ˣ e^(−λ)λʲ/j!",
                f"x tal que F(x − 1) ≤ r < F(x) con λ = {fmt(p['lam'])}",
                "1")
    if dist == "binomial":
        n = int(p["n"])
        if method == "bernoulli":
            return ("x = #{ rⱼ < p }  en n ensayos",
                    f"x = número de rⱼ < {fmt(p['p'])} entre {n} rⱼ consecutivos",
                    str(n))
        return ("x tal que F(x − 1) ≤ r < F(x),  F(x) = Σⱼ₌₀ˣ C(n,j)pʲ(1−p)ⁿ⁻ʲ",
                f"x tal que F(x − 1) ≤ r < F(x) con n = {n}, p = {fmt(p['p'])}",
                "1")
    return ("", "", "1")


# =========================================================================
# PROBABILIDAD TEORICA (con su desarrollo para mostrar en pantalla)
# =========================================================================
def _cdf_value_and_expr(dist: str, p: Dict[str, float], x: float, strict: bool) -> Tuple[float, str, str]:
    """Devuelve (valor, simbolo, desarrollo) de P(X < x) si strict, si no P(X <= x)."""
    if dist == "uniforme":
        a, b = p["a"], p["b"]
        v = uniform_cdf(x, a, b)
        if x <= a:
            expr = f"0  (x = {fmt(x)} ≤ A)"
        elif x >= b:
            expr = f"1  (x = {fmt(x)} ≥ B)"
        else:
            expr = f"(x − A)/(B − A) = ({fmt(x)} − {fmt(a)})/({fmt(b)} − {fmt(a)}) = {fmt_p(v)}"
        return v, f"F({fmt(x)})", expr

    if dist == "normal":
        mu, sigma = p["mu"], p["sigma"]
        z = (x - mu) / sigma
        v = normal_cdf(x, mu, sigma)
        expr = f"Φ((x − μ)/σ) = Φ(({fmt(x)} − {fmt(mu)})/{fmt(sigma)}) = Φ({z:.4f}) = {fmt_p(v)}"
        return v, f"F({fmt(x)})", expr

    if dist == "erlang":
        k, lam = int(p["k"]), p["lam"]
        v = erlang_cdf(x, k, lam)
        if x <= 0:
            expr = f"0  (x = {fmt(x)} ≤ 0)"
        else:
            lx = lam * x
            expr = (f"1 − Σₙ₌₀^{k - 1} e^(−λx)(λx)ⁿ/n!  con λx = {fmt(lam)}·{fmt(x)} = {fmt(lx, 4)}"
                    f"  →  1 − Σₙ₌₀^{k - 1} e^(−{fmt(lx, 4)})·{fmt(lx, 4)}ⁿ/n! = {fmt_p(v)}")
        return v, f"F({fmt(x)})", expr

    # Discretas: P(X < x) = F(ceil(x) - 1) ; P(X <= x) = F(floor(x))
    t = (math.ceil(x) - 1) if strict else math.floor(x)
    if dist == "poisson":
        lam = p["lam"]
        v = poisson_cdf(t, lam)
        if t < 0:
            expr = "0  (no hay valores negativos)"
        else:
            expr = f"Σⱼ₌₀^{t} e^(−{fmt(lam)})·{fmt(lam)}ʲ/j! = {fmt_p(v)}"
        return v, f"F({t})", expr

    if dist == "binomial":
        n, pp = int(p["n"]), p["p"]
        v = binomial_cdf(t, n, pp)
        if t < 0:
            expr = "0  (no hay valores negativos)"
        elif t >= n:
            expr = f"1  (x ≥ n = {n})"
        else:
            expr = f"Σⱼ₌₀^{t} C({n},j)·{fmt(pp)}ʲ·{fmt(1 - pp)}^({n}−j) = {fmt_p(v)}"
        return v, f"F({t})", expr

    return 0.0, "F(x)", ""


def theoretical_probability(dist: str, p: Dict[str, float], case_id: str, case: Dict[str, Any]) -> Dict[str, Any]:
    discrete = DIST_META[dist]["discrete"]
    if case_id == "menor":
        x, op = case["x"], case["op"]
        strict = op == "<"
        v, sym, expr = _cdf_value_and_expr(dist, p, x, strict)
        cond = f"X {'<' if strict else '≤'} {fmt(x)}"
        lines = []
        if discrete and strict:
            lines.append(f"P({cond}) = P(X ≤ {math.ceil(x) - 1}) = {sym}")
        elif discrete:
            lines.append(f"P({cond}) = P(X ≤ {math.floor(x)}) = {sym}")
        else:
            lines.append(f"P({cond}) = {sym}")
        lines.append(f"{sym} = {expr}")
        return {"condition": f"P({cond})", "p": v, "lines": lines}

    if case_id == "mayor":
        x, op = case["x"], case["op"]
        strict = op == ">"
        # P(X > x) = 1 - P(X <= x) ; P(X >= x) = 1 - P(X < x)
        v_c, sym, expr = _cdf_value_and_expr(dist, p, x, strict=not strict)
        v = max(0.0, 1.0 - v_c)
        cond = f"X {'>' if strict else '≥'} {fmt(x)}"
        comp = f"X {'≤' if strict else '<'} {fmt(x)}"
        lines = [f"P({cond}) = 1 − P({comp}) = 1 − {sym}",
                 f"{sym} = {expr}",
                 f"P({cond}) = 1 − {fmt_p(v_c)} = {fmt_p(v)}"]
        return {"condition": f"P({cond})", "p": v, "lines": lines}

    # rango: P(a <= X <= b) = P(X <= b) - P(X < a)
    a, b = case["a"], case["b"]
    v_b, sym_b, expr_b = _cdf_value_and_expr(dist, p, b, strict=False)
    v_a, sym_a, expr_a = _cdf_value_and_expr(dist, p, a, strict=True)
    v = max(0.0, v_b - v_a)
    cond = f"{fmt(a)} ≤ X ≤ {fmt(b)}"
    lines = [f"P({cond}) = P(X ≤ {fmt(b)}) − P(X < {fmt(a)}) = {sym_b} − {sym_a}",
             f"{sym_b} = {expr_b}",
             f"{sym_a} = {expr_a}",
             f"P({cond}) = {fmt_p(v_b)} − {fmt_p(v_a)} = {fmt_p(v)}"]
    return {"condition": f"P({cond})", "p": v, "lines": lines}


def _satisfies(case_id: str, case: Dict[str, Any], x: float) -> bool:
    if case_id == "menor":
        return x < case["x"] if case["op"] == "<" else x <= case["x"]
    if case_id == "mayor":
        return x > case["x"] if case["op"] == ">" else x >= case["x"]
    return case["a"] <= x <= case["b"]


def theoretical_moments(dist: str, p: Dict[str, float]) -> Tuple[float, float, str, str]:
    if dist == "uniforme":
        a, b = p["a"], p["b"]
        return (a + b) / 2, (b - a) ** 2 / 12, "(A + B)/2", "(B − A)²/12"
    if dist == "normal":
        return p["mu"], p["sigma"] ** 2, "μ", "σ²"
    if dist == "erlang":
        return p["k"] / p["lam"], p["k"] / p["lam"] ** 2, "k/λ", "k/λ²"
    if dist == "poisson":
        return p["lam"], p["lam"], "λ", "λ"
    n, pp = p["n"], p["p"]
    return n * pp, n * pp * (1 - pp), "n·p", "n·p·(1 − p)"


# =========================================================================
# HISTOGRAMA (observado vs esperado) PARA LA GRAFICA
# =========================================================================
def _histogram(dist: str, p: Dict[str, float], values: List[float]) -> Dict[str, Any]:
    nv = len(values)
    if nv == 0:
        return {"labels": [], "observed": [], "expected": [], "discrete": DIST_META[dist]["discrete"]}

    if DIST_META[dist]["discrete"]:
        if dist == "poisson":
            lam = p["lam"]
            hi_theo = int(math.ceil(lam + 4 * math.sqrt(lam) + 2))
            pmf = lambda t: poisson_pmf(t, lam)
        else:
            n, pp = int(p["n"]), p["p"]
            hi_theo = n
            pmf = lambda t: binomial_pmf(t, n, pp)
        hi = int(max(hi_theo if dist == "binomial" else min(hi_theo, 60), max(values)))
        labels, obs, exp = [], [], []
        counts: Dict[int, int] = {}
        for v in values:
            counts[int(v)] = counts.get(int(v), 0) + 1
        for t in range(0, hi + 1):
            labels.append(str(t))
            obs.append(counts.get(t, 0))
            exp.append(round(nv * pmf(t), 4))
        return {"labels": labels, "observed": obs, "expected": exp, "discrete": True}

    # Continuas
    if dist == "uniforme":
        lo_t, hi_t = p["a"], p["b"]
        cdf = lambda x: uniform_cdf(x, p["a"], p["b"])
    elif dist == "normal":
        lo_t, hi_t = p["mu"] - 3.5 * p["sigma"], p["mu"] + 3.5 * p["sigma"]
        cdf = lambda x: normal_cdf(x, p["mu"], p["sigma"])
    else:
        k, lam = int(p["k"]), p["lam"]
        lo_t, hi_t = 0.0, erlang_inv(0.995, k, lam)
        cdf = lambda x: erlang_cdf(x, k, lam)
    lo = min(lo_t, min(values))
    hi = max(hi_t, max(values))
    if hi <= lo:
        hi = lo + 1.0
    bins = max(5, min(25, int(round(math.sqrt(nv)))))
    width = (hi - lo) / bins
    obs = [0] * bins
    for v in values:
        idx = int((v - lo) / width)
        obs[min(max(idx, 0), bins - 1)] += 1
    labels, exp = [], []
    for j in range(bins):
        a = lo + j * width
        b = a + width
        labels.append(f"{a:.2f}–{b:.2f}")
        fa = 0.0 if j == 0 else cdf(a)          # el primer y ultimo bin absorben las colas
        fb = 1.0 if j == bins - 1 else cdf(b)
        exp.append(round(nv * max(0.0, fb - fa), 4))
    return {"labels": labels, "observed": obs, "expected": exp, "discrete": False}


# =========================================================================
# VALIDACION DE UNA DISTRIBUCION
# =========================================================================
def _params_label(dist: str, p: Dict[str, float]) -> str:
    if dist == "uniforme":
        return f"A = {fmt(p['a'])},  B = {fmt(p['b'])}"
    if dist == "normal":
        return f"μ = {fmt(p['mu'])},  σ = {fmt(p['sigma'])}"
    if dist == "erlang":
        return f"k = {int(p['k'])},  λ = {fmt(p['lam'])}"
    if dist == "poisson":
        return f"λ = {fmt(p['lam'])}"
    return f"n = {int(p['n'])},  p = {fmt(p['p'])}"


def validate_distribution(dist: str, cfg: Dict[str, Any], numbers: List[float], alpha: float,
                          order: int = 1, sample_limit: int = 200) -> Dict[str, Any]:
    meta = DIST_META[dist]
    method = cfg["method"]
    p = cfg["params"]
    base = {
        "id": dist,
        "order": order,
        "name": meta["name"],
        "short_name": meta["short"],
        "discrete": meta["discrete"],
        "method": method,
        "method_label": METHOD_LABELS.get((dist, method), method),
        "available_methods": [{"id": m, "label": METHOD_LABELS[(dist, m)]} for m in DIST_METHODS[dist]],
        "params": p,
        "params_label": _params_label(dist, p),
        "config": cfg,
        "n_r": len(numbers),
    }

    errs = _param_errors(dist, p)
    if errs:
        base.update({"status": "error", "errors": errs, "cases": [], "n_values": 0})
        return base

    formula, formula_p, r_per_value = conversion_formula(dist, method, p)
    conv = convert(dist, method, p, numbers)
    values = conv["values"]
    nv = len(values)
    z = z_alpha_2(alpha)

    base.update({
        "conversion_formula": formula,
        "conversion_formula_params": formula_p,
        "r_per_value": r_per_value,
        "n_values": nv,
        "discarded": conv["discarded"],
        "z": round(z, 4),
    })

    # ---- Pasos 3 y 4: conteo y validacion ----
    cases_out = []
    for cid in CASE_ORDER:
        case = cfg["cases"][cid]
        theo = theoretical_probability(dist, p, cid, case)
        count = sum(1 for x in values if _satisfies(cid, case, x))
        p_theo = theo["p"]
        p_sim = count / nv if nv else 0.0
        diff = abs(p_sim - p_theo)
        margin = z * math.sqrt(max(p_theo * (1 - p_theo), 0.0) / nv) if nv else 0.0
        validated = nv >= MIN_VALUES and diff <= margin + 1e-12
        rel = (diff / p_theo * 100.0) if p_theo > 0 else None
        cases_out.append({
            "id": cid,
            "label": CASE_LABELS[cid],
            "case": case,
            "condition": theo["condition"],
            "count": count,
            "n": nv,
            "expected_count": round(nv * p_theo, 4),
            "p_sim": round(p_sim, 6),
            "p_theo": round(p_theo, 6),
            "diff": round(diff, 6),
            "rel_error_pct": round(rel, 2) if rel is not None else None,
            "margin": round(margin, 6),
            "band_low": round(max(0.0, p_theo - margin), 6),
            "band_high": round(min(1.0, p_theo + margin), 6),
            "validated": bool(validated),
            "sim_expr": f"{count} / {nv} = {fmt_p(p_sim)}",
            "theo_lines": theo["lines"],
            "margin_expr": (f"Z_(α/2)·√(P(1 − P)/n) = {z:.4f}·√({fmt_p(p_theo)}·{fmt_p(1 - p_theo)}/{nv})"
                            f" = {fmt_p(margin)}"),
            "decision_expr": (f"|{fmt_p(p_sim)} − {fmt_p(p_theo)}| = {fmt_p(diff)} "
                              f"{'≤' if validated else '>'} {fmt_p(margin)}"),
        })

    # ---- Momentos ----
    mean_t, var_t, mean_f, var_f = theoretical_moments(dist, p)
    mean_s = statistics.fmean(values) if nv else 0.0
    var_s = statistics.variance(values) if nv > 1 else 0.0

    # ---- Tabla de conversion (muestra) ----
    trace = conv["trace"]
    has_r = trace and trace[0].get("r") is not None
    aux_label = {
        ("normal", "tlc"): "Σ rⱼ (12)",
        ("erlang", "convolucion"): "Π rⱼ",
        ("poisson", "multiplicativo"): "Π rⱼ (final)",
        ("binomial", "bernoulli"): "Éxitos (rⱼ < p)",
    }.get((dist, method))
    columns = ["i", "rᵢ usados"]
    if has_r:
        columns.append("rᵢ")
    if aux_label:
        columns.append(aux_label)
    columns.append("xᵢ convertido")
    short_cond = []
    for c in cases_out:
        cs = c["case"]
        if c["id"] == "rango":
            short_cond.append(f"¿{fmt(cs['a'])}≤x≤{fmt(cs['b'])}?")
        else:
            op = {"<": "<", "<=": "≤", ">": ">", ">=": "≥"}[cs["op"]]
            short_cond.append(f"¿x{op}{fmt(cs['x'])}?")
    columns += short_cond
    rows = []
    for i, (tr, x) in enumerate(zip(trace, values), start=1):
        if i > sample_limit:
            break
        row = {"i": i, "used": tr["used"]}
        if has_r:
            row["r"] = round(tr["r"], 6)
        if aux_label:
            row["aux"] = tr["aux"] if dist == "binomial" else float(f"{tr['aux']:.6g}")
        row["x"] = int(x) if meta["discrete"] else round(x, 6)
        for c, cid in zip(cases_out, CASE_ORDER):
            row[cid] = "✓" if _satisfies(cid, cfg["cases"][cid], x) else "·"
        rows.append(row)

    # ---- Estado ----
    notes = []
    if nv < MIN_VALUES:
        status = "inconclusive"
        notes.append(f"Solo se obtuvieron {nv} valores convertidos; se requieren al menos {MIN_VALUES} para validar.")
    else:
        status = "pass" if all(c["validated"] for c in cases_out) else "fail"
    if nv < RECOMMENDED_VALUES:
        notes.append(f"Con {nv} valores el margen de error es amplio; para una validación más exigente "
                     f"genere más números (se recomiendan {RECOMMENDED_VALUES} o más).")
    if r_per_value not in ("1",):
        notes.append(f"Este método consume {r_per_value} rᵢ por cada valor: {len(numbers)} rᵢ → {nv} valores.")
    if conv["discarded"]:
        if dist == "poisson" and method == "multiplicativo":
            notes.append("Los últimos rᵢ no alcanzaron a completar un valor (Π rⱼ nunca bajó de e^(−λ)) y se descartaron.")
        elif dist == "normal":
            notes.append(f"Se descartaron {conv['discarded']} rᵢ = 0 porque Φ⁻¹(0) = −∞.")
        else:
            notes.append(f"Se descartaron {conv['discarded']} grupos con algún rᵢ = 0 porque ln(0) no existe.")
    if dist == "erlang":
        notes.append("λ es la tasa de cada una de las k fases exponenciales (media = k/λ). "
                     "Si su curso define la Erlang con media 1/λ (Coss Bu), ingrese aquí λ·k.")
    if dist == "normal" and method == "tlc":
        notes.append("La suma de 12 rᵢ es una aproximación a la normal (Teorema del Límite Central); "
                     "la probabilidad teórica se calcula con la Normal exacta Φ.")
    if meta["discrete"]:
        notes.append("En distribuciones discretas P(X < x) y P(X ≤ x) son distintas: revise el operador de cada caso.")

    passed = sum(1 for c in cases_out if c["validated"])
    base.update({
        "status": status,
        "cases": cases_out,
        "cases_passed": passed,
        "moments": {
            "mean_sim": round(mean_s, 6), "mean_theo": round(mean_t, 6), "mean_formula": mean_f,
            "var_sim": round(var_s, 6), "var_theo": round(var_t, 6), "var_formula": var_f,
        },
        "histogram": _histogram(dist, p, values),
        "sample_table": {
            "columns": columns,
            "rows": rows,
            "truncated": nv > sample_limit,
            "total_rows": nv,
        },
        "notes": notes,
    })
    return base


# =========================================================================
# ORQUESTADOR
# =========================================================================
def run_distribution_validations(numbers: List[float], alpha: float = 0.05,
                                 config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        alpha = float(alpha)
    except (TypeError, ValueError):
        alpha = 0.05
    if not (0 < alpha < 1):
        alpha = 0.05

    numbers = [float(x) for x in (numbers or [])]
    cfg = normalize_config(config)

    if len(numbers) < MIN_VALUES:
        return {
            "success": False,
            "errors": [f"Se requieren al menos {MIN_VALUES} números pseudoaleatorios para validar las conversiones."],
            "alpha": alpha,
            "n_r": len(numbers),
            "config": cfg,
            "distributions": [],
        }

    dists = [validate_distribution(d, cfg[d], numbers, alpha, order=i + 1)
             for i, d in enumerate(DIST_ORDER)]
    total = len(dists)
    passed = sum(1 for d in dists if d["status"] == "pass")
    cases_total = sum(len(d.get("cases", [])) for d in dists)
    cases_passed = sum(d.get("cases_passed", 0) for d in dists)

    if passed == total:
        verdict, label = "VALIDADO", f"Todas las conversiones validadas — {cases_passed}/{cases_total} casos coinciden"
    elif passed >= math.ceil(total / 2):
        verdict, label = "PARCIAL", f"Validación parcial — {cases_passed}/{cases_total} casos coinciden"
    else:
        verdict, label = "NO_VALIDADO", f"Conversiones no validadas — solo {cases_passed}/{cases_total} casos coinciden"

    return {
        "success": True,
        "alpha": alpha,
        "z": round(z_alpha_2(alpha), 4),
        "n_r": len(numbers),
        "config": cfg,
        "summary": {
            "passed": passed,
            "total": total,
            "cases_passed": cases_passed,
            "cases_total": cases_total,
            "verdict": verdict,
            "verdict_label": label,
        },
        "distributions": dists,
    }
