"""
System architecture providers for vtop.
"""

from .base import SystemProvider
from .factory import get_system_provider

__all__ = ['SystemProvider', 'get_system_provider']
