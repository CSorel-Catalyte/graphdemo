"""
Storage layer for the AI Knowledge Mapper system.
Contains adapters for vector and graph databases.
"""

try:
    from .qdrant_adapter import QdrantAdapter
    from .oxigraph_adapter import OxigraphAdapter
    __all__ = ["QdrantAdapter", "OxigraphAdapter"]
except ImportError as e:
    # Dependencies not installed - this is expected during development
    print(f"Storage dependencies not available: {e}")
    __all__ = []