"""Explicit opt-in for all demo seed entrypoints."""
import os

def require_demo():
    if os.getenv('FRAMATEX_MODE') != 'DEMO':
        raise SystemExit('Données fictives refusées : utiliser FRAMATEX_MODE=DEMO sur une installation dédiée.')
