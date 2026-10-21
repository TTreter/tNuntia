"""
tNuntia: Motor de Inteligência Artificial para Cortes, Notícias e Redes Sociais Legislativas.
Integrado com tVerbum para economia de tokens.
"""

from .models import (
    VideoCut,
    SpeakerQuote,
    NewsArticle,
    CarouselSlide,
    SocialMediaPackage,
    SessionHighlights,
    NuntiaConfig,
    NuntiaOutput,
)
from .ai_engine import NuntiaAIEngine
from .exporter import NuntiaExporter
from .cutter import VideoCutter
from .tverbum_client import TVerbumClient

__version__ = "1.0.0"
__all__ = [
    "VideoCut",
    "NewsArticle",
    "CarouselSlide",
    "SocialMediaPackage",
    "SessionHighlights",
    "NuntiaConfig",
    "NuntiaOutput",
    "NuntiaAIEngine",
    "NuntiaExporter",
    "VideoCutter",
    "TVerbumClient",
]
