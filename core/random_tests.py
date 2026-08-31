"""
Pruebas Estadisticas de Aleatoriedad para Secuencias PRNG
==========================================================
Implementa las 7 pruebas descritas en la "Especificacion Tecnica de
Pruebas de Aleatoriedad" (Evaluacion de Secuencias Continuas U(0,1)) y
en la "Especificacion Tecnica: Prueba de las Corridas" (Capitulo 3,
Coss Bu):

 1. Prueba de Promedio (Media Aritmetica)
 2. Prueba de Frecuencia (Chi-Cuadrada por Subintervalos)
 3. Prueba de Distancia (Huecos / Gap Test)
 4. Prueba de Series (Pares Solapados de bits)
 5. Prueba de Kolmogorov-Smirnov (K-S)
 6. Prueba de Poker (Clasico Decimal, 5 digitos)
 7. Prueba de Corridas Arriba y Abajo del Promedio

No requiere dependencias externas (solo la libreria estandar):
- Cuantiles Normales: statistics.NormalDist (Python >= 3.8)
- Cuantiles Chi-Cuadrado: funcion gamma incompleta regularizada
  implementada a mano (algoritmo de Numerical Recipes) + busqueda
  binaria, ya que la libreria estandar no trae chi2.ppf.

Todas las pruebas se aplican sobre la secuencia continua R_i in [0, 1)
que produce cualquiera de los 5 metodos generadores de la aplicacion,
de forma que el resultado (X de N pruebas superadas) sea comparable
entre metodos. Donde el enunciado original ofrece una variante binaria
y una continua (Frecuencia, Poker), se usa la variante continua/decimal
para mantener esa comparabilidad; para la Prueba de Series -que en el
enunciado solo se define sobre cadenas de bits- se deriva una cadena
binaria por umbral de mediana (b_i = 1 si R_i >= 0.5, si no 0), lo cual
se documenta explicitamente en las notas metodologicas de cada prueba.
"""

import math
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple


# =========================================================================
# UTILIDADES NUMERICAS: Normal y Chi-Cuadrado sin dependencias externas
# =========================================================================

_NORMAL = statistics.NormalDist(mu=0.0, sigma=1.0)


def z_alpha_2(alpha: float) -> float:
    """Valor critico Z_(alpha/2) de la Normal Estandar para una prueba bilateral."""
    alpha = min(max(alpha, 1e-9), 1 - 1e-9)
    return _NORMAL.inv_cdf(1 - alpha / 2)


def norm_cdf(x: float) -> float:
    return _NORMAL.cdf(x)


def _log_gamma(x: float) -> float:
    return math.lgamma(x)


def _lower_incomplete_gamma_reg_series(s: float, x: float) -> float:
    """Serie de potencias para P(s, x) (valida para x < s + 1)."""
    if x <= 0:
        return 0.0
    ap = s
    total = 1.0 / s
    delta = total
    for _ in range(500):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * 1e-14:
            break
    return total * math.exp(-x + s * math.log(x) - _log_gamma(s))


def _upper_incomplete_gamma_reg_cf(s: float, x: float) -> float:
    """Fraccion continua de Lentz para Q(s, x) (valida para x >= s + 1)."""
    tiny = 1e-300
    b = x + 1.0 - s
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - s)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h * math.exp(-x + s * math.log(x) - _log_gamma(s))


def chi2_cdf(x: float, df: float) -> float:
    """CDF de la distribucion Chi-Cuadrado con `df` grados de libertad."""
    if x <= 0:
        return 0.0
    s = df / 2.0
    y = x / 2.0
    if y < s + 1.0:
        return _lower_incomplete_gamma_reg_series(s, y)
    return 1.0 - _upper_incomplete_gamma_reg_cf(s, y)


def chi2_ppf(q: float, df: float) -> float:
    """Cuantil (inversa de la CDF) de la Chi-Cuadrado, via busqueda binaria."""
    if df <= 0:
        return 0.0
    q = min(max(q, 1e-9), 1 - 1e-9)
    lo, hi = 0.0, max(10.0, df * 4.0)
    tries = 0
    while chi2_cdf(hi, df) < q and tries < 60:
        hi *= 2.0
        tries += 1
    for _ in range(150):
        mid = (lo + hi) / 2.0
        if chi2_cdf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def chi2_critical(alpha: float, df: float) -> float:
    """Valor critico chi^2_(alpha, df) (cola superior)."""
    alpha = min(max(alpha, 1e-9), 1 - 1e-9)
    return chi2_ppf(1.0 - alpha, df)


def ks_critical(alpha: float, n: int) -> float:
    """
    Valor critico asintotico D_(alpha, n) para Kolmogorov-Smirnov.
    c(alpha) = sqrt(-0.5 * ln(alpha / 2)) reproduce exactamente los valores
    tabulados del PDF (alpha=0.10 -> 1.22, 0.05 -> 1.36, 0.01 -> 1.63).
    Se usa el ajuste de muestra finita de Stephens (1970):
        D_critico = c(alpha) / (sqrt(n) + 0.12 + 0.11/sqrt(n))
    que converge a la formula asintotica c(alpha)/sqrt(n) cuando n crece,
    y da una aproximacion razonable incluso para n <= 35.
    """
    alpha = min(max(alpha, 1e-9), 1 - 1e-9)
    c_alpha = math.sqrt(-0.5 * math.log(alpha / 2.0))
    n = max(1, n)
    denom = math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)
    return c_alpha / denom


# =========================================================================
# HELPER: Colapso de clases para pruebas Chi-Cuadrado (E_i >= 5)
# =========================================================================

def collapse_classes(entries: List[Dict[str, Any]], min_expected: float = 5.0) -> List[Dict[str, Any]]:
    """
    Fusiona clases adyacentes (en el orden dado) hasta que todas las
    frecuencias esperadas sean >= min_expected, o hasta que solo quede
    una clase (caso en el que la prueba no se puede evaluar). Cada
    entrada debe tener las llaves: label, observed, expected, prob.
    """
    entries = [dict(e) for e in entries]
    while len(entries) > 1:
        idx = None
        min_val = None
        for i, e in enumerate(entries):
            if e["expected"] < min_expected and (min_val is None or e["expected"] < min_val):
                idx = i
                min_val = e["expected"]
        if idx is None:
            break
        j = idx + 1 if idx < len(entries) - 1 else idx - 1
        a, b = entries[idx], entries[j]
        merged = {
            "label": f"{a['label']} + {b['label']}",
            "observed": a["observed"] + b["observed"],
            "expected": a["expected"] + b["expected"],
            "prob": a["prob"] + b["prob"],
        }
        lo, hi = min(idx, j), max(idx, j)
        entries = entries[:lo] + [merged] + entries[hi + 1:]
    return entries


def chi2_from_entries(entries: Sequence[Dict[str, Any]]) -> float:
    return sum((e["observed"] - e["expected"]) ** 2 / e["expected"] for e in entries)


# =========================================================================
# HELPER: Deteccion y agrupacion de corridas (Pruebas de Corridas)
# =========================================================================

def _run_lengths(binary_seq: Sequence[int]) -> List[int]:
    """Devuelve la longitud de cada corrida (racha) de simbolos identicos
    consecutivos en `binary_seq`."""
    lengths: List[int] = []
    if not binary_seq:
        return lengths
    cur = binary_seq[0]
    ln = 1
    for b in binary_seq[1:]:
        if b == cur:
            ln += 1
        else:
            lengths.append(ln)
            cur = b
            ln = 1
    lengths.append(ln)
    return lengths


def _build_run_classes(
    lengths: List[int], total_expected: float, fe_func, cap: int = 30, min_expected: float = 5.0
) -> Optional[Tuple[List[Dict[str, Any]], int]]:
    """
    Construye las clases de longitud de corrida i=1..h a partir de las
    frecuencias esperadas FE_i que entrega `fe_func`, agrupando la cola
    (todas las longitudes i > h) en una sola clase en cuanto FE_i cae por
    debajo de `min_expected` -- tal como indica el enunciado ("agrupar las
    categorias superiores de longitud i"). La expectativa de la clase cola
    se obtiene por resta (total_expected - suma de FE_i tabuladas) en vez
    de sumar una formula hasta el infinito, ya que FE_i ya son conteos
    esperados (no probabilidades) y su suma total teorica es exactamente
    `total_expected` (resultado de Knuth). El resultado final se pasa por
    collapse_classes como red de seguridad, para garantizar Eᵢ >= 5 en
    todas las clases incluso si la clase cola sigue quedando por debajo.
    """
    if not lengths:
        return None
    max_len = max(lengths)
    raw_entries: List[Dict[str, Any]] = []
    cum_fe = 0.0
    i = 1
    while i <= min(max_len, cap):
        fe = fe_func(i)
        if fe <= 0 or fe < min_expected:
            break
        obs = sum(1 for l in lengths if l == i)
        raw_entries.append({"label": f"i={i}", "observed": obs, "expected": fe, "prob": 0.0})
        cum_fe += fe
        i += 1
    h_used = i - 1
    obs_tail = sum(1 for l in lengths if l > h_used)
    fe_tail = total_expected - cum_fe
    if fe_tail <= 0:
        fe_tail = 1e-9
    raw_entries.append({"label": f"i≥{h_used + 1}", "observed": obs_tail, "expected": fe_tail, "prob": 0.0})
    entries = collapse_classes(raw_entries, min_expected=min_expected)
    return entries, h_used


def _round(x: Optional[float], nd: int = 6) -> Optional[float]:
    if x is None:
        return None
    try:
        if math.isnan(x) or math.isinf(x):
            return None
    except TypeError:
        return x
    return round(x, nd)


def _cap_rows(rows: List[Dict[str, Any]], limit: int = 60) -> Tuple[List[Dict[str, Any]], bool]:
    if len(rows) <= limit:
        return rows, False
    return rows[:limit], True


# =========================================================================
# 1. PRUEBA DE PROMEDIO (MEDIA ARITMETICA)
# =========================================================================
def test_promedio(numbers: List[float], alpha: float) -> Dict[str, Any]:
    n = len(numbers)
    mean = sum(numbers) / n
    z0 = (mean - 0.5) * math.sqrt(12 * n)
    z_crit = z_alpha_2(alpha)
    passed = abs(z0) <= z_crit

    rows, truncated = _cap_rows(
        [{"i": i + 1, "xi": _round(x)} for i, x in enumerate(numbers)]
    )

    return {
        "id": "promedio",
        "order": 1,
        "name": "Prueba de Promedio (Media Aritmética)",
        "objective": "Validar si el promedio muestral de n valores continuos en [0,1) converge al valor esperado teórico μ = 0.5.",
        "status": "pass" if passed else "fail",
        "passed": passed,
        "statistic_label": "Z₀",
        "statistic": _round(z0, 4),
        "critical_label": "Z_{α/2}",
        "critical_value": _round(z_crit, 4),
        "df": None,
        "decision_rule": "Se acepta H₀ (aleatorio) si |Z₀| ≤ Z_{α/2}",
        "conclusion": (
            f"|Z₀| = {abs(z0):.4f} {'≤' if passed else '>'} Z_(α/2) = {z_crit:.4f} ⇒ "
            f"se {'acepta' if passed else 'rechaza'} H₀: la secuencia "
            f"{'sí' if passed else 'NO'} es consistente con una media 0.5."
        ),
        "steps": [
            {"label": "Media muestral", "formula": "x̄ = (1/n) Σ xᵢ", "result": f"x̄ = {mean:.6f}  (n = {n})"},
            {"label": "Estadístico Z₀ (TLC, σ² = 1/12)", "formula": "Z₀ = (x̄ − 0.5)·√(12n)", "result": f"Z₀ = ({mean:.6f} − 0.5)·√({12*n}) = {z0:.4f}"},
            {"label": "Valor crítico", "formula": "Z_(α/2), α = " + f"{alpha:.4f}", "result": f"Z_(α/2) = {z_crit:.4f}"},
        ],
        "notes": [],
        "data_table": {
            "columns": ["i", "xᵢ"],
            "rows": rows,
            "truncated": truncated,
            "total_rows": n,
        },
    }


# =========================================================================
# 2. PRUEBA DE FRECUENCIA (CHI-CUADRADA POR SUBINTERVALOS)
# =========================================================================
def test_frecuencia(numbers: List[float], alpha: float) -> Dict[str, Any]:
    n = len(numbers)
    k = max(5, min(20, n // 5))
    observed = [0] * k
    for x in numbers:
        idx = min(int(x * k), k - 1)
        observed[idx] += 1
    expected = n / k
    chi0 = sum((o - expected) ** 2 / expected for o in observed)
    df = k - 1
    crit = chi2_critical(alpha, df)
    passed = chi0 < crit

    notes = []
    if expected < 5:
        notes.append(
            f"La frecuencia esperada por clase (E = n/k = {expected:.2f}) es menor a 5 "
            "porque la muestra n es pequeña; se recomienda aumentar n para mayor potencia estadística."
        )

    rows = [
        {
            "clase": i + 1,
            "intervalo": f"[{i/k:.3f}, {(i+1)/k:.3f})",
            "oi": o,
            "ei": _round(expected, 3),
            "aporte": _round((o - expected) ** 2 / expected, 4),
        }
        for i, o in enumerate(observed)
    ]

    return {
        "id": "frecuencia",
        "order": 2,
        "name": "Prueba de Frecuencia (Uniformidad por Subintervalos)",
        "objective": "Comprobar la distribución homogénea de los valores continuos en k subintervalos de igual longitud dentro de [0,1).",
        "status": "pass" if passed else "fail",
        "passed": passed,
        "statistic_label": "χ₀²",
        "statistic": _round(chi0, 4),
        "critical_label": f"χ²_(α, {df})",
        "critical_value": _round(crit, 4),
        "df": df,
        "decision_rule": "Se acepta H₀ si χ₀² < χ²_(α, k−1)",
        "conclusion": (
            f"χ₀² = {chi0:.4f} {'<' if passed else '≥'} χ²_(α,{df}) = {crit:.4f} ⇒ "
            f"se {'acepta' if passed else 'rechaza'} H₀: la distribución por subintervalos "
            f"{'sí' if passed else 'NO'} es homogénea."
        ),
        "steps": [
            {"label": "Número de intervalos", "formula": "k = clamp(n/5, 5, 20)", "result": f"k = {k}  (n = {n})"},
            {"label": "Frecuencia esperada", "formula": "Eᵢ = n / k", "result": f"Eᵢ = {expected:.4f} para cada clase"},
            {"label": "Estadístico", "formula": "χ₀² = Σ (Oᵢ − Eᵢ)² / Eᵢ", "result": f"χ₀² = {chi0:.4f}"},
            {"label": "Grados de libertad y valor crítico", "formula": "ν = k − 1", "result": f"ν = {df} ⇒ χ²_(α,{df}) = {crit:.4f}"},
        ],
        "notes": notes,
        "data_table": {
            "columns": ["Clase", "Intervalo", "Oᵢ", "Eᵢ", "Aporte χ²"],
            "rows": rows,
            "truncated": False,
            "total_rows": len(rows),
        },
    }


# =========================================================================
# 3. PRUEBA DE DISTANCIA (HUECOS / GAP TEST)
# =========================================================================
def test_distancia(numbers: List[float], alpha: float, lo: float = 0.0, hi: float = 0.5) -> Dict[str, Any]:
    p = hi - lo
    q = 1.0 - p

    hits_idx = [i for i, x in enumerate(numbers) if lo <= x < hi]

    gaps: List[int] = []
    for a, b in zip(hits_idx, hits_idx[1:]):
        gaps.append(b - a - 1)

    if len(gaps) < 5:
        return _insufficient_data(
            "distancia", 3, "Prueba de Distancia (Huecos / Gap Test)",
            "Evaluar la longitud de separación (huecos) entre apariciones sucesivas de valores que caen en un subrango [α, β) ⊂ [0,1).",
            f"Se necesitan al menos 5 huecos completos entre ocurrencias dentro de [{lo}, {hi}) y solo se observaron {len(gaps)}. "
            "Aumente n o amplíe el intervalo de interés para tener más ocurrencias.",
        )

    N = len(gaps)
    h_max = min(max(gaps) + 1, 30)

    raw_entries = []
    for i in range(h_max):
        prob_i = p * ((1 - p) ** i)
        obs_i = sum(1 for g in gaps if g == i)
        raw_entries.append({"label": f"i={i}", "observed": obs_i, "expected": N * prob_i, "prob": prob_i})
    prob_tail = (1 - p) ** h_max
    obs_tail = sum(1 for g in gaps if g >= h_max)
    raw_entries.append({"label": f"i≥{h_max}", "observed": obs_tail, "expected": N * prob_tail, "prob": prob_tail})

    entries = collapse_classes(raw_entries)
    if len(entries) < 2:
        return _insufficient_data(
            "distancia", 3, "Prueba de Distancia (Huecos / Gap Test)",
            "Evaluar la longitud de separación (huecos) entre apariciones sucesivas de valores que caen en un subrango [α, β) ⊂ [0,1).",
            "No fue posible formar al menos 2 clases con frecuencia esperada ≥ 5 a partir de los huecos observados.",
        )

    chi0 = chi2_from_entries(entries)
    df = len(entries) - 1
    crit = chi2_critical(alpha, df)
    passed = chi0 < crit

    rows = [
        {"clase": e["label"], "oi": e["observed"], "ei": _round(e["expected"], 3), "aporte": _round((e["observed"] - e["expected"]) ** 2 / e["expected"], 4)}
        for e in entries
    ]

    return {
        "id": "distancia",
        "order": 3,
        "name": "Prueba de Distancia (Huecos / Gap Test)",
        "objective": "Evaluar la longitud de separación (huecos) entre apariciones sucesivas de valores que caen dentro de un subrango específico [α, β) ⊂ [0,1).",
        "status": "pass" if passed else "fail",
        "passed": passed,
        "statistic_label": "χ₀²",
        "statistic": _round(chi0, 4),
        "critical_label": f"χ²_(α, {df})",
        "critical_value": _round(crit, 4),
        "df": df,
        "decision_rule": "Se acepta H₀ si χ₀² < χ²_(α, h)",
        "conclusion": (
            f"χ₀² = {chi0:.4f} {'<' if passed else '≥'} χ²_(α,{df}) = {crit:.4f} ⇒ "
            f"se {'acepta' if passed else 'rechaza'} H₀: los huecos entre ocurrencias en [{lo}, {hi}) "
            f"{'sí' if passed else 'NO'} siguen la distribución geométrica esperada."
        ),
        "steps": [
            {"label": "Intervalo de interés", "formula": "[α, β) ⊂ [0,1)", "result": f"[{lo}, {hi})  ⇒  p = β−α = {p:.4f}, q = 1−p = {q:.4f}"},
            {"label": "Huecos observados", "formula": "N = total de huecos entre ocurrencias", "result": f"N = {N} huecos (a partir de {len(hits_idx)} ocurrencias en la muestra)"},
            {"label": "Probabilidades teóricas", "formula": "P(i)=p(1−p)ⁱ  ;  P(i≥h)=(1−p)ʰ", "result": f"Clases agrupadas dinámicamente hasta lograr Eᵢ ≥ 5 (quedaron {len(entries)} clases)"},
            {"label": "Estadístico", "formula": "χ₀² = Σ (Oᵢ − Eᵢ)² / Eᵢ", "result": f"χ₀² = {chi0:.4f}"},
            {"label": "Grados de libertad y valor crítico", "formula": "ν = h (clases − 1)", "result": f"ν = {df} ⇒ χ²_(α,{df}) = {crit:.4f}"},
        ],
        "notes": [
            "Las clases de huecos se agruparon automáticamente (criterio de Cochran, Eᵢ ≥ 5) partiendo de una clase por cada longitud de hueco observada."
        ],
        "data_table": {
            "columns": ["Clase (i)", "Oᵢ", "Eᵢ", "Aporte χ²"],
            "rows": rows,
            "truncated": False,
            "total_rows": len(rows),
        },
    }


# =========================================================================
# 4. PRUEBA DE SERIES (PARES SOLAPADOS DE BITS)
# =========================================================================
def test_series(numbers: List[float], alpha: float) -> Dict[str, Any]:
    bits = [1 if x >= 0.5 else 0 for x in numbers]
    n = len(bits)
    n0 = bits.count(0)
    n1 = bits.count(1)

    n00 = n01 = n10 = n11 = 0
    for a, b in zip(bits, bits[1:]):
        if a == 0 and b == 0:
            n00 += 1
        elif a == 0 and b == 1:
            n01 += 1
        elif a == 1 and b == 0:
            n10 += 1
        else:
            n11 += 1

    x2 = (4.0 / (n - 1)) * (n00**2 + n01**2 + n10**2 + n11**2) - (2.0 / n) * (n0**2 + n1**2) + 1
    df = 2
    crit = chi2_critical(alpha, df)
    passed = x2 < crit

    rows, truncated = _cap_rows(
        [{"i": i + 1, "xi": _round(x), "bit": b} for i, (x, b) in enumerate(zip(numbers, bits))]
    )

    return {
        "id": "series",
        "order": 4,
        "name": "Prueba de Series (Pares Solapados)",
        "objective": "Verificar si los pares consecutivos de bits son independientes y equiprobables.",
        "status": "pass" if passed else "fail",
        "passed": passed,
        "statistic_label": "X₂",
        "statistic": _round(x2, 4),
        "critical_label": f"χ²_(α, {df})",
        "critical_value": _round(crit, 4),
        "df": df,
        "decision_rule": "Se acepta H₀ si X₂ < χ²_(α, 2)",
        "conclusion": (
            f"X₂ = {x2:.4f} {'<' if passed else '≥'} χ²_(α,2) = {crit:.4f} ⇒ "
            f"se {'acepta' if passed else 'rechaza'} H₀: los pares consecutivos de bits "
            f"{'sí' if passed else 'NO'} son independientes y equiprobables."
        ),
        "steps": [
            {"label": "Binarización de la muestra", "formula": "bᵢ = 1 si Rᵢ ≥ 0.5, si no 0", "result": f"n₀ = {n0} ceros, n₁ = {n1} unos (n = {n})"},
            {"label": "Frecuencias de pares solapados", "formula": "n₀₀, n₀₁, n₁₀, n₁₁", "result": f"n₀₀={n00}, n₀₁={n01}, n₁₀={n10}, n₁₁={n11} (Σ = {n00+n01+n10+n11} = n−1)"},
            {"label": "Estadístico exacto", "formula": "X₂ = [4/(n−1)]·(n₀₀²+n₀₁²+n₁₀²+n₁₁²) − (2/n)·(n₀²+n₁²) + 1", "result": f"X₂ = {x2:.4f}"},
            {"label": "Grados de libertad y valor crítico", "formula": "ν = 2", "result": f"χ²_(α,2) = {crit:.4f}"},
        ],
        "notes": [
            "El enunciado define esta prueba sobre cadenas binarias; como los métodos de este software producen "
            "números continuos Rᵢ ∈ [0,1), se deriva una cadena de bits por umbral de mediana "
            "(bᵢ = 1 si Rᵢ ≥ 0.5) para poder aplicarla de forma uniforme a los 5 métodos."
        ],
        "data_table": {
            "columns": ["i", "Rᵢ", "bᵢ"],
            "rows": rows,
            "truncated": truncated,
            "total_rows": n,
        },
    }


# =========================================================================
# 5. PRUEBA DE KOLMOGOROV-SMIRNOV (K-S)
# =========================================================================
def test_ks(numbers: List[float], alpha: float) -> Dict[str, Any]:
    n = len(numbers)
    xs = sorted(numbers)

    d_plus = max((i + 1) / n - xs[i] for i in range(n))
    d_minus = max(xs[i] - i / n for i in range(n))
    d = max(d_plus, d_minus)

    crit = ks_critical(alpha, n)
    passed = d <= crit

    rows, truncated = _cap_rows(
        [
            {
                "i": i + 1,
                "xi": _round(xs[i]),
                "i_n": _round((i + 1) / n, 6),
                "im1_n": _round(i / n, 6),
                "dplus_i": _round((i + 1) / n - xs[i], 6),
                "dminus_i": _round(xs[i] - i / n, 6),
            }
            for i in range(n)
        ]
    )

    return {
        "id": "kolmogorov_smirnov",
        "order": 5,
        "name": "Prueba de Kolmogorov-Smirnov (K-S)",
        "objective": "Evaluar la máxima desviación absoluta entre la función de distribución acumulada empírica Fₙ(x) y la teórica F(x) = x.",
        "status": "pass" if passed else "fail",
        "passed": passed,
        "statistic_label": "D",
        "statistic": _round(d, 6),
        "critical_label": "D_(α, n)",
        "critical_value": _round(crit, 6),
        "df": None,
        "decision_rule": "Se acepta H₀ si D ≤ D_(α, n)",
        "conclusion": (
            f"D = {d:.6f} {'≤' if passed else '>'} D_(α,n) = {crit:.6f} ⇒ "
            f"se {'acepta' if passed else 'rechaza'} H₀: la muestra {'sí' if passed else 'NO'} "
            "es consistente con la distribución uniforme F(x) = x."
        ),
        "steps": [
            {"label": "Ordenar muestra", "formula": "x₍₁₎ ≤ x₍₂₎ ≤ … ≤ x₍ₙ₎", "result": f"n = {n} valores ordenados"},
            {"label": "Discrepancia superior", "formula": "D⁺ = max[ i/n − x₍ᵢ₎ ]", "result": f"D⁺ = {d_plus:.6f}"},
            {"label": "Discrepancia inferior", "formula": "D⁻ = max[ x₍ᵢ₎ − (i−1)/n ]", "result": f"D⁻ = {d_minus:.6f}"},
            {"label": "Estadístico supremo", "formula": "D = max(D⁺, D⁻)", "result": f"D = {d:.6f}"},
            {"label": "Valor crítico (aprox. Stephens 1970)", "formula": "D_(α,n) = c(α) / (√n + 0.12 + 0.11/√n)", "result": f"D_(α,n) = {crit:.6f}"},
        ],
        "notes": [] if n > 35 else [
            "n ≤ 35: se usa la aproximación de muestra finita de Stephens (1970), ya que el PDF solo tabula "
            "las cotas asintóticas válidas para n > 35."
        ],
        "data_table": {
            "columns": ["i", "x₍ᵢ₎", "i/n", "(i−1)/n", "D⁺ᵢ", "D⁻ᵢ"],
            "rows": rows,
            "truncated": truncated,
            "total_rows": n,
        },
    }


# =========================================================================
# 6. PRUEBA DE POKER (CLASICO DECIMAL, 5 DIGITOS)
# =========================================================================
_POKER_CLASSES = [
    ("TD", "Todos Diferentes", 0.3024),
    ("1P", "Un Par", 0.5040),
    ("2P", "Dos Pares", 0.1080),
    ("T", "Tercia", 0.0720),
    ("F", "Full", 0.0090),
    ("P4", "Póker", 0.0045),
    ("Q", "Quintilla", 0.0001),
]

_POKER_LOOKUP = {
    (1, 1, 1, 1, 1): "TD",
    (2, 1, 1, 1): "1P",
    (2, 2, 1): "2P",
    (3, 1, 1): "T",
    (3, 2): "F",
    (4, 1): "P4",
    (5,): "Q",
}


def _poker_digits(x: float) -> str:
    v = int(x * 100000)
    v = max(0, min(99999, v))
    return f"{v:05d}"


def _poker_hand(digits: str) -> str:
    counts = tuple(sorted(Counter(digits).values(), reverse=True))
    return _POKER_LOOKUP.get(counts, "TD")


def test_poker(numbers: List[float], alpha: float) -> Dict[str, Any]:
    n = len(numbers)
    hands = [_poker_hand(_poker_digits(x)) for x in numbers]
    counts = Counter(hands)

    raw_entries = [
        {"label": f"{code} ({label})", "observed": counts.get(code, 0), "expected": n * p, "prob": p}
        for code, label, p in _POKER_CLASSES
    ]
    entries = collapse_classes(raw_entries)
    if len(entries) < 2:
        return _insufficient_data(
            "poker", 6, "Prueba de Poker (Clásico Decimal)",
            "Analizar la frecuencia de combinaciones de dígitos en bloques de 5 dígitos, similar a las manos de póker.",
            "La muestra es demasiado pequeña para formar al menos 2 clases con frecuencia esperada ≥ 5.",
        )

    chi0 = chi2_from_entries(entries)
    df = len(entries) - 1
    crit = chi2_critical(alpha, df)
    passed = chi0 < crit

    rows = [
        {"clase": e["label"], "oi": e["observed"], "ei": _round(e["expected"], 3), "aporte": _round((e["observed"] - e["expected"]) ** 2 / e["expected"], 4)}
        for e in entries
    ]
    sample_rows, sample_truncated = _cap_rows(
        [{"i": i + 1, "xi": _round(x), "digitos": _poker_digits(x), "mano": h} for i, (x, h) in enumerate(zip(numbers, hands))]
    )

    return {
        "id": "poker",
        "order": 6,
        "name": "Prueba de Poker (Clásico Decimal, 5 dígitos)",
        "objective": "Analizar la frecuencia de combinaciones de dígitos en bloques de 5 dígitos, similar a las manos de póker.",
        "status": "pass" if passed else "fail",
        "passed": passed,
        "statistic_label": "X₃",
        "statistic": _round(chi0, 4),
        "critical_label": f"χ²_(α, {df})",
        "critical_value": _round(crit, 4),
        "df": df,
        "decision_rule": "Se acepta H₀ si X₃ < χ²_(α, ν)",
        "conclusion": (
            f"X₃ = {chi0:.4f} {'<' if passed else '≥'} χ²_(α,{df}) = {crit:.4f} ⇒ "
            f"se {'acepta' if passed else 'rechaza'} H₀: la frecuencia de las manos de póker "
            f"{'sí' if passed else 'NO'} coincide con la distribución teórica."
        ),
        "steps": [
            {"label": "Extracción de dígitos", "formula": "dígitos(Rᵢ) = ⌊Rᵢ · 10⁵⌋, con relleno a 5 cifras", "result": f"n = {n} bloques de 5 dígitos"},
            {"label": "Clasificación de manos", "formula": "Según multiplicidad de dígitos repetidos", "result": "TD / 1P / 2P / T / F / P4 / Q"},
            {"label": "Colapso de clases", "formula": "Se fusionan clases adyacentes con Eⱼ < 5", "result": f"Quedaron {len(entries)} clases tras el colapso"},
            {"label": "Estadístico", "formula": "χ² = Σ (Oᵢ − Eᵢ)² / Eᵢ", "result": f"X₃ = {chi0:.4f}"},
            {"label": "Grados de libertad y valor crítico", "formula": "ν = clases − 1", "result": f"ν = {df} ⇒ χ²_(α,{df}) = {crit:.4f}"},
        ],
        "notes": [
            "Se usa la variante decimal clásica (5 dígitos por bloque) del enunciado, que aplica directamente "
            "sobre los valores continuos Rᵢ de cualquiera de los 5 métodos."
        ],
        "data_table": {
            "columns": ["Clase", "Oᵢ", "Eᵢ", "Aporte χ²"],
            "rows": rows,
            "truncated": False,
            "total_rows": len(rows),
        },
        "sample_table": {
            "columns": ["i", "Rᵢ", "Dígitos", "Mano"],
            "rows": sample_rows,
            "truncated": sample_truncated,
            "total_rows": n,
        },
    }


# =========================================================================
# 7. PRUEBA DE CORRIDAS ARRIBA Y ABAJO DEL PROMEDIO
# =========================================================================
def test_corridas_promedio(numbers: List[float], alpha: float) -> Dict[str, Any]:
    n = len(numbers)
    bits = [0 if x < 0.5 else 1 for x in numbers]
    lengths = _run_lengths(bits)
    total_runs = len(lengths)

    obj = (
        "Evaluar la alternancia de los valores respecto al valor esperado teórico μ = 0.5 "
        "(variante estática de la prueba de la distancia), mediante el conteo y la longitud de "
        "las corridas (rachas) de valores consecutivos por encima o por debajo de la media."
    )

    if total_runs < 5:
        return _insufficient_data(
            "corridas_promedio", 7, "Prueba de Corridas Arriba y Abajo del Promedio", obj,
            f"Solo se observaron {total_runs} corridas en la secuencia binarizada; se necesitan al menos 5 "
            "para construir la tabla de clases. Aumente n y vuelva a generar.",
        )

    total_expected = (n + 1) / 2.0

    def fe_i(i: int) -> float:
        return (n - i + 3) / (2 ** (i + 1))

    built = _build_run_classes(lengths, total_expected, fe_i, cap=30)
    entries, h_used = built if built else (None, 0)
    if not entries or len(entries) < 2:
        return _insufficient_data(
            "corridas_promedio", 7, "Prueba de Corridas Arriba y Abajo del Promedio", obj,
            "No fue posible formar al menos 2 clases con frecuencia esperada ≥ 5 a partir de las corridas observadas.",
        )

    chi0 = chi2_from_entries(entries)
    df = len(entries) - 1
    crit = chi2_critical(alpha, df)
    passed = chi0 <= crit

    rows = [
        {"clase": e["label"], "oi": e["observed"], "ei": _round(e["expected"], 3), "aporte": _round((e["observed"] - e["expected"]) ** 2 / e["expected"], 4)}
        for e in entries
    ]
    sample_rows, sample_truncated = _cap_rows(
        [{"i": i + 1, "xi": _round(x), "bit": b} for i, (x, b) in enumerate(zip(numbers, bits))]
    )

    return {
        "id": "corridas_promedio",
        "order": 7,
        "name": "Prueba de Corridas Arriba y Abajo del Promedio",
        "objective": obj,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "statistic_label": "X₀²",
        "statistic": _round(chi0, 4),
        "critical_label": f"χ²_(α, {df})",
        "critical_value": _round(crit, 4),
        "df": df,
        "decision_rule": "Se acepta H₀ si X₀² ≤ χ²_(α, k−1)",
        "conclusion": (
            f"X₀² = {chi0:.4f} {'≤' if passed else '>'} χ²_(α,{df}) = {crit:.4f} ⇒ "
            f"se {'acepta' if passed else 'rechaza'} H₀: la alternancia de corridas respecto a μ = 0.5 "
            f"{'sí' if passed else 'NO'} es consistente con independencia."
        ),
        "steps": [
            {"label": "Binarización estática", "formula": "sᵢ = 0 si Rᵢ < 0.5, sᵢ = 1 si Rᵢ ≥ 0.5", "result": f"n = {n} símbolos, {total_runs} corridas detectadas"},
            {"label": "Total esperado de corridas", "formula": "E(Total) = (N + 1) / 2", "result": f"E(Total) = {total_expected:.4f}"},
            {"label": "Frecuencia esperada por longitud", "formula": "FEᵢ = (N − i + 3) / 2^(i+1)", "result": f"Clases agrupadas (criterio de Cochran, FEᵢ ≥ 5) hasta i = {h_used}; quedaron {len(entries)} clases"},
            {"label": "Estadístico", "formula": "X₀² = Σ (FOᵢ − FEᵢ)² / FEᵢ", "result": f"X₀² = {chi0:.4f}"},
            {"label": "Grados de libertad y valor crítico", "formula": "ν = k − 1", "result": f"ν = {df} ⇒ χ²_(α,{df}) = {crit:.4f}"},
        ],
        "notes": [
            "Versión 1 del enunciado (Capítulo 3, Coss Bu): se compara cada valor contra μ = 0.5 en vez de contra su predecesor inmediato."
        ],
        "data_table": {
            "columns": ["Clase (longitud i)", "FOᵢ", "FEᵢ", "Aporte χ²"],
            "rows": rows,
            "truncated": False,
            "total_rows": len(rows),
        },
        "sample_table": {
            "columns": ["i", "Rᵢ", "sᵢ"],
            "rows": sample_rows,
            "truncated": sample_truncated,
            "total_rows": n,
        },
    }


def _insufficient_data(test_id: str, order: int, name: str, objective: str, reason: str) -> Dict[str, Any]:
    return {
        "id": test_id,
        "order": order,
        "name": name,
        "objective": objective,
        "status": "inconclusive",
        "passed": False,
        "statistic_label": None,
        "statistic": None,
        "critical_label": None,
        "critical_value": None,
        "df": None,
        "decision_rule": None,
        "conclusion": f"Datos insuficientes: {reason}",
        "steps": [],
        "notes": [reason],
        "data_table": {"columns": [], "rows": [], "truncated": False, "total_rows": 0},
    }


# =========================================================================
# ORQUESTADOR
# =========================================================================
_ALL_TESTS = [
    test_promedio,
    test_frecuencia,
    test_distancia,
    test_series,
    test_ks,
    test_poker,
    test_corridas_promedio,
]


def run_all_tests(numbers: List[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Ejecuta las 8 pruebas estadísticas sobre la secuencia `numbers` (valores en [0,1))."""
    try:
        alpha = float(alpha)
    except (TypeError, ValueError):
        alpha = 0.05
    if not (0 < alpha < 1):
        alpha = 0.05

    n = len(numbers)
    if n < 10:
        return {
            "success": False,
            "errors": ["Se requieren al menos 10 valores generados para ejecutar las pruebas estadísticas."],
            "alpha": alpha,
            "n": n,
            "summary": {"passed": 0, "total": len(_ALL_TESTS), "verdict": "NO_CONCLUYENTE", "verdict_label": "Muestra insuficiente"},
            "tests": [],
        }

    tests = [fn(numbers, alpha) for fn in _ALL_TESTS]
    passed_count = sum(1 for t in tests if t["status"] == "pass")
    total = len(tests)

    if passed_count == total:
        verdict = "ALEATORIO"
        verdict_label = f"Aleatorio — {passed_count}/{total} pruebas superadas"
    elif passed_count >= math.ceil(total * 0.5):
        verdict = "ALEATORIO_CON_RESERVAS"
        verdict_label = f"Aleatorio con reservas — {passed_count}/{total} pruebas superadas"
    else:
        verdict = "NO_ALEATORIO"
        verdict_label = f"No aleatorio — solo {passed_count}/{total} pruebas superadas"

    return {
        "success": True,
        "alpha": alpha,
        "n": n,
        "summary": {
            "passed": passed_count,
            "total": total,
            "verdict": verdict,
            "verdict_label": verdict_label,
        },
        "tests": tests,
    }
