"""
Generador de Documentación Técnica y Matemática en PDF
PseudoAleatorios Studio - Suite de Simulación Digital
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas con pie de página dinámico 'Página X de Y'."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (páginas > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "PseudoAleatorios Studio — Arquitectura Lógica y Modelado Matemático")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Footer
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, "Documento Técnico de Simulación Digital — Módulo de Generadores Pseudoaleatorios")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)
        self.restoreState()


def generate_documentation_pdf(output_path: str = "Documentacion_Logica_PseudoAleatorios.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Estilos Personalizados
    c_primary = colors.HexColor("#1E1B4B")     # Indigo muy oscuro
    c_secondary = colors.HexColor("#4338CA")   # Indigo medio
    c_accent = colors.HexColor("#047857")      # Verde esmeralda oscuro
    c_dark = colors.HexColor("#0F172A")        # Slate oscuro
    c_gray = colors.HexColor("#334155")        # Slate texto
    c_bg_box = colors.HexColor("#F8FAFC")      # Fondo gris claro
    c_border = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        alignment=0,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=c_secondary,
        alignment=0,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_secondary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_gray,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_gray,
        leftIndent=14,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=2,
        spaceAfter=2
    )

    box_text_style = ParagraphStyle(
        'Box_Text',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_dark
    )

    story = []

    # =========================================================================
    # PORTADA / ENCABEZADO
    # =========================================================================
    story.append(Paragraph("DOCUMENTO DE ESPECIFICACIÓN LÓGICA Y MATEMÁTICA", title_style))
    story.append(Paragraph("Arquitectura de Algoritmos, Teoremas de Periodo y Estructura del Sistema PRNG", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_secondary, spaceBefore=0, spaceAfter=12))

    meta_table_data = [
        [Paragraph("<b>Asignatura:</b> Simulación Digital", body_style), Paragraph("<b>Módulo:</b> Generadores de Números Pseudoaleatorios (PRNG)", body_style)],
        [Paragraph("<b>Autores:</b> Adrian Angulo M. & Samuel Molina R.", body_style), Paragraph("<b>Tecnología:</b> Python 3 / FastAPI / OpenPyXL", body_style)],
        [Paragraph("<b>Alcance:</b> Lógica Matemática, Validaciones y Algoritmos", body_style), Paragraph("<b>Fecha de Revisión:</b> Agosto 2026", body_style)]
    ]
    meta_table = Table(meta_table_data, colWidths=[250, 254])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_box),
        ('BOX', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECCIÓN 1: MAPA DE ARQUITECTURA Y DÓNDE RESIDE LA LÓGICA
    # =========================================================================
    story.append(Paragraph("1. Arquitectura del Código y Ubicación de la Lógica", h1_style))
    story.append(Paragraph(
        "Toda la lógica de negocio, validaciones formales de teoría de números, generación de secuencias y cálculos estocásticos "
        "se encuentra estrictamente modularizada en la capa de backend dentro del paquete <code>core/</code> y el despachador <code>app.py</code>. "
        "A continuación se detalla la responsabilidad de cada archivo:",
        body_style
    ))

    arch_data = [
        [Paragraph("<b>Archivo / Módulo</b>", box_text_style), Paragraph("<b>Responsabilidad y Funciones Principales</b>", box_text_style), Paragraph("<b>Lógica que Implementa</b>", box_text_style)],
        [
            Paragraph("<code>core/validators.py</code>", code_style),
            Paragraph("• <code>validate_gclm()</code><br/>• <code>validate_gcm()</code><br/>• <code>validate_cuadrados_medios()</code><br/>• <code>validate_productos_medios()</code><br/>• <code>validate_bbs()</code><br/>• Utilidades: <code>is_prime()</code>, <code>gcd()</code>, <code>find_primitive_roots()</code>, <code>is_power_of_two()</code>", box_text_style),
            Paragraph("Verificación matemática de dominios, Teorema de Hull-Dobell, raíces primitivas mod m, periodo maximal de Lehmer, primos de Blum (p ≡ 3 mod 4) y heurísticas de von Neumann.", box_text_style)
        ],
        [
            Paragraph("<code>core/generators.py</code>", code_style),
            Paragraph("• <code>generate_gclm()</code><br/>• <code>generate_gcm()</code><br/>• <code>generate_cuadrados_medios()</code><br/>• <code>generate_productos_medios()</code><br/>• <code>generate_bbs()</code><br/>• <code>calculate_stats()</code>", box_text_style),
            Paragraph("Máquinas de estado iterativas. Generación de trazas paso a paso, detección de ciclos por historial de estados, cálculo de media, varianza, retardo Lag-1 (R_i vs R_{i+1}) y autocorrelación.", box_text_style)
        ],
        [
            Paragraph("<code>core/recommenders.py</code>", code_style),
            Paragraph("• <code>generate_gclm_optimal()</code><br/>• <code>generate_gcm_optimal()</code><br/>• <code>generate_cuadrados_medios_optimal()</code><br/>• <code>generate_productos_medios_optimal()</code><br/>• <code>generate_bbs_optimal()</code>", box_text_style),
            Paragraph("Síntesis constructiva de parámetros óptimos que garantizan periodo maximal según los teoremas algebraicos sin intervención manual.", box_text_style)
        ],
        [
            Paragraph("<code>core/excel_exporter.py</code>", code_style),
            Paragraph("• <code>export_prng_to_excel()</code><br/>• <code>_build_sheet1()</code><br/>• <code>_build_sheet2()</code>", box_text_style),
            Paragraph("Construcción del libro .xlsx profesional en memoria con OpenPyXL: tabla de parámetros, secuencia numérica con 6 decimales y gráfico de dispersión nativo.", box_text_style)
        ],
        [
            Paragraph("<code>app.py</code>", code_style),
            Paragraph("• <code>/api/generate</code><br/>• <code>/api/validate</code><br/>• <code>/api/recommend</code><br/>• <code>/api/download/{filename}</code>", box_text_style),
            Paragraph("Controlador REST API (FastAPI) que desacopla la comunicación frontend-backend y gestiona descargas nativas con <code>FileResponse</code>.", box_text_style)
        ]
    ]

    arch_table = Table(arch_data, colWidths=[110, 194, 200])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECCIÓN 2: EXPLICACIÓN DETALLADA DE CADA MÉTODO
    # =========================================================================
    story.append(Paragraph("2. Análisis Detallado de los 5 Métodos Pseudoaleatorios", h1_style))
    story.append(Paragraph(
        "A continuación se expone la formulación matemática exacta, restricciones de dominio, teoremas de periodo, "
        "características operativas y modo de fallo de cada uno de los algoritmos implementados.",
        body_style
    ))

    # -------------------------------------------------------------------------
    # 2.1 CONGRUENCIAL LINEAL MIXTO (GCLM)
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.1 Generador Congruencial Lineal Mixto (GCLM)", h2_style))
    story.append(Paragraph("<b>Formulación Recursiva:</b>", body_style))
    story.append(Paragraph("<code>X_{i+1} = (a · X_i + c) mod m</code> &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; <code>R_i = X_i / m  ∈ [0, 1)</code>", code_style))
    story.append(Paragraph("<b>Parámetros y Dominio:</b>", body_style))
    story.append(Paragraph("• <b>X₀ (Semilla Inicial):</b> Entero no negativo en el rango <code>0 ≤ X₀ &lt; m</code>.", bullet_style))
    story.append(Paragraph("• <b>a (Multiplicador):</b> Entero constante <code>1 &lt; a &lt; m</code>.", bullet_style))
    story.append(Paragraph("• <b>c (Incremento / Constante Aditiva):</b> Entero constante <code>1 ≤ c &lt; m</code>.", bullet_style))
    story.append(Paragraph("• <b>m (Módulo):</b> Entero positivo <code>m &gt; max(X₀, a, c)</code>.", bullet_style))
    
    story.append(Paragraph("<b>Teorema Fundamental de Hull-Dobell (Periodo Completo N = m):</b>", body_style))
    story.append(Paragraph(
        "El generador tiene periodo completo <b>N = m</b> (genera todos los números entre 0 y m-1 sin repetir ninguno antes) "
        "<b>si y sólo si</b> se cumplen simultáneamente las siguientes 3 condiciones algebraicas:",
        body_style
    ))

    hd_box_data = [
        [Paragraph("<b>Condición 1:</b>", box_text_style), Paragraph("<code>mcd(c, m) = 1</code> (c y m deben ser estrictamente coprimos).", box_text_style)],
        [Paragraph("<b>Condición 2:</b>", box_text_style), Paragraph("Todo factor primo <code>p</code> de <code>m</code> debe dividir exactamente a <code>(a - 1)</code>, es decir, <code>(a - 1) mod p = 0</code>.", box_text_style)],
        [Paragraph("<b>Condición 3:</b>", box_text_style), Paragraph("Si 4 divide a <code>m</code> (<code>m mod 4 = 0</code>), entonces 4 debe dividir a <code>(a - 1)</code> (<code>(a - 1) mod 4 = 0</code>).", box_text_style)]
    ]
    hd_table = Table(hd_box_data, colWidths=[85, 419])
    hd_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#86EFAC")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#DCFCE7")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(hd_table)
    story.append(Paragraph("<b>Características:</b> Altísima velocidad de cómputo. Si Hull-Dobell se cumple, la elección de la semilla X₀ no afecta la longitud del periodo completo N = m.", body_style))
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # 2.2 CONGRUENCIAL MULTIPLICATIVO (GCM / LEHMER)
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.2 Generador Congruencial Multiplicativo (GCM / Lehmer)", h2_style))
    story.append(Paragraph("<b>Formulación Recursiva:</b>", body_style))
    story.append(Paragraph("<code>X_{i+1} = (a · X_i) mod m</code> &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; <code>R_i = X_i / m  ∈ (0, 1)</code> &nbsp;&nbsp;(c = 0)", code_style))
    story.append(Paragraph("<b>Parámetros y Dominio:</b>", body_style))
    story.append(Paragraph("• <b>X₀ (Semilla Inicial):</b> Entero positivo <code>0 &lt; X₀ &lt; m</code>. <b>X₀ ≠ 0</b> (0 es un estado absorbente que anula la secuencia).", bullet_style))
    story.append(Paragraph("• <b>a (Multiplicador):</b> Entero constante <code>1 &lt; a &lt; m</code>.", bullet_style))
    story.append(Paragraph("• <b>m (Módulo):</b> Entero positivo mayor que a y X₀.", bullet_style))

    story.append(Paragraph("<b>Reglas de Periodo Maximal:</b>", body_style))
    story.append(Paragraph("Al carecer de término aditivo (c=0), el GCM nunca puede alcanzar periodo N=m. Su periodo maximal depende de la estructura algebraica de m:", body_style))

    gcm_box_data = [
        [
            Paragraph("<b>Caso A: Módulo Potencia de 2 (m = 2ᵍ con g ≥ 4)</b>", box_text_style),
            Paragraph("• Periodo maximal alcanzable: <b>N = m / 4 = 2^(g-2)</b>.<br/>"
                      "• Restricción de semilla: <code>X₀</code> debe ser <b>impar</b> (<code>mcd(X₀, m) = 1</code>).<br/>"
                      "• Restricción del multiplicador: <code>a = 3 + 8k</code> o <code>a = 5 + 8k</code> (con k entero ≥ 0).", box_text_style)
        ],
        [
            Paragraph("<b>Caso B: Módulo Primo (m es un número primo)</b>", box_text_style),
            Paragraph("• Periodo maximal alcanzable: <b>N = m - 1</b>.<br/>"
                      "• Restricción de semilla: Cualquier <code>0 &lt; X₀ &lt; m</code>.<br/>"
                      "• Restricción del multiplicador: <code>a</code> debe ser una <b>raíz primitiva módulo m</b>, es decir, el orden multiplicativo de a mod m debe ser exactamente m - 1 (para todo factor primo q de m-1: <code>a^((m-1)/q) mod m ≠ 1</code>).", box_text_style)
        ]
    ]
    gcm_table = Table(gcm_box_data, colWidths=[160, 344])
    gcm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, c_border),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(gcm_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # 2.3 CUADRADOS MEDIOS (MIDDLE-SQUARE)
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.3 Algoritmo de Cuadrados Medios (John von Neumann, 1949)", h2_style))
    story.append(Paragraph("<b>Mecánica del Algoritmo:</b>", body_style))
    story.append(Paragraph(
        "1. Se toma la semilla actual de <code>D</code> dígitos <code>X_i</code> (con D par, comúnmente D=4).<br/>"
        "2. Se eleva al cuadrado: <code>Y_i = (X_i)²</code> (produce hasta <code>2D</code> dígitos).<br/>"
        "3. Si <code>Y_i</code> tiene menos de <code>2D</code> dígitos, se rellena con ceros a la izquierda hasta longitud <code>2D</code>.<br/>"
        "4. Se extraen los <code>D</code> dígitos centrales como el siguiente valor <code>X_{i+1}</code>.<br/>"
        "5. El número normalizado se obtiene como: <code>R_i = X_{i+1} / 10^D  ∈ [0, 1)</code>.",
        body_style
    ))
    story.append(Paragraph("<b>Patologías y Modos de Fallo (Heurísticas de Validación):</b>", body_style))
    story.append(Paragraph("• <b>Colapso a Cero:</b> Si los dígitos centrales extraídos son <code>0000</code>, todas las iteraciones subsiguientes se convierten en cero indefinidamente.", bullet_style))
    story.append(Paragraph("• <b>Punto Fijo Degenerativo:</b> Ciertas semillas generan su propio valor al cuadrado (ej. <code>3792² = 14379264 → 3792</code>), deteniendo la variabilidad.", bullet_style))
    story.append(Paragraph("• <b>Terminaciones Riesgosas:</b> Semillas que terminan en <code>00</code>, <code>25</code>, <code>50</code> o <code>75</code> multiplican ceros hacia el centro en pocas iteraciones.", bullet_style))
    story.append(Paragraph("• <b>Periodos Cortos:</b> Carece de base matemática para garantizar periodo largo; es un método histórico no congruencial.", bullet_style))
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # 2.4 PRODUCTOS MEDIOS (MIDDLE-PRODUCT)
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.4 Algoritmo de Productos Medios", h2_style))
    story.append(Paragraph("<b>Mecánica del Algoritmo:</b>", body_style))
    story.append(Paragraph(
        "1. Requiere dos semillas iniciales de <code>D</code> dígitos: <code>X₀</code> y <code>X₁</code> (con <code>X₀ ≠ X₁</code>).<br/>"
        "2. En el paso <code>i</code>, se multiplican los dos estados previos: <code>Y_i = X_{i-1} · X_i</code>.<br/>"
        "3. Se rellena <code>Y_i</code> con ceros a la izquierda a longitud <code>2D</code>.<br/>"
        "4. Se extraen los <code>D</code> dígitos centrales como <code>X_{i+1}</code>.<br/>"
        "5. <code>R_i = X_{i+1} / 10^D</code>.",
        body_style
    ))
    story.append(Paragraph("<b>Restricciones y Ventajas:</b>", body_style))
    story.append(Paragraph("• <b>Condición de Semillas:</b> <code>mcd(X₀, X₁) = 1</code> (coprimas) y longitud exacta de D dígitos sin ceros terminales.", bullet_style))
    story.append(Paragraph("• <b>Mejora frente a Cuadrados Medios:</b> Al involucrar dos estados en la multiplicación, reduce sustancialmente la tasa de colapso a puntos fijos y alarga el ciclo promedio.", bullet_style))
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # 2.5 BLUM BLUM SHUB (BBS - CSPRNG)
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.5 Generador Criptográfico Blum Blum Shub (BBS, 1986)", h2_style))
    story.append(Paragraph("<b>Formulación y Base Criptográfica:</b>", body_style))
    story.append(Paragraph(
        "Blum Blum Shub es un generador pseudoaleatorio criptográficamente seguro (CSPRNG). "
        "Su seguridad matemática se fundamenta en la intratabilidad computacional del <b>Problema de Residuos Cuadráticos</b> "
        "y la dificultad de factorizar el entero de Blum <code>M = p · q</code>.",
        body_style
    ))
    story.append(Paragraph("<b>Mecánica Iterativa:</b>", body_style))
    story.append(Paragraph("• <b>Entero de Blum:</b> <code>M = p · q</code>, donde <code>p</code> y <code>q</code> son primos grandes con <code>p ≡ 3 (mod 4)</code> y <code>q ≡ 3 (mod 4)</code>.", bullet_style))
    story.append(Paragraph("• <b>Semilla Inicial:</b> <code>s</code> tal que <code>mcd(s, M) = 1</code> y <code>s ∉ {0, 1}</code>.", bullet_style))
    story.append(Paragraph("• <b>Estado Inicial (i = 0):</b> <code>X₀ = (s)² mod M</code>.", bullet_style))
    story.append(Paragraph("• <b>Evolución del Estado:</b> <code>X_{i+1} = (X_i)² mod M</code>.", bullet_style))
    story.append(Paragraph("• <b>Extracción de Bit Criptográfico:</b> <code>b_i = X_i mod 2</code> (bit de paridad / LSB).", bullet_style))
    story.append(Paragraph("• <b>Número Pseudoaleatorio Normalizado:</b> <code>R_i = X_i / M  ∈ (0, 1)</code>.", bullet_style))
    story.append(Paragraph("<b>Longitud del Periodo:</b> El ciclo en el grupo de residuos cuadráticos divide a <code>λ(λ(M))</code>, donde <code>λ(M) = mcm(p-1, q-1)</code> es la función indicatriz de Carmichael.", body_style))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECCIÓN 3: TABLA COMPARATIVA RESUMEN
    # =========================================================================
    story.append(Paragraph("3. Matriz Comparativa de Algoritmos PRNG", h1_style))

    comp_data = [
        [Paragraph("<b>Método</b>", box_text_style), Paragraph("<b>Fórmula de Avance</b>", box_text_style), Paragraph("<b>Periodo Maximal</b>", box_text_style), Paragraph("<b>Seguridad / Aplicación</b>", box_text_style)],
        [
            Paragraph("<b>GCLM (Mixto)</b>", box_text_style),
            Paragraph("<code>X_{i+1} = (aX_i + c) mod m</code>", code_style),
            Paragraph("<code>N = m</code> (Hull-Dobell)", box_text_style),
            Paragraph("No criptográfico. Excelente para simulación de Monte Carlo e ingeniería.", box_text_style)
        ],
        [
            Paragraph("<b>GCM (Lehmer)</b>", box_text_style),
            Paragraph("<code>X_{i+1} = (aX_i) mod m</code>", code_style),
            Paragraph("<code>N = m/4</code> (2ᵍ) o<br/><code>N = m-1</code> (primo)", box_text_style),
            Paragraph("No criptográfico. Muy rápido computacionalmente (sin sumas).", box_text_style)
        ],
        [
            Paragraph("<b>Cuadrados Medios</b>", box_text_style),
            Paragraph("<code>X_{i+1} = Centro_D((X_i)²)</code>", code_style),
            Paragraph("Impredecible (corto)", box_text_style),
            Paragraph("Histórico / Didáctico. Riesgo de colapso a 0000 o bucles cortos.", box_text_style)
        ],
        [
            Paragraph("<b>Productos Medios</b>", box_text_style),
            Paragraph("<code>X_{i+1} = Centro_D(X_{i-1}·X_i)</code>", code_style),
            Paragraph("Impredecible", box_text_style),
            Paragraph("Histórico. Mayor longitud de periodo que Cuadrados Medios.", box_text_style)
        ],
        [
            Paragraph("<b>Blum Blum Shub</b>", box_text_style),
            Paragraph("<code>X_{i+1} = (X_i)² mod (p·q)</code>", code_style),
            Paragraph("Divide a λ(λ(M))", box_text_style),
            Paragraph("<b>Criptográficamente Seguro (CSPRNG)</b>. Generación de claves y cifrado.", box_text_style)
        ]
    ]

    comp_table = Table(comp_data, colWidths=[95, 145, 114, 150])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECCIÓN 4: MOTOR DE ANÁLISIS ESTOCÁSTICO Y DETECCIÓN DE CICLOS
    # =========================================================================
    story.append(Paragraph("4. Motor de Detección de Ciclos y Estadísticas", h1_style))
    story.append(Paragraph(
        "En <code>core/generators.py</code> (función <code>calculate_stats()</code>) se implementó un motor analítico que evalúa en tiempo de ejecución:",
        body_style
    ))
    story.append(Paragraph("• <b>Detección de Ciclos por Memoria de Estados (Hash Map O(1)):</b> Durante la iteración, cada estado generado <code>X_i</code> (o el par <code>(X_{i-1}, X_i)</code> en Productos Medios) se indexa en una tabla hash. En el instante exacto en que un estado se repite, se registra el inicio del bucle, se marca la fila en la tabla visual y se calcula el periodo exacto <code>Periodo = i_{actual} - i_{previo}</code>.", bullet_style))
    story.append(Paragraph("• <b>Análisis de Independencia Estocástica (Dispersión de Retardo Lag-1):</b> Se construyen los pares ordenados <code>(R_i, R_{i+1})</code> en el plano unitario <code>[0, 1) × [0, 1)</code>. Permite detectar visual y cuantitativamente la presencia de hiperplanos o patrones deterministas.", bullet_style))
    story.append(Paragraph("• <b>Coeficiente de Autocorrelación Lag-1 (ρ₁):</b> Se computa el estadístico formal <code>ρ₁ = Cov(R_i, R_{i+1}) / Var(R_i)</code>. Para una secuencia verdaderamente independiente, <code>ρ₁ ≈ 0</code>.", bullet_style))

    # Construir PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generado exitosamente en: {output_path}")


if __name__ == "__main__":
    generate_documentation_pdf()
