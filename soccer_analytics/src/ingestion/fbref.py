"""
FBref data ingestion service.

FBref provides comprehensive football statistics including:
- Match schedules and results
- Team season stats (multiple stat_types: standard, keeper, shooting, passing, etc.)
- Player season stats
- Match-level statistics

Philosophy: Using soccerdata's FBref wrapper with proper caching,
graceful error handling, and consistent DataFrame outputs.
"""

import logging
from typing import Optional, List, Dict, Any
import pandas as pd

try:
    import soccerdata as sd
except ImportError:
    raise ImportError("soccerdata is required. Install with: pip install soccerdata")

from .base import BaseIngestionService, SourceUnavailableError, DataValidationError

logger = logging.getLogger(__name__)


class FBrefService(BaseIngestionService):
    """
    Ingestion service for FBref data.
    
    FBref offers extensive football statistics with multiple stat types:
    - standard: Basic stats (goals, assists, shots, etc.)
    - keeper: Goalkeeper-specific stats
    - shooting: Detailed shooting statistics
    - passing: Passing metrics including progressive passes
    - passing_types: Pass type breakdowns
    - gca: Goal and shot creating actions
    - defense: Defensive actions
    - possession: Possession-based metrics
    - playing_time: Minutes played, appearances
    - misc: Miscellaneous statistics
    
    Uses soccerdata.FBref wrapper which handles:
    - HTML parsing
    - Local caching
    - Rate limiting
    - League identifier mapping
    """
    
    source_name = "fbref"
    
    # Available stat types for team and player stats
    TEAM_STAT_TYPES = [
        'standard', 'keeper', 'keeper_adv', 'shooting', 'passing',
        'passing_types', 'gca', 'defense', 'possession', 'playing_time',
        'misc', 'scores_fixtures'
    ]
    
    PLAYER_STAT_TYPES = [
        'standard', 'keeper', 'shooting', 'passing', 'passing_types',
        'gca', 'defense', 'possession', 'playing_time', 'misc',
        'summary'  # Combined summary stats
    ]
    
    def __init__(self, config: Any, session: Any = None):
        """
        Initialize FBref service.
        
        Args:
            config: Application configuration
            session: Optional database session
        """
        super().__init__(config, session)
        
        # Initialize soccerdata FBref wrapper
        # The wrapper automatically uses SOCCERDATA_DIR from environment/config
        self.fbref = sd.FBref(
            leagues=self._get_league_ids(),
            proxy=self._get_proxy(),
            no_cache=not getattr(config, 'use_cache', True),
        )
    
    def _get_league_ids(self) -> Optional[List[str]]:
        """
        Get list of league IDs to use with FBref.
        
        Returns None to use all available leagues (default).
        Can be overridden to restrict to specific leagues.
        """
        return None  # Use all available leagues
    
    def _get_proxy(self) -> Optional[str]:
        """Get proxy configuration if available."""
        return None  # Proxy can be configured via environment
    
    def _fetch_data(
        self,
        league: str,
        season: str,
        stat_type: str = 'standard',
        level: str = 'team'
    ) -> pd.DataFrame:
        """
        Fetch data from FBref.
        
        Args:
            league: League identifier (e.g., "Premier League", "La Liga")
            season: Season identifier (e.g., "2023-2024")
            stat_type: Type of statistics to fetch
            level: 'team' or 'player'
        
        Returns:
            DataFrame with requested statistics
        
        Raises:
            SourceUnavailableError: If FBref is unavailable
            DataValidationError: If returned data is invalid
        """
        try:
            if level == 'team':
                return self.fbref.read_team_season_stats(
                    leagues=[league],
                    seasons=[season],
                    stat_type=stat_type,
                )
            elif level == 'player':
                return self.fbref.read_player_season_stats(
                    leagues=[league],
                    seasons=[season],
                    stat_type=stat_type,
                )
            else:
                raise ValueError(f"Invalid level: {level}. Must be 'team' or 'player'")
        
        except Exception as e:
            self.logger.error(f"FBref fetch error for {league} {season}: {e}")
            raise SourceUnavailableError(f"FBref error: {str(e)}")
    
    def read_schedule(
        self,
        league: str,
        season: str,
        force_cache: bool = False
    ) -> pd.DataFrame:
        """
        Read match schedule/results for a league season.
        
        Args:
            league: League identifier
            season: Season identifier
            force_cache: Force refresh of cached data
        
        Returns:
            DataFrame with match schedule including:
            - Date, time, venue
            - Home/away teams
            - Scores (FT and HT)
            - Referee, attendance
            - Source URLs
        """
        try:
            df = self.fbref.read_schedule(
                leagues=[league],
                seasons=[season],
                force_cache=force_cache,
            )
            
            if df is not None and not df.empty:
                self.logger.info(
                    f"Fetched {len(df)} matches for {league} {season}"
                )
            
            return df
        
        except Exception as e:
            self.logger.error(f"Failed to read schedule: {e}")
            return pd.DataFrame()
    
    def read_team_stats(
        self,
        league: str,
        season: str,
        stat_types: Optional[List[str]] = None,
        combine: bool = True
    ) -> pd.DataFrame:
        """
        Read team season statistics.
        
        Args:
            league: League identifier
            season: Season identifier
            stat_types: List of stat types to fetch (default: ['standard'])
            combine: If True, combine all stat types into single DataFrame
        
        Returns:
            DataFrame with team statistics. If combine=True, returns
            multi-index columns with stat_type prefixes.
        """
        stat_types = stat_types or ['standard']
        
        # Validate stat types
        invalid = set(stat_types) - set(self.TEAM_STAT_TYPES)
        if invalid:
            self.logger.warning(f"Invalid stat types: {invalid}")
            stat_types = [s for s in stat_types if s in self.TEAM_STAT_TYPES]
        
        if not stat_types:
            return pd.DataFrame()
        
        dfs = []
        for stat_type in stat_types:
            try:
                df = self.fetch_with_retry(
                    league=league,
                    season=season,
                    stat_type=stat_type,
                    level='team'
                )
                
                if df is not None and not df.empty:
                    # Add stat_type prefix to columns for merging
                    if combine and len(stat_types) > 1:
                        df.columns = pd.MultiIndex.from_product(
                            [[stat_type], df.columns],
                            names=['stat_type', 'metric']
                        )
                    dfs.append(df)
                
            except SourceUnavailableError as e:
                self.logger.warning(f"Failed to fetch {stat_type}: {e}")
                continue
        
        if not dfs:
            return pd.DataFrame()
        
        if combine and len(dfs) > 1:
            # Merge on team identifiers
            result = dfs[0]
            for df in dfs[1:]:
                result = result.join(df, how='outer')
            return result
        
        return dfs[0]
    
    def read_player_stats(
        self,
        league: str,
        season: str,
        stat_types: Optional[List[str]] = None,
        combine: bool = True
    ) -> pd.DataFrame:
        """
        Read player season statistics.
        
        Args:
            league: League identifier
            season: Season identifier
            stat_types: List of stat types to fetch
            combine: If True, combine all stat types
        
        Returns:
            DataFrame with player statistics
        """
        stat_types = stat_types or ['standard']
        
        # Validate stat types
        invalid = set(stat_types) - set(self.PLAYER_STAT_TYPES)
        if invalid:
            self.logger.warning(f"Invalid stat types: {invalid}")
            stat_types = [s for s in stat_types if s in self.PLAYER_STAT_TYPES]
        
        if not stat_types:
            return pd.DataFrame()
        
        dfs = []
        for stat_type in stat_types:
            try:
                df = self.fetch_with_retry(
                    league=league,
                    season=season,
                    stat_type=stat_type,
                    level='player'
                )
                
                if df is not None and not df.empty:
                    if combine and len(stat_types) > 1:
                        df.columns = pd.MultiIndex.from_product(
                            [[stat_type], df.columns],
                            names=['stat_type', 'metric']
                        )
                    dfs.append(df)
            
            except SourceUnavailableError as e:
                self.logger.warning(f"Failed to fetch {stat_type}: {e}")
                continue
        
        if not dfs:
            return pd.DataFrame()
        
        if combine and len(dfs) > 1:
            result = dfs[0]
            for df in dfs[1:]:
                result = result.join(df, how='outer')
            return result
        
        return dfs[0]
    
    def get_available_leagues(self) -> Dict[str, str]:
        """
        Get dictionary of available leagues.
        
        Returns:
            Dict mapping league keys to league names
        """
        try:
            return self.fbref.available_leagues()
        except Exception as e:
            self.logger.error(f"Failed to get available leagues: {e}")
            return {}
    
    def normalize_for_storage(self, df: pd.DataFrame, level: str = 'team') -> pd.DataFrame:
        """
        Normalize FBref DataFrame for database storage.
        
        Performs:
        - Column name normalization (lowercase, underscores)
        - Date conversion
        - Team name normalization
        - Removal of duplicate index levels
        
        Args:
            df: Raw FBref DataFrame
            level: 'team' or 'player'
        
        Returns:
            Normalized DataFrame ready for storage
        """
        if df is None or df.empty:
            return df
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip('_') for col in df.columns.values]
        
        # Normalize column names
        df.columns = (
            df.columns
            .str.lower()
            .str.replace(r'[^\w]', '_', regex=True)
            .str.strip('_')
        )
        
        # Rename common columns for consistency
        rename_map = {
            'season': 'season',
            'team': 'team_name',
            'games': 'matches_played',
            'mp': 'matches_played',
            'wins': 'wins',
            'draws': 'draws',
            'losses': 'losses',
            'gf': 'goals_for',
            'ga': 'goals_against',
            'gd': 'goal_difference',
            'pts': 'points',
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        # Normalize dates
        date_cols = [c for c in df.columns if 'date' in c.lower()]
        for col in date_cols:
            df = self.normalize_dates(df, col)
        
        # Normalize team names
        if 'team_name' in df.columns:
            df = self.normalize_team_names(df, 'team_name')
        
        # Remove duplicates based on key columns
        if level == 'team' and 'team_name' in df.columns and 'season' in df.columns:
            df = self.remove_duplicates(df, subset=['team_name', 'season'])
        elif level == 'player' and 'player' in df.columns:
            df = self.remove_duplicates(df, subset=['player', 'team_name', 'season'])
        
        return df
