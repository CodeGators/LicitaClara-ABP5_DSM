"""Metadata única. Importar módulos registra as tabelas sem abrir conexão."""

from licita_backend.models import analysis, audit, collection, complementary, procurement
from licita_backend.models.base import Base

__all__ = ["Base", "analysis", "audit", "collection", "complementary", "procurement"]
