"""Registro central de modelos — cada módulo com modelos importado aqui popula o metadata."""
from app.core.db import Base

metadata = Base.metadata
