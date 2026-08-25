"""
Validators and Number Theoretic Utilities for PRNG Algorithms
Implements:
- Hull-Dobell Theorem verification for Mixed Congruential (GCLM)
- Maximal period checks for Multiplicative Congruential (GCM)
- Heuristic and structural checks for Middle Square & Middle Product
- Blum Blum Shub (BBS) cryptographic requirements and safe primes
"""

import math
from typing import Dict, List, Any, Tuple


def gcd(a: int, b: int) -> int:
    """Computes Greatest Common Divisor."""
    return math.gcd(abs(a), abs(b))


def is_prime(n: int) -> bool:
    """
    Checks if integer n is prime using a deterministic Miller-Rabin test.
    The witness set {2,3,5,7,11,13,17,19,23,29,31,37} is proven deterministic
    for every n < 3.3 * 10^24, so this is exact (not probabilistic) for any
    value a user could realistically type into this app - and unlike the old
    trial-division loop, it stays fast even if someone enters a very large
    modulus/prime (trial division degrades to O(sqrt(n)), which can take
    seconds to minutes once n has 15+ digits).
    """
    if n <= 1:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n == p:
            return True
        if n % p == 0:
            return False

    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1

    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def get_prime_factors(n: int) -> List[int]:
    """Returns unique prime factors of n."""
    factors = set()
    d = 2
    temp = abs(n)
    while d * d <= temp:
        if temp % d == 0:
            factors.add(d)
            while temp % d == 0:
                temp //= d
        d += 1
    if temp > 1:
        factors.add(temp)
    return sorted(list(factors))


def is_power_of_two(n: int) -> Tuple[bool, int]:
    """Checks if n = 2^g and returns (is_pow2, g)."""
    if n <= 0:
        return False, 0
    if (n & (n - 1)) == 0:
        g = int(math.log2(n))
        return True, g
    return False, 0


def euler_totient(n: int) -> int:
    """Computes Euler's totient function phi(n)."""
    result = n
    p = 2
    temp = n
    while p * p <= temp:
        if temp % p == 0:
            while temp % p == 0:
                temp //= p
            result -= result // p
        p += 1
    if temp > 1:
        result -= result // temp
    return result


def is_primitive_root(a: int, m: int) -> bool:
    """Checks if a is a primitive root modulo m (m prime or valid modulus)."""
    if not is_prime(m):
        return False
    if gcd(a, m) != 1:
        return False
    phi = m - 1
    factors = get_prime_factors(phi)
    for p in factors:
        if pow(a, phi // p, m) == 1:
            return False
    return True


def find_primitive_roots(m: int, limit: int = 5) -> List[int]:
    """Finds first few primitive roots modulo m (if m is prime)."""
    if not is_prime(m):
        return []
    roots = []
    for a in range(2, m):
        if is_primitive_root(a, m):
            roots.append(a)
            if len(roots) >= limit:
                break
    return roots


def carmichael_lambda(n: int) -> int:
    """Computes Carmichael lambda function for n = p * q where p, q are distinct primes."""
    factors = get_prime_factors(n)
    if len(factors) == 2 and factors[0] * factors[1] == n:
        p, q = factors[0], factors[1]
        return math.lcm(p - 1, q - 1)
    return euler_totient(n)


# ==========================================
# 1. VALIDACION CONGRUENCIAL MIXTO (GCLM)
# ==========================================
def validate_gclm(X0: int, a: int, c: int, m: int) -> Dict[str, Any]:
    """
    Validates GCLM parameters and checks Hull-Dobell Theorem:
    1. gcd(c, m) == 1
    2. Every prime factor of m divides (a - 1)
    3. If 4 divides m, then 4 divides (a - 1)
    """
    errors = []
    warnings = []
    
    if m <= 0:
        errors.append("El modulo 'm' debe ser un entero positivo mayor que 0.")
    if X0 < 0 or (m > 0 and X0 >= m):
        errors.append("La semilla 'X0' debe cumplir 0 <= X0 < m.")
    if a <= 1 or (m > 0 and a >= m):
        errors.append("El multiplicador 'a' debe cumplir 1 < a < m.")
    if c <= 0 or (m > 0 and c >= m):
        errors.append("El incremento 'c' debe cumplir 1 <= c < m.")
        
    if errors:
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "hull_dobell": {"passed": False, "c1": False, "c2": False, "c3": False, "details": []},
            "full_period": False,
            "max_period": 0
        }

    # Hull-Dobell conditions
    # Condicion 1: gcd(c, m) = 1
    gcd_c_m = gcd(c, m)
    c1 = (gcd_c_m == 1)
    c1_msg = f"mcd(c, m) = mcd({c}, {m}) = {gcd_c_m} {'(Coprimos)' if c1 else '(NO son coprimos)'}"

    # Condicion 2: Todo factor primo de m divide a (a - 1)
    a_minus_1 = a - 1
    prime_factors_m = get_prime_factors(m)
    failing_factors = [p for p in prime_factors_m if a_minus_1 % p != 0]
    c2 = (len(failing_factors) == 0)
    c2_msg = f"Factores primos de m={m}: {prime_factors_m}. (a-1)={a_minus_1} " + (
        "es divisible por todos" if c2 else f"NO es divisible por {failing_factors}"
    )

    # Condicion 3: Si 4 divide a m, entonces 4 divide a (a - 1)
    m_div_4 = (m % 4 == 0)
    a_div_4 = (a_minus_1 % 4 == 0)
    if m_div_4:
        c3 = a_div_4
        c3_msg = f"4 divide a m ({m}). (a-1)={a_minus_1} " + ("es multiplo de 4" if c3 else "NO es multiplo de 4")
    else:
        c3 = True
        c3_msg = f"4 no divide a m ({m}), por lo que esta condicion se cumple trivialmente"

    hull_dobell_passed = c1 and c2 and c3

    if not hull_dobell_passed:
        warnings.append("No cumple el Teorema de Hull-Dobell: El periodo generado sera MENOR a m (periodo incompleto).")

    return {
        "valid": True,
        "errors": errors,
        "warnings": warnings,
        "hull_dobell": {
            "passed": hull_dobell_passed,
            "c1": c1,
            "c1_msg": c1_msg,
            "c2": c2,
            "c2_msg": c2_msg,
            "c3": c3,
            "c3_msg": c3_msg,
            "prime_factors": prime_factors_m
        },
        "full_period": hull_dobell_passed,
        "max_period": m if hull_dobell_passed else "< m (reducido)"
    }


# ==========================================
# 2. VALIDACION CONGRUENCIAL MULTIPLICATIVO (GCM)
# ==========================================
def validate_gcm(X0: int, a: int, m: int) -> Dict[str, Any]:
    """
    Validates GCM parameters and checks maximal period rules:
    - Case m = 2^g (g >= 4): N = m / 4 = 2^(g-2) if X0 is odd and a = 3+8k or 5+8k
    - Case m is prime: N = m - 1 if a is a primitive root mod m and 0 < X0 < m
    """
    errors = []
    warnings = []

    if m <= 0:
        errors.append("El modulo 'm' debe ser un entero positivo mayor que 0.")
    if X0 <= 0 or (m > 0 and X0 >= m):
        errors.append("La semilla 'X0' debe cumplir 0 < X0 < m (no puede ser 0).")
    if a <= 1 or (m > 0 and a >= m):
        errors.append("El multiplicador 'a' debe cumplir 1 < a < m.")

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "case": "unknown",
            "maximal_period": False,
            "theoretical_period": 0,
            "details": {}
        }

    is_pow2, g = is_power_of_two(m)
    m_is_prime = is_prime(m)

    details = {}
    maximal_period = False
    theoretical_period = "Desconocido / Sub-optimo"

    if is_pow2:
        case = f"Potencia de 2 (m = 2^{g})"
        x0_odd = (X0 % 2 == 1)
        a_mod_8 = a % 8
        a_valid = (a_mod_8 == 3 or a_mod_8 == 5)
        
        details["is_power_of_two"] = True
        details["g"] = g
        details["x0_odd"] = x0_odd
        details["x0_msg"] = f"X0={X0} es {'impar' if x0_odd else 'par (debe ser impar para periodo maximal)'}"
        details["a_mod_8"] = a_mod_8
        details["a_msg"] = f"a mod 8 = {a_mod_8} {'(cumple 3 o 5 + 8k)' if a_valid else '(no cumple 3 o 5 + 8k)'}"
        
        if g >= 4:
            if x0_odd and a_valid:
                maximal_period = True
                max_n = 2 ** (g - 2)
                theoretical_period = f"N = m/4 = {max_n}"
            else:
                warnings.append(f"Para m=2^{g}, se requiere X0 impar y a = 3 o 5 (mod 8) para alcanzar el periodo maximal m/4.")
        else:
            warnings.append("Se recomienda un exponente g >= 4 para modulos de potencia de dos.")

    elif m_is_prime:
        case = f"Modulo Primo (m = {m})"
        is_prim_root = is_primitive_root(a, m)
        x0_valid = (1 <= X0 < m)

        details["is_prime"] = True
        details["is_primitive_root"] = is_prim_root
        details["a_msg"] = f"a={a} {'es raiz primitiva mod ' + str(m) if is_prim_root else 'NO es raiz primitiva mod ' + str(m)}"
        details["x0_msg"] = f"X0={X0} esta en {{1, ..., m-1}}" if x0_valid else "X0 fuera de rango"

        if is_prim_root and x0_valid:
            maximal_period = True
            theoretical_period = f"N = m - 1 = {m - 1}"
        else:
            warnings.append(f"Para m={m} primo, 'a' debe ser raiz primitiva para alcanzar el periodo maximal de {m-1}.")
    else:
        case = "Modulo Compuesto General"
        warnings.append("El modulo m no es ni primo ni potencia de 2. El periodo sera mas corto.")

    return {
        "valid": True,
        "errors": errors,
        "warnings": warnings,
        "case": case,
        "is_power_of_two": is_pow2,
        "is_prime": m_is_prime,
        "maximal_period": maximal_period,
        "theoretical_period": theoretical_period,
        "details": details
    }


# ==========================================
# 3. VALIDACION CUADRADOS MEDIOS
# ==========================================
def validate_cuadrados_medios(X0: int, D: int) -> Dict[str, Any]:
    """
    Validates Middle Square parameters and checks heuristic recommendations:
    - D must be even integer (typically 4, 6, 8)
    - X0 must have exactly D digits (10^(D-1) <= X0 < 10^D)
    """
    errors = []
    warnings = []

    if D <= 0 or D % 2 != 0:
        errors.append("La cantidad de digitos 'D' debe ser un entero par positivo (ej. 4, 6, 8).")
    
    if D > 0:
        min_x0 = 10 ** (D - 1)
        max_x0 = (10 ** D) - 1
        if X0 < min_x0 or X0 > max_x0:
            errors.append(f"La semilla 'X0' debe tener exactamente D={D} digitos (entre {min_x0} y {max_x0}).")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "heuristics": {}}

    x0_str = str(X0)
    heuristics = {}

    ends_bad = x0_str.endswith("00") or x0_str.endswith("25") or x0_str.endswith("50") or x0_str.endswith("0")
    if ends_bad:
        warnings.append(f"La semilla termina en '{x0_str[-2:]}'. Se desaconseja ya que acelera el colapso a ceros.")
    heuristics["trailing_zeros_or_cycles"] = not ends_bad

    has_zero_chain = "00" in x0_str
    if has_zero_chain:
        warnings.append("La semilla contiene ceros consecutivos, lo que propaga ceros al elevar al cuadrado.")
    heuristics["no_internal_zero_chain"] = not has_zero_chain

    if D == 4 and X0 == 3792:
        warnings.append("X0 = 3792 es un punto fijo clasico de ciclo 1 (3792^2 = 14379264 -> 3792).")

    return {
        "valid": True,
        "errors": errors,
        "warnings": warnings,
        "heuristics": heuristics,
        "note": "El metodo de Cuadrados Medios no tiene estructura algebraica de grupo."
    }


# ==========================================
# 4. VALIDACION PRODUCTOS MEDIOS
# ==========================================
def validate_productos_medios(X0: int, X1: int, D: int) -> Dict[str, Any]:
    """
    Validates Middle Product parameters:
    - D must be even integer (4, 6, 8)
    - X0 and X1 must have exactly D digits
    - X0 != X1
    """
    errors = []
    warnings = []

    if D <= 0 or D % 2 != 0:
        errors.append("La cantidad de digitos 'D' debe ser un entero par positivo (ej. 4, 6, 8).")

    if D > 0:
        min_val = 10 ** (D - 1)
        max_val = (10 ** D) - 1
        if X0 < min_val or X0 > max_val:
            errors.append(f"La primera semilla 'X0' debe tener exactamente D={D} digitos (entre {min_val} y {max_val}).")
        if X1 < min_val or X1 > max_val:
            errors.append(f"La segunda semilla 'X1' debe tener exactamente D={D} digitos (entre {min_val} y {max_val}).")

    if X0 == X1:
        warnings.append("Las semillas X0 y X1 son identicas; se comportara como Cuadrados Medios en la primera iteracion.")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "heuristics": {}}

    x0_str = str(X0)
    x1_str = str(X1)
    heuristics = {}

    if x0_str.endswith("0") or x1_str.endswith("0"):
        warnings.append("Una o ambas semillas terminan en cero. Multiplicar por cero arrastra ceros a los digitos centrales.")
        heuristics["no_trailing_zeros"] = False
    else:
        heuristics["no_trailing_zeros"] = True

    seeds_coprime = (gcd(X0, X1) == 1)
    heuristics["coprime_seeds"] = seeds_coprime
    if not seeds_coprime:
        warnings.append(f"mcd(X0, X1) = {gcd(X0, X1)} (no son coprimos). Se recomienda que sean coprimas para mayor dispersion.")

    return {
        "valid": True,
        "errors": errors,
        "warnings": warnings,
        "heuristics": heuristics,
        "note": "El metodo de Productos Medios mitiga el colapso temprano pero carece de periodo completo garantizado."
    }


# ==========================================
# 5. VALIDACION BLUM BLUM SHUB (BBS)
# ==========================================
def validate_bbs(p: int, q: int, s: int) -> Dict[str, Any]:
    """
    Validates BBS parameters:
    - p, q must be distinct primes with p = 3 mod 4, q = 3 mod 4
    - M = p * q
    - s must be coprime to M: gcd(s, M) == 1
    """
    errors = []
    warnings = []

    if p <= 1 or not is_prime(p):
        errors.append(f"'p'={p} debe ser un numero primo.")
    if q <= 1 or not is_prime(q):
        errors.append(f"'q'={q} debe ser un numero primo.")
    if p == q and p > 1:
        errors.append("'p' y 'q' deben ser primos distintos.")

    p_blum = (p % 4 == 3) if is_prime(p) else False
    q_blum = (q % 4 == 3) if is_prime(q) else False

    if is_prime(p) and not p_blum:
        errors.append(f"'p'={p} no cumple la condicion de Blum (p = 3 mod 4). p mod 4 = {p % 4}.")
    if is_prime(q) and not q_blum:
        errors.append(f"'q'={q} no cumple la condicion de Blum (q = 3 mod 4). q mod 4 = {q % 4}.")

    M = p * q if (p > 0 and q > 0) else 0

    if s <= 1:
        errors.append("La semilla 's' debe ser un entero mayor que 1.")
    elif M > 0:
        gcd_s_M = gcd(s, M)
        if gcd_s_M != 1:
            errors.append(f"La semilla 's'={s} NO es coprima con M={M} (mcd(s, M) = {gcd_s_M}).")

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "M": M,
            "details": {}
        }

    p_safe = is_prime((p - 1) // 2)
    q_safe = is_prime((q - 1) // 2)
    safe_primes = p_safe and q_safe

    lambda_M = carmichael_lambda(M)

    return {
        "valid": True,
        "errors": errors,
        "warnings": warnings,
        "M": M,
        "p_blum": p_blum,
        "q_blum": q_blum,
        "safe_primes": safe_primes,
        "carmichael_lambda": lambda_M,
        "details": {
            "p_msg": f"p={p} (Primo Blum: {p} = 3 mod 4)",
            "q_msg": f"q={q} (Primo Blum: {q} = 3 mod 4)",
            "M_msg": f"M = p x q = {p} x {q} = {M} (Entero de Blum)",
            "s_msg": f"mcd(s, M) = mcd({s}, {M}) = 1 (Coprimos)",
            "safe_primes_msg": f"Primos seguros: {'Si' if safe_primes else 'No'}"
        }
    }
