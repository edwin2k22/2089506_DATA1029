"""
Whoscored ingestion service for detailed match events and lineups.

Provides:
- Match schedules and results
- Missing players (injuries/suspensions)
- Detailed match events (events, raw, spadl, atomic-spadl formats)
- Lineups and formations

Philosophy: Following soccerdata's approach with Selenium support,
graceful error handling, and multiple event format options.
"""

import logging
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime

try:
    from soccerdata import WhoScored as SoccerDataWhoScored
except ImportError:
    raise ImportError("soccerdata library required. Install with: pip install soccerdata")

from .base import BaseIngestionService, IngestionError, SourceUnavailableError

logger = logging.getLogger(__name__)


class WhoscoredService(BaseIngestionService):
    """
    Service for ingesting data from WhoScored.com.
    
    WhoScored provides:
    - Detailed match events (passes, shots, tackles, etc.)
    - Player ratings and statistics
    - Lineups and formations
    - Missing players (injuries/suspensions)
    - Live match data
    
    Note: WhoScored uses JavaScript-heavy pages, requiring Selenium.
    Proper browser configuration is essential.
    """
    
    source_name = "whoscored"
    
    # Supported event formats
    EVENT_FORMATS = ['events', 'raw', 'spadl', 'atomic-spadl', 'loader']
    
    def __init__(self, config: Any, session: Any = None):
        """
        Initialize WhoScored service.
        
        Args:
            config: Application configuration
            session: Optional database session
        """
        super().__init__(config, session)
        
        # Initialize soccerdata WhoScored reader
        # Configuration options for Selenium/browser
        self.no_cache = getattr(config, 'whoscored_no_cache', False)
        self.no_store = getattr(config, 'whoscored_no_store', False)
        
        # Browser configuration for Selenium
        self.headless = getattr(config, 'whoscored_headless', True)
        self.proxy = getattr(config, 'whoscored_proxy', None)
        self.path_to_browser = getattr(config, 'whoscored_browser_path', None)
        
        # Rate limiting - WhoScored is sensitive to scraping
        self.request_delay = getattr(config, 'whoscored_request_delay', 5.0)
        
        try:
            self.reader = SoccerDataWhoScored(
                data_dir=self.config.data_dir,
                no_cache=self.no_cache,
                no_store=self.no_store,
                proxy=self.proxy,
            )
            self.logger.info("WhoScored reader initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WhoScored reader: {e}")
            raise IngestionError(f"Cannot initialize WhoScored: {e}")
    
    def _fetch_data(
        self,
        league: str,
        season: str,
        stat_type: str = 'schedule',
        **kwargs
    ) -> pd.DataFrame:
        """
        Fetch data from WhoScored.
        
        Args:
            league: League identifier (from league_dict.json)
            season: Season identifier (e.g., '2023-2024')
            stat_type: Type of data to fetch:
                - 'schedule': Match schedule and results
                - 'missing_players': Injured/suspended players
                - 'events': Match events (requires match_id)
                - 'lineups': Team lineups (requires match_id)
            match_id: Specific match ID (for events/lineups)
            event_format: Format for events (events/raw/spadl/atomic-spadl/loader)
            live: Fetch live data (default: False)
            retry_missing: Retry fetching missing data (default: True)
            on_error: Error handling ('raise', 'skip', 'warn')
            
        Returns:
            pandas DataFrame with requested data
        """
        stat_type = kwargs.get('stat_type', 'schedule')
        match_id = kwargs.get('match_id', None)
        event_format = kwargs.get('event_format', 'events')
        live = kwargs.get('live', False)
        retry_missing = kwargs.get('retry_missing', True)
        on_error = kwargs.get('on_error', 'warn')
        
        if event_format not in self.EVENT_FORMATS:
            raise ValueError(f"Invalid event format: {event_format}. Must be one of {self.EVENT_FORMATS}")
        
        try:
            if stat_type == 'schedule':
                return self._fetch_schedule(league, season)
            elif stat_type == 'missing_players':
                return self._fetch_missing_players(league, season)
            elif stat_type == 'events':
                if not match_id:
                    raise ValueError("match_id required for events")
                return self._fetch_events(league, season, match_id, event_format)
            elif stat_type == 'lineups':
                if not match_id:
                    raise ValueError("match_id required for lineups")
                return self._fetch_lineups(league, season, match_id)
            else:
                raise ValueError(f"Unknown stat_type: {stat_type}")
                
        except Exception as e:
            self.logger.error(f"Error fetching {stat_type} for {league} {season}: {e}")
            if on_error == 'raise':
                raise
            elif on_error == 'skip':
                self.logger.warning("Skipping due to error")
                return pd.DataFrame()
            else:  # warn
                self.logger.warning(f"Continuing despite error: {e}")
                return pd.DataFrame()
    
    def _fetch_schedule(self, league: str, season: str) -> pd.DataFrame:
        """Fetch match schedule and results."""
        self.logger.info(f"Fetching WhoScored schedule for {league} - {season}")
        
        df = self.reader.read_schedule(
            leagues=league,
            seasons=season,
            force_cache=True,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No schedule data for {league} {season}")
            return pd.DataFrame()
        
        # Normalize
        df = self.normalize_dates(df, 'date')
        df = self.remove_duplicates(df, subset=['match_id', 'home_team', 'away_team'])
        
        self.logger.info(f"Fetched {len(df)} matches from WhoScored")
        return df
    
    def _fetch_missing_players(self, league: str, season: str) -> pd.DataFrame:
        """Fetch injured and suspended players."""
        self.logger.info(f"Fetching WhoScored missing players for {league} - {season}")
        
        df = self.reader.read_missing_players(
            leagues=league,
            seasons=season,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No missing players data for {league} {season}")
            return pd.DataFrame()
        
        # Normalize
        df = self.normalize_dates(df, 'expected_return')
        
        self.logger.info(f"Fetched {len(df)} missing player records")
        return df
    
    def _fetch_events(
        self,
        league: str,
        season: str,
        match_id: int,
        event_format: str = 'events'
    ) -> pd.DataFrame:
        """
        Fetch detailed match events.
        
        Event formats:
        - 'events': Standard event dictionary
        - 'raw': Raw JSON from WhoScored
        - 'spadl': SPADL format (standardized)
        - 'atomic-spadl': Atomic SPADL (finer granularity)
        - 'loader': Loader format for analysis
        """
        self.logger.info(f"Fetching WhoScored events for match {match_id} ({event_format})")
        
        df = self.reader.read_events(
            match_id=match_id,
            output_format=event_format,
            force_cache=True,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No events data for match {match_id}")
            return pd.DataFrame()
        
        # Events are already normalized by soccerdata
        self.logger.info(f"Fetched {len(df)} events for match {match_id}")
        return df
    
    def _fetch_lineups(self, league: str, season: str, match_id: int) -> pd.DataFrame:
        """Fetch team lineups for a match."""
        self.logger.info(f"Fetching WhoScored lineups for match {match_id}")
        
        # Lineups are typically included in events data
        # We fetch events and extract lineup information
        df = self.reader.read_events(
            match_id=match_id,
            output_format='loader',  # Loader format includes lineups
            force_cache=True,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No lineup data for match {match_id}")
            return pd.DataFrame()
        
        self.logger.info(f"Fetched lineups for match {match_id}")
        return df
    
    def get_available_leagues(self) -> Dict[str, str]:
        """
        Get available leagues from WhoScored.
        
        Returns:
            Dict mapping league names to identifiers
        """
        try:
            # WhoScored doesn't have a direct available_leagues() method
            # We rely on league_dict.json configuration
            return self.config.available_leagues.get('whoscored', {})
        except Exception as e:
            self.logger.error(f"Error getting available leagues: {e}")
            return {}
    
    def validate_league(self, league: str) -> bool:
        """
        Validate that a league is available in WhoScored.
        
        Args:
            league: League identifier to validate
            
        Returns:
            True if league is available
        """
        available = self.get_available_leagues()
        return league in available.values() or league in available.keys()
    
    def fetch_match_events_batch(
        self,
        league: str,
        season: str,
        match_ids: List[int],
        event_format: str = 'events',
        delay_between_requests: float = 3.0
    ) -> Dict[int, pd.DataFrame]:
        """
        Fetch events for multiple matches with rate limiting.
        
        Args:
            league: League identifier
            season: Season identifier
            match_ids: List of match IDs
            event_format: Event format
            delay_between_requests: Delay between requests (seconds)
            
        Returns:
            Dict mapping match_id to events DataFrame
        """
        import time
        
        results = {}
        total = len(match_ids)
        
        for i, match_id in enumerate(match_ids):
            try:
                self.logger.info(f"Fetching events for match {i+1}/{total}: {match_id}")
                df = self._fetch_events(league, season, match_id, event_format)
                results[match_id] = df
                
                # Rate limiting to avoid blocking
                if i < total - 1:
                    time.sleep(delay_between_requests)
                    
            except Exception as e:
                self.logger.error(f"Failed to fetch events for match {match_id}: {e}")
                results[match_id] = pd.DataFrame()
        
        return results
