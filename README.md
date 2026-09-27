# Generador de Números Pseudoaleatorios

Aplicación web local (FastAPI + JavaScript) para generar y analizar secuencias de números pseudoaleatorios con 5 métodos clásicos: Congruencial Lineal Mixto (GCLM), Congruencial Multiplicativo (GCM/Lehmer), Cuadrados Medios, Productos Medios y Blum Blum Shub (BBS). Incluye validación en tiempo real de los teoremas asociados, gráfica de independencia (retardo lag-1) y exportación a Excel con fórmulas nativas.

## Validación de Distribuciones (conversiones estadísticas)

La pestaña **Validación de Distribuciones** toma los rᵢ generados y los convierte a cinco distribuciones: **Uniforme entre A y B, Normal, Erlang, Poisson y Binomial**. Para cada una:

1. **Generación:** se usan los N números rᵢ de la secuencia actual (se recomiendan 1000 o más).
2. **Conversión:** transformada inversa (1 rᵢ → 1 valor, por defecto) o el método clásico del libro (suma de 12 rᵢ para la Normal, producto de k rᵢ para Erlang, método multiplicativo para Poisson y suma de Bernoullis para la Binomial).
3. **Conteo:** se cuenta cuántos valores cumplen cada caso — *menor que* (`<` o `≤`), *mayor que* (`>` o `≥`) y *entre a y b* — y se divide entre n para obtener la probabilidad simulada.
4. **Validación:** se calcula la probabilidad teórica con la fórmula de la distribución. La conversión queda **VALIDADA** si `|P_sim − P_teo| ≤ Z(α/2)·√(P_teo(1 − P_teo)/n)`, es decir, si ambas probabilidades coinciden dentro del margen de error del nivel α elegido.

Los parámetros, el método y los valores de cada caso se editan en la misma pestaña. Al exportar a Excel se agregan las hojas **V0 Resumen** y **V1–V5** (una por distribución) con fórmulas nativas: conversión de cada rᵢ, `CONTAR.SI.CONJUNTO` para el conteo y `DISTR.NORM.N`, `POISSON.DIST`, `DISTR.BINOM.N`, etc. para la probabilidad teórica. En esas hojas α, los operadores y los valores de cada caso son editables (celdas amarillas).

## Requisitos previos

- **Python 3.10 o superior** instalado y agregado al PATH (`python --version` debe funcionar en una terminal).
- **pip** (viene incluido con Python).
- Conexión a internet la primera vez que se abre la página en el navegador (solo para cargar Chart.js y las tipografías desde un CDN; el resto de la app funciona 100% en local). Si no hay internet, la app sigue funcionando pero no se dibuja la gráfica de dispersión.

No se necesita Node.js, base de datos, ni ninguna instalación adicional.

## Instalación en un equipo nuevo

1. Copia toda la carpeta `PseudoAleatorios` al equipo.
2. Abre una terminal (CMD, PowerShell o similar) dentro de esa carpeta:
   ```
   cd ruta\a\PseudoAleatorios
   ```
3. (Opcional pero recomendado) Crea un entorno virtual para no mezclar las dependencias con otros proyectos de Python:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
   En Mac/Linux el activar sería `source venv/bin/activate`.
4. Instala las dependencias del proyecto:
   ```
   pip install -r requirements.txt
   ```

## Cómo ejecutar la aplicación

Con las dependencias ya instaladas, desde la carpeta del proyecto:

```
python main.py
```

Esto:
- Levanta un servidor local en `http://127.0.0.1:8000`.
- Abre automáticamente esa dirección en tu navegador predeterminado.

Para **detener** el servidor, vuelve a la terminal donde quedó corriendo y presiona `Ctrl + C`.

## Solución de problemas comunes

**"python no se reconoce como un comando..."**
Python no está instalado o no está en el PATH. Instálalo desde python.org marcando la opción "Add Python to PATH" durante la instalación.

**`ModuleNotFoundError: No module named 'fastapi'` (o similar)**
No se instalaron las dependencias, o se instalaron en un entorno distinto al que estás usando para ejecutar. Repite el paso `pip install -r requirements.txt` dentro del mismo entorno/terminal donde ejecutas `python main.py`.

**El navegador no abre solo / se abre en blanco**
Abre manualmente `http://127.0.0.1:8000` en el navegador. Si sigue en blanco, revisa la consola de la terminal donde corre `python main.py` por si hay un error, y copia ese mensaje para diagnosticarlo.

**El botón "Exportar en Excel" no descarga nada o descarga un archivo con nombre raro**
Haz un refresco fuerte (`Ctrl+F5`) y reinicia el servidor. Si persiste, revisa la consola del navegador (F12 → pestaña Console) por errores.

**La gráfica de dispersión no aparece**
Necesita internet para cargar Chart.js desde un CDN. El resto de la aplicación (tabla, exportación a Excel, validaciones) funciona igual sin conexión.
