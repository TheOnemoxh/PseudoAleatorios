"""
Vercel Serverless Entrypoint for FastAPI
"""

import sys
import os
from pathlib import Path

# Agregar directorio raíz al sys.path para importaciones de módulos
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app
