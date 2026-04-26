"""
Sofascore ingestion service for comprehensive match and team data.

Provides:
- Match schedules and results
- Team and player statistics
- Lineups and formations
- Live scores and in-game events
- Tournament standings

Philosophy: Following soccerdata's approach with consistent DataFrame outputs,
cache management, and responsible API usage.
"""

import logging
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime

try:
    from soccerdata import Sofascore as SoccerDataSofascore
except ImportError:
    raise ImportError("soccerdata library required. Install with: pip install soccerdata")

from .base import BaseIngestionService, IngestionError

logger = logging.getLogger(__name__)


class SofascoreService(BaseIngestionService):
    """
    Service for ingesting data from Sofascore.com.
    
    Sofascore provides:
    - Comprehensive match schedules across many leagues
    - Detailed team and player statistics
    - Lineups with player positions
    - Live match data and in-game events
    - Tournament standings and brackets
    
    Note: Sofascore has good API coverage but rate limits apply.
    """
    
    source_name = "sofascore"
    
    # Supported stat types
    STAT_TYPES = [
        'schedule',
        'team_stats',
        'player_stats',
        'lineups',
        'standings',
        'shotmap',
    ]
    
    def __init__(self, config: Any, session: Any = None):
        """
        Initialize Sofascore service.
        
        Args:
            config: Application configuration
            session: Optional database session
        """
        super().__init__(config, session)
        
        # Configuration options
        self.no_cache = getattr(config, 'sofascore_no_cache', False)
        self.no_store = getattr(config, 'sofascore_no_store', False)
        self.proxy = getattr(config, 'sofascore_proxy', None)
        
        # Rate limiting
        self.request_delay = getattr(config, 'sofascore_request_delay', 2.0)
        
        try:
            self.reader = SoccerDataSofascore(
                data_dir=self.config.data_dir,
                no_cache=self.no_cache,
                no_store=self.no_store,
                proxy=self.proxy,
            )
            self.logger.info("Sofascore reader initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Sofascore reader: {e}")
            raise IngestionError(f"Cannot initialize Sofascore: {e}")
    
    def _fetch_data(
        self,
        league: str,
        season: str,
        stat_type: str = 'schedule',
        **kwargs
    ) -> pd.DataFrame:
        """
        Fetch data from Sofascore.
        
        Args:
            league: League identifier (from league_dict.json)
            season: Season identifier (e.g., '2023-2024')
            stat_type: Type of data to fetch:
                - 'schedule': Match schedule and results
                - 'team_stats': Team statistics for the season
                - 'player_stats': Player statistics for the season
                - 'lineups': Team lineups (requires match_id)
                - 'standings': League standings
                - 'shotmap': Shot map data (requires match_id)
            match_id: Specific match ID (for lineups/shotmap)
            team_id: Specific team ID (for team-specific stats)
            player_id: Specific player ID (for player-specific stats)
            
        Returns:
            pandas DataFrame with requested data
        """
        stat_type = kwargs.get('stat_type', 'schedule')
        match_id = kwargs.get('match_id', None)
        team_id = kwargs.get('team_id', None)
        player_id = kwargs.get('player_id', None)
        
        if stat_type not in self.STAT_TYPES:
            raise ValueError(f"Invalid stat_type: {stat_type}. Must be one of {self.STAT_TYPES}")
        
        try:
            if stat_type == 'schedule':
                return self._fetch_schedule(league, season)
            elif stat_type == 'team_stats':
                return self._fetch_team_stats(league, season, team_id)
            elif stat_type == 'player_stats':
                return self._fetch_player_stats(league, season, player_id)
            elif stat_type == 'lineups':
                if not match_id:
                    raise ValueError("match_id required for lineups")
                return self._fetch_lineups(league, season, match_id)
            elif stat_type == 'standings':
                return self._fetch_standings(league, season)
            elif stat_type == 'shotmap':
                if not match_id:
                    raise ValueError("match_id required for shotmap")
                return self._fetch_shotmap(league, season, match_id)
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
        self.logger.info(f"Fetching Sofascore schedule for {league} - {season}")
        
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
        
        self.logger.info(f"Fetched {len(df)} matches from Sofascore")
        return df
    
    def _fetch_team_stats(
        self,
        league: str,
        season: str,
        team_id: Optional[int] = None
    ) -> pd.DataFrame:
        """Fetch team statistics for a season."""
        self.logger.info(f"Fetching Sofascore team stats for {league} - {season}")
        
        if team_id:
            df = self.reader.read_team_season_stats(
                leagues=league,
                seasons=season,
                team_ids=team_id,
            )
        else:
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
    
    def _fetch_player_stats(
        self,
        league: str,
        season: str,
        player_id: Optional[int] = None
    ) -> pd.DataFrame:
        """Fetch player statistics for a season."""
        self.logger.info(f"Fetching Sofascore player stats for {league} - {season}")
        
        if player_id:
            df = self.reader.read_player_season_stats(
                leagues=league,
                seasons=season,
                player_ids=player_id,
            )
        else:
            df = self.reader.read_player_season_stats(
                leagues=league,
                seasons=season,
            )
        
        if df is None or df.empty:
            self.logger.warning(f"No player stats data for {league} {season}")
            return pd.DataFrame()
        
        # Normalize
        if 'player' in df.columns:
            df = self.normalize_team_names(df, 'player')  # Reuse normalization logic
        
        self.logger.info(f"Fetched {len(df)} player stat records")
        return df
    
    def _fetch_lineups(self, league: str, season: str, match_id: int) -> pd.DataFrame:
        """Fetch team lineups for a match."""
        self.logger.info(f"Fetching Sofascore lineups for match {match_id}")
        
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
        self.logger.info(f"Fetching Sofascore standings for {league} - {season}")
        
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
    
    def _fetch_shotmap(self, league: str, season: str, match_id: int) -> pd.DataFrame:
        """Fetch shot map data for a match."""
        self.logger.info(f"Fetching Sofascore shotmap for match {match_id}")
        
        df = self.reader.read_shotmap(
            match_id=match_id,
            force_cache=True,
        )
        
        if df is None or df.empty:
            self.logger.warning(f"No shotmap data for match {match_id}")
            return pd.DataFrame()
        
        self.logger.info(f"Fetched {len(df)} shots for match {match_id}")
        return df
    
    def get_available_leagues(self) -> Dict[str, str]:
        """
        Get available leagues from Sofascore.
        
        Returns:
            Dict mapping league names to identifiers
        """
        try:
            return self.config.available_leagues.get('sofascore', {})
        except Exception as e:
            self.logger.error(f"Error getting available leagues: {e}")
            return {}
    
    def validate_league(self, league: str) -> bool:
        """Validate that a league is available in Sofascore."""
        available = self.get_available_leagues()
        return league in available.values() or league in available.keys()
    
    def fetch_comprehensive_match_data(
        self,
        league: str,
        season: str,
        match_id: int
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch all available data for a specific match.
        
        Args:
            league: League identifier
            season: Season identifier
            match_id: Match ID
            
        Returns:
            Dict with keys: 'schedule', 'lineups', 'shotmap'
        """
        results = {}
        
        try:
            # Get basic match info from schedule
            schedule = self._fetch_schedule(league, season)
            if not schedule.empty:
                results['schedule'] = schedule[schedule['match_id'] == match_id]
            
            # Get lineups
            results['lineups'] = self._fetch_lineups(league, season, match_id)
            
            # Get shotmap
            results['shotmap'] = self._fetch_shotmap(league, season, match_id)
            
        except Exception as e:
            self.logger.error(f"Error fetching comprehensive data for match {match_id}: {e}")
        
        return results
