"""
Core PRNG package containing generation algorithms, validators, recommenders, statistical tests, and Excel exporter.
"""
from .validators import validate_gclm, validate_gcm, validate_cuadrados_medios, validate_productos_medios, validate_bbs
from .generators import generate_gclm, generate_gcm, generate_cuadrados_medios, generate_productos_medios, generate_bbs
from .recommenders import (
    generate_gclm_optimal,
    generate_gcm_optimal,
    generate_cuadrados_medios_optimal,
    generate_productos_medios_optimal,
    generate_bbs_optimal
)
from .stats import calculate_stats
from .random_tests import run_all_tests
