"""
Main ingestion orchestrator.

Coordinates data ingestion from multiple sources:
- Manages source-specific services
- Handles league/season iteration
- Performs upsert operations to database
- Logs ingestion progress and results

Philosophy: Idempotent ingestion jobs with proper error handling,
batch processing, and comprehensive logging for monitoring.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from ..config import settings
from ..storage.database import get_database
from ..storage.models import (
    DimLeague, DimSeason, DimTeam, DimPlayer,
    FactMatch, FactTeamSeasonStats, FactPlayerSeasonStats,
    FactOdds, FactEloHistory, IngestionLog
)

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """
    Orchestrates data ingestion from all configured sources.
    
    Responsibilities:
    - Initialize source-specific ingestion services
    - Iterate over configured leagues and seasons
    - Fetch, normalize, and store data
    - Track ingestion progress and errors
    - Provide idempotent operations (safe to re-run)
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the orchestrator.
        
        Args:
            database_url: Database connection URL (uses config default if None)
        """
        self.config = settings
        self.database_url = database_url or self.config.database_url
        
        # Initialize database
        self.db = get_database(self.database_url)
        self.db.init_db()
        
        # Source services (lazy-loaded)
        self._services = {}
        
        # Current run tracking
        self.run_id = str(uuid.uuid4())
        self.session = None
    
    def _get_service(self, source_name: str, session: Session = None):
        """
        Get or create ingestion service for a source.
        
        Args:
            source_name: Name of the source (fbref, matchhistory, etc.)
            session: Optional database session
        
        Returns:
            Initialized service instance
        """
        if source_name in self._services:
            return self._services[source_name]
        
        # Lazy import to avoid circular dependencies
        if source_name == 'fbref':
            from ..ingestion.fbref import FBrefService
            service_class = FBrefService
        elif source_name == 'matchhistory':
            from ..ingestion.matchhistory import MatchHistoryService
            service_class = MatchHistoryService
        elif source_name == 'clubelo':
            from ..ingestion.clubelo import ClubEloService
            service_class = ClubEloService
        elif source_name == 'whoscored':
            # Placeholder for future implementation
            logger.warning("WhoScored service not yet implemented")
            return None
        elif source_name == 'sofascore':
            logger.warning("Sofascore service not yet implemented")
            return None
        elif source_name == 'espn':
            logger.warning("ESPN service not yet implemented")
            return None
        elif source_name == 'understat':
            logger.warning("Understat service not yet implemented")
            return None
        elif source_name == 'sofifa':
            logger.warning("SoFIFA service not yet implemented")
            return None
        else:
            logger.error(f"Unknown source: {source_name}")
            return None
        
        service = service_class(config=self.config, session=session)
        self._services[source_name] = service
        return service
    
    def get_or_create_league(
        self,
        session: Session,
        name: str,
        country: Optional[str] = None,
        country_code: Optional[str] = None,
        level: int = 1,
        source_ids: Optional[Dict] = None
    ) -> DimLeague:
        """
        Get existing league or create new one.
        
        Args:
            session: Database session
            name: League name
            country: Country name
            country_code: Country code (ISO)
            level: Division level (1 = top)
            source_ids: Dict of source-specific identifiers
        
        Returns:
            DimLeague instance
        """
        league = session.query(DimLeague).filter_by(name=name).first()
        
        if league is None:
            league = DimLeague(
                name=name,
                country=country,
                country_code=country_code,
                level=level,
                source_ids=source_ids or {}
            )
            session.add(league)
            session.commit()
            logger.info(f"Created league: {name}")
        else:
            # Update if needed
            if source_ids:
                current_ids = league.source_ids or {}
                current_ids.update(source_ids)
                league.source_ids = current_ids
        
        return league
    
    def get_or_create_season(
        self,
        session: Session,
        league: DimLeague,
        year: str
    ) -> DimSeason:
        """
        Get existing season or create new one.
        
        Args:
            session: Database session
            league: Parent league
            year: Season year (e.g., "2023-2024")
        
        Returns:
            DimSeason instance
        """
        season = session.query(DimSeason).filter_by(
            league_id=league.id,
            year=year
        ).first()
        
        if season is None:
            # Parse year range
            try:
                start_year = int(year.split('-')[0])
                end_year = int(year.split('-')[1]) if '-' in year else start_year + 1
                
                start_date = f"{start_year}-{league.season_start_month:02d}-01"
                end_date = f"{end_year}-{league.season_end_month:02d}-28"
            except:
                start_date = None
                end_date = None
            
            season = DimSeason(
                league_id=league.id,
                year=year,
                start_date=start_date,
                end_date=end_date,
                is_current=True  # Mark as current, can be updated later
            )
            session.add(season)
            session.commit()
            logger.info(f"Created season: {year} for {league.name}")
        
        return season
    
    def get_or_create_team(
        self,
        session: Session,
        name: str,
        short_name: Optional[str] = None,
        country: Optional[str] = None,
        source_ids: Optional[Dict] = None
    ) -> DimTeam:
        """
        Get existing team or create new one.
        
        Args:
            session: Database session
            name: Team name
            short_name: Short name/abbreviation
            country: Country
            source_ids: Source-specific identifiers
        
        Returns:
            DimTeam instance
        """
        team = session.query(DimTeam).filter_by(name=name).first()
        
        if team is None:
            team = DimTeam(
                name=name,
                short_name=short_name,
                country=country,
                alternative_names=[],
                source_ids=source_ids or {}
            )
            session.add(team)
            session.commit()
            logger.debug(f"Created team: {name}")
        else:
            # Update source IDs
            if source_ids:
                current_ids = team.source_ids or {}
                current_ids.update(source_ids)
                team.source_ids = current_ids
        
        return team
    
    def ingest_fbref_schedule(
        self,
        league_name: str,
        season: str,
        league_config: Optional[Dict] = None
    ) -> Tuple[int, int]:
        """
        Ingest match schedule from FBref.
        
        Args:
            league_name: League identifier
            season: Season identifier
            league_config: Optional league configuration from league_dict
        
        Returns:
            Tuple of (matches_processed, matches_inserted)
        """
        session = self.db.SessionLocal()
        service = self._get_service('fbref', session)
        
        if service is None:
            return 0, 0
        
        try:
            # Fetch schedule
            df = service.read_schedule(league_name, season)
            
            if df is None or df.empty:
                logger.warning(f"No schedule data for {league_name} {season}")
                return 0, 0
            
            # Get or create league/season
            league_config = league_config or {}
            league = self.get_or_create_league(
                session,
                name=league_config.get('name', league_name),
                country=league_config.get('country'),
                country_code=league_config.get('country_code'),
                level=league_config.get('level', 1),
                source_ids={'FBref': league_name}
            )
            db_season = self.get_or_create_season(session, league, season)
            
            inserted = 0
            for _, row in df.iterrows():
                # Get or create teams
                home_team = self.get_or_create_team(
                    session,
                    name=row.get('Home', row.get('HomeTeam', '')),
                    source_ids={'FBref': row.get('Home', '')}
                )
                away_team = self.get_or_create_team(
                    session,
                    name=row.get('Away', row.get('AwayTeam', '')),
                    source_ids={'FBref': row.get('Away', '')}
                )
                
                # Check for existing match
                match_date = pd.to_datetime(row.get('Date'))
                existing = session.query(FactMatch).filter_by(
                    league_id=league.id,
                    season_id=db_season.id,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    match_date=match_date
                ).first()
                
                if existing is None:
                    match = FactMatch(
                        league_id=league.id,
                        season_id=db_season.id,
                        home_team_id=home_team.id,
                        away_team_id=away_team.id,
                        match_date=match_date,
                        match_time=row.get('Time'),
                        home_score=row.get('HG') if pd.notna(row.get('HG')) else None,
                        away_score=row.get('AG') if pd.notna(row.get('AG')) else None,
                        halftime_home_score=row.get('H HG') if pd.notna(row.get('H HG')) else None,
                        halftime_away_score=row.get('H AG') if pd.notna(row.get('H AG')) else None,
                        venue=row.get('Venue'),
                        attendance=row.get('Attendance') if pd.notna(row.get('Attendance')) else None,
                        referee=row.get('Referee'),
                        status='completed' if pd.notna(row.get('HG')) else 'scheduled',
                        round=row.get('Round'),
                        source_urls={'FBref': row.get('URL', '')}
                    )
                    session.add(match)
                    inserted += 1
            
            session.commit()
            logger.info(f"Ingested {inserted} matches from FBref for {league_name} {season}")
            
            return len(df), inserted
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error ingesting FBref schedule: {e}")
            return 0, 0
        
        finally:
            session.close()
    
    def ingest_matchhistory(
        self,
        league_div: str,
        season: str,
        league_config: Optional[Dict] = None
    ) -> Tuple[int, int, int]:
        """
        Ingest match history with odds from Football-Data.co.uk.
        
        Args:
            league_div: League Div code (e.g., 'E0')
            season: Season identifier
            league_config: Optional league configuration
        
        Returns:
            Tuple of (matches_processed, matches_inserted, odds_inserted)
        """
        session = self.db.SessionLocal()
        service = self._get_service('matchhistory', session)
        
        if service is None:
            return 0, 0, 0
        
        try:
            # Fetch match history
            df = service.read_match_history(league_div, season)
            
            if df is None or df.empty:
                logger.warning(f"No match history for {league_div} {season}")
                return 0, 0, 0
            
            # Normalize and split
            normalized = service.normalize_for_storage(df)
            matches_df = normalized['matches']
            odds_df = normalized['odds']
            
            # Get or create league
            league_config = league_config or {}
            league = self.get_or_create_league(
                session,
                name=league_config.get('name', league_div),
                country=league_config.get('country'),
                country_code=league_config.get('country_code'),
                level=league_config.get('level', 1),
                source_ids={'MatchHistory': league_div}
            )
            db_season = self.get_or_create_season(session, league, season)
            
            # Insert matches
            matches_inserted = 0
            for _, row in matches_df.iterrows():
                home_team = self.get_or_create_team(session, str(row.get('home_team', '')))
                away_team = self.get_or_create_team(session, str(row.get('away_team', '')))
                
                existing = session.query(FactMatch).filter_by(
                    league_id=league.id,
                    season_id=db_season.id,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    match_date=row.get('date')
                ).first()
                
                if existing is None:
                    match = FactMatch(
                        league_id=league.id,
                        season_id=db_season.id,
                        home_team_id=home_team.id,
                        away_team_id=away_team.id,
                        match_date=row.get('date'),
                        home_score=row.get('fthg'),
                        away_score=row.get('ftag'),
                        status='completed'
                    )
                    session.add(match)
                    matches_inserted += 1
            
            session.commit()
            
            # Insert odds
            odds_inserted = 0
            if not odds_df.empty:
                for _, row in odds_df.iterrows():
                    # Find matching match
                    match = session.query(FactMatch).filter_by(
                        league_id=league.id,
                        season_id=db_season.id,
                        match_date=pd.to_datetime(row.get('date'))
                    ).first()
                    
                    if match:
                        odd = FactOdds(
                            match_id=match.id,
                            bookmaker=row.get('bookmaker', ''),
                            home_odd=row.get('home_odd'),
                            draw_odd=row.get('draw_odd'),
                            away_odd=row.get('away_odd'),
                            is_closing=row.get('is_closing', False),
                            source='MatchHistory'
                        )
                        session.add(odd)
                        odds_inserted += 1
                
                session.commit()
            
            logger.info(
                f"Ingested {matches_inserted} matches and {odds_inserted} odds "
                f"from MatchHistory for {league_div} {season}"
            )
            
            return len(matches_df), matches_inserted, odds_inserted
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error ingesting MatchHistory: {e}")
            return 0, 0, 0
        
        finally:
            session.close()
    
    def ingest_clubelo(self, date: Optional[str] = None) -> Tuple[int, int]:
        """
        Ingest ClubElo ratings.
        
        Args:
            date: Specific date (YYYY-MM-DD) or None for today
        
        Returns:
            Tuple of (ratings_processed, ratings_inserted)
        """
        session = self.db.SessionLocal()
        service = self._get_service('clubelo', session)
        
        if service is None:
            return 0, 0
        
        try:
            df = service.read_by_date(date)
            
            if df is None or df.empty:
                logger.warning(f"No Elo data for {date or 'today'}")
                return 0, 0
            
            normalized = service.normalize_for_storage(df)
            
            inserted = 0
            for _, row in normalized.iterrows():
                team = self.get_or_create_team(
                    session,
                    name=row.get('team_name', ''),
                    country=row.get('country')
                )
                
                # Check for existing rating
                existing = session.query(FactEloHistory).filter_by(
                    team_id=team.id,
                    date=row.get('valid_to').date() if row.get('valid_to') else None
                ).first()
                
                if existing is None:
                    elo = FactEloHistory(
                        team_id=team.id,
                        date=row.get('valid_to').date() if row.get('valid_to') else None,
                        elo_rating=row.get('elo_rating'),
                        rank=row.get('rank'),
                        source='ClubElo'
                    )
                    session.add(elo)
                    inserted += 1
            
            session.commit()
            logger.info(f"Ingested {inserted} Elo ratings")
            
            return len(df), inserted
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error ingesting ClubElo: {e}")
            return 0, 0
        
        finally:
            session.close()
    
    def run_full_ingestion(
        self,
        sources: Optional[List[str]] = None,
        leagues: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Run full ingestion for all configured sources and leagues.
        
        Args:
            sources: List of sources to ingest (None = all active)
            leagues: List of (league, season) tuples (None = defaults)
        
        Returns:
            Dict with ingestion statistics
        """
        sources = sources or self.config.get_active_sources_list()
        leagues = leagues or self.config.get_default_leagues_list()
        
        # Load league configurations
        league_dict = self.config.load_league_dict()
        leagues_config = league_dict.get('leagues', {})
        
        stats = {
            'run_id': self.run_id,
            'started_at': datetime.now().isoformat(),
            'sources': {},
            'summary': {
                'total_processed': 0,
                'total_inserted': 0,
            }
        }
        
        logger.info(f"Starting full ingestion: sources={sources}, leagues={leagues}")
        
        for source in sources:
            source_stats = {'leagues': {}}
            
            for league_key, season in leagues:
                league_config = leagues_config.get(league_key, {})
                
                # Get source-specific league identifier
                source_id_key = {
                    'fbref': 'FBref',
                    'matchhistory': 'MatchHistory',
                    'clubelo': 'ClubElo',
                }.get(source)
                
                if source_id_key:
                    source_league = league_config.get(source_id_key)
                    if not source_league:
                        logger.warning(f"No {source} ID for {league_key}, skipping")
                        continue
                else:
                    source_league = league_key
                
                # Ingest based on source
                if source == 'fbref':
                    processed, inserted = self.ingest_fbref_schedule(
                        source_league, season, league_config
                    )
                    key = f"{league_key}:{season}"
                    source_stats['leagues'][key] = {
                        'processed': processed,
                        'inserted': inserted
                    }
                
                elif source == 'matchhistory':
                    processed, inserted, odds = self.ingest_matchhistory(
                        source_league, season, league_config
                    )
                    key = f"{league_key}:{season}"
                    source_stats['leagues'][key] = {
                        'processed': processed,
                        'inserted': inserted,
                        'odds_inserted': odds
                    }
                
                elif source == 'clubelo':
                    processed, inserted = self.ingest_clubelo()
                    source_stats['current_ratings'] = {
                        'processed': processed,
                        'inserted': inserted
                    }
            
            stats['sources'][source] = source_stats
        
        stats['ended_at'] = datetime.now().isoformat()
        logger.info(f"Ingestion completed: {stats}")
        
        return stats
