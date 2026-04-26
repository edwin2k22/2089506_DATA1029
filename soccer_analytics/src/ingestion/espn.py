"""
ESPN ingestion service for match data and team statistics.

Provides:
- Match schedules and results
- Team and player statistics
- Lineups and formations
- Standings and tournament data

Philosophy: Following soccerdata's approach with JSON API consumption,
cache management, and consistent DataFrame outputs.
"""

import logging
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime

try:
    from soccerdata import ESPN as SoccerDataESPN
except ImportError:
    raise ImportError("soccerdata library required. Install with: pip install soccerdata")

from .base import BaseIngestionService, IngestionError

logger = logging.getLogger(__name__)


class EspnService(BaseIngestionService):
    """
    Service for ingesting data from ESPN.com/soccer.
    
    ESPN provides:
    - Match schedules and results for major leagues
    - Team and player statistics
    - Lineups and match reports
    - Standings and tournament brackets
    
    Note: ESPN uses a JSON API which is relatively stable and fast.
    """
    
    source_name = "espn"
    
    # Supported stat types
    STAT_TYPES = [
        'schedule',
        'team_stats',
        'player_stats',
        'lineups',
        'standings',
        'summary',
    ]
    
    def __init__(self, config: Any, session: Any = None):
        """
        Initialize ESPN service.
        
        Args:
            config: Application configuration
            session: Optional database session
        """
        super().__init__(config, session)
        
        # Configuration options
        self.no_cache = getattr(config, 'espn_no_cache', False)
        self.no_store = getattr(config, 'espn_no_store', False)
        self.proxy = getattr(config, 'espn_proxy', None)
        
        # Rate limiting - ESPN is generally tolerant but we should be respectful
        self.request_delay = getattr(config, 'espn_request_delay', 1.0)
        
        try:
            self.reader = SoccerDataESPN(
                data_dir=self.config.data_dir,
                no_cache=self.no_cache,
                no_store=self.no_store,
                proxy=self.proxy,
            )
            self.logger.info("ESPN reader initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize ESPN reader: {e}")
            raise IngestionError(f"Cannot initialize ESPN: {e}")
    
    def _fetch_data(
        self,
        league: str,
        season: str,
        stat_type: str = 'schedule',
        **kwargs
    ) -> pd.DataFrame:
        """
        Fetch data from ESPN.
        
        Args:
            league: League identifier (from league_dict.json)
            season: Season identifier (e.g., '2023-2024')
            stat_type: Type of data to fetch:
                - 'schedule': Match schedule and results
                - 'team_stats': Team statistics for the season
                - 'player_stats': Player statistics for the season
                - 'lineups': Team lineups (requires match_id)
                - 'standings': League standings
                - 'summary': Match summary (requires match_id)
            match_id: Specific match ID (for lineups/summary)
            
        Returns:
            pandas DataFrame with requested data
        """
        stat_type = kwargs.get('stat_type', 'schedule')
        match_id = kwargs.get('match_id', None)
        
        if stat_type not in self.STAT_TYPES:
            raise ValueError(f"Invalid stat_type: {stat_type}. Must be one of {self.STAT_TYPES}")
        
        try:
            if stat_type == 'schedule':
                return self._fetch_schedule(league, season)
            elif stat_type == 'team_stats':
                return self._fetch_team_stats(league, season)
            elif stat_type == 'player_stats':
                return self._fetch_player_stats(league, season)
            elif stat_type == 'lineups':
                if not match_id:
                    raise ValueError("match_id required for lineups")
                return self._fetch_lineups(league, season, match_id)
            elif stat_type == 'standings':
                return self._fetch_standings(league, season)
            elif stat_type == 'summary':
                if not match_id:
                    raise ValueError("match_id required for summary")
                return self._fetch_summary(league, season, match_id)
            else:
                raise ValueError(f"Unknown stat_type: {stat_type}")
                
        except Exception as e:
            self.logger.error(f"Error fetching {stat_type} for {league} {season}: {e}")
            on_error = kwargs.get('on_error', 'warn')
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
        self.logger.info(f"Fetching ESPN schedule for {league} - {season}")
        
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
        
        self.logger.info(f"Fetched {len(df)} matches from ESPN")
        return df
    
    def _fetch_team_stats(self, league: str, season: str) -> pd.DataFrame:
        """Fetch team statistics for a season."""
        self.logger.info(f"Fetching ESPN team stats for {league} - {season}")
        
        df = self.reader.read_team_season_stats(
            leagues=league,
            seasons=season,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No team stats data for {league} {season}")
            return pd.DataFrame()
        
        # Normalize team names
        if 'team' in df.columns:
            df = self.normalize_team_names(df, 'team')
        
        self.logger.info(f"Fetched {len(df)} team stat records")
        return df
    
    def _fetch_player_stats(self, league: str, season: str) -> pd.DataFrame:
        """Fetch player statistics for a season."""
        self.logger.info(f"Fetching ESPN player stats for {league} - {season}")
        
        df = self.reader.read_player_season_stats(
            leagues=league,
            seasons=season,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No player stats data for {league} {season}")
            return pd.DataFrame()
        
        # Normalize
        if 'player' in df.columns:
            df = self.normalize_team_names(df, 'player')
        
        self.logger.info(f"Fetched {len(df)} player stat records")
        return df
    
    def _fetch_lineups(self, league: str, season: str, match_id: int) -> pd.DataFrame:
        """Fetch team lineups for a match."""
        self.logger.info(f"Fetching ESPN lineups for match {match_id}")
        
        df = self.reader.read_lineups(
            match_id=match_id,
            force_cache=True,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No lineup data for match {match_id}")
            return pd.DataFrame()
        
        self.logger.info(f"Fetched lineups for match {match_id}")
        return df
    
    def _fetch_standings(self, league: str, season: str) -> pd.DataFrame:
        """Fetch league standings."""
        self.logger.info(f"Fetching ESPN standings for {league} - {season}")
        
        df = self.reader.read_standings(
            leagues=league,
            seasons=season,
            force_cache=True,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No standings data for {league} {season}")
            return pd.DataFrame()
        
        self.logger.info(f"Fetched standings with {len(df)} teams")
        return df
    
    def _fetch_summary(self, league: str, season: str, match_id: int) -> pd.DataFrame:
        """Fetch match summary including key events and statistics."""
        self.logger.info(f"Fetching ESPN summary for match {match_id}")
        
        df = self.reader.read_match_summary(
            match_id=match_id,
            force_cache=True,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No summary data for match {match_id}")
            return pd.DataFrame()
        
        self.logger.info(f"Fetched summary for match {match_id}")
        return df
    
    def get_available_leagues(self) -> Dict[str, str]:
        """
        Get available leagues from ESPN.
        
        Returns:
            Dict mapping league names to identifiers
        """
        try:
            return self.config.available_leagues.get('espn', {})
        except Exception as e:
            self.logger.error(f"Error getting available leagues: {e}")
            return {}
    
    def validate_league(self, league: str) -> bool:
        """Validate that a league is available in ESPN."""
        available = self.get_available_leagues()
        return league in available.values() or league in available.keys()
    
    def fetch_season_package(
        self,
        league: str,
        season: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch comprehensive season data package.
        
        Args:
            league: League identifier
            season: Season identifier
            
        Returns:
            Dict with keys: 'schedule', 'team_stats', 'player_stats', 'standings'
        """
        results = {}
        
        try:
            results['schedule'] = self._fetch_schedule(league, season)
            results['team_stats'] = self._fetch_team_stats(league, season)
            results['player_stats'] = self._fetch_player_stats(league, season)
            results['standings'] = self._fetch_standings(league, season)
            
        except Exception as e:
            self.logger.error(f"Error fetching season package for {league} {season}: {e}")
        
        return results
