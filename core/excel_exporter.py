"""
Excel Exporter for PRNG Sequences
Generates a professionally styled .xlsx workbook using openpyxl:
- Sheet 1: Metadata, Variables, Diagnóstico de Teoremas y Tabla Completa Paso a Paso
  con los valores numéricos calculados de la secuencia pseudoaleatoria.
- Sheet 2: Pares de Independencia Lag-1 (R_i vs R_{i+1}) y Gráfico de Dispersión Nativo.
- Sheets 3-9: Una hoja por cada una de las 7 Pruebas Estadísticas de Aleatoriedad
  (Promedio, Frecuencia, Distancia, Series, Kolmogorov-Smirnov, Poker y Corridas
  Arriba/Abajo del Promedio), con los datos, el paso a paso y las fórmulas
  NATIVAS de Excel (no valores fijos) para que el usuario pueda editar el
  nivel de significancia (y, en Distancia, el subrango de interés) y ver el
  resultado recalcularse en vivo.
- Hojas V0-V5: Validación de las Conversiones Estadísticas (Uniforme, Normal, Erlang,
  Poisson y Binomial): conversión de cada Rᵢ, conteo "menor que / mayor que / entre a y b"
  con CONTAR.SI.CONJUNTO y comparación contra la probabilidad teórica (fórmulas nativas).
- Paleta moderna: Verde Esmeralda (#10B981) y Morado (#7C3AED / #4C1D95).
"""

import io
import math
from typing import Dict, Any, Optional, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import ScatterChart, Reference, Series


COLOR_PURPLE = "7C3AED"
COLOR_PURPLE_DARK = "4C1D95"
COLOR_PURPLE_LIGHT = "F3E8FF"
COLOR_GREEN = "10B981"
COLOR_GREEN_DARK = "047857"
COLOR_GREEN_LIGHT = "ECFDF5"
COLOR_AMBER_LIGHT = "FFFBEB"
COLOR_ZEBRA = "F9FAFB"
COLOR_WHITE = "FFFFFF"
COLOR_TEXT = "111827"
COLOR_BORDER = "D1D5DB"

SHEET1_TITLE = "Secuencia y Calculos"
SHEET2_TITLE = "Analisis de Independencia"

# Metadatos de las 7 Pruebas Estadisticas (nombre corto de hoja + titulo + objetivo)
TEST_SHEET_META = {
    "promedio":       ("T1 Promedio",     "PRUEBA DE PROMEDIO (MEDIA ARITMÉTICA)",
                        "Objetivo: Validar si el promedio muestral de los n valores continuos en [0,1) converge al valor esperado teórico μ = 0.5, mediante el estadístico Z0 basado en el Teorema del Límite Central."),
    "frecuencia":      ("T2 Frecuencia",  "PRUEBA DE FRECUENCIA (UNIFORMIDAD POR SUBINTERVALOS)",
                        "Objetivo: Comprobar que los valores se distribuyen de forma homogénea en k subintervalos de igual longitud dentro de [0,1), mediante una prueba Chi-Cuadrado de bondad de ajuste."),
    "distancia":       ("T3 Distancia",   "PRUEBA DE DISTANCIA (HUECOS / GAP TEST)",
                        "Objetivo: Evaluar la longitud de separación (huecos) entre apariciones sucesivas de valores que caen dentro de un subrango de interés [α, β) ⊂ [0,1)."),
    "series":          ("T4 Series",      "PRUEBA DE SERIES (PARES SOLAPADOS)",
                        "Objetivo: Verificar que los pares consecutivos de bits (derivados de Ri por umbral de mediana) sean independientes y equiprobables."),
    "kolmogorov_smirnov": ("T5 Kolmogorov-Smirnov", "PRUEBA DE KOLMOGOROV-SMIRNOV (K-S)",
                        "Objetivo: Evaluar la máxima desviación absoluta entre la función de distribución acumulada empírica Fn(x) y la teórica F(x) = x."),
    "poker":           ("T6 Poker",       "PRUEBA DE POKER (CLÁSICO DECIMAL, 5 DÍGITOS)",
                        "Objetivo: Analizar la frecuencia de combinaciones de dígitos en bloques de 5 dígitos, clasificados en 7 manos de póker, contra sus probabilidades teóricas."),
    "corridas_promedio": ("T7 Corridas Promedio", "PRUEBA DE CORRIDAS ARRIBA Y ABAJO DEL PROMEDIO",
                        "Objetivo: Evaluar la alternancia de los valores respecto al valor esperado teórico μ = 0.5 (variante estática de la prueba de la distancia), mediante el conteo y la longitud de las corridas (rachas) por encima o por debajo de la media."),
}


def create_thin_border():
    thin = Side(border_style="thin", color=COLOR_BORDER)
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def export_prng_to_excel(gen_result: Dict[str, Any], alpha: float = 0.05,
                        dist_config: Optional[Dict[str, Any]] = None) -> io.BytesIO:
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = SHEET1_TITLE
    ws1.views.sheetView[0].showGridLines = True

    ws2 = wb.create_sheet(title=SHEET2_TITLE)
    ws2.views.sheetView[0].showGridLines = True

    method = gen_result.get("method", "congruencial_mixto")
    method_name = gen_result.get("method_name", "Generador Pseudoaleatorio")
    params = gen_result.get("params", {})
    steps = gen_result.get("steps", [])
    stats = gen_result.get("stats", {})
    validation = gen_result.get("validation", {})
    cycle = gen_result.get("cycle", {})

    ri_col_letter, data_start_row = _build_sheet1(ws1, method, method_name, params, steps, validation, cycle)
    _build_sheet2(ws2, method_name, stats, steps)

    try:
        alpha = float(alpha)
    except (TypeError, ValueError):
        alpha = 0.05
    if not (0 < alpha < 1):
        alpha = 0.05

    n = len(steps)
    numbers = gen_result.get("numbers") or [s.get("Ri", 0.0) for s in steps]
    if n >= 10:
        _build_test_sheets(wb, SHEET1_TITLE, ri_col_letter, data_start_row, n, alpha, numbers)
        # Validacion de las conversiones estadisticas (V0 Resumen + V1..V5 una hoja por distribucion)
        from .excel_distributions import build_distribution_sheets
        build_distribution_sheets(wb, SHEET1_TITLE, ri_col_letter, data_start_row, n, alpha, dist_config)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _build_sheet1(ws, method: str, method_name: str, params: Dict[str, Any], steps: list, validation: Dict[str, Any], cycle: Dict[str, Any]) -> Tuple[str, int]:
    thin_border = create_thin_border()

    # 1. Main Title Banner
    ws.merge_cells("A1:G2")
    title_cell = ws["A1"]
    title_cell.value = f"SIMULACION DIGITAL — {method_name.upper()}"
    title_cell.font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color=COLOR_PURPLE, end_color=COLOR_PURPLE, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    # 2. Subtitle / Diagnosis
    ws.merge_cells("A3:G3")
    sub_cell = ws["A3"]
    period_info = cycle.get("message", "Secuencia calculada correctamente.")
    sub_cell.value = f"Diagnóstico de Periodo: {period_info}"
    sub_cell.font = Font(name="Arial", size=10, italic=True, color="FFFFFF")
    sub_cell.fill = PatternFill(start_color=COLOR_PURPLE_DARK, end_color=COLOR_PURPLE_DARK, fill_type="solid")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")

    # 3. Parameters Section Header
    ws.cell(row=5, column=1, value="PARÁMETROS Y VARIABLES DE ENTRADA").font = Font(name="Arial", size=11, bold=True, color=COLOR_PURPLE_DARK)

    param_headers = ["Variable", "Denominación", "Valor", "Descripción y Dominio Matemático"]
    for col_idx, h in enumerate(param_headers, 1):
        c = ws.cell(row=6, column=col_idx, value=h)
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color=COLOR_GREEN_DARK, end_color=COLOR_GREEN_DARK, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    param_rows = []
    if method in ["congruencial_mixto", "gclm"]:
        param_rows = [
            ("X0", "Semilla Inicial", params.get("X0"), "0 <= X0 < m"),
            ("a", "Multiplicador", params.get("a"), "1 < a < m (Hull-Dobell: todo primo divide a-1, 4 divide a-1)"),
            ("c", "Incremento / Aditivo", params.get("c"), "1 <= c < m (Hull-Dobell: mcd(c,m)=1)"),
            ("m", "Módulo", params.get("m"), f"m > X0, a, c. Factores primos: {validation.get('hull_dobell', {}).get('prime_factors')}"),
            ("n", "Cantidad a Generar", params.get("n"), "Total de números generados")
        ]
    elif method in ["congruencial_multiplicativo", "gcm"]:
        param_rows = [
            ("X0", "Semilla Inicial", params.get("X0"), "Impar, mcd(X0, m) = 1, X0 != 0"),
            ("a", "Multiplicador", params.get("a"), "1 < a < m (Raíz primitiva o 3/5 + 8k)"),
            ("m", "Módulo", params.get("m"), f"Tipo: {validation.get('case')}"),
            ("n", "Cantidad a Generar", params.get("n"), "Total de números generados")
        ]
    elif method in ["cuadrados_medios", "cm"]:
        param_rows = [
            ("D", "Cantidad de Dígitos", params.get("D"), "Entero par positivo (4, 6, 8)"),
            ("X0", "Semilla Inicial", params.get("X0"), "Exactamente D dígitos"),
            ("n", "Cantidad a Generar", params.get("n"), "Total de números generados")
        ]
    elif method in ["productos_medios", "pm"]:
        param_rows = [
            ("D", "Cantidad de Dígitos", params.get("D"), "Entero par positivo (4, 6, 8)"),
            ("X0", "Primera Semilla", params.get("X0"), "Exactamente D dígitos"),
            ("X1", "Segunda Semilla", params.get("X1"), "Exactamente D dígitos, X1 != X0"),
            ("n", "Cantidad a Generar", params.get("n"), "Total de números generados")
        ]
    elif method in ["blum_blum_shub", "bbs"]:
        param_rows = [
            ("p", "Primo Secreto 1", params.get("p"), "Primo de Blum: p = 3 (mod 4)"),
            ("q", "Primo Secreto 2", params.get("q"), "Primo de Blum: q = 3 (mod 4)"),
            ("M", "Entero de Blum", params.get("M", params.get("p", 1) * params.get("q", 1)), "M = p x q"),
            ("s", "Semilla Inicial", params.get("s"), "mcd(s, M) = 1"),
            ("n", "Cantidad de Bits / Numeros", params.get("n"), "Total de iteraciones generadas")
        ]

    cur_row = 7
    for row_data in param_rows:
        for c_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=cur_row, column=c_idx, value=val)
            cell.font = Font(name="Arial", size=10, bold=(c_idx == 1))
            cell.alignment = Alignment(horizontal="center" if c_idx in [1, 3] else "left", vertical="center")
            cell.border = thin_border
            cell.fill = PatternFill(start_color=COLOR_PURPLE_LIGHT if c_idx == 1 else COLOR_WHITE, fill_type="solid")
        cur_row += 1

    # 4. Table Header for Step-by-Step Calculations
    cur_row += 2
    ws.cell(row=cur_row, column=1, value="TABLA DE CALCULOS ITERATIVOS Y SECUENCIA GENERADA").font = Font(name="Arial", size=11, bold=True, color=COLOR_PURPLE_DARK)
    cur_row += 1

    headers = []
    ri_col_idx = 5
    if method in ["congruencial_mixto", "gclm"]:
        headers = ["i", "X_{i-1}", "Operación (a × X_{i-1} + c)", "X_i = (aX_{i-1}+c) mod m", "R_i = X_i / m"]
        ri_col_idx = 5
    elif method in ["congruencial_multiplicativo", "gcm"]:
        headers = ["i", "X_{i-1}", "Operación (a × X_{i-1})", "X_i = (aX_{i-1}) mod m", "R_i = X_i / m"]
        ri_col_idx = 5
    elif method in ["cuadrados_medios", "cm"]:
        headers = ["i", "X_{i-1}", "Y_{i-1} = (X_{i-1})²", "Y_{i-1} (Relleno 2D)", "Dígitos Centrales (X_i)", "R_i = X_i / 10^D", "Estado"]
        ri_col_idx = 6
    elif method in ["productos_medios", "pm"]:
        headers = ["i", "X_{i-2}", "X_{i-1}", "Y_{i-1} = X_{i-2} × X_{i-1}", "Y_{i-1} (Relleno 2D)", "Dígitos Centrales (X_i)", "R_i = X_i / 10^D"]
        ri_col_idx = 7
    elif method in ["blum_blum_shub", "bbs"]:
        headers = ["i", "X_{i-1}", "Y_{i-1} = (X_{i-1})²", "X_i = Y_{i-1} mod M", "Bit b_i (X_i mod 2)", "R_i = X_i / M"]
        ri_col_idx = 6

    header_row = cur_row
    for c_idx, h in enumerate(headers, 1):
        c = ws.cell(row=header_row, column=c_idx, value=h)
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color=COLOR_PURPLE, end_color=COLOR_PURPLE, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = thin_border

    cur_row += 1
    data_start_row = cur_row
    ri_col_letter = get_column_letter(ri_col_idx)

    for s in steps:
        i_val = s.get("i", 0)
        row_bg = COLOR_ZEBRA if (i_val % 2 == 0) else COLOR_WHITE
        fill_style = PatternFill(start_color=row_bg, fill_type="solid")

        if method in ["congruencial_mixto", "gclm"]:
            row_cells = [
                (i_val, "center", False, None),
                (s.get("Xi"), "right", True, None),
                (s.get("operation"), "center", False, None),
                (s.get("next_Xi"), "right", False, None),
                (float(s.get("Ri", 0.0)), "right", True, "0.000000"),
            ]
        elif method in ["congruencial_multiplicativo", "gcm"]:
            row_cells = [
                (i_val, "center", False, None),
                (s.get("Xi"), "right", True, None),
                (s.get("operation"), "center", False, None),
                (s.get("next_Xi"), "right", False, None),
                (float(s.get("Ri", 0.0)), "right", True, "0.000000"),
            ]
        elif method in ["cuadrados_medios", "cm"]:
            row_cells = [
                (i_val, "center", False, None),
                (s.get("Xi"), "right", True, None),
                (s.get("Yi"), "right", False, None),
                (str(s.get("Yi_padded", "")), "center", False, None),
                (str(s.get("extracted_digits", "")), "center", True, None),
                (float(s.get("Ri", 0.0)), "right", True, "0.000000"),
                (s.get("status", "Normal"), "center", False, None),
            ]
        elif method in ["productos_medios", "pm"]:
            row_cells = [
                (i_val, "center", False, None),
                (s.get("Xi_minus_1"), "right", False, None),
                (s.get("Xi"), "right", True, None),
                (s.get("Yi"), "right", False, None),
                (str(s.get("Yi_padded", "")), "center", False, None),
                (str(s.get("extracted_digits", "")), "center", True, None),
                (float(s.get("Ri", 0.0)), "right", True, "0.000000"),
            ]
        elif method in ["blum_blum_shub", "bbs"]:
            row_cells = [
                (i_val, "center", False, None),
                (s.get("Xi"), "right", True, None),
                (s.get("Xi_sq"), "right", False, None),
                (s.get("next_Xi"), "right", False, None),
                (s.get("bit"), "center", True, None),
                (float(s.get("Ri", 0.0)), "right", True, "0.000000"),
            ]
        else:
            row_cells = [(i_val, "center", False, None)]

        for c_idx, (val, align, is_bold, num_fmt) in enumerate(row_cells, 1):
            cell = ws.cell(row=cur_row, column=c_idx, value=val)
            cell.font = Font(name="Arial", size=10, bold=is_bold, color=COLOR_TEXT)
            cell.alignment = Alignment(horizontal=align, vertical="center")
            cell.border = thin_border
            cell.fill = fill_style
            if num_fmt:
                cell.number_format = num_fmt

        cur_row += 1

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    return ri_col_letter, data_start_row


def _build_sheet2(ws, method_name: str, stats: Dict[str, Any], steps: list):
    thin_border = create_thin_border()

    ws.merge_cells("A1:F2")
    title_cell = ws["A1"]
    title_cell.value = f"ANÁLISIS DE INDEPENDENCIA ESTOCÁSTICA (LAG-1) — {method_name.upper()}"
    title_cell.font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color=COLOR_PURPLE, end_color=COLOR_PURPLE, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    r_idx = 4
    ws.cell(row=r_idx, column=1, value="PARES DE RETARDO CONSECUTIVOS (R_i vs R_{i+1})").font = Font(name="Arial", size=11, bold=True, color=COLOR_PURPLE_DARK)
    r_idx += 1

    ws.cell(row=r_idx, column=1, value="R_i (Eje X)").font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    ws.cell(row=r_idx, column=1).fill = PatternFill(start_color=COLOR_GREEN_DARK, fill_type="solid")
    ws.cell(row=r_idx, column=2, value="R_{i+1} (Eje Y)").font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    ws.cell(row=r_idx, column=2).fill = PatternFill(start_color=COLOR_GREEN_DARK, fill_type="solid")

    r_idx += 1
    pair_start_row = r_idx

    pairs = stats.get("lag1_pairs", [])
    if not pairs and len(steps) > 1:
        pairs = [{"x": steps[i]["Ri"], "y": steps[i+1]["Ri"]} for i in range(len(steps)-1)]

    for p in pairs:
        c1 = ws.cell(row=r_idx, column=1, value=float(p.get("x", 0.0)))
        c2 = ws.cell(row=r_idx, column=2, value=float(p.get("y", 0.0)))
        c1.number_format = "0.000000"
        c2.number_format = "0.000000"
        c1.alignment = Alignment(horizontal="right", vertical="center")
        c2.alignment = Alignment(horizontal="right", vertical="center")
        c1.border = thin_border
        c2.border = thin_border
        r_idx += 1

    pair_end_row = r_idx - 1

    if len(pairs) > 1:
        try:
            chart = ScatterChart()
            chart.title = "Gráfico de Dispersión / Retardo (R_i vs R_{i+1})"
            chart.style = 13
            chart.x_axis.title = "R_i (Valor Actual)"
            chart.y_axis.title = "R_{i+1} (Valor Siguiente)"
            chart.width = 18
            chart.height = 12

            xvalues = Reference(ws, min_col=1, min_row=pair_start_row, max_row=pair_end_row)
            yvalues = Reference(ws, min_col=2, min_row=pair_start_row, max_row=pair_end_row)
            series = Series(yvalues, xvalues, title="Pares (R_i, R_{i+1})")
            series.marker.symbol = "circle"
            series.marker.size = 6
            series.marker.graphicalProperties.solidFill = COLOR_GREEN
            series.marker.graphicalProperties.line.solidFill = COLOR_PURPLE
            series.graphicalProperties.line.noFill = True

            chart.series.append(series)
            ws.add_chart(chart, "D5")
        except Exception:
            pass

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


# =========================================================================
# HELPERS COMPARTIDOS PARA LAS 7 HOJAS DE PRUEBAS ESTADISTICAS
# =========================================================================

def _title_banner(ws, text, span_cols=7):
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=span_cols)
    cell = ws.cell(row=1, column=1, value=text)
    cell.font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color=COLOR_PURPLE, end_color=COLOR_PURPLE, fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center")


def _objective_row(ws, row, text, span_cols=7):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span_cols)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(name="Arial", size=9.5, italic=True, color="FFFFFF")
    cell.fill = PatternFill(start_color=COLOR_PURPLE_DARK, end_color=COLOR_PURPLE_DARK, fill_type="solid")
    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 32


def _section_header(ws, row, text):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(name="Arial", size=10.5, bold=True, color=COLOR_PURPLE_DARK)


def _alpha_input_row(ws, row, alpha, thin_border, label="Nivel de Significancia (α):"):
    lbl = ws.cell(row=row, column=1, value=label)
    lbl.font = Font(name="Arial", size=10, bold=True)
    lbl.alignment = Alignment(horizontal="left", vertical="center")
    val = ws.cell(row=row, column=2, value=alpha)
    val.font = Font(name="Arial", size=11, bold=True, color=COLOR_GREEN_DARK)
    val.fill = PatternFill(start_color=COLOR_AMBER_LIGHT, fill_type="solid")
    val.number_format = "0.00%"
    val.alignment = Alignment(horizontal="center", vertical="center")
    val.border = thin_border
    note = ws.cell(row=row, column=3, value="← Editable: cambie el % de error y toda la hoja se recalcula")
    note.font = Font(name="Arial", size=9, italic=True, color=COLOR_TEXT)
    return f"$B${row}"


def _kv_row(ws, row, label, value, thin_border, num_fmt=None, highlight=False, note=None, bold_label=False):
    lbl = ws.cell(row=row, column=1, value=label)
    lbl.font = Font(name="Arial", size=10, bold=bold_label)
    lbl.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    val = ws.cell(row=row, column=2, value=value)
    val.font = Font(name="Arial", size=10.5, bold=highlight, color=COLOR_GREEN_DARK if highlight else COLOR_TEXT)
    val.fill = PatternFill(start_color=COLOR_GREEN_LIGHT if highlight else COLOR_WHITE, fill_type="solid")
    val.alignment = Alignment(horizontal="center", vertical="center")
    val.border = thin_border
    if num_fmt:
        val.number_format = num_fmt
    if note:
        n = ws.cell(row=row, column=3, value=note)
        n.font = Font(name="Arial", size=9, italic=True, color=COLOR_TEXT)
        n.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    return f"$B${row}"


def _decision_row(ws, row, stat_cell, crit_cell, thin_border, comparator="<=", label="DECISIÓN:", span_cols=(2, 5)):
    lbl = ws.cell(row=row, column=1, value=label)
    lbl.font = Font(name="Arial", size=11, bold=True)
    formula = f'=IF({stat_cell}{comparator}{crit_cell},"✓ SE ACEPTA H0  (secuencia consistente con aleatoriedad)","✗ SE RECHAZA H0  (NO consistente con aleatoriedad)")'
    ws.merge_cells(start_row=row, start_column=span_cols[0], end_row=row, end_column=span_cols[1])
    val = ws.cell(row=row, column=span_cols[0], value=formula)
    val.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    val.fill = PatternFill(start_color=COLOR_PURPLE, fill_type="solid")
    val.alignment = Alignment(horizontal="center", vertical="center")
    val.border = thin_border
    ws.row_dimensions[row].height = 20
    return row


def _table_header(ws, row, headers, thin_border, start_col=1):
    for i, h in enumerate(headers):
        c = ws.cell(row=row, column=start_col + i, value=h)
        c.font = Font(name="Arial", size=9.5, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color=COLOR_GREEN_DARK, end_color=COLOR_GREEN_DARK, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = thin_border


def _autosize(ws, min_width=10):
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max((len(str(cell.value)) if cell.value is not None else 0) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 3, min_width)


def _collapse_entries(entries, min_expected=5.0):
    """
    Fusiona clases adyacentes (en el orden dado) hasta que todas las frecuencias
    esperadas sean >= min_expected. Cada entrada es un dict con: label, codes
    (lista de códigos/valores que identifican esa clase en los datos), observed,
    expected, prob. 'codes' se usa luego para construir la formula Oi como suma
    de COUNTIF de cada código original agrupado.
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
            "codes": list(a["codes"]) + list(b["codes"]),
            "observed": a["observed"] + b["observed"],
            "expected": a["expected"] + b["expected"],
            "prob": a["prob"] + b["prob"],
        }
        lo, hi = min(idx, j), max(idx, j)
        entries = entries[:lo] + [merged] + entries[hi + 1:]
    return entries


def _poker_hand_py(x):
    v = max(0, min(99999, int(x * 100000)))
    s = f"{v:05d}"
    from collections import Counter
    counts = tuple(sorted(Counter(s).values(), reverse=True))
    lookup = {(1, 1, 1, 1, 1): "TD", (2, 1, 1, 1): "1P", (2, 2, 1): "2P",
              (3, 1, 1): "T", (3, 2): "F", (4, 1): "P4", (5,): "Q"}
    return lookup.get(counts, "TD")


def _plan_poker_groups(numbers, min_expected=5.0):
    """Decide (a partir de los datos REALES generados) como agrupar las 7 clases
    de Poker para que todas las Eᵢ >= 5, exactamente igual que hace la app web
    (core/random_tests.py) para que la hoja de Excel y la prueba mostrada en
    pantalla usen la misma cantidad de clases / grados de libertad."""
    from collections import Counter
    n = len(numbers)
    hands = [_poker_hand_py(x) for x in numbers]
    counts = Counter(hands)
    entries = [
        {"label": f"{code} ({label})", "codes": [code], "observed": counts.get(code, 0),
         "expected": n * p, "prob": p}
        for code, label, p in _POKER_CLASSES
    ]
    return _collapse_entries(entries, min_expected)


def _plan_gap_groups(numbers, lo=0.0, hi=0.5, h_cap=30, min_expected=5.0):
    """Decide (a partir de los datos REALES generados, con el intervalo por
    defecto) cuantas clases de huecos (0..h-1, mas la cola i>=h) hacen falta
    para que todas las Eᵢ >= 5. Devuelve (entries, h_used, N) o None si no hay
    huecos suficientes para evaluar la prueba."""
    p = hi - lo
    if not (0 < p < 1):
        return None
    hits_idx = [i for i, x in enumerate(numbers) if lo <= x < hi]
    gaps = [b - a - 1 for a, b in zip(hits_idx, hits_idx[1:])]
    N = len(gaps)
    if N < 5:
        return None

    h_used = min(max(gaps) + 1, h_cap)
    entries = []
    for i in range(h_used):
        prob_i = p * ((1 - p) ** i)
        obs_i = sum(1 for g in gaps if g == i)
        entries.append({"label": f"i={i}", "codes": [("i", i)], "observed": obs_i,
                         "expected": N * prob_i, "prob": prob_i})
    prob_tail = (1 - p) ** h_used
    obs_tail = sum(1 for g in gaps if g >= h_used)
    entries.append({"label": f"i≥{h_used}", "codes": [("tail", h_used)], "observed": obs_tail,
                     "expected": N * prob_tail, "prob": prob_tail})

    entries = _collapse_entries(entries, min_expected)
    if len(entries) < 2:
        return None
    return entries, h_used, N


def _run_lengths_py(binary_seq):
    """Longitud de cada corrida (racha) de simbolos identicos consecutivos.
    Misma logica que random_tests._run_lengths, replicada aqui para no
    depender de ese modulo al construir las hojas de Excel."""
    lengths = []
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


def _plan_run_length_groups(lengths, total_expected, fe_func, cap=30, min_expected=5.0):
    """Decide (a partir de las corridas REALES observadas) cuantas clases
    individuales de longitud i=1..h hacen falta antes de agrupar la cola
    (i>=h+1) en una sola clase -- exactamente igual que random_tests._build_run_classes,
    para que la hoja de Excel y la prueba mostrada en pantalla usen la misma
    cantidad de clases / grados de libertad. Devuelve (entries, h_used) o None."""
    if not lengths or len(lengths) < 5:
        return None
    max_len = max(lengths)
    raw_entries = []
    cum_fe = 0.0
    i = 1
    while i <= min(max_len, cap):
        fe = fe_func(i)
        if fe <= 0 or fe < min_expected:
            break
        obs = sum(1 for l in lengths if l == i)
        raw_entries.append({"label": f"i={i}", "codes": [("i", i)], "observed": obs, "expected": fe, "prob": 0.0})
        cum_fe += fe
        i += 1
    h_used = i - 1
    obs_tail = sum(1 for l in lengths if l > h_used)
    fe_tail = total_expected - cum_fe
    if fe_tail <= 0:
        fe_tail = 1e-9
    raw_entries.append({"label": f"i≥{h_used + 1}", "codes": [("tail", h_used + 1)], "observed": obs_tail, "expected": fe_tail, "prob": 0.0})
    entries = _collapse_entries(raw_entries, min_expected)
    if len(entries) < 2:
        return None
    return entries, h_used


def _new_test_sheet(wb, sheet_name, title, objective, alpha):
    ws = wb.create_sheet(title=sheet_name)
    ws.views.sheetView[0].showGridLines = True
    thin_border = create_thin_border()
    _title_banner(ws, title)
    _objective_row(ws, 3, objective)
    row = 5
    _section_header(ws, row, "PARÁMETROS DE LA PRUEBA")
    row += 1
    alpha_cell = _alpha_input_row(ws, row, alpha, thin_border)
    row += 2
    return ws, thin_border, alpha_cell, row


def _build_test_sheets(wb, ws1_title, ri_col_letter, data_start_row, n, alpha, numbers):
    ri_range = f"'{ws1_title}'!${ri_col_letter}${data_start_row}:${ri_col_letter}${data_start_row + n - 1}"

    _sheet_promedio(wb, ri_range, alpha)
    _sheet_frecuencia(wb, ri_range, n, alpha)
    _sheet_distancia(wb, ws1_title, ri_col_letter, data_start_row, n, alpha, numbers)
    _sheet_series(wb, ws1_title, ri_col_letter, data_start_row, n, alpha)
    _sheet_ks(wb, ri_range, n, alpha)
    _sheet_poker(wb, ws1_title, ri_col_letter, data_start_row, n, alpha, numbers)
    _sheet_corridas_promedio(wb, ws1_title, ri_col_letter, data_start_row, n, alpha, numbers)


# =========================================================================
# T1. PRUEBA DE PROMEDIO
# =========================================================================
def _sheet_promedio(wb, ri_range, alpha):
    name, title, objective = TEST_SHEET_META["promedio"]
    ws, tb, alpha_cell, row = _new_test_sheet(wb, name, title, objective, alpha)

    _section_header(ws, row, "CÁLCULOS (Fórmulas nativas de Excel)")
    row += 1
    n_cell = _kv_row(ws, row, "n  (cantidad de valores)", f"=COUNT({ri_range})", tb, num_fmt="0")
    row += 1
    mean_cell = _kv_row(ws, row, "x̄  (media muestral)  =  (1/n)·Σxᵢ", f"=AVERAGE({ri_range})", tb, num_fmt="0.000000")
    row += 1
    z0_cell = _kv_row(ws, row, "Z₀  =  (x̄ − 0.5)·√(12n)", f"=({mean_cell}-0.5)*SQRT(12*{n_cell})", tb, num_fmt="0.0000", highlight=True)
    row += 1
    absz0_cell = _kv_row(ws, row, "|Z₀|", f"=ABS({z0_cell})", tb, num_fmt="0.0000")
    row += 1
    zcrit_cell = _kv_row(ws, row, "Z_(α/2)  =  NORM.S.INV(1 − α/2)", f"=_xlfn.NORM.S.INV(1-{alpha_cell}/2)", tb, num_fmt="0.0000", highlight=True)
    row += 2

    _section_header(ws, row, "CRITERIO DE DECISIÓN:  Se acepta H0 si |Z₀| ≤ Z_(α/2)")
    row += 1
    _decision_row(ws, row, absz0_cell, zcrit_cell, tb)

    _autosize(ws)
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["C"].width = 42


# =========================================================================
# T2. PRUEBA DE FRECUENCIA (Chi-Cuadrado por Subintervalos)
# =========================================================================
def _sheet_frecuencia(wb, ri_range, n, alpha):
    name, title, objective = TEST_SHEET_META["frecuencia"]
    ws, tb, alpha_cell, row = _new_test_sheet(wb, name, title, objective, alpha)

    k = max(5, min(20, n // 5))

    n_cell = _kv_row(ws, row, "n  (cantidad de valores)", f"=COUNT({ri_range})", tb, num_fmt="0")
    row += 1
    k_cell = _kv_row(ws, row, "k  (número de subintervalos)  =  clamp(n/5, 5, 20)", f"=MAX(5,MIN(20,INT({n_cell}/5)))", tb, num_fmt="0")
    row += 1
    e_cell = _kv_row(ws, row, "Eᵢ  (frecuencia esperada)  =  n / k", f"={n_cell}/{k_cell}", tb, num_fmt="0.0000")
    row += 1
    warn_c = ws.cell(row=row, column=1, value=f'=IF({e_cell}<5,"⚠ Advertencia: Eᵢ < 5 (muestra pequeña). Aumente n para una prueba más potente.","")')
    warn_c.font = Font(name="Arial", size=9, italic=True, color="B45309")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 2

    _section_header(ws, row, f"TABLA DE FRECUENCIAS OBSERVADAS Y ESPERADAS (k = {k} subintervalos)")
    row += 1
    _table_header(ws, row, ["Clase", "Límite Inf.", "Límite Sup.", "Oᵢ (observado)", "Eᵢ (esperado)", "(Oᵢ−Eᵢ)²/Eᵢ"], tb)
    row += 1
    table_start = row
    for cls in range(1, k + 1):
        ws.cell(row=row, column=1, value=cls).border = tb
        ws.cell(row=row, column=1).alignment = Alignment(horizontal="center")
        lo_f = f"=({cls}-1)/{k_cell}"
        hi_f = f"={cls}/{k_cell}"
        lo_c = ws.cell(row=row, column=2, value=lo_f)
        hi_c = ws.cell(row=row, column=3, value=hi_f)
        for cc in (lo_c, hi_c):
            cc.number_format = "0.0000"
            cc.border = tb
            cc.alignment = Alignment(horizontal="center")
        oi_f = f"=COUNTIFS({ri_range},\">=\"&B{row},{ri_range},\"<\"&C{row})"
        oi_c = ws.cell(row=row, column=4, value=oi_f)
        oi_c.border = tb
        oi_c.alignment = Alignment(horizontal="center")
        ei_c = ws.cell(row=row, column=5, value=f"={e_cell}")
        ei_c.number_format = "0.0000"
        ei_c.border = tb
        ei_c.alignment = Alignment(horizontal="center")
        contrib_c = ws.cell(row=row, column=6, value=f"=(D{row}-E{row})^2/E{row}")
        contrib_c.number_format = "0.0000"
        contrib_c.border = tb
        contrib_c.alignment = Alignment(horizontal="center")
        row += 1
    table_end = row - 1

    row += 1
    chi0_cell = _kv_row(ws, row, "χ₀²  =  Σ (Oᵢ−Eᵢ)²/Eᵢ", f"=SUM(F{table_start}:F{table_end})", tb, num_fmt="0.0000", highlight=True)
    row += 1
    df_cell = _kv_row(ws, row, "ν  (grados de libertad)  =  k − 1", f"={k_cell}-1", tb, num_fmt="0")
    row += 1
    crit_cell = _kv_row(ws, row, "χ²_(α, ν)  =  CHISQ.INV.RT(α, ν)", f"=_xlfn.CHISQ.INV.RT({alpha_cell},{df_cell})", tb, num_fmt="0.0000", highlight=True)
    row += 2

    _section_header(ws, row, "CRITERIO DE DECISIÓN:  Se acepta H0 si χ₀² < χ²_(α, k−1)")
    row += 1
    _decision_row(ws, row, chi0_cell, crit_cell, tb, comparator="<")

    _autosize(ws)
    ws.column_dimensions["A"].width = 46


# =========================================================================
# T3. PRUEBA DE DISTANCIA (Huecos / Gap Test)
# El numero de clases (h) se decide una sola vez, al exportar, a partir de los
# huecos REALES observados con el intervalo por defecto [0, 0.5) -- agrupando
# clases adyacentes hasta lograr Eᵢ >= 5 (mismo criterio que la app web). Si el
# usuario cambia α/β o los datos de la Hoja 1 despues de abrir el archivo, el
# estadistico se recalcula en vivo, pero la cantidad de clases queda fija.
# =========================================================================
def _sheet_distancia(wb, ws1_title, ri_col_letter, data_start_row, n, alpha, numbers):
    name, title, objective = TEST_SHEET_META["distancia"]
    ws, tb, alpha_cell, row = _new_test_sheet(wb, name, title, objective, alpha)

    plan = _plan_gap_groups(numbers, lo=0.0, hi=0.5)
    if plan is None:
        warn = ws.cell(row=row, column=1, value="⚠ Datos insuficientes: con el intervalo por defecto [0, 0.5) no se observaron huecos suficientes (mínimo 5) para evaluar esta prueba. Aumente la cantidad de valores generados (n) y vuelva a exportar.")
        warn.font = Font(name="Arial", size=10.5, bold=True, color="B45309")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        _autosize(ws)
        return
    entries, h_used, _N_expected = plan

    lo_lbl = ws.cell(row=row, column=1, value="Límite inferior del intervalo de interés (α):")
    lo_lbl.font = Font(name="Arial", size=10, bold=True)
    lo_cell_ref = ws.cell(row=row, column=2, value=0.0)
    lo_cell_ref.fill = PatternFill(start_color=COLOR_AMBER_LIGHT, fill_type="solid")
    lo_cell_ref.number_format = "0.0000"
    lo_cell_ref.border = tb
    lo_cell_ref.alignment = Alignment(horizontal="center")
    lo_cell = f"$B${row}"
    row += 1

    hi_lbl = ws.cell(row=row, column=1, value="Límite superior del intervalo de interés (β):")
    hi_lbl.font = Font(name="Arial", size=10, bold=True)
    hi_cell_ref = ws.cell(row=row, column=2, value=0.5)
    hi_cell_ref.fill = PatternFill(start_color=COLOR_AMBER_LIGHT, fill_type="solid")
    hi_cell_ref.number_format = "0.0000"
    hi_cell_ref.border = tb
    hi_cell_ref.alignment = Alignment(horizontal="center")
    hi_cell = f"$B${row}"
    row += 1
    note = ws.cell(row=row, column=1, value="(editables — por defecto [0, 0.5), p = 0.5, siguiendo el ejemplo de referencia del enunciado)")
    note.font = Font(name="Arial", size=9, italic=True, color=COLOR_TEXT)
    row += 1

    p_cell = _kv_row(ws, row, "p = β − α", f"={hi_cell}-{lo_cell}", tb, num_fmt="0.0000")
    row += 1
    note2 = ws.cell(row=row, column=1, value=f"La cantidad de clases ({len(entries)}) se calculó al exportar, agrupando huecos hasta lograr Eᵢ ≥ 5 (criterio de Cochran) con el intervalo por defecto.")
    note2.font = Font(name="Arial", size=9, italic=True, color=COLOR_TEXT)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 2

    h = h_used
    df = len(entries) - 1
    _section_header(ws, row, f"MARCADO DE HUECOS SOBRE LA SECUENCIA (h = {h}, ν = {df})")
    row += 1
    _table_header(ws, row, ["i", "Rᵢ", "¿Cae en [α,β)?", "Fila del hueco (si aplica)", "Fila hueco anterior", "Longitud del hueco"], tb)
    row += 1
    helper_start = row

    for k in range(1, n + 1):
        src_row = data_start_row + k - 1
        c_rownum = ws.cell(row=row, column=1, value=k)
        c_rownum.border = tb
        c_rownum.alignment = Alignment(horizontal="center")

        c_ri = ws.cell(row=row, column=2, value=f"='{ws1_title}'!{ri_col_letter}{src_row}")
        c_ri.number_format = "0.000000"
        c_ri.border = tb
        c_ri.alignment = Alignment(horizontal="center")

        c_hit = ws.cell(row=row, column=3, value=f"=IF(AND(B{row}>={lo_cell},B{row}<{hi_cell}),1,0)")
        c_hit.border = tb
        c_hit.alignment = Alignment(horizontal="center")

        c_hitrow = ws.cell(row=row, column=4, value=f'=IF(C{row}=1,A{row},"")')
        c_hitrow.border = tb
        c_hitrow.alignment = Alignment(horizontal="center")

        if row == helper_start:
            prev_formula = '=""'
        else:
            prev_formula = f'=IFERROR(LOOKUP(2,1/($D${helper_start}:D{row-1}<>""),$D${helper_start}:D{row-1}),"")'
        c_prev = ws.cell(row=row, column=5, value=prev_formula)
        c_prev.border = tb
        c_prev.alignment = Alignment(horizontal="center")

        c_gap = ws.cell(row=row, column=6, value=f'=IF(AND(C{row}=1,E{row}<>""),A{row}-E{row}-1,"")')
        c_gap.border = tb
        c_gap.alignment = Alignment(horizontal="center")

        row += 1

    helper_end = row - 1
    gap_range = f"$F${helper_start}:$F${helper_end}"

    row += 1
    N_cell = _kv_row(ws, row, "N  (total de huecos completos observados)", f"=COUNT({gap_range})", tb, num_fmt="0")
    row += 2

    _section_header(ws, row, "TABLA DE CLASES DE HUECOS (clases agrupadas automáticamente donde Eᵢ < 5)")
    row += 1
    _table_header(ws, row, ["Clase", "Oᵢ (observado)", "P(i) teórica", "Eᵢ = N·P(i)", "(Oᵢ−Eᵢ)²/Eᵢ"], tb)
    row += 1
    class_start = row
    for entry in entries:
        ws.cell(row=row, column=1, value=entry["label"]).border = tb

        oi_terms = []
        pi_terms = []
        for kind, val in entry["codes"]:
            if kind == "i":
                oi_terms.append(f'COUNTIF({gap_range},{val})')
                pi_terms.append(f"{p_cell}*(1-{p_cell})^{val}")
            else:  # tail
                oi_terms.append(f'COUNTIF({gap_range},">="&{val})')
                pi_terms.append(f"(1-{p_cell})^{val}")

        oi_c = ws.cell(row=row, column=2, value="=" + "+".join(oi_terms))
        oi_c.border = tb
        oi_c.alignment = Alignment(horizontal="center")
        pi_c = ws.cell(row=row, column=3, value="=" + "+".join(pi_terms))
        pi_c.number_format = "0.000000"
        pi_c.border = tb
        pi_c.alignment = Alignment(horizontal="center")
        ei_c = ws.cell(row=row, column=4, value=f"={N_cell}*C{row}")
        ei_c.number_format = "0.0000"
        ei_c.border = tb
        ei_c.alignment = Alignment(horizontal="center")
        contrib_c = ws.cell(row=row, column=5, value=f"=(B{row}-D{row})^2/D{row}")
        contrib_c.number_format = "0.0000"
        contrib_c.border = tb
        contrib_c.alignment = Alignment(horizontal="center")
        row += 1

    class_end = row - 1
    row += 1

    chi0_cell = _kv_row(ws, row, "χ₀²  =  Σ (Oᵢ−Eᵢ)²/Eᵢ", f"=SUM(E{class_start}:E{class_end})", tb, num_fmt="0.0000", highlight=True)
    row += 1
    crit_cell = _kv_row(ws, row, f"χ²_(α, {df})  =  CHISQ.INV.RT(α, {df})", f"=_xlfn.CHISQ.INV.RT({alpha_cell},{df})", tb, num_fmt="0.0000", highlight=True)
    row += 2

    _section_header(ws, row, "CRITERIO DE DECISIÓN:  Se acepta H0 si χ₀² < χ²_(α, h)")
    row += 1
    _decision_row(ws, row, chi0_cell, crit_cell, tb, comparator="<")

    _autosize(ws)
    ws.column_dimensions["A"].width = 30
    ws.freeze_panes = f"A{helper_start}"


# =========================================================================
# T4. PRUEBA DE SERIES (Pares Solapados de bits)
# =========================================================================
def _sheet_series(wb, ws1_title, ri_col_letter, data_start_row, n, alpha):
    name, title, objective = TEST_SHEET_META["series"]
    ws, tb, alpha_cell, row = _new_test_sheet(wb, name, title, objective, alpha)

    note = ws.cell(row=row, column=1, value="Nota: se binariza cada Rᵢ por umbral de mediana (bᵢ = 1 si Rᵢ ≥ 0.5), ya que la prueba se define sobre cadenas de bits.")
    note.font = Font(name="Arial", size=9, italic=True, color=COLOR_TEXT)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 2

    _section_header(ws, row, "BINARIZACIÓN Y PARES SOLAPADOS")
    row += 1
    _table_header(ws, row, ["i", "Rᵢ", "bᵢ", "Par (bᵢ, bᵢ₊₁)"], tb)
    row += 1
    helper_start = row

    for k in range(1, n + 1):
        src_row = data_start_row + k - 1
        ws.cell(row=row, column=1, value=k).border = tb
        c_ri = ws.cell(row=row, column=2, value=f"='{ws1_title}'!{ri_col_letter}{src_row}")
        c_ri.number_format = "0.000000"
        c_ri.border = tb
        c_bit = ws.cell(row=row, column=3, value=f"=IF(B{row}>=0.5,1,0)")
        c_bit.border = tb
        c_bit.alignment = Alignment(horizontal="center")
        if k < n:
            c_pair = ws.cell(row=row, column=4, value=f"=C{row}&C{row+1}")
        else:
            c_pair = ws.cell(row=row, column=4, value="")
        c_pair.border = tb
        c_pair.alignment = Alignment(horizontal="center")
        row += 1

    helper_end = row - 1
    bit_range = f"$C${helper_start}:$C${helper_end}"
    pair_range = f"$D${helper_start}:$D${helper_end}"

    row += 1
    n_cell = _kv_row(ws, row, "n", f"=COUNT({bit_range})", tb, num_fmt="0")
    row += 1
    n0_cell = _kv_row(ws, row, "n₀  (ceros)", f'=COUNTIF({bit_range},0)', tb, num_fmt="0")
    row += 1
    n1_cell = _kv_row(ws, row, "n₁  (unos)", f'=COUNTIF({bit_range},1)', tb, num_fmt="0")
    row += 1
    n00_cell = _kv_row(ws, row, "n₀₀", f'=COUNTIF({pair_range},"00")', tb, num_fmt="0")
    row += 1
    n01_cell = _kv_row(ws, row, "n₀₁", f'=COUNTIF({pair_range},"01")', tb, num_fmt="0")
    row += 1
    n10_cell = _kv_row(ws, row, "n₁₀", f'=COUNTIF({pair_range},"10")', tb, num_fmt="0")
    row += 1
    n11_cell = _kv_row(ws, row, "n₁₁", f'=COUNTIF({pair_range},"11")', tb, num_fmt="0")
    row += 2

    x2_formula = (
        f"=(4/({n_cell}-1))*({n00_cell}^2+{n01_cell}^2+{n10_cell}^2+{n11_cell}^2)"
        f"-(2/{n_cell})*({n0_cell}^2+{n1_cell}^2)+1"
    )
    x2_cell = _kv_row(ws, row, "X₂ = [4/(n−1)]·(n₀₀²+n₀₁²+n₁₀²+n₁₁²) − (2/n)·(n₀²+n₁²) + 1", x2_formula, tb, num_fmt="0.0000", highlight=True)
    row += 1
    crit_cell = _kv_row(ws, row, "χ²_(α, 2)  =  CHISQ.INV.RT(α, 2)", f"=_xlfn.CHISQ.INV.RT({alpha_cell},2)", tb, num_fmt="0.0000", highlight=True)
    row += 2

    _section_header(ws, row, "CRITERIO DE DECISIÓN:  Se acepta H0 si X₂ < χ²_(α, 2)")
    row += 1
    _decision_row(ws, row, x2_cell, crit_cell, tb, comparator="<")

    _autosize(ws)
    ws.column_dimensions["A"].width = 50
    ws.freeze_panes = f"A{helper_start}"


# =========================================================================
# T5. PRUEBA DE KOLMOGOROV-SMIRNOV (K-S)
# =========================================================================
def _sheet_ks(wb, ri_range, n, alpha):
    name, title, objective = TEST_SHEET_META["kolmogorov_smirnov"]
    ws, tb, alpha_cell, row = _new_test_sheet(wb, name, title, objective, alpha)

    n_cell = _kv_row(ws, row, "n  (cantidad de valores)", f"=COUNT({ri_range})", tb, num_fmt="0")
    row += 2

    _section_header(ws, row, "MUESTRA ORDENADA Y DISCREPANCIAS")
    row += 1
    _table_header(ws, row, ["i", "x₍ᵢ₎ (ordenado)", "i/n", "(i−1)/n", "D⁺ᵢ = i/n − x₍ᵢ₎", "D⁻ᵢ = x₍ᵢ₎ − (i−1)/n"], tb)
    row += 1
    table_start = row

    for k in range(1, n + 1):
        ws.cell(row=row, column=1, value=k).border = tb
        c_sorted = ws.cell(row=row, column=2, value=f"=SMALL({ri_range},A{row})")
        c_sorted.number_format = "0.000000"
        c_sorted.border = tb
        c_in = ws.cell(row=row, column=3, value=f"=A{row}/{n_cell}")
        c_in.number_format = "0.000000"
        c_in.border = tb
        c_im1n = ws.cell(row=row, column=4, value=f"=(A{row}-1)/{n_cell}")
        c_im1n.number_format = "0.000000"
        c_im1n.border = tb
        c_dplus = ws.cell(row=row, column=5, value=f"=C{row}-B{row}")
        c_dplus.number_format = "0.000000"
        c_dplus.border = tb
        c_dminus = ws.cell(row=row, column=6, value=f"=B{row}-D{row}")
        c_dminus.number_format = "0.000000"
        c_dminus.border = tb
        row += 1

    table_end = row - 1
    row += 1

    dplus_cell = _kv_row(ws, row, "D⁺  =  MAX(D⁺ᵢ)", f"=MAX(E{table_start}:E{table_end})", tb, num_fmt="0.000000")
    row += 1
    dminus_cell = _kv_row(ws, row, "D⁻  =  MAX(D⁻ᵢ)", f"=MAX(F{table_start}:F{table_end})", tb, num_fmt="0.000000")
    row += 1
    d_cell = _kv_row(ws, row, "D  =  MAX(D⁺, D⁻)", f"=MAX({dplus_cell},{dminus_cell})", tb, num_fmt="0.000000", highlight=True)
    row += 1
    c_alpha_cell = _kv_row(ws, row, "c(α)  =  √(−0.5·LN(α/2))", f"=SQRT(-0.5*LN({alpha_cell}/2))", tb, num_fmt="0.0000")
    row += 1
    crit_cell = _kv_row(
        ws, row, "D_(α,n)  ≈  c(α) / (√n + 0.12 + 0.11/√n)   [aprox. Stephens, 1970]",
        f"={c_alpha_cell}/(SQRT({n_cell})+0.12+0.11/SQRT({n_cell}))", tb, num_fmt="0.000000", highlight=True
    )
    row += 2

    _section_header(ws, row, "CRITERIO DE DECISIÓN:  Se acepta H0 si D ≤ D_(α, n)")
    row += 1
    _decision_row(ws, row, d_cell, crit_cell, tb, comparator="<=")

    _autosize(ws)
    ws.column_dimensions["A"].width = 55
    ws.freeze_panes = f"A{table_start}"


# =========================================================================
# T6. PRUEBA DE POKER (Clásico Decimal, 5 dígitos) — 7 clases fijas (df=6, ref. PDF)
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
# sum(cnt1..cnt5) es unico por mano: TD=5, 1P=7, 2P=9, T=11, F=13, P4=17, Q=25

def _sheet_poker(wb, ws1_title, ri_col_letter, data_start_row, n, alpha, numbers):
    name, title, objective = TEST_SHEET_META["poker"]
    ws, tb, alpha_cell, row = _new_test_sheet(wb, name, title, objective, alpha)

    entries = _plan_poker_groups(numbers)
    if len(entries) < 2:
        warn = ws.cell(row=row, column=1, value=f"⚠ Datos insuficientes: con n={n} no se pudieron formar al menos 2 clases con frecuencia esperada ≥ 5. Aumente la cantidad de valores generados y vuelva a exportar.")
        warn.font = Font(name="Arial", size=10.5, bold=True, color="B45309")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
        _autosize(ws)
        return
    df = len(entries) - 1

    note = ws.cell(row=row, column=1, value=f"Nota: las 7 manos posibles se agruparon automáticamente ({len(entries)} clases, ν = {df}) para que todas las Eᵢ ≥ 5 con esta muestra (n = {n}), igual que en la vista web.")
    note.font = Font(name="Arial", size=9, italic=True, color=COLOR_TEXT)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
    row += 2

    _section_header(ws, row, "EXTRACCIÓN DE DÍGITOS Y CLASIFICACIÓN DE MANOS")
    row += 1
    _table_header(ws, row, ["i", "Rᵢ", "Dígitos (5)", "cnt₁", "cnt₂", "cnt₃", "cnt₄", "cnt₅", "Σcnt", "Mano"], tb)
    row += 1
    helper_start = row

    for k in range(1, n + 1):
        src_row = data_start_row + k - 1
        ws.cell(row=row, column=1, value=k).border = tb
        c_ri = ws.cell(row=row, column=2, value=f"='{ws1_title}'!{ri_col_letter}{src_row}")
        c_ri.number_format = "0.000000"
        c_ri.border = tb
        c_dig = ws.cell(row=row, column=3, value=f'=TEXT(INT(B{row}*100000),"00000")')
        c_dig.border = tb
        c_dig.alignment = Alignment(horizontal="center")
        for j in range(1, 6):
            col = 3 + j  # D..H
            col_letter = get_column_letter(col)
            f = f'=LEN($C{row})-LEN(SUBSTITUTE($C{row},MID($C{row},{j},1),""))'
            cc = ws.cell(row=row, column=col, value=f)
            cc.border = tb
            cc.alignment = Alignment(horizontal="center")
        sumsq_c = ws.cell(row=row, column=9, value=f"=SUM(D{row}:H{row})")
        sumsq_c.border = tb
        sumsq_c.alignment = Alignment(horizontal="center")
        mano_formula = (
            f'=IF(I{row}=5,"TD",IF(I{row}=7,"1P",IF(I{row}=9,"2P",'
            f'IF(I{row}=11,"T",IF(I{row}=13,"F",IF(I{row}=17,"P4","Q"))))))'
        )
        mano_c = ws.cell(row=row, column=10, value=mano_formula)
        mano_c.border = tb
        mano_c.alignment = Alignment(horizontal="center")
        row += 1

    helper_end = row - 1
    mano_range = f"$J${helper_start}:$J${helper_end}"

    row += 1
    n_cell = _kv_row(ws, row, "n", f"=COUNT($B${helper_start}:$B${helper_end})", tb, num_fmt="0")
    row += 2

    _section_header(ws, row, "TABLA DE FRECUENCIAS POR MANO (agrupada donde hizo falta)")
    row += 1
    _table_header(ws, row, ["Mano(s)", "Probabilidad Teórica", "Oᵢ (observado)", "Eᵢ = n·p", "(Oᵢ−Eᵢ)²/Eᵢ"], tb)
    row += 1
    class_start = row
    for entry in entries:
        ws.cell(row=row, column=1, value=entry["label"]).border = tb
        p_c = ws.cell(row=row, column=2, value=entry["prob"])
        p_c.number_format = "0.00000"
        p_c.border = tb
        p_c.alignment = Alignment(horizontal="center")
        oi_terms = [f'COUNTIF({mano_range},"{code}")' for code in entry["codes"]]
        oi_c = ws.cell(row=row, column=3, value="=" + "+".join(oi_terms))
        oi_c.border = tb
        oi_c.alignment = Alignment(horizontal="center")
        ei_c = ws.cell(row=row, column=4, value=f"={n_cell}*B{row}")
        ei_c.number_format = "0.0000"
        ei_c.border = tb
        ei_c.alignment = Alignment(horizontal="center")
        contrib_c = ws.cell(row=row, column=5, value=f"=(C{row}-D{row})^2/D{row}")
        contrib_c.number_format = "0.0000"
        contrib_c.border = tb
        contrib_c.alignment = Alignment(horizontal="center")
        row += 1
    class_end = row - 1
    row += 1

    x3_cell = _kv_row(ws, row, "X₃  =  Σ (Oᵢ−Eᵢ)²/Eᵢ", f"=SUM(E{class_start}:E{class_end})", tb, num_fmt="0.0000", highlight=True)
    row += 1
    crit_cell = _kv_row(ws, row, f"χ²_(α, {df})  =  CHISQ.INV.RT(α, {df})", f"=_xlfn.CHISQ.INV.RT({alpha_cell},{df})", tb, num_fmt="0.0000", highlight=True)
    row += 2

    _section_header(ws, row, f"CRITERIO DE DECISIÓN:  Se acepta H0 si X₃ < χ²_(α, {df})")
    row += 1
    _decision_row(ws, row, x3_cell, crit_cell, tb, comparator="<")

    _autosize(ws)
    ws.column_dimensions["A"].width = 30
    ws.freeze_panes = f"A{helper_start}"




# =========================================================================
# T7. PRUEBA DE CORRIDAS ARRIBA Y ABAJO DEL PROMEDIO
# Version estatica (Cap. 3, Coss Bu): se compara cada Ri contra mu=0.5. La
# deteccion de corridas se hace con una recurrencia hacia adelante (columna
# "Longitud corrida actual", que solo referencia la fila anterior) y una
# columna de cierre de corrida que compara contra la fila SIGUIENTE (una
# referencia hacia adelante, sin ciclos -- el mismo patron que ya usa la
# columna "Par (bi, bi+1)" de la hoja de Series). El numero de clases (h) se
# decide una sola vez al exportar, a partir de las corridas REALES
# observadas, agrupando la cola donde FEi < 5 (criterio de Cochran).
# =========================================================================
def _sheet_corridas_promedio(wb, ws1_title, ri_col_letter, data_start_row, n, alpha, numbers):
    name, title, objective = TEST_SHEET_META["corridas_promedio"]
    ws, tb, alpha_cell, row = _new_test_sheet(wb, name, title, objective, alpha)

    bits = [0 if x < 0.5 else 1 for x in numbers]
    lengths = _run_lengths_py(bits)

    if len(lengths) < 5:
        warn = ws.cell(row=row, column=1, value=f"⚠ Datos insuficientes: con n={n} solo se observaron {len(lengths)} corridas; se necesitan al menos 5 para construir la tabla de clases. Aumente la cantidad de valores generados y vuelva a exportar.")
        warn.font = Font(name="Arial", size=10.5, bold=True, color="B45309")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        _autosize(ws)
        return

    total_expected_py = (n + 1) / 2.0

    def fe_i(i):
        return (n - i + 3) / (2 ** (i + 1))

    plan = _plan_run_length_groups(lengths, total_expected_py, fe_i, cap=30)
    if plan is None:
        warn = ws.cell(row=row, column=1, value="⚠ Datos insuficientes: no fue posible formar al menos 2 clases con frecuencia esperada ≥ 5 a partir de las corridas observadas. Aumente la cantidad de valores generados y vuelva a exportar.")
        warn.font = Font(name="Arial", size=10.5, bold=True, color="B45309")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        _autosize(ws)
        return
    entries, h_used = plan
    df = len(entries) - 1

    n_cell = _kv_row(ws, row, "n  (cantidad de valores)", f"=COUNT('{ws1_title}'!${ri_col_letter}${data_start_row}:${ri_col_letter}${data_start_row + n - 1})", tb, num_fmt="0")
    row += 1
    total_cell = _kv_row(ws, row, "E(Total de corridas)  =  (n + 1) / 2", f"=({n_cell}+1)/2", tb, num_fmt="0.0000")
    row += 1
    note2 = ws.cell(row=row, column=1, value=f"La cantidad de clases ({len(entries)}) se calculó al exportar, agrupando corridas hasta lograr FEᵢ ≥ 5 (criterio de Cochran).")
    note2.font = Font(name="Arial", size=9, italic=True, color=COLOR_TEXT)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 2

    _section_header(ws, row, f"BINARIZACIÓN Y DETECCIÓN DE CORRIDAS (h = {h_used}, ν = {df})")
    row += 1
    _table_header(ws, row, ["i", "Rᵢ", "sᵢ (0 si Rᵢ<0.5, 1 si Rᵢ≥0.5)", "Longitud corrida actual", "Longitud si es fin de corrida"], tb)
    row += 1
    helper_start = row

    for k in range(1, n + 1):
        src_row = data_start_row + k - 1
        ws.cell(row=row, column=1, value=k).border = tb
        ws.cell(row=row, column=1).alignment = Alignment(horizontal="center")

        c_ri = ws.cell(row=row, column=2, value=f"='{ws1_title}'!{ri_col_letter}{src_row}")
        c_ri.number_format = "0.000000"
        c_ri.border = tb
        c_ri.alignment = Alignment(horizontal="center")

        c_bit = ws.cell(row=row, column=3, value=f"=IF(B{row}>=0.5,1,0)")
        c_bit.border = tb
        c_bit.alignment = Alignment(horizontal="center")

        if row == helper_start:
            len_formula = "=1"
        else:
            len_formula = f"=IF(C{row}=C{row-1},D{row-1}+1,1)"
        c_len = ws.cell(row=row, column=4, value=len_formula)
        c_len.border = tb
        c_len.alignment = Alignment(horizontal="center")

        if k == n:
            end_formula = f"=D{row}"
        else:
            end_formula = f'=IF(C{row}<>C{row+1},D{row},"")'
        c_end = ws.cell(row=row, column=5, value=end_formula)
        c_end.border = tb
        c_end.alignment = Alignment(horizontal="center")

        row += 1

    helper_end = row - 1
    run_range = f"$E${helper_start}:$E${helper_end}"

    row += 1
    runs_cell = _kv_row(ws, row, "Corridas totales observadas  =  COUNT(rango)", f"=COUNT({run_range})", tb, num_fmt="0")
    row += 2

    _section_header(ws, row, "TABLA DE CLASES DE LONGITUD DE CORRIDA (clases agrupadas automáticamente donde FEᵢ < 5)")
    row += 1
    _table_header(ws, row, ["Clase (longitud i)", "FOᵢ (observado)", "FEᵢ (esperado)", "(FOᵢ−FEᵢ)²/FEᵢ"], tb)
    row += 1
    class_start = row
    fe_col_letter = "C"
    for entry in entries:
        ws.cell(row=row, column=1, value=entry["label"]).border = tb

        oi_terms = []
        has_tail = False
        for kind, val in entry["codes"]:
            if kind == "i":
                oi_terms.append(f'COUNTIF({run_range},{val})')
            else:
                oi_terms.append(f'COUNTIF({run_range},">="&{val})')
                has_tail = True
        oi_c = ws.cell(row=row, column=2, value="=" + "+".join(oi_terms))
        oi_c.border = tb
        oi_c.alignment = Alignment(horizontal="center")

        if has_tail:
            fe_formula = f"={total_cell}-SUM({fe_col_letter}{class_start}:{fe_col_letter}{row-1})" if row > class_start else f"={total_cell}"
        else:
            i_val = next(val for kind, val in entry["codes"] if kind == "i")
            fe_formula = f"=({n_cell}-{i_val}+3)/2^{i_val + 1}"
        fe_c = ws.cell(row=row, column=3, value=fe_formula)
        fe_c.number_format = "0.0000"
        fe_c.border = tb
        fe_c.alignment = Alignment(horizontal="center")

        contrib_c = ws.cell(row=row, column=4, value=f"=(B{row}-C{row})^2/C{row}")
        contrib_c.number_format = "0.0000"
        contrib_c.border = tb
        contrib_c.alignment = Alignment(horizontal="center")
        row += 1

    class_end = row - 1
    row += 1

    chi0_cell = _kv_row(ws, row, "X₀²  =  Σ (FOᵢ−FEᵢ)²/FEᵢ", f"=SUM(D{class_start}:D{class_end})", tb, num_fmt="0.0000", highlight=True)
    row += 1
    crit_cell = _kv_row(ws, row, f"χ²_(α, {df})  =  CHISQ.INV.RT(α, {df})", f"=_xlfn.CHISQ.INV.RT({alpha_cell},{df})", tb, num_fmt="0.0000", highlight=True)
    row += 2

    _section_header(ws, row, "CRITERIO DE DECISIÓN:  Se acepta H0 si X₀² ≤ χ²_(α, k−1)")
    row += 1
    _decision_row(ws, row, chi0_cell, crit_cell, tb, comparator="<=")

    _autosize(ws)
    ws.column_dimensions["A"].width = 34
    ws.freeze_panes = f"A{helper_start}"

