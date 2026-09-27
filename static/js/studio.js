/**
 * PseudoAleatorios Studio - Frontend Engine
 * Arquitectura reactiva y limpia para la generación, validación en tiempo real
 * y análisis estocástico de números pseudoaleatorios.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Estado Global de la Aplicación
  const state = {
    currentMethod: 'congruencial_mixto',
    gcmCaseType: 'pow2',
    lastResult: null,
    alpha: 0.05,
    lastTests: null,
    selectedTestId: 'promedio',
    lastDists: null,
    selectedDistId: 'uniforme',
    distConfig: null,
    charts: {
      scatter: null,
      distHist: null
    }
  };

  const TEST_SHORT_NAMES = {
    promedio: 'Promedio',
    frecuencia: 'Frecuencia',
    distancia: 'Distancia',
    series: 'Series',
    kolmogorov_smirnov: 'Kolmogorov-Smirnov',
    poker: 'Poker',
    corridas_promedio: 'Corridas del Promedio'
  };

  // Metadatos de Contexto por Algoritmo
  const methodMetadata = {
    congruencial_mixto: {
      name: 'Congruencial Lineal Mixto (GCLM)',
      tag: 'Teorema Hull-Dobell',
      formula: 'X_{i+1} = (a × X_i + c) mod m'
    },
    congruencial_multiplicativo: {
      name: 'Congruencial Multiplicativo (GCM)',
      tag: 'Periodo Maximal (Lehmer)',
      formula: 'X_{i+1} = (a × X_i) mod m'
    },
    cuadrados_medios: {
      name: 'Cuadrados Medios (Middle-Square)',
      tag: 'John von Neumann',
      formula: 'Y_i = (X_i)²  →  X_{i+1} = Extraer_D(Y_i)'
    },
    productos_medios: {
      name: 'Productos Medios (Middle-Product)',
      tag: 'Dos Semillas Iniciales',
      formula: 'Y_i = X_{i-1} × X_i  →  X_{i+1} = Extraer_D(Y_i)'
    },
    blum_blum_shub: {
      name: 'Blum Blum Shub (BBS)',
      tag: 'Criptoseguro (Primos Blum)',
      formula: 'X_{i+1} = (X_i)² mod (p × q)   |   b_i = X_{i+1} mod 2'
    }
  };

  // Valores predeterminados por método
  const defaultParams = {
    congruencial_mixto: { X0: 123, a: 101, c: 457, m: 1024, n: 50 },
    congruencial_multiplicativo: { X0: 31, a: 19, m: 1024, n: 50 },
    cuadrados_medios: { D: 4, X0: 5735, n: 30 },
    productos_medios: { D: 4, X0: 5015, X1: 5934, n: 30 },
    blum_blum_shub: { p: 499, q: 503, s: 8923, n: 50 }
  };

  // DOM Helpers
  function getEl(id) {
    return document.getElementById(id);
  }

  function safeInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isFinite(n) ? n : fallback;
  }

  function safeSetText(id, text) {
    const el = typeof id === 'string' ? getEl(id) : id;
    if (el) el.textContent = text;
  }

  // Inicialización
  function init() {
    setupEventListeners();
    initDistributions();
    setMethod('congruencial_mixto');
  }

  // Configuración de Event Listeners
  function setupEventListeners() {
    // Selector de métodos (Pill tabs)
    document.querySelectorAll('.method-tab-btn').forEach(tab => {
      tab.addEventListener('click', () => {
        const method = tab.getAttribute('data-method');
        setMethod(method);
      });
    });

    // Selector de caso para GCM (Potencia de 2 vs Primo)
    document.querySelectorAll('.case-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.case-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        state.gcmCaseType = pill.getAttribute('data-case') || 'pow2';
        triggerLiveValidation();
      });
    });

    // Botón Generar
    const btnGen = getEl('btn-generate');
    if (btnGen) btnGen.addEventListener('click', generateNumbers);

    // Botón Parámetros Aleatorios Óptimos
    const btnRand = getEl('btn-random-optimal');
    if (btnRand) btnRand.addEventListener('click', loadRandomOptimalParams);

    // Botones de Restablecer
    const btnReset = getEl('btn-reset-form');
    if (btnReset) btnReset.addEventListener('click', resetToDefaultParams);

    const btnQuickReset = getEl('btn-quick-reset');
    if (btnQuickReset) btnQuickReset.addEventListener('click', resetToDefaultParams);

    // Botón Exportar Excel
    const btnExp = getEl('btn-export-excel');
    if (btnExp) btnExp.addEventListener('click', exportExcel);

    // Botón Copiar Flujo Binario
    const btnCopyBits = getEl('btn-copy-bitstream');
    if (btnCopyBits) {
      btnCopyBits.addEventListener('click', () => {
        const bitsContent = getEl('bbs-bitstream-content')?.textContent?.trim();
        if (bitsContent) {
          navigator.clipboard.writeText(bitsContent)
            .then(() => showToast('Flujo binario copiado al portapapeles', 'success'))
            .catch(() => showToast('No se pudo copiar automáticamente', 'error'));
        }
      });
    }

    // Selector de Nivel de Significancia (alpha) para las Pruebas Estadisticas
    const inputAlpha = getEl('input-alpha');
    const inputAlphaCustom = getEl('input-alpha-custom');
    if (inputAlpha) {
      inputAlpha.addEventListener('change', () => {
        if (inputAlphaCustom) {
          inputAlphaCustom.style.display = inputAlpha.value === 'custom' ? 'block' : 'none';
        }
        updateAlphaAndRetest();
      });
    }
    if (inputAlphaCustom) {
      inputAlphaCustom.addEventListener('input', () => updateAlphaAndRetest());
    }

    // Pestañas de Visualización (Scatter / Tabla / Bitstream)
    document.querySelectorAll('.viz-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const vizId = btn.getAttribute('data-viz');
        setVizTab(vizId);
      });
    });
  }

  // Cambio de Método Activo
  function setMethod(methodKey) {
    state.currentMethod = methodKey;

    // Actualizar tabs visualmente
    document.querySelectorAll('.method-tab-btn').forEach(tab => {
      if (tab.getAttribute('data-method') === methodKey) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    // Actualizar Context Card de algoritmo
    const meta = methodMetadata[methodKey] || {};
    safeSetText('algo-context-name', meta.name || 'Generador');
    safeSetText('algo-context-tag', meta.tag || 'Algoritmo');
    safeSetText('algo-context-formula', meta.formula || '');

    // Mostrar/ocultar pestaña de Bitstream para BBS
    const btnBbs = getEl('btn-viz-bitstream');
    if (btnBbs) {
      if (methodKey === 'blum_blum_shub') {
        btnBbs.style.display = 'inline-flex';
      } else {
        btnBbs.style.display = 'none';
        const bitstreamPanel = getEl('panel-viz-bitstream');
        if (bitstreamPanel && bitstreamPanel.classList.contains('active')) {
          setVizTab('scatter');
        }
      }
    }

    // Mostrar u ocultar selector de caso para GCM
    const isGCM = methodKey === 'congruencial_multiplicativo';
    const caseSelector = getEl('gcm-case-selector');
    if (caseSelector) caseSelector.style.display = isGCM ? 'flex' : 'none';

    // Renderizar inputs dinámicos del método
    renderFormInputs(methodKey);

    // Cargar parámetros por defecto y generar secuencia inicial
    resetToDefaultParams();
  }

  // Renderizado de Inputs Dinámicos
  function renderFormInputs(method) {
    let html = '';

    if (method === 'congruencial_mixto') {
      html = `
        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">X₀</span> Semilla:</label>
            <span class="input-helper-badge">0 ≤ X₀ &lt; m</span>
          </div>
          <input type="number" id="input-X0" class="custom-input" value="123" min="0">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">a</span> Multiplicador:</label>
            <span class="input-helper-badge">1 &lt; a &lt; m</span>
          </div>
          <input type="number" id="input-a" class="custom-input" value="101" min="2">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">c</span> Incremento:</label>
            <span class="input-helper-badge">1 ≤ c &lt; m</span>
          </div>
          <input type="number" id="input-c" class="custom-input" value="457" min="1">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">m</span> Módulo:</label>
            <span class="input-helper-badge">m &gt; X₀, a, c</span>
          </div>
          <input type="number" id="input-m" class="custom-input" value="1024" min="2">
        </div>

        <div class="input-group full-width">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">n</span> Iteraciones a Generar:</label>
            <span class="input-helper-badge">Cantidad de valores</span>
          </div>
          <input type="number" id="input-n" class="custom-input" value="50" min="5" max="1000">
        </div>
      `;
    } else if (method === 'congruencial_multiplicativo') {
      html = `
        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">X₀</span> Semilla:</label>
            <span class="input-helper-badge">Impar, mcd(X₀,m)=1</span>
          </div>
          <input type="number" id="input-X0" class="custom-input" value="31" min="1">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">a</span> Multiplicador:</label>
            <span class="input-helper-badge">1 &lt; a &lt; m</span>
          </div>
          <input type="number" id="input-a" class="custom-input" value="19" min="2">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">m</span> Módulo:</label>
            <span class="input-helper-badge">Primo o 2ᵍ</span>
          </div>
          <input type="number" id="input-m" class="custom-input" value="1024" min="2">
        </div>

        <div class="input-group full-width">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">n</span> Iteraciones a Generar:</label>
            <span class="input-helper-badge">Cantidad de valores</span>
          </div>
          <input type="number" id="input-n" class="custom-input" value="50" min="5" max="1000">
        </div>
      `;
    } else if (method === 'cuadrados_medios') {
      html = `
        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">D</span> Dígitos (D):</label>
            <span class="input-helper-badge">Par (4, 6, 8)</span>
          </div>
          <select id="input-D" class="custom-select">
            <option value="4" selected>D = 4 cifras</option>
            <option value="6">D = 6 cifras</option>
            <option value="8">D = 8 cifras</option>
          </select>
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">X₀</span> Semilla Inicial:</label>
            <span class="input-helper-badge">D dígitos</span>
          </div>
          <input type="number" id="input-X0" class="custom-input" value="5735" min="1000" max="9999">
        </div>

        <div class="input-group full-width">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">n</span> Iteraciones a Generar:</label>
            <span class="input-helper-badge">Cantidad</span>
          </div>
          <input type="number" id="input-n" class="custom-input" value="30" min="5" max="500">
        </div>
      `;
    } else if (method === 'productos_medios') {
      html = `
        <div class="input-group full-width">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">D</span> Dígitos (D):</label>
            <span class="input-helper-badge">Par (4, 6, 8)</span>
          </div>
          <select id="input-D" class="custom-select">
            <option value="4" selected>D = 4 cifras</option>
            <option value="6">D = 6 cifras</option>
            <option value="8">D = 8 cifras</option>
          </select>
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">X₀</span> Semilla 1:</label>
            <span class="input-helper-badge">D dígitos</span>
          </div>
          <input type="number" id="input-X0" class="custom-input" value="5015" min="1000" max="9999">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">X₁</span> Semilla 2:</label>
            <span class="input-helper-badge">D dígitos, X₁ ≠ X₀</span>
          </div>
          <input type="number" id="input-X1" class="custom-input" value="5934" min="1000" max="9999">
        </div>

        <div class="input-group full-width">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">n</span> Iteraciones a Generar:</label>
            <span class="input-helper-badge">Cantidad</span>
          </div>
          <input type="number" id="input-n" class="custom-input" value="30" min="5" max="500">
        </div>
      `;
    } else if (method === 'blum_blum_shub') {
      html = `
        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">p</span> Primo Blum 1:</label>
            <span class="input-helper-badge">p ≡ 3 mod 4</span>
          </div>
          <input type="number" id="input-p" class="custom-input" value="499" min="3">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">q</span> Primo Blum 2:</label>
            <span class="input-helper-badge">q ≡ 3 mod 4</span>
          </div>
          <input type="number" id="input-q" class="custom-input" value="503" min="3">
        </div>

        <div class="input-group">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">s</span> Semilla (s):</label>
            <span class="input-helper-badge">mcd(s, p×q)=1</span>
          </div>
          <input type="number" id="input-s" class="custom-input" value="8923" min="2">
        </div>

        <div class="input-group full-width">
          <div class="input-label-row">
            <label class="input-label"><span class="input-var-symbol">n</span> Longitud de Secuencia:</label>
            <span class="input-helper-badge">Cantidad de bits</span>
          </div>
          <input type="number" id="input-n" class="custom-input" value="50" min="10" max="500">
        </div>
      `;
    }

    const container = getEl('dynamic-inputs-container');
    if (container) {
      container.innerHTML = html;

      // Eventos de validación en vivo para inputs
      container.querySelectorAll('input, select').forEach(inp => {
        inp.addEventListener('input', triggerLiveValidation);
        inp.addEventListener('change', triggerLiveValidation);
      });

      // Listener especial para cambios de dígitos D
      const selectD = getEl('input-D');
      if (selectD) {
        selectD.addEventListener('change', (e) => {
          const dVal = parseInt(e.target.value);
          const minVal = Math.pow(10, dVal - 1);
          const maxVal = Math.pow(10, dVal) - 1;
          const inpX0 = getEl('input-X0');
          const inpX1 = getEl('input-X1');
          if (inpX0) {
            inpX0.min = minVal;
            inpX0.max = maxVal;
            if (parseInt(inpX0.value) < minVal || parseInt(inpX0.value) > maxVal) {
              inpX0.value = minVal + 123;
            }
          }
          if (inpX1) {
            inpX1.min = minVal;
            inpX1.max = maxVal;
            if (parseInt(inpX1.value) < minVal || parseInt(inpX1.value) > maxVal) {
              inpX1.value = minVal + 456;
            }
          }
          triggerLiveValidation();
        });
      }
    }
  }

  // Restablecer parámetros iniciales
  function resetToDefaultParams() {
    const params = defaultParams[state.currentMethod] || {};
    applyParamsToInputs(params);
  }

  // Aplicar objeto de parámetros a los inputs del formulario
  function applyParamsToInputs(params) {
    if (!params) return;
    for (const [key, val] of Object.entries(params)) {
      const input = getEl(`input-${key}`);
      if (input) {
        input.value = val;
      }
    }
    triggerLiveValidation();
    generateNumbers();
  }

  // Obtener parámetros numéricos del formulario
  function getFormParams() {
    const method = state.currentMethod;
    const params = {};

    if (method === 'congruencial_mixto') {
      params.X0 = safeInt(getEl('input-X0')?.value, 0);
      params.a = safeInt(getEl('input-a')?.value, 1);
      params.c = safeInt(getEl('input-c')?.value, 1);
      params.m = safeInt(getEl('input-m')?.value, 1);
      params.n = safeInt(getEl('input-n')?.value, 50);
    } else if (method === 'congruencial_multiplicativo') {
      params.X0 = safeInt(getEl('input-X0')?.value, 1);
      params.a = safeInt(getEl('input-a')?.value, 1);
      params.m = safeInt(getEl('input-m')?.value, 1);
      params.n = safeInt(getEl('input-n')?.value, 50);
    } else if (method === 'cuadrados_medios') {
      params.D = safeInt(getEl('input-D')?.value, 4);
      params.X0 = safeInt(getEl('input-X0')?.value, 1000);
      params.n = safeInt(getEl('input-n')?.value, 30);
    } else if (method === 'productos_medios') {
      params.D = safeInt(getEl('input-D')?.value, 4);
      params.X0 = safeInt(getEl('input-X0')?.value, 1000);
      params.X1 = safeInt(getEl('input-X1')?.value, 1001);
      params.n = safeInt(getEl('input-n')?.value, 30);
    } else if (method === 'blum_blum_shub') {
      params.p = safeInt(getEl('input-p')?.value, 499);
      params.q = safeInt(getEl('input-q')?.value, 503);
      params.s = safeInt(getEl('input-s')?.value, 8923);
      params.n = safeInt(getEl('input-n')?.value, 50);
    }

    return params;
  }

  // Validación en tiempo real (Debounced)
  let validationDebounceTimer = null;
  function triggerLiveValidation() {
    clearTimeout(validationDebounceTimer);
    validationDebounceTimer = setTimeout(async () => {
      const params = getFormParams();
      try {
        const response = await fetch('/api/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ method: state.currentMethod, params })
        });
        if (response.ok) {
          const valData = await response.json();
          renderChecklist(valData);
        }
      } catch (err) {
        console.warn('Error en validación:', err);
      }
    }, 100);
  }

  // Renderizar Diagnóstico Teórico (Checklist)
  function renderChecklist(valData) {
    const container = getEl('theorem-checklist-items');
    if (!container) return;

    container.innerHTML = '';
    const method = state.currentMethod;

    if (!valData.valid) {
      (valData.errors || ['Parámetros incompletos']).forEach(err => {
        const row = document.createElement('div');
        row.className = 'checklist-item';
        row.innerHTML = `<i class="fa-solid fa-circle-xmark fail"></i> <span>${err}</span>`;
        container.appendChild(row);
      });
      return;
    }

    if (method === 'congruencial_mixto') {
      const hd = valData.hull_dobell || {};
      const c1Icon = hd.c1 ? 'fa-circle-check pass' : 'fa-circle-xmark fail';
      const c2Icon = hd.c2 ? 'fa-circle-check pass' : 'fa-circle-xmark fail';
      const c3Icon = hd.c3 ? 'fa-circle-check pass' : 'fa-circle-xmark fail';

      container.innerHTML = `
        <div class="checklist-item">
          <i class="fa-solid ${c1Icon}"></i>
          <span>${hd.c1_msg || 'mcd(c, m) = 1 (Coprimos)'}</span>
        </div>
        <div class="checklist-item">
          <i class="fa-solid ${c2Icon}"></i>
          <span>${hd.c2_msg || 'Primos de m dividen a (a-1)'}</span>
        </div>
        <div class="checklist-item">
          <i class="fa-solid ${c3Icon}"></i>
          <span>${hd.c3_msg || 'Si 4|m entonces 4|(a-1)'}</span>
        </div>
      `;
    } else if (method === 'congruencial_multiplicativo') {
      const details = valData.details || {};
      const maxP = valData.maximal_period;
      container.innerHTML = `
        <div class="checklist-item">
          <i class="fa-solid ${maxP ? 'fa-circle-check pass' : 'fa-triangle-exclamation warn'}"></i>
          <span>${details.a_msg || 'Multiplicador válido'}</span>
        </div>
        <div class="checklist-item">
          <i class="fa-solid ${maxP ? 'fa-circle-check pass' : 'fa-triangle-exclamation warn'}"></i>
          <span>${details.x0_msg || 'Semilla válida'}</span>
        </div>
      `;
    } else if (method === 'cuadrados_medios') {
      const heur = valData.heuristics || {};
      container.innerHTML = `
        <div class="checklist-item">
          <i class="fa-solid ${heur.trailing_zeros_or_cycles ? 'fa-circle-check pass' : 'fa-triangle-exclamation warn'}"></i>
          <span>${heur.trailing_zeros_or_cycles ? 'Sin terminación degenerativa (00, 25, 50)' : 'Terminación riesgosa (00, 25, 50)'}</span>
        </div>
        <div class="checklist-item">
          <i class="fa-solid ${heur.no_internal_zero_chain ? 'fa-circle-check pass' : 'fa-triangle-exclamation warn'}"></i>
          <span>${heur.no_internal_zero_chain ? 'Sin cadenas de ceros centrales' : 'Contiene ceros consecutivos'}</span>
        </div>
      `;
    } else if (method === 'productos_medios') {
      const heur = valData.heuristics || {};
      container.innerHTML = `
        <div class="checklist-item">
          <i class="fa-solid ${heur.no_trailing_zeros ? 'fa-circle-check pass' : 'fa-triangle-exclamation warn'}"></i>
          <span>${heur.no_trailing_zeros ? 'Semillas sin ceros terminales' : 'Semillas terminan en cero'}</span>
        </div>
        <div class="checklist-item">
          <i class="fa-solid ${heur.coprime_seeds ? 'fa-circle-check pass' : 'fa-triangle-exclamation warn'}"></i>
          <span>${heur.coprime_seeds ? 'Semillas coprimas mcd(X₀, X₁)=1' : 'Semillas comparten factores comunes'}</span>
        </div>
      `;
    } else if (method === 'blum_blum_shub') {
      const details = valData.details || {};
      container.innerHTML = `
        <div class="checklist-item">
          <i class="fa-solid fa-circle-check pass"></i>
          <span>${details.p_msg || 'p primo de Blum'}</span>
        </div>
        <div class="checklist-item">
          <i class="fa-solid fa-circle-check pass"></i>
          <span>${details.q_msg || 'q primo de Blum'}</span>
        </div>
        <div class="checklist-item">
          <i class="fa-solid fa-circle-check pass"></i>
          <span>${details.s_msg || 's coprimo con M'}</span>
        </div>
      `;
    }
  }

  // Generar Parámetros Óptimos
  async function loadRandomOptimalParams() {
    try {
      let subType = 'default';
      if (state.currentMethod === 'cuadrados_medios' || state.currentMethod === 'productos_medios') {
        subType = getEl('input-D')?.value || '4';
      } else if (state.currentMethod === 'congruencial_multiplicativo') {
        subType = state.gcmCaseType || 'pow2';
      }
      const response = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: state.currentMethod, sub_type: subType })
      });
      if (response.ok) {
        const data = await response.json();
        applyParamsToInputs(data);
        showToast(data.explanation || 'Parámetros óptimos calculados según teoremas', 'success');
      }
    } catch (err) {
      showToast('Error al generar parámetros aleatorios', 'error');
    }
  }

  // Generación de la Secuencia
  async function generateNumbers() {
    const method = state.currentMethod;
    const params = getFormParams();

    const btnGen = getEl('btn-generate');
    if (btnGen) {
      btnGen.disabled = true;
      btnGen.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando...';
    }

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method, params })
      });

      const result = await response.json();
      state.lastResult = result;

      if (!result.success) {
        showToast(result.errors ? result.errors[0] : 'Error en la generación', 'error');
        return;
      }

      updateResultsUI(result);
      runStatisticalTests(result.numbers);
      runDistributionValidations(result.numbers);

    } catch (err) {
      console.error('Error al generar:', err);
      showToast('Error de conexión con el servidor', 'error');
    } finally {
      if (btnGen) {
        btnGen.disabled = false;
        btnGen.innerHTML = '<i class="fa-solid fa-bolt"></i> Generar Secuencia';
      }
    }
  }

  // Actualizar Interfaz con Resultados
  function updateResultsUI(res) {
    if (!res) return;
    const stats = res.stats || {};
    const cycle = res.cycle || {};

    safeSetText('current-results-method-name', res.method_name || 'Generador Pseudoaleatorio');
    safeSetText('current-results-summary', cycle.message || 'Secuencia calculada correctamente.');

    // KPIs
    safeSetText('kpi-count', stats.count || 0);
    safeSetText('kpi-count-sub', 'Iteraciones');

    // BBS Bitstream
    if (res.bitstream) {
      safeSetText('bbs-bitstream-content', res.bitstream);
      safeSetText('bbs-bit-balance-label', `Balance: ${stats.bit_balance || ''}`);
    }

    // Gráfica de Dispersión
    try {
      renderIndependenceScatterChart(stats.lag1_pairs || []);
    } catch (err) {
      console.error('Error al renderizar gráfica de dispersión:', err);
    }

    // Tabla de Iteraciones
    renderTable(res);
  }

  // Gráfica de Independencia y Retardo (Lag-1) con Paleta Verde y Morado
  function renderIndependenceScatterChart(pairs) {
    const canvas = getEl('chart-independence-scatter');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (state.charts.scatter) {
      state.charts.scatter.destroy();
    }

    const scatterData = pairs.map(p => ({ x: p.x, y: p.y }));

    state.charts.scatter = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Pares Consecutivos (Rᵢ, Rᵢ₊₁)',
          data: scatterData,
          backgroundColor: 'rgba(52, 211, 153, 0.88)',
          borderColor: 'rgba(168, 85, 247, 0.95)',
          borderWidth: 1.5,
          pointRadius: 4.5,
          pointHoverRadius: 7,
          pointHoverBackgroundColor: '#C084FC',
          pointHoverBorderColor: '#34D399'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        scales: {
          x: {
            min: 0,
            max: 1,
            title: {
              display: true,
              text: 'R_i (Valor Normalizado Actual)',
              font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' },
              color: '#C4B5FD'
            },
            ticks: { color: '#8B7CA8', font: { family: 'JetBrains Mono' } },
            grid: { color: 'rgba(168, 85, 247, 0.08)' }
          },
          y: {
            min: 0,
            max: 1,
            title: {
              display: true,
              text: 'R_{i+1} (Valor Normalizado Siguiente)',
              font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' },
              color: '#C4B5FD'
            },
            ticks: { color: '#8B7CA8', font: { family: 'JetBrains Mono' } },
            grid: { color: 'rgba(168, 85, 247, 0.08)' }
          }
        },
        plugins: {
          tooltip: {
            backgroundColor: 'rgba(20, 13, 38, 0.94)',
            titleFont: { family: 'Plus Jakarta Sans', weight: 'bold' },
            bodyFont: { family: 'JetBrains Mono' },
            padding: 10,
            borderColor: 'rgba(168, 85, 247, 0.3)',
            borderWidth: 1,
            callbacks: {
              label: (context) => `i=${context.dataIndex + 1}: (R_i: ${context.parsed.x.toFixed(6)}, R_i+1: ${context.parsed.y.toFixed(6)})`
            }
          },
          legend: {
            labels: {
              font: { family: 'Plus Jakarta Sans', weight: '600' },
              color: '#F3E8FF'
            }
          }
        }
      }
    });
  }

  // Exportar Excel (.xlsx) con descarga directa 100% nativa del navegador
  function exportExcel() {
    const method = state.currentMethod;
    const params = getFormParams();
    const alpha = getCurrentAlpha();
    const filename = `PRNG_${method}.xlsx`;

    const btnExp = getEl('btn-export-excel');
    if (btnExp) {
      btnExp.disabled = true;
      btnExp.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando XLSX...';
    }

    try {
      const queryParams = new URLSearchParams({ method, alpha, ...params });
      // Configuracion de la validacion de distribuciones (parametros, metodo y casos)
      if (state.distConfig) {
        queryParams.set('dist_config', JSON.stringify(state.distConfig));
      }
      const downloadUrl = `/api/download/${filename}?${queryParams.toString()}`;

      // Redirección nativa del navegador: Chrome/Edge intercepta el encabezado Content-Disposition
      // y descarga el archivo directamente como PRNG_...xlsx sin crear ningún objeto Blob en memoria
      window.location.href = downloadUrl;
      showToast(`Descargando ${filename}`, 'success');
    } catch (err) {
      console.error('Error al exportar Excel:', err);
      showToast('Error al generar archivo Excel', 'error');
    } finally {
      setTimeout(() => {
        if (btnExp) {
          btnExp.disabled = false;
          btnExp.innerHTML = '<i class="fa-solid fa-file-excel"></i> Exportar Excel (.xlsx)';
        }
      }, 1000);
    }
  }

  // Renderizar Tabla Paso a Paso
  function renderTable(res) {
    const method = res.method;
    const steps = res.steps || [];

    const thead = getEl('results-table-head');
    const tbody = getEl('results-table-body');
    if (!thead || !tbody) return;

    // Encabezados
    let headHtml = '<tr>';
    if (method === 'congruencial_mixto') {
      headHtml += '<th>i</th><th>Xᵢ₋₁</th><th>(a × Xᵢ₋₁ + c)</th><th>Xᵢ = (aXᵢ₋₁+c) mod m</th><th>Rᵢ = Xᵢ / m</th>';
    } else if (method === 'congruencial_multiplicativo') {
      headHtml += '<th>i</th><th>Xᵢ₋₁</th><th>(a × Xᵢ₋₁)</th><th>Xᵢ = (aXᵢ₋₁) mod m</th><th>Rᵢ = Xᵢ / m</th>';
    } else if (method === 'cuadrados_medios') {
      headHtml += '<th>i</th><th>Xᵢ₋₁</th><th>Yᵢ₋₁ = (Xᵢ₋₁)²</th><th>Yᵢ₋₁ (Relleno 2D)</th><th>Cifras Centrales (Xᵢ)</th><th>Rᵢ = Xᵢ / 10ᴰ</th><th>Estado</th>';
    } else if (method === 'productos_medios') {
      headHtml += '<th>i</th><th>Xᵢ₋₂</th><th>Xᵢ₋₁</th><th>Yᵢ₋₁ = Xᵢ₋₂ × Xᵢ₋₁</th><th>Yᵢ₋₁ (Relleno 2D)</th><th>Cifras Centrales (Xᵢ)</th><th>Rᵢ = Xᵢ / 10ᴰ</th>';
    } else if (method === 'blum_blum_shub') {
      headHtml += '<th>i</th><th>Xᵢ₋₁</th><th>(Xᵢ₋₁)²</th><th>Xᵢ = (Xᵢ₋₁)² mod M</th><th>Bit bᵢ (Xᵢ mod 2)</th><th>Rᵢ = Xᵢ / M</th>';
    }
    headHtml += '</tr>';
    thead.innerHTML = headHtml;

    // Filas
    let bodyHtml = '';
    steps.forEach(s => {
      const isCycle = s.is_cycle_point;
      const rowClass = isCycle ? 'cycle-row' : '';

      bodyHtml += `<tr class="${rowClass}">`;
      if (method === 'congruencial_mixto') {
        bodyHtml += `
          <td><strong>${s.i}</strong></td>
          <td class="mono">${s.Xi}</td>
          <td class="mono">${s.operation}</td>
          <td class="mono">${s.next_Xi}</td>
          <td class="ri-highlight">${s.Ri.toFixed(6)}</td>
        `;
      } else if (method === 'congruencial_multiplicativo') {
        bodyHtml += `
          <td><strong>${s.i}</strong></td>
          <td class="mono">${s.Xi}</td>
          <td class="mono">${s.operation}</td>
          <td class="mono">${s.next_Xi}</td>
          <td class="ri-highlight">${s.Ri.toFixed(6)}</td>
        `;
      } else if (method === 'cuadrados_medios') {
        bodyHtml += `
          <td><strong>${s.i}</strong></td>
          <td class="mono">${s.Xi}</td>
          <td class="mono">${s.Yi}</td>
          <td class="mono" style="letter-spacing: 1px;">${s.Yi_padded}</td>
          <td class="mono" style="color: var(--green-neon); font-weight: 700;">${s.extracted_digits}</td>
          <td class="ri-highlight">${s.Ri.toFixed(6)}</td>
          <td><span class="badge-status-${s.status === 'Normal' ? 'pass' : 'fail'}">${s.status}</span></td>
        `;
      } else if (method === 'productos_medios') {
        bodyHtml += `
          <td><strong>${s.i}</strong></td>
          <td class="mono">${s.Xi_minus_1}</td>
          <td class="mono">${s.Xi}</td>
          <td class="mono">${s.Yi}</td>
          <td class="mono" style="letter-spacing: 1px;">${s.Yi_padded}</td>
          <td class="mono" style="color: var(--green-neon); font-weight: 700;">${s.extracted_digits}</td>
          <td class="ri-highlight">${s.Ri.toFixed(6)}</td>
        `;
      } else if (method === 'blum_blum_shub') {
        bodyHtml += `
          <td><strong>${s.i}</strong></td>
          <td class="mono">${s.Xi}</td>
          <td class="mono">${s.Xi_sq}</td>
          <td class="mono">${s.next_Xi}</td>
          <td class="mono" style="text-align: center; font-weight: 800; color: var(--green-neon);">${s.bit}</td>
          <td class="ri-highlight">${s.Ri.toFixed(6)}</td>
        `;
      }
      bodyHtml += '</tr>';
    });

    tbody.innerHTML = bodyHtml;
    safeSetText('table-row-count-label', `${steps.length} iteraciones calculadas`);
  }

  // Pestañas de Visualización
  function setVizTab(vizId) {
    document.querySelectorAll('.viz-tab-btn').forEach(btn => {
      if (btn.getAttribute('data-viz') === vizId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    document.querySelectorAll('.tab-content-panel').forEach(panel => {
      if (panel.id === `panel-viz-${vizId}`) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });
  }

  // Notificaciones Toast
  function showToast(message, type = 'info') {
    const container = getEl('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'fa-circle-check' : (type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info');
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = '0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  // =========================================================================
  // PRUEBAS ESTADISTICAS DE ALEATORIEDAD (7 pruebas)
  // =========================================================================

  function getCurrentAlpha() {
    const sel = getEl('input-alpha');
    if (!sel) return 0.05;
    if (sel.value === 'custom') {
      const custom = getEl('input-alpha-custom');
      let pct = parseFloat(custom ? custom.value : NaN);
      if (!Number.isFinite(pct) || pct <= 0 || pct >= 100) pct = 5;
      return pct / 100;
    }
    const val = parseFloat(sel.value);
    return Number.isFinite(val) ? val : 0.05;
  }

  let alphaDebounceTimer = null;
  function updateAlphaAndRetest() {
    state.alpha = getCurrentAlpha();
    clearTimeout(alphaDebounceTimer);
    alphaDebounceTimer = setTimeout(() => {
      if (state.lastResult && state.lastResult.numbers && state.lastResult.numbers.length) {
        runStatisticalTests(state.lastResult.numbers);
        runDistributionValidations(state.lastResult.numbers);
      }
    }, 250);
  }

  async function runStatisticalTests(numbers) {
    const summaryEl = getEl('tests-summary-card');
    if (!numbers || !numbers.length) return;

    state.alpha = getCurrentAlpha();

    if (summaryEl) {
      summaryEl.innerHTML = '<div class="tests-loading"><i class="fa-solid fa-spinner fa-spin"></i> Calculando las 7 pruebas estadísticas...</div>';
    }

    try {
      const response = await fetch('/api/tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numbers, alpha: state.alpha })
      });
      const data = await response.json();
      state.lastTests = data;

      if (!data.success) {
        renderTestsError((data.errors && data.errors[0]) || 'No se pudieron calcular las pruebas estadísticas.');
        return;
      }

      renderTestsSummary(data);
      renderTestsSelector(data.tests);

      const stillExists = data.tests.some(t => t.id === state.selectedTestId);
      const selected = stillExists ? data.tests.find(t => t.id === state.selectedTestId) : data.tests[0];
      state.selectedTestId = selected.id;
      renderTestDetail(selected);

    } catch (err) {
      console.error('Error al ejecutar pruebas estadísticas:', err);
      renderTestsError('Error de conexión con el servidor al calcular las pruebas.');
    }
  }

  function renderTestsError(message) {
    const summaryEl = getEl('tests-summary-card');
    if (summaryEl) {
      summaryEl.innerHTML = `<div class="tests-error-banner"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(message)}</div>`;
    }
    const selectorEl = getEl('tests-selector-row');
    if (selectorEl) selectorEl.innerHTML = '';
    const detailEl = getEl('test-detail-panel');
    if (detailEl) detailEl.innerHTML = '';
  }

  function renderTestsSummary(data) {
    const el = getEl('tests-summary-card');
    if (!el) return;
    const s = data.summary || {};

    let verdictClass = 'verdict-fail';
    let verdictIcon = 'fa-circle-xmark';
    if (s.verdict === 'ALEATORIO') {
      verdictClass = 'verdict-pass';
      verdictIcon = 'fa-circle-check';
    } else if (s.verdict === 'ALEATORIO_CON_RESERVAS') {
      verdictClass = 'verdict-warn';
      verdictIcon = 'fa-triangle-exclamation';
    }

    el.innerHTML = `
      <div class="tests-verdict-box ${verdictClass}">
        <div class="tests-verdict-icon"><i class="fa-solid ${verdictIcon}"></i></div>
        <div class="tests-verdict-meta">
          <div class="tests-verdict-ratio">${s.passed} <span>/ ${s.total} pruebas superadas</span></div>
          <div class="tests-verdict-text">${escapeHtml(s.verdict_label || '')}</div>
        </div>
        <div class="tests-verdict-alpha">
          <span class="tests-verdict-alpha-label">Significancia</span>
          <span class="tests-verdict-alpha-value">α = ${(data.alpha * 100).toFixed(2)}%</span>
        </div>
      </div>
    `;
  }

  function renderTestsSelector(tests) {
    const el = getEl('tests-selector-row');
    if (!el) return;
    el.innerHTML = '';

    tests.slice().sort((a, b) => a.order - b.order).forEach(t => {
      const btn = document.createElement('button');
      btn.type = 'button';
      const isActive = t.id === state.selectedTestId;
      btn.className = `test-pill test-pill-${t.status}` + (isActive ? ' active' : '');
      const icon = t.status === 'pass' ? 'fa-circle-check' : (t.status === 'fail' ? 'fa-circle-xmark' : 'fa-circle-question');
      const shortName = TEST_SHORT_NAMES[t.id] || t.name;
      btn.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${t.order}. ${escapeHtml(shortName)}</span>`;
      btn.addEventListener('click', () => {
        state.selectedTestId = t.id;
        document.querySelectorAll('.test-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        renderTestDetail(t);
      });
      el.appendChild(btn);
    });
  }

  function renderTestDetail(test) {
    const el = getEl('test-detail-panel');
    if (!el || !test) return;

    if (test.status === 'inconclusive') {
      el.innerHTML = `
        <div class="test-detail-header">
          <h4>${test.order}. ${escapeHtml(test.name)}</h4>
        </div>
        <p class="test-detail-objective">${escapeHtml(test.objective)}</p>
        <div class="test-inconclusive-banner">
          <i class="fa-solid fa-circle-question"></i>
          <span>${escapeHtml(test.conclusion)}</span>
        </div>
      `;
      return;
    }

    const passed = test.status === 'pass';

    const statBlock = `
      <div class="test-stat-compare">
        <div class="test-stat-box">
          <span class="test-stat-label">${escapeHtml(test.statistic_label || 'Estadístico')}</span>
          <span class="test-stat-value">${formatNum(test.statistic)}</span>
        </div>
        <div class="test-stat-vs">vs</div>
        <div class="test-stat-box">
          <span class="test-stat-label">${escapeHtml(test.critical_label || 'Valor Crítico')}</span>
          <span class="test-stat-value">${formatNum(test.critical_value)}</span>
        </div>
        <div class="test-stat-verdict ${passed ? 'pass' : 'fail'}">
          <i class="fa-solid ${passed ? 'fa-circle-check' : 'fa-circle-xmark'}"></i>
          ${passed ? 'Se acepta H₀' : 'Se rechaza H₀'}
        </div>
      </div>
    `;

    const stepsHtml = (test.steps || []).map((s, idx) => `
        <div class="test-step-row">
          <div class="test-step-num">${idx + 1}</div>
          <div class="test-step-body">
            <div class="test-step-label">${escapeHtml(s.label)}</div>
            <div class="test-step-formula">${escapeHtml(s.formula)}</div>
            <div class="test-step-result">${escapeHtml(s.result)}</div>
          </div>
        </div>
    `).join('');

    const notesHtml = (test.notes && test.notes.length) ? `
        <div class="test-notes-box">
          <i class="fa-solid fa-circle-info"></i>
          <ul>${test.notes.map(n => `<li>${escapeHtml(n)}</li>`).join('')}</ul>
        </div>
    ` : '';

    const dataTableHtml = renderTestDataTable(test.data_table, 'Datos y cálculos');
    const sampleTableHtml = test.sample_table ? renderTestDataTable(test.sample_table, 'Clasificación de cada valor (muestra)') : '';

    el.innerHTML = `
      <div class="test-detail-header">
        <h4>${test.order}. ${escapeHtml(test.name)}</h4>
      </div>
      <p class="test-detail-objective">${escapeHtml(test.objective)}</p>
      ${statBlock}
      <div class="test-decision-rule"><strong>Regla de decisión:</strong> ${escapeHtml(test.decision_rule || '')}</div>
      <div class="test-conclusion-box ${passed ? 'pass' : 'fail'}">${escapeHtml(test.conclusion)}</div>
      <div class="test-steps-list">${stepsHtml}</div>
      ${notesHtml}
      ${dataTableHtml}
      ${sampleTableHtml}
    `;
  }

  function renderTestDataTable(table, title) {
    if (!table || !table.columns || table.columns.length === 0 || !table.rows || table.rows.length === 0) return '';
    const bodyRows = table.rows.map(r => {
      const vals = Object.values(r);
      return `<tr>${vals.map(v => `<td class="mono">${formatCell(v)}</td>`).join('')}</tr>`;
    }).join('');
    const truncNote = table.truncated
      ? `<p class="test-table-trunc-note">Mostrando ${table.rows.length} de ${table.total_rows} filas.</p>`
      : '';
    return `
      <div class="test-data-table-wrapper">
        <h5>${escapeHtml(title)}</h5>
        <div class="table-wrapper-studio">
          <table class="custom-table-studio">
            <thead><tr>${table.columns.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr></thead>
            <tbody>${bodyRows}</tbody>
          </table>
        </div>
        ${truncNote}
      </div>
    `;
  }

  function formatCell(v) {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'number') {
      return Number.isInteger(v) ? String(v) : v.toFixed(6).replace(/0+$/, '').replace(/\.$/, '');
    }
    return escapeHtml(String(v));
  }

  function formatNum(v) {
    if (v === null || v === undefined) return '—';
    return String(v);
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  // =========================================================================
  // VALIDACION DE LAS CONVERSIONES ESTADISTICAS (5 distribuciones)
  // Paso 1: rᵢ generados → Paso 2: conversión → Paso 3: conteo (menor que /
  // mayor que / entre a y b) → Paso 4: comparación con la probabilidad teórica.
  // =========================================================================

  const DIST_ORDER = ['uniforme', 'normal', 'erlang', 'poisson', 'binomial'];

  // Debe coincidir con DEFAULT_CONFIG de core/distributions.py
  const DIST_DEFAULTS = {
    uniforme: { method: 'inversa', params: { a: 5, b: 15 },
      cases: { menor: { op: '<', x: 8 }, mayor: { op: '>', x: 12 }, rango: { a: 7, b: 11 } } },
    normal: { method: 'inversa', params: { mu: 50, sigma: 10 },
      cases: { menor: { op: '<', x: 45 }, mayor: { op: '>', x: 60 }, rango: { a: 40, b: 55 } } },
    erlang: { method: 'inversa', params: { k: 3, lam: 0.5 },
      cases: { menor: { op: '<', x: 4 }, mayor: { op: '>', x: 8 }, rango: { a: 3, b: 7 } } },
    poisson: { method: 'inversa', params: { lam: 4 },
      cases: { menor: { op: '<', x: 3 }, mayor: { op: '>', x: 5 }, rango: { a: 2, b: 6 } } },
    binomial: { method: 'inversa', params: { n: 10, p: 0.3 },
      cases: { menor: { op: '<', x: 3 }, mayor: { op: '>', x: 4 }, rango: { a: 2, b: 5 } } }
  };

  const DIST_UI = {
    uniforme: {
      short: 'Uniforme (A, B)', icon: 'fa-grip-lines',
      params: [
        { key: 'a', sym: 'A', label: 'Límite inferior', hint: 'A < B', step: 'any' },
        { key: 'b', sym: 'B', label: 'Límite superior', hint: 'B > A', step: 'any' }
      ],
      methods: [{ id: 'inversa', label: 'Transformada inversa', formula: 'x = A + (B − A)·r' }]
    },
    normal: {
      short: 'Normal (μ, σ)', icon: 'fa-bell',
      params: [
        { key: 'mu', sym: 'μ', label: 'Media', hint: 'cualquier real', step: 'any' },
        { key: 'sigma', sym: 'σ', label: 'Desviación estándar', hint: 'σ > 0', step: 'any', min: 0 }
      ],
      methods: [
        { id: 'inversa', label: 'Transformada inversa', formula: 'x = μ + σ·Φ⁻¹(r)' },
        { id: 'tlc', label: 'Suma de 12 rᵢ (TLC)', formula: 'x = μ + σ·(Σ₁¹² rⱼ − 6)' }
      ]
    },
    erlang: {
      short: 'Erlang (k, λ)', icon: 'fa-hourglass-half',
      params: [
        { key: 'k', sym: 'k', label: 'Fases (forma)', hint: 'entero 1–50', step: 1, min: 1 },
        { key: 'lam', sym: 'λ', label: 'Tasa de cada fase', hint: 'λ > 0 · media = k/λ', step: 'any', min: 0 }
      ],
      methods: [
        { id: 'inversa', label: 'Transformada inversa', formula: 'x = F⁻¹(r)' },
        { id: 'convolucion', label: 'Producto de k rᵢ', formula: 'x = −(1/λ)·ln(Π rⱼ)' }
      ]
    },
    poisson: {
      short: 'Poisson (λ)', icon: 'fa-chart-column',
      params: [
        { key: 'lam', sym: 'λ', label: 'Tasa media', hint: '0 < λ ≤ 100', step: 'any', min: 0 }
      ],
      methods: [
        { id: 'inversa', label: 'Transformada inversa', formula: 'F(x−1) ≤ r < F(x)' },
        { id: 'multiplicativo', label: 'Multiplicativo', formula: 'Π rⱼ < e^(−λ)' }
      ]
    },
    binomial: {
      short: 'Binomial (n, p)', icon: 'fa-coins',
      params: [
        { key: 'n', sym: 'n', label: 'Ensayos', hint: 'entero 1–200', step: 1, min: 1 },
        { key: 'p', sym: 'p', label: 'Probabilidad de éxito', hint: '0 < p < 1', step: 0.01, min: 0, max: 1 }
      ],
      methods: [
        { id: 'inversa', label: 'Transformada inversa', formula: 'F(x−1) ≤ r < F(x)' },
        { id: 'bernoulli', label: 'Suma de Bernoullis', formula: 'x = #{rⱼ < p}' }
      ]
    }
  };

  function cloneDeep(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function initDistributions() {
    state.distConfig = cloneDeep(DIST_DEFAULTS);
    renderDistSelector(null);
    renderDistConfig();
  }

  let distDebounceTimer = null;
  function scheduleDistValidation() {
    clearTimeout(distDebounceTimer);
    distDebounceTimer = setTimeout(() => {
      if (state.lastResult && state.lastResult.numbers && state.lastResult.numbers.length) {
        runDistributionValidations(state.lastResult.numbers);
      }
    }, 350);
  }

  let distRequestSeq = 0;
  async function runDistributionValidations(numbers) {
    if (!numbers || !numbers.length) return;
    const seq = ++distRequestSeq;
    const summaryEl = getEl('dists-summary-card');
    if (summaryEl && !state.lastDists) {
      summaryEl.innerHTML = '<div class="tests-loading"><i class="fa-solid fa-spinner fa-spin"></i> Convirtiendo y validando las 5 distribuciones...</div>';
    }

    try {
      const response = await fetch('/api/distributions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numbers, alpha: getCurrentAlpha(), config: state.distConfig })
      });
      const data = await response.json();
      if (seq !== distRequestSeq) return; // llegó una respuesta más nueva

      if (!data.success) {
        state.lastDists = null;
        renderDistsError((data.errors && data.errors[0]) || 'No se pudieron validar las conversiones.');
        return;
      }
      state.lastDists = data;
      renderDistsSummary(data);
      renderDistSelector(data.distributions);
      const selected = data.distributions.find(d => d.id === state.selectedDistId) || data.distributions[0];
      state.selectedDistId = selected.id;
      renderDistDetail(selected, data);
    } catch (err) {
      console.error('Error al validar distribuciones:', err);
      if (seq === distRequestSeq) renderDistsError('Error de conexión con el servidor al validar las distribuciones.');
    }
  }

  function renderDistsError(message) {
    const summaryEl = getEl('dists-summary-card');
    if (summaryEl) {
      summaryEl.innerHTML = `<div class="tests-error-banner"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(message)}</div>`;
    }
    const detailEl = getEl('dist-detail-panel');
    if (detailEl) detailEl.innerHTML = '';
  }

  function renderDistsSummary(data) {
    const el = getEl('dists-summary-card');
    if (!el) return;
    const s = data.summary || {};
    let verdictClass = 'verdict-fail';
    let verdictIcon = 'fa-circle-xmark';
    if (s.verdict === 'VALIDADO') {
      verdictClass = 'verdict-pass';
      verdictIcon = 'fa-circle-check';
    } else if (s.verdict === 'PARCIAL') {
      verdictClass = 'verdict-warn';
      verdictIcon = 'fa-triangle-exclamation';
    }
    el.innerHTML = `
      <div class="tests-verdict-box ${verdictClass}">
        <div class="tests-verdict-icon"><i class="fa-solid ${verdictIcon}"></i></div>
        <div class="tests-verdict-meta">
          <div class="tests-verdict-ratio">${s.passed} <span>/ ${s.total} conversiones validadas</span></div>
          <div class="tests-verdict-text">${escapeHtml(s.verdict_label || '')}</div>
        </div>
        <div class="tests-verdict-alpha">
          <span class="tests-verdict-alpha-label">rᵢ usados · Significancia</span>
          <span class="tests-verdict-alpha-value">N = ${data.n_r} · α = ${(data.alpha * 100).toFixed(2)}%</span>
        </div>
      </div>
    `;
  }

  function renderDistSelector(dists) {
    const el = getEl('dists-selector-row');
    if (!el) return;
    el.innerHTML = '';
    const byId = {};
    (dists || []).forEach(d => { byId[d.id] = d; });

    DIST_ORDER.forEach((id, idx) => {
      const d = byId[id];
      const status = d ? d.status : 'pending';
      const icon = status === 'pass' ? 'fa-circle-check'
        : (status === 'fail' ? 'fa-circle-xmark'
          : (status === 'pending' ? 'fa-circle-notch' : 'fa-circle-question'));
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `test-pill test-pill-${status}` + (id === state.selectedDistId ? ' active' : '');
      const cases = d && d.cases && d.cases.length ? ` <span class="dist-pill-count">${d.cases_passed}/${d.cases.length}</span>` : '';
      btn.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${idx + 1}. ${escapeHtml(DIST_UI[id].short)}</span>${cases}`;
      btn.addEventListener('click', () => {
        state.selectedDistId = id;
        document.querySelectorAll('#dists-selector-row .test-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        renderDistConfig();
        const current = state.lastDists && state.lastDists.distributions.find(x => x.id === id);
        if (current) renderDistDetail(current, state.lastDists);
      });
      el.appendChild(btn);
    });
  }

  function opSymbol(op) {
    return { '<': '<', '<=': '≤', '>': '>', '>=': '≥' }[op] || op;
  }

  // Panel de configuración de la distribución seleccionada (se re-dibuja solo al
  // cambiar de distribución, para no perder el foco mientras se escribe)
  function renderDistConfig() {
    const el = getEl('dist-config-card');
    if (!el || !state.distConfig) return;
    const id = state.selectedDistId;
    const ui = DIST_UI[id];
    const cfg = state.distConfig[id];

    const paramsHtml = ui.params.map(pm => `
      <div class="input-group">
        <div class="input-label-row">
          <label class="input-label" for="dist-param-${pm.key}"><span class="input-var-symbol">${pm.sym}</span> ${pm.label}:</label>
          <span class="input-helper-badge">${pm.hint}</span>
        </div>
        <input type="number" id="dist-param-${pm.key}" class="custom-input" data-dist-param="${pm.key}"
               value="${cfg.params[pm.key]}" step="${pm.step}" ${pm.min !== undefined ? `min="${pm.min}"` : ''} ${pm.max !== undefined ? `max="${pm.max}"` : ''}>
      </div>
    `).join('');

    const methodsHtml = ui.methods.map(m => `
      <button type="button" class="case-pill dist-method-pill ${cfg.method === m.id ? 'active' : ''}" data-dist-method="${m.id}" title="${escapeHtml(m.formula)}">
        <span class="dist-method-name">${escapeHtml(m.label)}</span>
        <span class="dist-method-formula">${escapeHtml(m.formula)}</span>
      </button>
    `).join('');

    const c = cfg.cases;
    el.innerHTML = `
      <div class="dist-config-grid">
        <div class="dist-config-block">
          <div class="dist-config-title"><i class="fa-solid fa-sliders"></i> Parámetros de la distribución</div>
          <div class="dist-params-grid">${paramsHtml}</div>
          <div class="dist-config-title dist-config-title-sub"><i class="fa-solid fa-right-left"></i> Fórmula de conversión (Paso 2)</div>
          <div class="case-pill-group dist-method-group">${methodsHtml}</div>
        </div>
        <div class="dist-config-block">
          <div class="dist-config-title"><i class="fa-solid fa-filter"></i> Casos a validar (Paso 3: conteo)</div>
          <div class="dist-case-inputs">
            <div class="dist-case-input-row">
              <span class="dist-case-tag">Menor que</span>
              <span class="dist-case-x">P(X</span>
              <select class="custom-select dist-op-select" data-dist-case="menor" data-dist-field="op" aria-label="Operador menor que">
                <option value="<" ${c.menor.op === '<' ? 'selected' : ''}>&lt;</option>
                <option value="<=" ${c.menor.op === '<=' ? 'selected' : ''}>≤</option>
              </select>
              <input type="number" class="custom-input dist-case-num" data-dist-case="menor" data-dist-field="x" value="${c.menor.x}" step="any" aria-label="Valor x del caso menor que">
              <span class="dist-case-x">)</span>
            </div>
            <div class="dist-case-input-row">
              <span class="dist-case-tag">Mayor que</span>
              <span class="dist-case-x">P(X</span>
              <select class="custom-select dist-op-select" data-dist-case="mayor" data-dist-field="op" aria-label="Operador mayor que">
                <option value=">" ${c.mayor.op === '>' ? 'selected' : ''}>&gt;</option>
                <option value=">=" ${c.mayor.op === '>=' ? 'selected' : ''}>≥</option>
              </select>
              <input type="number" class="custom-input dist-case-num" data-dist-case="mayor" data-dist-field="x" value="${c.mayor.x}" step="any" aria-label="Valor x del caso mayor que">
              <span class="dist-case-x">)</span>
            </div>
            <div class="dist-case-input-row">
              <span class="dist-case-tag">Rango</span>
              <span class="dist-case-x">P(</span>
              <input type="number" class="custom-input dist-case-num" data-dist-case="rango" data-dist-field="a" value="${c.rango.a}" step="any" aria-label="Límite a del rango">
              <span class="dist-case-x">≤ X ≤</span>
              <input type="number" class="custom-input dist-case-num" data-dist-case="rango" data-dist-field="b" value="${c.rango.b}" step="any" aria-label="Límite b del rango">
              <span class="dist-case-x">)</span>
            </div>
          </div>
          <button type="button" class="panel-action-link dist-reset-link" id="btn-dist-reset">
            <i class="fa-solid fa-rotate-left"></i> Valores por defecto de esta distribución
          </button>
        </div>
      </div>
    `;

    el.querySelectorAll('[data-dist-param]').forEach(inp => {
      inp.addEventListener('input', () => {
        const v = parseFloat(inp.value);
        if (!Number.isFinite(v)) return;
        state.distConfig[id].params[inp.getAttribute('data-dist-param')] = v;
        scheduleDistValidation();
      });
    });
    el.querySelectorAll('[data-dist-case]').forEach(inp => {
      const handler = () => {
        const caseId = inp.getAttribute('data-dist-case');
        const field = inp.getAttribute('data-dist-field');
        if (field === 'op') {
          state.distConfig[id].cases[caseId].op = inp.value;
        } else {
          const v = parseFloat(inp.value);
          if (!Number.isFinite(v)) return;
          state.distConfig[id].cases[caseId][field] = v;
        }
        scheduleDistValidation();
      };
      inp.addEventListener('input', handler);
      inp.addEventListener('change', handler);
    });
    el.querySelectorAll('[data-dist-method]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.distConfig[id].method = btn.getAttribute('data-dist-method');
        el.querySelectorAll('[data-dist-method]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        scheduleDistValidation();
      });
    });
    const resetBtn = getEl('btn-dist-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        state.distConfig[id] = cloneDeep(DIST_DEFAULTS[id]);
        renderDistConfig();
        scheduleDistValidation();
      });
    }
  }

  function fmtP(v) {
    return (v === null || v === undefined) ? '—' : Number(v).toFixed(6);
  }

  function fmtShort(v) {
    if (v === null || v === undefined) return '—';
    const n = Number(v);
    if (Number.isInteger(n)) return String(n);
    return n.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  }

  function renderDistDetail(d, all) {
    const el = getEl('dist-detail-panel');
    if (!el || !d) return;

    if (d.status === 'error') {
      el.innerHTML = `
        <div class="test-detail-header"><h4>${d.order}. ${escapeHtml(d.name)}</h4></div>
        <div class="tests-error-banner"><i class="fa-solid fa-triangle-exclamation"></i>
          ${(d.errors || []).map(escapeHtml).join(' ')}</div>
      `;
      destroyDistChart();
      return;
    }

    const genName = (state.lastResult && state.lastResult.method_name) || 'el generador seleccionado';
    const nums = (state.lastResult && state.lastResult.numbers) || [];
    const firstR = nums.slice(0, 3).map(r => Number(r).toFixed(4)).join(', ');
    const firstX = (d.sample_table.rows || []).slice(0, 3).map(r => fmtShort(r.x)).join(', ');

    const countLines = d.cases.map(c => `${c.label}: #{ ${c.condition.slice(2, -1).replace(/X/g, 'xᵢ')} } = ${c.count}   →   P_sim = ${c.sim_expr}`);

    const steps = [
      {
        label: 'Paso 1 · Generación de los números pseudoaleatorios',
        formula: `Se toman los N = ${d.n_r} rᵢ ∈ [0, 1) generados con ${genName}.`,
        result: `r₁, r₂, r₃, … = ${firstR}${nums.length > 3 ? ', …' : ''}`
      },
      {
        label: `Paso 2 · Conversión estadística (${d.method_label})`,
        formula: `${d.conversion_formula}     →     ${d.conversion_formula_params}`,
        result: `${d.n_r} rᵢ → ${d.n_values} valores xᵢ (${d.r_per_value} rᵢ por valor).  x₁, x₂, x₃, … = ${firstX}${d.n_values > 3 ? ', …' : ''}`
      },
      {
        label: 'Paso 3 · Conteo: menor que, mayor que y rango (probabilidad simulada)',
        formula: 'P_sim = (cantidad de xᵢ que cumplen la condición) / n',
        result: countLines.join('\n')
      },
      {
        label: 'Paso 4 · Validación contra la probabilidad teórica',
        formula: `Se acepta que P_sim = P_teo si |P_sim − P_teo| ≤ Z_(α/2)·√(P_teo(1 − P_teo)/n),  con Z_(α/2) = ${d.z}`,
        result: d.cases.map(c => `${c.condition}: ${c.decision_expr} → ${c.validated ? 'VALIDADA' : 'NO VALIDADA'}`).join('\n')
      }
    ];

    const stepsHtml = steps.map((s, idx) => `
      <div class="test-step-row">
        <div class="test-step-num">${idx + 1}</div>
        <div class="test-step-body">
          <div class="test-step-label">${escapeHtml(s.label)}</div>
          <div class="test-step-formula">${escapeHtml(s.formula)}</div>
          <div class="test-step-result dist-multiline">${escapeHtml(s.result)}</div>
        </div>
      </div>
    `).join('');

    const casesHtml = d.cases.map(c => `
      <div class="dist-case-card ${c.validated ? 'pass' : 'fail'}">
        <div class="dist-case-card-head">
          <span class="dist-case-tag">${escapeHtml(c.label)}</span>
          <span class="test-stat-verdict ${c.validated ? 'pass' : 'fail'}">
            <i class="fa-solid ${c.validated ? 'fa-circle-check' : 'fa-circle-xmark'}"></i>
            ${c.validated ? 'VALIDADA' : 'NO VALIDADA'}
          </span>
        </div>
        <div class="dist-case-condition">${escapeHtml(c.condition)}</div>
        <div class="dist-prob-compare">
          <div class="test-stat-box">
            <span class="test-stat-label">P simulada (conteo)</span>
            <span class="test-stat-value">${fmtP(c.p_sim)}</span>
            <span class="dist-prob-sub">${c.count} / ${c.n}</span>
          </div>
          <div class="test-stat-vs">${c.validated ? '≈' : '≠'}</div>
          <div class="test-stat-box">
            <span class="test-stat-label">P teórica (fórmula)</span>
            <span class="test-stat-value">${fmtP(c.p_theo)}</span>
            <span class="dist-prob-sub">esperados ≈ ${fmtShort(c.expected_count)}</span>
          </div>
        </div>
        <div class="dist-diff-row">
          <span>|Diferencia| <strong>${fmtP(c.diff)}</strong></span>
          <span>${c.validated ? '≤' : '>'}</span>
          <span>Margen <strong>${fmtP(c.margin)}</strong></span>
          ${c.rel_error_pct !== null && c.rel_error_pct !== undefined ? `<span class="dist-rel">error relativo ${c.rel_error_pct}%</span>` : ''}
        </div>
        <details class="dist-theo-details">
          <summary>Ver cálculo de la probabilidad teórica</summary>
          <div class="test-step-formula dist-multiline">${escapeHtml(c.theo_lines.join('\n'))}</div>
          <div class="test-step-formula">Margen = ${escapeHtml(c.margin_expr)}</div>
          <div class="test-step-formula">Banda de aceptación: [${fmtP(c.band_low)}, ${fmtP(c.band_high)}]</div>
        </details>
      </div>
    `).join('');

    const m = d.moments || {};
    const momentsHtml = `
      <div class="dist-moments-row">
        <div class="dist-moment">
          <span class="test-stat-label">Media simulada x̄</span>
          <span class="test-stat-value">${fmtShort(m.mean_sim)}</span>
        </div>
        <div class="dist-moment">
          <span class="test-stat-label">Media teórica ${escapeHtml(m.mean_formula || '')}</span>
          <span class="test-stat-value">${fmtShort(m.mean_theo)}</span>
        </div>
        <div class="dist-moment">
          <span class="test-stat-label">Varianza simulada s²</span>
          <span class="test-stat-value">${fmtShort(m.var_sim)}</span>
        </div>
        <div class="dist-moment">
          <span class="test-stat-label">Varianza teórica ${escapeHtml(m.var_formula || '')}</span>
          <span class="test-stat-value">${fmtShort(m.var_theo)}</span>
        </div>
      </div>
    `;

    const passedAll = d.status === 'pass';
    let conclusion;
    if (d.status === 'inconclusive') {
      conclusion = `<div class="test-inconclusive-banner"><i class="fa-solid fa-circle-question"></i><span>Validación no concluyente: se obtuvieron muy pocos valores convertidos (${d.n_values}).</span></div>`;
    } else {
      conclusion = `<div class="test-conclusion-box ${passedAll ? 'pass' : 'fail'}">${passedAll
        ? `La conversión a la ${escapeHtml(d.name)} está VALIDADA: en los ${d.cases.length} casos la probabilidad obtenida contando los números convertidos coincide con la probabilidad teórica (${d.cases_passed}/${d.cases.length}).`
        : `La conversión a la ${escapeHtml(d.name)} NO queda validada: ${d.cases.length - d.cases_passed} de ${d.cases.length} casos se salen del margen de error. Pruebe con más números generados o revise la calidad de la secuencia.`}</div>`;
    }

    const notesHtml = (d.notes && d.notes.length) ? `
      <div class="test-notes-box">
        <i class="fa-solid fa-circle-info"></i>
        <ul>${d.notes.map(n => `<li>${escapeHtml(n)}</li>`).join('')}</ul>
      </div>
    ` : '';

    el.innerHTML = `
      <div class="test-detail-header dist-detail-header">
        <h4>${d.order}. ${escapeHtml(d.name)} <span class="dist-params-badge">${escapeHtml(d.params_label)}</span></h4>
        <span class="algo-badge">${escapeHtml(d.method_label)}</span>
      </div>
      ${conclusion}
      <div class="dist-case-cards">${casesHtml}</div>
      <div class="test-decision-rule"><strong>Regla de decisión:</strong> la conversión se considera correcta si la probabilidad simulada y la teórica son iguales dentro del margen de error de una proporción, |P_sim − P_teo| ≤ Z_(α/2)·√(P_teo(1 − P_teo)/n), con α = ${(all.alpha * 100).toFixed(2)}%.</div>
      <div class="test-steps-list">${stepsHtml}</div>
      <div class="test-data-table-wrapper">
        <h5>Frecuencia observada vs. esperada (${d.discrete ? 'valores discretos' : 'intervalos de clase'})</h5>
        <div class="dist-chart-container"><canvas id="chart-dist-hist"></canvas></div>
      </div>
      ${momentsHtml}
      ${notesHtml}
      ${renderTestDataTable(d.sample_table, 'Tabla de conversión rᵢ → xᵢ y conteo de cada caso (✓ = cumple)')}
    `;

    renderDistChart(d);
  }

  function destroyDistChart() {
    if (state.charts.distHist) {
      state.charts.distHist.destroy();
      state.charts.distHist = null;
    }
  }

  function renderDistChart(d) {
    destroyDistChart();
    const canvas = getEl('chart-dist-hist');
    if (!canvas || typeof Chart === 'undefined' || !d.histogram) return;
    const h = d.histogram;
    state.charts.distHist = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: h.labels,
        datasets: [
          {
            type: 'bar',
            label: 'Frecuencia observada (conteo de xᵢ)',
            data: h.observed,
            backgroundColor: 'rgba(52, 211, 153, 0.55)',
            borderColor: 'rgba(52, 211, 153, 0.95)',
            borderWidth: 1,
            order: 2
          },
          {
            type: 'line',
            label: 'Frecuencia esperada (n × probabilidad teórica)',
            data: h.expected,
            borderColor: '#C084FC',
            backgroundColor: 'rgba(192, 132, 252, 0.2)',
            borderWidth: 2,
            pointRadius: h.discrete ? 3 : 2,
            tension: h.discrete ? 0 : 0.3,
            order: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 200 },
        scales: {
          x: {
            title: { display: true, text: h.discrete ? 'Valor de x' : 'Intervalo de x', color: '#C4B5FD', font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' } },
            ticks: { color: '#8B7CA8', font: { family: 'JetBrains Mono', size: 10 }, maxRotation: 60, autoSkip: true },
            grid: { color: 'rgba(168, 85, 247, 0.06)' }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Frecuencia', color: '#C4B5FD', font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' } },
            ticks: { color: '#8B7CA8', font: { family: 'JetBrains Mono' } },
            grid: { color: 'rgba(168, 85, 247, 0.08)' }
          }
        },
        plugins: {
          legend: { labels: { color: '#F3E8FF', font: { family: 'Plus Jakarta Sans', weight: '600' } } },
          tooltip: {
            backgroundColor: 'rgba(20, 13, 38, 0.94)',
            titleFont: { family: 'Plus Jakarta Sans', weight: 'bold' },
            bodyFont: { family: 'JetBrains Mono' },
            borderColor: 'rgba(168, 85, 247, 0.3)',
            borderWidth: 1
          }
        }
      }
    });
  }

  // Inicializar
  init();
});
