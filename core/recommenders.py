"""
Parameter Recommenders and Optimal Generators for PRNG Algorithms
Provides random parameter generators adhering to mathematical constraints.
"""

import random
from typing import Dict, Any
from .validators import is_prime, find_primitive_roots, gcd


def generate_gclm_optimal(scale: str = "medium") -> Dict[str, Any]:
    if scale == "small":
        g = random.randint(4, 7)
    elif scale == "large":
        g = random.randint(14, 18)
    else:
        g = random.randint(8, 12)

    m = 2 ** g
    max_k = (m - 2) // 4
    k = random.randint(1, max(1, max_k))
    a = 1 + 4 * k
    c = random.randrange(1, m, 2)
    X0 = random.randint(0, m - 1)

    return {
        "X0": X0,
        "a": a,
        "c": c,
        "m": m,
        "n": min(100, m),
        "explanation": f"Generado con m=2^{g}={m}, a=1+4({k})={a}, c={c}, X0={X0}. Periodo Completo N={m}."
    }


def generate_gcm_optimal(case_type: str = "pow2") -> Dict[str, Any]:
    if case_type == "pow2":
        g = random.randint(7, 12)
        m = 2 ** g
        base = random.choice([3, 5])
        max_k = (m - base - 1) // 8
        k = random.randint(1, max(1, max_k))
        a = base + 8 * k
        X0 = random.randrange(1, m, 2)
        return {
            "X0": X0,
            "a": a,
            "m": m,
            "n": 50,
            "explanation": f"Modulo potencia de dos m=2^{g}={m}, a={a}, X0={X0}. Periodo maximal N={m//4}."
        }
    else:
        candidate_primes = [101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997, 1009]
        m = random.choice(candidate_primes)
        roots = find_primitive_roots(m, limit=10)
        a = random.choice(roots) if roots else 3
        X0 = random.randint(1, m - 1)
        return {
            "X0": X0,
            "a": a,
            "m": m,
            "n": 50,
            "explanation": f"Modulo primo m={m}, a={a}, X0={X0}. Periodo maximal N={m-1}."
        }


def generate_cuadrados_medios_optimal(D: int = 4) -> Dict[str, Any]:
    while True:
        min_v = 10 ** (D - 1)
        max_v = (10 ** D) - 1
        X0 = random.randint(min_v, max_v)
        s = str(X0)
        if not s.endswith("0") and not s.endswith("25") and not s.endswith("50") and not s.endswith("75") and "00" not in s:
            if X0 != 3792:
                return {
                    "D": D,
                    "X0": X0,
                    "n": 30,
                    "explanation": f"Semilla aleatoria X0={X0} de D={D} digitos."
                }


def generate_productos_medios_optimal(D: int = 4) -> Dict[str, Any]:
    min_v = 10 ** (D - 1)
    max_v = (10 ** D) - 1
    while True:
        X0 = random.randint(min_v, max_v)
        s0 = str(X0)
        if not s0.endswith("0") and "00" not in s0:
            break
    while True:
        X1 = random.randint(min_v, max_v)
        s1 = str(X1)
        if X1 != X0 and not s1.endswith("0") and "00" not in s1 and gcd(X0, X1) == 1:
            break
    return {
        "D": D,
        "X0": X0,
        "X1": X1,
        "n": 35,
        "explanation": f"Semillas coprimas X0={X0}, X1={X1} de D={D} digitos."
    }


def generate_bbs_optimal() -> Dict[str, Any]:
    blum_primes = [
        43, 47, 67, 71, 79, 83, 103, 107, 127, 131, 139, 151, 163, 167, 179, 191, 199,
        211, 223, 227, 239, 251, 263, 271, 283, 307, 311, 331, 347, 359, 367, 379, 383,
        419, 431, 439, 443, 463, 467, 479, 487, 491, 499, 503, 523, 547, 563, 571, 587,
        599, 607, 619, 631, 643, 647, 659, 683, 691, 719, 727, 739, 743, 751, 787, 811,
        823, 827, 839, 859, 863, 883, 887, 907, 911, 919, 947, 967, 971, 983, 991, 1019
    ]
    p = random.choice(blum_primes)
    while True:
        q = random.choice(blum_primes)
        if q != p:
            break
    M = p * q
    while True:
        s = random.randint(100, M - 1)
        if gcd(s, M) == 1:
            break

    return {
        "p": p,
        "q": q,
        "s": s,
        "n": 50,
        "explanation": f"Generado: p={p}, q={q}, M={M}, semilla s={s}."
    }
