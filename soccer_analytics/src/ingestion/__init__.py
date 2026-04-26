"""
Ingestion services for soccer data sources.

This module provides services for ingesting data from multiple sources:
- FBref: Comprehensive match and player statistics
- WhoScored: Detailed match events and lineups (Selenium-based)
- Sofascore: Match data, team/player stats, live scores
- ESPN: Match schedules, stats, lineups (JSON API)
- MatchHistory: Results and odds from Football-Data.co.uk
- ClubElo: Team Elo ratings over time

Philosophy: Following soccerdata's approach with consistent DataFrame outputs,
cache management, responsible scraping, and graceful error handling.
"""

from .base import (
    BaseIngestionService,
    IngestionError,
    SourceUnavailableError,
    DataValidationError,
    with_retry,
)
# Lazy imports to avoid circular dependency issues during testing
try:
    from .fbref import FBrefService as FbrefService
    from .whoscored import WhoscoredService
    from .sofascore import SofascoreService
    from .espn import EspnService
    from .matchhistory import MatchHistoryService
    from .clubelo import ClubEloService
    from .orchestrator import IngestionOrchestrator
except (ImportError, ValueError):
    # These imports may fail during testing when modules aren't fully set up
    FbrefService = None
    WhoscoredService = None
    SofascoreService = None
    EspnService = None
    MatchHistoryService = None
    ClubEloService = None
    IngestionOrchestrator = None

__all__ = [
    # Base classes
    'BaseIngestionService',
    'IngestionError',
    'SourceUnavailableError',
    'DataValidationError',
    'with_retry',
    
    # Source services
    'FbrefService',
    'WhoscoredService',
    'SofascoreService',
    'EspnService',
    'MatchHistoryService',
    'ClubEloService',
    
    # Orchestrator
    'IngestionOrchestrator',
]

# Service registry for dynamic loading
SERVICE_REGISTRY = {
    'fbref': FbrefService,
    'whoscored': WhoscoredService,
    'sofascore': SofascoreService,
    'espn': EspnService,
    'matchhistory': MatchHistoryService,
    'clubelo': ClubEloService,
}


def get_service(source_name: str, config, session=None):
    """
    Get an ingestion service by name.
    
    Args:
        source_name: Name of the source (fbref, whoscored, etc.)
        config: Application configuration
        session: Optional database session
        
    Returns:
        Instance of the requested service
        
    Raises:
        ValueError: If source_name is not recognized
    """
    if source_name not in SERVICE_REGISTRY:
        available = ', '.join(SERVICE_REGISTRY.keys())
        raise ValueError(f"Unknown source: {source_name}. Available: {available}")
    
    return SERVICE_REGISTRY[source_name](config=config, session=session)


def list_available_services() -> list:
    """
    List all available ingestion services.
    
    Returns:
        List of service names
    """
    return list(SERVICE_REGISTRY.keys())