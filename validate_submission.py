#!/usr/bin/env python3
"""
Script oficial de validación de entregas para HealthSignal LATAM (Fase 3).
Verifica la integridad de los archivos results/signals.csv y results/evidence.csv.
"""

import sys
import argparse
from pathlib import Path

# Agregar raíz al path de Python para permitir importaciones correctas
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from evidence.validator import SubmissionValidator


def main():
    parser = argparse.ArgumentParser(description="Validador Oficial de Entregas de RISA Data V1.0")
    parser.add_argument(
        "--signals",
        type=str,
        default="results/signals.csv",
        help="Ruta al archivo signals.csv (por defecto: results/signals.csv)"
    )
    parser.add_argument(
        "--evidence",
        type=str,
        default="results/evidence.csv",
        help="Ruta al archivo evidence.csv (por defecto: results/evidence.csv)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  VALIDADOR DE ENTREGAS - HEALTHSIGNAL LATAM")
    print(f"  Archivo Senales:   {args.signals}")
    print(f"  Archivo Evidencia: {args.evidence}")
    print("=" * 70)

    validator = SubmissionValidator()
    success, errors = validator.validate_files(args.signals, args.evidence)

    if success:
        print("\n[SUCCESS] Los archivos cumplen con todas las reglas logicas, estructurales y temporales.")
        sys.exit(0)
    else:
        print(f"\n[FAILED] Se detectaron {len(errors)} errores de consistencia e integridad:")
        for idx, err in enumerate(errors, start=1):
            print(f"  {idx}. {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
