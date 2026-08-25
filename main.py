"""
Main entry point for Pseudo-Random Number Generator (PRNG) System
Run via console: python main.py
Starts the local server and automatically launches the user interface window.
"""

import sys
import time
import threading
import webbrowser
import uvicorn


def open_browser(url: str, delay: float = 1.2):
    """Opens default browser after waiting for server initialization."""
    time.sleep(delay)
    print(f"\n[+] Abriendo ventana de la aplicacion en: {url}")
    webbrowser.open(url)


def print_banner():
    banner = """
========================================================================
     GENERADOR DE NUMEROS PSEUDOALEATORIOS - SIMULACION DIGITAL
========================================================================
  Metodos Implementados:
   [1] Congruencial Lineal Mixto (GCLM) + Teorema de Hull-Dobell
   [2] Congruencial Multiplicativo (GCM / Lehmer) + Periodo Maximal
   [3] Cuadrados Medios (John von Neumann) + Deteccion de Ciclos
   [4] Productos Medios (Middle-Product) + Heuristicas de Semillas
   [5] Blum Blum Shub (BBS) + Primos Criptograficos de Blum

  Caracteristicas:
   - Selector dinamico de Periodo Completo / Maximal
   - Grafica de Dispersion / Retardo (Independencia R_i vs R_{i+1})
   - Exportacion profesional a Excel (.xlsx) con formulas nativas

  Iniciando servicio local en: http://127.0.0.1:8000
  Presione Ctrl+C en esta consola para detener el servidor.
========================================================================
    """
    print(banner)


def main():
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print_banner()

    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    try:
        uvicorn.run("app:app", host=host, port=port, log_level="info", access_log=False)
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido por el usuario.")
        sys.exit(0)


if __name__ == "__main__":
    main()
