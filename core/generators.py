"""
Core Pseudo-Random Number Generation Algorithms
Implements:
1. Generador Congruencial Lineal Mixto (GCLM)
2. Generador Congruencial Multiplicativo (GCM / Lehmer)
3. Algoritmo de Cuadrados Medios (John von Neumann)
4. Algoritmo de Productos Medios (Middle-Product)
5. Generador Blum Blum Shub (BBS - CSPRNG)
"""

from typing import Dict, Any, List
from .validators import validate_gclm, validate_gcm, validate_cuadrados_medios, validate_productos_medios, validate_bbs
from .stats import calculate_stats


# =========================================================================
# 1. GENERADOR CONGRUENCIAL LINEAL MIXTO (GCLM)
# =========================================================================
def generate_gclm(X0: int, a: int, c: int, m: int, n: int = 50) -> Dict[str, Any]:
    validation = validate_gclm(X0, a, c, m)
    if not validation["valid"]:
        return {
            "success": False,
            "method": "congruencial_mixto",
            "method_name": "Congruencial Lineal Mixto",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "validation": validation,
            "steps": [],
            "numbers": [],
            "stats": {},
            "cycle": {}
        }

    steps = []
    numbers = []
    seen_states = {}
    current_x = X0
    cycle_info = {"has_cycle": False, "period": 0, "start_index": None}

    for i in range(1, n + 1):
        next_mult = a * current_x + c
        next_x = next_mult % m
        ri = next_x / m

        step_record = {
            "i": i,
            "Xi": current_x,
            "operation": f"({a} x {current_x} + {c}) = {next_mult}",
            "mod_op": f"{next_mult} mod {m}",
            "next_Xi": next_x,
            "Ri": round(ri, 6),
            "Ri_raw": ri,
            "is_cycle_point": False
        }

        if current_x in seen_states and not cycle_info["has_cycle"]:
            cycle_info["has_cycle"] = True
            cycle_info["start_index"] = seen_states[current_x]
            cycle_info["period"] = i - seen_states[current_x]
            step_record["is_cycle_point"] = True
            cycle_info["message"] = f"Ciclo detectado en iteracion {i}: el valor {current_x} ya aparecio en iteracion {seen_states[current_x]} (Periodo = {cycle_info['period']})."

        seen_states[current_x] = i
        steps.append(step_record)
        numbers.append(ri)
        current_x = next_x

    if not cycle_info["has_cycle"]:
        if validation["hull_dobell"]["passed"]:
            cycle_info["message"] = f"Periodo Completo Garantizado por Hull-Dobell (N = {m})."
        else:
            cycle_info["message"] = f"No se detecto ciclo dentro de las {n} iteraciones generadas."

    stats = calculate_stats(numbers)

    return {
        "success": True,
        "method": "congruencial_mixto",
        "method_name": "Congruencial Lineal Mixto",
        "params": {"X0": X0, "a": a, "c": c, "m": m, "n": n},
        "validation": validation,
        "warnings": validation["warnings"],
        "cycle": cycle_info,
        "steps": steps,
        "numbers": numbers,
        "stats": stats
    }


# =========================================================================
# 2. GENERADOR CONGRUENCIAL MULTIPLICATIVO (GCM / LEHMER)
# =========================================================================
def generate_gcm(X0: int, a: int, m: int, n: int = 50) -> Dict[str, Any]:
    validation = validate_gcm(X0, a, m)
    if not validation["valid"]:
        return {
            "success": False,
            "method": "congruencial_multiplicativo",
            "method_name": "Congruencial Multiplicativo",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "validation": validation,
            "steps": [],
            "numbers": [],
            "stats": {},
            "cycle": {}
        }

    steps = []
    numbers = []
    seen_states = {}
    current_x = X0
    divisor = m
    cycle_info = {"has_cycle": False, "period": 0, "start_index": None}

    for i in range(1, n + 1):
        next_mult = a * current_x
        next_x = next_mult % m
        ri = next_x / divisor

        step_record = {
            "i": i,
            "Xi": current_x,
            "operation": f"({a} x {current_x}) = {next_mult}",
            "mod_op": f"{next_mult} mod {m}",
            "next_Xi": next_x,
            "Ri": round(ri, 6),
            "Ri_raw": ri,
            "is_cycle_point": False
        }

        if current_x in seen_states and not cycle_info["has_cycle"]:
            cycle_info["has_cycle"] = True
            cycle_info["start_index"] = seen_states[current_x]
            cycle_info["period"] = i - seen_states[current_x]
            step_record["is_cycle_point"] = True
            cycle_info["message"] = f"Ciclo detectado en iteracion {i}: estado repetido desde iteracion {seen_states[current_x]} (Periodo = {cycle_info['period']})."

        seen_states[current_x] = i
        steps.append(step_record)
        numbers.append(ri)
        current_x = next_x

    if not cycle_info["has_cycle"]:
        cycle_info["message"] = f"Periodo maximal teorico: {validation['theoretical_period']}."

    stats = calculate_stats(numbers)

    return {
        "success": True,
        "method": "congruencial_multiplicativo",
        "method_name": "Congruencial Multiplicativo",
        "params": {"X0": X0, "a": a, "m": m, "n": n},
        "validation": validation,
        "warnings": validation["warnings"],
        "cycle": cycle_info,
        "steps": steps,
        "numbers": numbers,
        "stats": stats
    }


# =========================================================================
# 3. ALGORITMO DE CUADRADOS MEDIOS (JOHN VON NEUMANN)
# =========================================================================
def generate_cuadrados_medios(X0: int, D: int = 4, n: int = 30) -> Dict[str, Any]:
    validation = validate_cuadrados_medios(X0, D)
    if not validation["valid"]:
        return {
            "success": False,
            "method": "cuadrados_medios",
            "method_name": "Cuadrados Medios",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "validation": validation,
            "steps": [],
            "numbers": [],
            "stats": {},
            "cycle": {}
        }

    steps = []
    numbers = []
    seen_states = {}
    current_x = X0
    cycle_info = {"has_cycle": False, "collapsed_to_zero": False, "period": 0, "start_index": None}

    divisor = 10 ** D

    for i in range(1, n + 1):
        y_val = current_x ** 2
        y_str = str(y_val).zfill(2 * D)

        start_pos = (len(y_str) - D) // 2
        extracted_str = y_str[start_pos : start_pos + D]
        next_x = int(extracted_str)
        ri = next_x / divisor

        status_msg = "Normal"
        if next_x == 0:
            status_msg = "Colapso a 0000"
            if not cycle_info["collapsed_to_zero"]:
                cycle_info["collapsed_to_zero"] = True
                cycle_info["collapse_index"] = i
        elif next_x == current_x:
            status_msg = "Punto Fijo"

        step_record = {
            "i": i,
            "Xi": current_x,
            "Yi": y_val,
            "Yi_padded": y_str,
            "extraction_indices": f"[{start_pos}:{start_pos+D}]",
            "extracted_digits": extracted_str,
            "next_Xi": next_x,
            "Ri": round(ri, 6),
            "Ri_raw": ri,
            "status": status_msg,
            "is_cycle_point": False
        }

        if current_x in seen_states and not cycle_info["has_cycle"]:
            cycle_info["has_cycle"] = True
            cycle_info["start_index"] = seen_states[current_x]
            cycle_info["period"] = i - seen_states[current_x]
            step_record["is_cycle_point"] = True
            cycle_info["message"] = f"Bucle detectado en iteracion {i}: valor {current_x} ya ocurrio en iteracion {seen_states[current_x]} (Periodo {cycle_info['period']})."

        seen_states[current_x] = i
        steps.append(step_record)
        numbers.append(ri)
        current_x = next_x

    if not cycle_info["has_cycle"]:
        if cycle_info["collapsed_to_zero"]:
            cycle_info["message"] = f"Secuencia colapso a cero en la iteracion {cycle_info.get('collapse_index')}."
        else:
            cycle_info["message"] = f"Secuencia completada sin bucles en {n} iteraciones."

    stats = calculate_stats(numbers)

    return {
        "success": True,
        "method": "cuadrados_medios",
        "method_name": "Cuadrados Medios",
        "params": {"X0": X0, "D": D, "n": n},
        "validation": validation,
        "warnings": validation["warnings"],
        "cycle": cycle_info,
        "steps": steps,
        "numbers": numbers,
        "stats": stats
    }


# =========================================================================
# 4. ALGORITMO DE PRODUCTOS MEDIOS (MIDDLE-PRODUCT)
# =========================================================================
def generate_productos_medios(X0: int, X1: int, D: int = 4, n: int = 30) -> Dict[str, Any]:
    validation = validate_productos_medios(X0, X1, D)
    if not validation["valid"]:
        return {
            "success": False,
            "method": "productos_medios",
            "method_name": "Productos Medios",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "validation": validation,
            "steps": [],
            "numbers": [],
            "stats": {},
            "cycle": {}
        }

    steps = []
    numbers = []
    seen_pairs = {}
    
    prev_x = X0
    current_x = X1
    divisor = 10 ** D
    cycle_info = {"has_cycle": False, "collapsed_to_zero": False, "period": 0, "start_index": None}

    for i in range(1, n + 1):
        y_val = prev_x * current_x
        y_str = str(y_val).zfill(2 * D)

        start_pos = (len(y_str) - D) // 2
        extracted_str = y_str[start_pos : start_pos + D]
        next_x = int(extracted_str)
        ri = next_x / divisor

        status_msg = "Normal"
        if next_x == 0:
            status_msg = "Colapso a 0000"
            if not cycle_info["collapsed_to_zero"]:
                cycle_info["collapsed_to_zero"] = True
                cycle_info["collapse_index"] = i

        step_record = {
            "i": i,
            "Xi_minus_1": prev_x,
            "Xi": current_x,
            "Yi": y_val,
            "Yi_padded": y_str,
            "extraction_indices": f"[{start_pos}:{start_pos+D}]",
            "extracted_digits": extracted_str,
            "next_Xi": next_x,
            "Ri": round(ri, 6),
            "Ri_raw": ri,
            "status": status_msg,
            "is_cycle_point": False
        }

        state_key = (prev_x, current_x)
        if state_key in seen_pairs and not cycle_info["has_cycle"]:
            cycle_info["has_cycle"] = True
            cycle_info["start_index"] = seen_pairs[state_key]
            cycle_info["period"] = i - seen_pairs[state_key]
            step_record["is_cycle_point"] = True
            cycle_info["message"] = f"Ciclo en iteracion {i}: par repetido desde iteracion {seen_pairs[state_key]} (Periodo = {cycle_info['period']})."

        seen_pairs[state_key] = i
        steps.append(step_record)
        numbers.append(ri)

        prev_x = current_x
        current_x = next_x

    if not cycle_info["has_cycle"]:
        if cycle_info["collapsed_to_zero"]:
            cycle_info["message"] = f"Secuencia colapso a cero en la iteracion {cycle_info.get('collapse_index')}."
        else:
            cycle_info["message"] = f"Secuencia completada sin bucles en {n} iteraciones."

    stats = calculate_stats(numbers)

    return {
        "success": True,
        "method": "productos_medios",
        "method_name": "Productos Medios",
        "params": {"X0": X0, "X1": X1, "D": D, "n": n},
        "validation": validation,
        "warnings": validation["warnings"],
        "cycle": cycle_info,
        "steps": steps,
        "numbers": numbers,
        "stats": stats
    }


# =========================================================================
# 5. GENERADOR BLUM BLUM SHUB (BBS - CSPRNG)
# =========================================================================
def generate_bbs(p: int, q: int, s: int, n: int = 50) -> Dict[str, Any]:
    validation = validate_bbs(p, q, s)
    if not validation["valid"]:
        return {
            "success": False,
            "method": "blum_blum_shub",
            "method_name": "Blum Blum Shub (BBS)",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "validation": validation,
            "steps": [],
            "numbers": [],
            "bits": "",
            "stats": {},
            "cycle": {}
        }

    M = p * q
    X0 = (s * s) % M

    steps = []
    numbers = []
    bits_list = []
    seen_states = {}
    current_x = X0
    cycle_info = {"has_cycle": False, "period": 0, "start_index": None}

    for i in range(0, n):
        ri = current_x / M
        bit = current_x % 2
        x_sq = current_x ** 2
        next_x = x_sq % M

        step_record = {
            "i": i,
            "Xi": current_x,
            "Xi_sq": x_sq,
            "mod_op": f"{x_sq} mod {M}",
            "next_Xi": next_x,
            "bit": bit,
            "Ri": round(ri, 6),
            "Ri_raw": ri,
            "is_cycle_point": False
        }

        if current_x in seen_states and not cycle_info["has_cycle"]:
            cycle_info["has_cycle"] = True
            cycle_info["start_index"] = seen_states[current_x]
            cycle_info["period"] = i - seen_states[current_x]
            step_record["is_cycle_point"] = True
            cycle_info["message"] = f"Ciclo de residuos cuadráticos en iteración i={i}: valor repetido desde i={seen_states[current_x]} (Periodo = {cycle_info['period']})."

        seen_states[current_x] = i
        steps.append(step_record)
        numbers.append(ri)
        bits_list.append(str(bit))
        current_x = next_x

    bitstream = "".join(bits_list)
    stats = calculate_stats(numbers)

    zeros_count = bitstream.count("0")
    ones_count = bitstream.count("1")
    stats["bitstream"] = bitstream
    stats["zeros_count"] = zeros_count
    stats["ones_count"] = ones_count
    stats["bit_balance"] = f"{ones_count} unos ({ones_count/len(bitstream)*100:.1f}%), {zeros_count} ceros ({zeros_count/len(bitstream)*100:.1f}%)"

    if not cycle_info["has_cycle"]:
        cycle_info["message"] = f"Secuencia generada sobre Z*_{M}. Sin ciclos en {n} iteraciones."

    return {
        "success": True,
        "method": "blum_blum_shub",
        "method_name": "Blum Blum Shub (BBS)",
        "params": {"p": p, "q": q, "s": s, "M": M, "X0": X0, "n": n},
        "validation": validation,
        "warnings": validation["warnings"],
        "cycle": cycle_info,
        "steps": steps,
        "numbers": numbers,
        "bitstream": bitstream,
        "stats": stats
    }
