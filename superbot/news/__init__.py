"""
News package for SuperBot Trading Unifié.
"""
from .news_manager import NewsManager, NewsEvent, SentimentScore

__all__ = [
    'NewsManager',
    'NewsEvent',
    'SentimentScore'
]