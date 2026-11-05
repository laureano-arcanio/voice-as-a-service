"""Panel. Ya está incluido en main.py, con /static servido desde panel/static: las rutas se cuelgan
de este router. El login es POST /auth/login (auth.py)."""
from fastapi import APIRouter

from . import pages, persons

router = APIRouter(include_in_schema=False)
router.include_router(persons.router)
router.include_router(pages.router)
