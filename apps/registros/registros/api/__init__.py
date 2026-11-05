"""API /v1 para la plataforma. Ya está incluido en main.py: las rutas se cuelgan de este router."""
from .v1 import router

__all__ = ["router"]
