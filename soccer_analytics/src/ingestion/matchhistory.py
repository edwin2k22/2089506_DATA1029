"""
MatchHistory (Football-Data.co.uk) ingestion service.

Football-Data.co.uk provides historical match results with:
- Match outcomes and scores
- Team statistics (shots, corners, cards)
- Betting odds from multiple bookmakers (pre-match and closing)

Philosophy: Using soccerdata's MatchHistory wrapper for CSV parsing,
with proper handling of varying column structures across seasons/leagues.
"""

import logging
from typing import Optional, List, Dict, Any
import pandas as pd

try:
    import soccerdata as sd
except ImportError:
    raise ImportError("soccerdata is required. Install with: pip install soccerdata")

from .base import BaseIngestionService, SourceUnavailableError

logger = logging.getLogger(__name__)


class MatchHistoryService(BaseIngestionService):
    """
    Ingestion service for Football-Data.co.uk match history.
    
    Provides:
    - Historical match results
    - Team match statistics
    - Betting odds from multiple bookmakers
    
    Column conventions (following Football-Data.co.uk):
    - Div: League division code
    - Date: Match date
    - Time: Match time
    - HomeTeam, AwayTeam: Team names
    - FTHG, FTAG: Full-time home/away goals
    - FTR: Full-time result (H/D/A)
    - HTHG, HTAG: Half-time goals
    - HTR: Half-time result
    - HS, AS: Shots (home/away)
    - HST, AST: Shots on target
    - HC, AC: Corners
    - HF, AF: Fouls
    - HY, AY: Yellow cards
    - HR, AR: Red cards
    
    Odds columns (examples):
    - B365H, B365D, B365A: Bet365 odds
    - PSH, PSD, PSA: Pinnacle odds
    - WHH, WHD, WHA: William Hill odds
    - PSCH, PSCD, PSCA: Closing odds (Pinnacle)
    
    Note: Available columns vary by season and league.
    """
    
    source_name = "matchhistory"
    
    # Common bookmaker prefixes in odds columns
    BOOKMAKERS = {
        'B365': 'Bet365',
        'PS': 'Pinnacle',
        'WH': 'William Hill',
        'IW': 'Interwetten',
        'VC': 'Victor Chandler',
        'GB': 'Gamebookers',
        'BS': 'Blue Square',
        'SB': 'Sportingbet',
        'SY': 'Stan James',
        'SS': 'SkyBet',
        'MR': 'Marathonbet',
        '10': 'Betten',
        '12': '12Bet',
        '18': '18Bet',
        '1X': '1xBet',
    }
    
    def __init__(self, config: Any, session: Any = None):
        """
        Initialize MatchHistory service.
        
        Args:
            config: Application configuration
            session: Optional database session
        """
        super().__init__(config, session)
        
        self.matchhistory = sd.MatchHistory(
            leagues=self._get_league_ids(),
            proxy=None,  # Can be configured via environment
            no_cache=not getattr(config, 'use_cache', True),
        )
    
    def _get_league_ids(self) -> Optional[List[str]]:
        """Get list of league IDs (Div codes) to use."""
        return None  # Use all available
    
    def _fetch_data(self, league: str, season: str) -> pd.DataFrame:
        """
        Fetch match history data.
        
        Args:
            league: League Div code (e.g., 'E0' for Premier League)
            season: Season (e.g., '2023-2024')
        
        Returns:
            DataFrame with match results and odds
        """
        try:
            return self.matchhistory.read_match_history(
                leagues=[league],
                seasons=[season],
            )
        except Exception as e:
            self.logger.error(f"MatchHistory fetch error: {e}")
            raise SourceUnavailableError(f"MatchHistory error: {str(e)}")
    
    def read_match_history(
        self,
        league: Optional[str] = None,
        season: Optional[str] = None,
        force_cache: bool = False
    ) -> pd.DataFrame:
        """
        Read match history for a league season.
        
        Note: soccerdata's MatchHistory.read_games() doesn't accept parameters.
        It returns all available data. Filtering is done post-fetch.
        
        Args:
            league: League Div code (for post-filtering)
            season: Season identifier (for post-filtering)
            force_cache: Force refresh of cached data
        
        Returns:
            DataFrame with matches, stats, and odds
        """
        try:
            # soccerdata MatchHistory.read_games() doesn't accept parameters
            # It fetches all available data from cache or source
            df = self.matchhistory.read_games()
            
            if df is None or df.empty:
                return df
            
            # Post-filter by league and season if specified
            if league and 'Div' in df.columns:
                df = df[df['Div'] == league]
            
            if season and 'Season' in df.columns:
                df = df[df['Season'] == season]
            elif season and 'Date' in df.columns:
                # Infer season from date
                try:
                    year = int(season.split('-')[0])
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df[df['Date'].dt.year >= year]
                except:
                    pass
            
            if not df.empty:
                self.logger.info(
                    f"Fetched {len(df)} matches from MatchHistory"
                    + (f" for {league} {season}" if league else "")
                )
            
            return df
        
        except Exception as e:
            self.logger.error(f"Failed to read match history: {e}")
            return pd.DataFrame()
    
    def extract_odds(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract betting odds from match history DataFrame.
        
        Identifies odds columns by their prefixes and creates
        a normalized odds DataFrame.
        
        Args:
            df: Raw match history DataFrame
        
        Returns:
            Normalized DataFrame with odds data
        """
        if df is None or df.empty:
            return pd.DataFrame()
        
        odds_records = []
        
        # Identify odds columns
        odds_cols = [c for c in df.columns if any(
            c.startswith(prefix) for prefix in self.BOOKMAKERS.keys()
        )]
        
        for idx, row in df.iterrows():
            # Get match identifiers
            match_key = {
                'date': row.get('Date'),
                'home_team': row.get('HomeTeam'),
                'away_team': row.get('AwayTeam'),
                'div': row.get('Div'),
            }
            
            # Extract odds for each bookmaker
            for prefix, bookmaker_name in self.BOOKMAKERS.items():
                home_col = f'{prefix}H'
                draw_col = f'{prefix}D'
                away_col = f'{prefix}A'
                
                # Check for closing odds (PSC = Pinnacle Closing)
                is_closing = prefix == 'PSC'
                
                if home_col in row and pd.notna(row[home_col]):
                    odds_records.append({
                        **match_key,
                        'bookmaker': bookmaker_name,
                        'bookmaker_code': prefix,
                        'home_odd': row[home_col],
                        'draw_odd': row.get(draw_col),
                        'away_odd': row.get(away_col),
                        'is_closing': is_closing,
                    })
        
        return pd.DataFrame(odds_records)
    
    def get_available_leagues(self) -> Dict[str, str]:
        """
        Get dictionary of available leagues.
        
        Returns:
            Dict mapping Div codes to league names
        """
        try:
            return self.matchhistory.available_leagues()
        except Exception as e:
            self.logger.error(f"Failed to get available leagues: {e}")
            return {}
    
    def normalize_for_storage(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Normalize match history data for database storage.
        
        Splits into separate DataFrames for:
        - Matches (results and basic info)
        - Team stats (match-level statistics)
        - Odds (betting odds)
        
        Args:
            df: Raw MatchHistory DataFrame
        
        Returns:
            Dict with keys 'matches', 'team_stats', 'odds'
        """
        if df is None or df.empty:
            return {'matches': pd.DataFrame(), 'team_stats': pd.DataFrame(), 'odds': pd.DataFrame()}
        
        # Normalize column names
        df = df.copy()
        df.columns = (
            df.columns
            .str.lower()
            .str.replace(r'[^\w]', '_', regex=True)
        )
        
        # Normalize dates
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Normalize team names
        for col in ['home_team', 'away_team']:
            if col in df.columns:
                df = self.normalize_team_names(df, col)
        
        # Separate matches data
        match_cols = [
            'div', 'date', 'time', 'home_team', 'away_team',
            'fthg', 'ftag', 'ftr', 'hthg', 'htag', 'htr',
            'referee', 'attendance', 'venue'
        ]
        matches_df = df[[c for c in match_cols if c in df.columns]].copy()
        
        # Separate team statistics
        stats_cols = [
            'hs', 'as', 'hst', 'ast', 'hc', 'ac', 'hf', 'af',
            'hy', 'ay', 'hr', 'ar'
        ]
        stats_df = df[[c for c in stats_cols if c in df.columns]].copy()
        
        # Add team context to stats (home/away)
        if not stats_df.empty:
            stats_df['home_team'] = df.get('home_team')
            stats_df['away_team'] = df.get('away_team')
            stats_df['date'] = df.get('date')
        
        # Extract odds
        odds_df = self.extract_odds(df)
        
        return {
            'matches': matches_df,
            'team_stats': stats_df,
            'odds': odds_df,
        }
    
    def validate_odds(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean odds data.
        
        Checks:
        - Odds are positive numbers
        - Sum of 1X2 odds implies reasonable margin
        - No obvious data errors
        
        Args:
            df: Odds DataFrame
        
        Returns:
            Validated DataFrame with invalid rows removed
        """
        if df is None or df.empty:
            return df
        
        # Filter valid odds (positive values)
        valid_mask = (
            (df['home_odd'] > 0) &
            (df['draw_odd'] > 0) &
            (df['away_odd'] > 0)
        )
        
        # Check implied probability (should be > 1 due to bookmaker margin)
        # Typical margin is 2-10%
        df_valid = df[valid_mask].copy()
        implied_prob = (
            1/df_valid['home_odd'] +
            1/df_valid['draw_odd'] +
            1/df_valid['away_odd']
        )
        valid_margin = (implied_prob >= 1.0) & (implied_prob <= 1.20)
        
        return df_valid[valid_margin]
