"""
ClubElo data ingestion service.

ClubElo provides team Elo ratings that are:
- Updated after every match
- Comparable across leagues and time
- Useful for team strength analysis and predictions

Philosophy: Using soccerdata's ClubElo wrapper with proper date handling
and efficient caching of historical ratings.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

try:
    import soccerdata as sd
except ImportError:
    raise ImportError("soccerdata is required. Install with: pip install soccerdata")

from .base import BaseIngestionService, SourceUnavailableError

logger = logging.getLogger(__name__)


class ClubEloService(BaseIngestionService):
    """
    Ingestion service for ClubElo team ratings.
    
    ClubElo provides:
    - Daily Elo ratings for teams worldwide
    - Historical rankings
    - League-specific ratings
    
    Key features:
    - Ratings updated after each match
    - Home advantage factored in
    - Margin of victory considered
    - Opponent strength weighted
    
    Uses soccerdata.ClubElo wrapper which handles:
    - HTML table parsing from clubelo.com
    - Local caching
    - Date-based queries
    """
    
    source_name = "clubelo"
    
    def __init__(self, config: Any, session: Any = None):
        """
        Initialize ClubElo service.
        
        Args:
            config: Application configuration
            session: Optional database session
        """
        super().__init__(config, session)
        
        self.clubelo = sd.ClubElo(
            proxy=None,
            no_cache=not getattr(config, 'use_cache', True),
        )
    
    def _fetch_data(self, league: str, season: str) -> pd.DataFrame:
        """
        Fetch Elo data by reading team history for a league.
        
        Note: ClubElo doesn't have direct league/season queries,
        so we fetch by date range and filter.
        """
        # This is handled by read_by_date or read_team_history
        raise NotImplementedError("Use read_by_date or read_team_history instead")
    
    def read_by_date(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        Read Elo ratings for a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD) or None for today
        
        Returns:
            DataFrame with columns:
            - Rank, Club, Country, Level, Elo, From, To
        """
        try:
            df = self.clubelo.read_by_date(date=date)
            
            if df is not None and not df.empty:
                self.logger.info(f"Fetched {len(df)} team ratings for {date or 'today'}")
            
            return df
        
        except Exception as e:
            self.logger.error(f"Failed to read Elo by date: {e}")
            return pd.DataFrame()
    
    def read_team_history(self, team: str) -> pd.DataFrame:
        """
        Read Elo history for a specific team.
        
        Args:
            team: Team name as it appears on ClubElo
        
        Returns:
            DataFrame with columns:
            - From, To, Elo, Rank
        """
        try:
            df = self.clubelo.read_team_history(team=team)
            
            if df is not None and not df.empty:
                self.logger.info(f"Fetched {len(df)} Elo records for team '{team}'")
            
            return df
        
        except Exception as e:
            self.logger.error(f"Failed to read team history: {e}")
            return pd.DataFrame()
    
    def read_league_ratings(
        self,
        league: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Read Elo ratings for teams in a league over a date range.
        
        This is a convenience method that:
        1. Gets current ratings for the league
        2. Optionally filters by date range
        
        Args:
            league: League identifier (used for filtering)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            DataFrame with Elo ratings
        """
        # Get most recent ratings
        df = self.read_by_date()
        
        if df.empty:
            return df
        
        # Filter by country if league mapping is available
        # This requires league_dict.json mappings
        league_dict = self.config.load_league_dict()
        leagues_config = league_dict.get('leagues', {})
        
        if league in leagues_config:
            country_code = leagues_config[league].get('country_code')
            if country_code:
                df = df[df['Country'] == country_code]
        
        # Filter by date range if specified
        if start_date:
            df = df[pd.to_datetime(df['To']) >= pd.to_datetime(start_date)]
        if end_date:
            df = df[pd.to_datetime(df['To']) <= pd.to_datetime(end_date)]
        
        return df
    
    def get_available_leagues(self) -> Dict[str, str]:
        """
        Get dictionary of available leagues.
        
        ClubElo uses country_level format (e.g., ENG_1, ESP_1).
        
        Returns:
            Dict mapping league codes to names
        """
        # ClubElo doesn't have a direct available_leagues method
        # We can infer from current ratings
        try:
            df = self.read_by_date()
            if df.empty:
                return {}
            
            # Group by country and level
            leagues = {}
            for _, row in df.iterrows():
                key = f"{row['Country']}_{row['Level']}"
                if key not in leagues:
                    leagues[key] = f"{row['Country']} Level {row['Level']}"
            
            return leagues
        
        except Exception as e:
            self.logger.error(f"Failed to get available leagues: {e}")
            return {}
    
    def normalize_for_storage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize ClubElo DataFrame for database storage.
        
        Performs:
        - Column name normalization
        - Date conversion
        - Team name normalization
        
        Args:
            df: Raw ClubElo DataFrame
        
        Returns:
            Normalized DataFrame
        """
        if df is None or df.empty:
            return df
        
        df = df.copy()
        
        # Normalize column names
        df.columns = (
            df.columns
            .str.lower()
            .str.replace(r'[^\w]', '_', regex=True)
        )
        
        # Rename for consistency
        rename_map = {
            'club': 'team_name',
            'elo': 'elo_rating',
            'rank': 'rank',
            'country': 'country',
            'level': 'level',
            'from': 'valid_from',
            'to': 'valid_to',
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        # Convert dates
        for col in ['valid_from', 'valid_to']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Normalize team names
        if 'team_name' in df.columns:
            df = self.normalize_team_names(df, 'team_name')
        
        return df
    
    def fetch_historical_snapshot(
        self,
        start_date: str,
        end_date: str,
        step_days: int = 30
    ) -> pd.DataFrame:
        """
        Fetch multiple historical snapshots of Elo ratings.
        
        Useful for building time series of team strengths.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            step_days: Days between snapshots
        
        Returns:
            Combined DataFrame with snapshot_date column
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        all_dfs = []
        current = start
        
        while current <= end:
            try:
                df = self.read_by_date(current.strftime('%Y-%m-%d'))
                if not df.empty:
                    df['snapshot_date'] = current
                    all_dfs.append(df)
                
                self.logger.debug(f"Fetched snapshot for {current.date()}")
            
            except Exception as e:
                self.logger.warning(f"Failed to fetch snapshot for {current.date()}: {e}")
            
            current += timedelta(days=step_days)
        
        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        
        return pd.DataFrame()
