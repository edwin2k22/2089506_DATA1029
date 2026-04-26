"""
FastAPI application for Soccer Analytics Platform.

Provides REST API endpoints for:
- League and season management
- Match data and statistics
- Team and player information
- Betting odds
- Elo ratings
- Ingestion job control

Philosophy: Clean REST design with pagination, filtering,
and consistent response formats.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.config import settings
from src.storage.database import get_database, get_session, Database
from src.storage.models import (
    DimLeague, DimSeason, DimTeam, DimPlayer,
    FactMatch, FactTeamSeasonStats, FactPlayerSeasonStats,
    FactOdds, FactEloHistory, IngestionLog
)

logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# =============================================================================

class LeagueResponse(BaseModel):
    id: int
    name: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    level: int = 1
    is_active: bool = True
    
    class Config:
        from_attributes = True


class SeasonResponse(BaseModel):
    id: int
    league_id: int
    year: str
    is_current: bool = False
    
    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    id: int
    name: str
    short_name: Optional[str] = None
    country: Optional[str] = None
    
    class Config:
        from_attributes = True


class MatchResponse(BaseModel):
    id: int
    league_id: int
    season_id: int
    match_date: datetime
    home_team_id: int
    away_team_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = 'scheduled'
    
    class Config:
        from_attributes = True


class PlayerResponse(BaseModel):
    id: int
    name: str
    nationality: Optional[str] = None
    position: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedResponse(BaseModel):
    items: List[Any]
    meta: PaginationMeta


# =============================================================================
# APPLICATION LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Soccer Analytics API")
    
    # Initialize database
    db = get_database(settings.database_url)
    db.init_db()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Soccer Analytics API")


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Soccer Analytics API",
    description="""
    REST API for football data from multiple sources.
    
    ## Data Sources
    - **FBref**: Match schedules, team/player statistics
    - **Football-Data.co.uk**: Results, statistics, betting odds
    - **ClubElo**: Team Elo ratings
    - **WhoScored**: Events, lineups (coming soon)
    - **Sofascore**: Detailed stats (coming soon)
    - **ESPN**: Scores, news (coming soon)
    - **Understat**: xG data (coming soon)
    - **SoFIFA**: Player ratings (coming soon)
    
    ## Features
    - Multi-source data aggregation
    - Historical data access
    - Betting odds tracking
    - Team strength metrics (Elo)
    
    ## Data Attribution
    Data provided by respective sources. Please review each source's
    terms of use before using this data commercially.
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def paginate(
    query,
    session: Session,
    page: int = 1,
    page_size: int = 20
) -> tuple:
    """
    Apply pagination to a query.
    
    Args:
        query: SQLAlchemy query
        session: Database session
        page: Page number (1-indexed)
        page_size: Items per page
    
    Returns:
        Tuple of (items, total, pages)
    """
    total = query.count()
    pages = (total + page_size - 1) // page_size
    
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return items, total, pages


# =============================================================================
# API ENDPOINTS - LEAGUES
# =============================================================================

@app.get("/leagues", response_model=List[LeagueResponse], tags=["Leagues"])
def list_leagues(
    country: Optional[str] = Query(None, description="Filter by country"),
    active_only: bool = Query(True, description="Only show active leagues"),
    db: Session = Depends(get_session)
):
    """
    List all available leagues.
    
    Filters:
    - `country`: Filter by country name or code
    - `active_only`: Only show currently active leagues
    """
    query = db.query(DimLeague)
    
    if country:
        query = query.filter(
            (DimLeague.country.ilike(f"%{country}%")) |
            (DimLeague.country_code == country.upper())
        )
    
    if active_only:
        query = query.filter(DimLeague.is_active == True)
    
    return query.order_by(DimLeague.name).all()


@app.get("/leagues/{league_id}", response_model=LeagueResponse, tags=["Leagues"])
def get_league(league_id: int, db: Session = Depends(get_session)):
    """Get details for a specific league."""
    league = db.query(DimLeague).filter(DimLeague.id == league_id).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    return league


@app.get("/leagues/{league_id}/seasons", response_model=List[SeasonResponse], tags=["Leagues"])
def list_league_seasons(league_id: int, db: Session = Depends(get_session)):
    """List all seasons for a league."""
    league = db.query(DimLeague).filter(DimLeague.id == league_id).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    return db.query(DimSeason).filter(
        DimSeason.league_id == league_id
    ).order_by(DimSeason.year.desc()).all()


# =============================================================================
# API ENDPOINTS - MATCHES
# =============================================================================

@app.get("/matches", tags=["Matches"])
def list_matches(
    league_id: Optional[int] = Query(None, description="Filter by league ID"),
    season_id: Optional[int] = Query(None, description="Filter by season ID"),
    team_id: Optional[int] = Query(None, description="Filter by team (home or away)"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_session)
):
    """
    List matches with filtering and pagination.
    
    Filters:
    - `league_id`: Filter by league
    - `season_id`: Filter by season
    - `team_id`: Filter by team (both home and away)
    - `date_from`: Start date (YYYY-MM-DD)
    - `date_to`: End date (YYYY-MM-DD)
    - `status`: Filter by status (completed, scheduled, etc.)
    """
    query = db.query(FactMatch)
    
    if league_id:
        query = query.filter(FactMatch.league_id == league_id)
    
    if season_id:
        query = query.filter(FactMatch.season_id == season_id)
    
    if team_id:
        query = query.filter(
            (FactMatch.home_team_id == team_id) |
            (FactMatch.away_team_id == team_id)
        )
    
    if date_from:
        query = query.filter(FactMatch.match_date >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        query = query.filter(FactMatch.match_date <= datetime.combine(date_to, datetime.max.time()))
    
    if status:
        query = query.filter(FactMatch.status == status)
    
    items, total, pages = paginate(query, db, page, page_size)
    
    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    }


@app.get("/matches/{match_id}", tags=["Matches"])
def get_match(match_id: int, db: Session = Depends(get_session)):
    """Get details for a specific match."""
    match = db.query(FactMatch).filter(FactMatch.id == match_id).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return match


@app.get("/matches/{match_id}/odds", tags=["Matches"])
def get_match_odds(match_id: int, db: Session = Depends(get_session)):
    """Get betting odds for a specific match."""
    match = db.query(FactMatch).filter(FactMatch.id == match_id).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    odds = db.query(FactOdds).filter(FactOdds.match_id == match_id).all()
    return odds


# =============================================================================
# API ENDPOINTS - TEAMS
# =============================================================================

@app.get("/teams", response_model=List[TeamResponse], tags=["Teams"])
def list_teams(
    country: Optional[str] = Query(None, description="Filter by country"),
    search: Optional[str] = Query(None, description="Search in team name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session)
):
    """List teams with optional filtering."""
    query = db.query(DimTeam)
    
    if country:
        query = query.filter(DimTeam.country.ilike(f"%{country}%"))
    
    if search:
        query = query.filter(DimTeam.name.ilike(f"%{search}%"))
    
    return query.order_by(DimTeam.name).all()


@app.get("/teams/{team_id}", response_model=TeamResponse, tags=["Teams"])
def get_team(team_id: int, db: Session = Depends(get_session)):
    """Get details for a specific team."""
    team = db.query(DimTeam).filter(DimTeam.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return team


@app.get("/teams/{team_id}/matches", tags=["Teams"])
def get_team_matches(
    team_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session)
):
    """Get all matches for a team."""
    team = db.query(DimTeam).filter(DimTeam.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    query = db.query(FactMatch).filter(
        (FactMatch.home_team_id == team_id) |
        (FactMatch.away_team_id == team_id)
    ).order_by(FactMatch.match_date.desc())
    
    items, total, pages = paginate(query, db, page, page_size)
    
    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    }


# =============================================================================
# API ENDPOINTS - PLAYERS
# =============================================================================

@app.get("/players", response_model=List[PlayerResponse], tags=["Players"])
def list_players(
    nationality: Optional[str] = Query(None, description="Filter by nationality"),
    position: Optional[str] = Query(None, description="Filter by position"),
    search: Optional[str] = Query(None, description="Search in player name"),
    db: Session = Depends(get_session)
):
    """List players with optional filtering."""
    query = db.query(DimPlayer)
    
    if nationality:
        query = query.filter(DimPlayer.nationality.ilike(f"%{nationality}%"))
    
    if position:
        query = query.filter(DimPlayer.position.ilike(f"%{position}%"))
    
    if search:
        query = query.filter(DimPlayer.name.ilike(f"%{search}%"))
    
    return query.order_by(DimPlayer.name).limit(100).all()


@app.get("/players/{player_id}", response_model=PlayerResponse, tags=["Players"])
def get_player(player_id: int, db: Session = Depends(get_session)):
    """Get details for a specific player."""
    player = db.query(DimPlayer).filter(DimPlayer.id == player_id).first()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return player


# =============================================================================
# API ENDPOINTS - ELO RATINGS
# =============================================================================

@app.get("/elo", tags=["Elo Ratings"])
def get_elo_ratings(
    team_id: Optional[int] = Query(None, description="Filter by team"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_session)
):
    """
    Get ClubElo ratings.
    
    Filters:
    - `team_id`: Filter by specific team
    - `date_from`: Start date
    - `date_to`: End date
    """
    query = db.query(FactEloHistory)
    
    if team_id:
        query = query.filter(FactEloHistory.team_id == team_id)
    
    if date_from:
        query = query.filter(FactEloHistory.date >= date_from)
    
    if date_to:
        query = query.filter(FactEloHistory.date <= date_to)
    
    return query.order_by(
        FactEloHistory.date.desc(),
        FactEloHistory.elo_rating.desc()
    ).limit(limit).all()


# =============================================================================
# API ENDPOINTS - INGESTION MANAGEMENT
# =============================================================================

@app.get("/ingestion/logs", tags=["Ingestion"])
def get_ingestion_logs(
    source: Optional[str] = Query(None, description="Filter by source"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session)
):
    """Get recent ingestion logs."""
    query = db.query(IngestionLog)
    
    if source:
        query = query.filter(IngestionLog.source == source)
    
    if status:
        query = query.filter(IngestionLog.status == status)
    
    return query.order_by(IngestionLog.started_at.desc()).limit(limit).all()


@app.post("/ingestion/run", tags=["Ingestion"])
async def run_ingestion(
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(None, description="Sources to ingest"),
    leagues: Optional[List[str]] = Query(None, description="Leagues to ingest"),
    db: Session = Depends(get_session)
):
    """
    Trigger a new ingestion job.
    
    Runs asynchronously in the background. Returns immediately with job status.
    """
    from ..ingestion.orchestrator import IngestionOrchestrator
    
    def run_background_ingestion():
        try:
            orchestrator = IngestionOrchestrator()
            stats = orchestrator.run_full_ingestion(
                sources=sources,
                leagues=[(l, "2023-2024") for l in leagues] if leagues else None
            )
            logger.info(f"Background ingestion completed: {stats}")
        except Exception as e:
            logger.error(f"Background ingestion failed: {e}")
    
    background_tasks.add_task(run_background_ingestion)
    
    return {
        "status": "started",
        "message": "Ingestion job started in background",
        "sources": sources,
        "leagues": leagues
    }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_session)):
    """Check API and database health."""
    db_status = "healthy"
    try:
        db.execute("SELECT 1")
    except:
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/ready", tags=["Health"])
def readiness_check(db: Session = Depends(get_session)):
    """Check if the API is ready to serve requests."""
    try:
        db.execute("SELECT 1")
        return {"ready": True, "status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"ready": False, "status": "unhealthy", "error": str(e)})


@app.get("/", tags=["Root"])
def root():
    """Root endpoint with API information."""
    return {
        "name": "Soccer Analytics API",
        "version": "0.1.0",
        "description": "REST API for football data from multiple sources",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }
