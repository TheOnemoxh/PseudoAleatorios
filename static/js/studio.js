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
    charts: {
      scatter: null
    }
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
    const filename = `PRNG_${method}.xlsx`;

    const btnExp = getEl('btn-export-excel');
    if (btnExp) {
      btnExp.disabled = true;
      btnExp.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando XLSX...';
    }

    try {
      const queryParams = new URLSearchParams({ method, ...params });
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

  // Inicializar
  init();
});
