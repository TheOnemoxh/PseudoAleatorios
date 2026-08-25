"""
Excel Exporter for PRNG Sequences
Generates a professionally styled .xlsx workbook using openpyxl:
- Sheet 1: Metadata, Variables, Diagnóstico de Teoremas y Tabla Completa Paso a Paso
  con los valores numéricos calculados de la secuencia pseudoaleatoria.
- Sheet 2: Pares de Independencia Lag-1 (R_i vs R_{i+1}) y Gráfico de Dispersión Nativo.
- Paleta moderna: Verde Esmeralda (#10B981) y Morado (#7C3AED / #4C1D95).
"""

import io
from typing import Dict, Any, Tuple
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
COLOR_ZEBRA = "F9FAFB"
COLOR_WHITE = "FFFFFF"
COLOR_TEXT = "111827"
COLOR_BORDER = "D1D5DB"

SHEET1_TITLE = "Secuencia y Calculos"
SHEET2_TITLE = "Analisis de Independencia"


def create_thin_border():
    thin = Side(border_style="thin", color=COLOR_BORDER)
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def export_prng_to_excel(gen_result: Dict[str, Any]) -> io.BytesIO:
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
