"""
Database models and schema for Soccer Analytics Platform.

This module defines the SQLAlchemy ORM models following the architecture:
- Dimensions: leagues, seasons, teams, players
- Facts: matches, team_stats, player_stats, odds, events

Philosophy: 
- Clear separation between dimensions and facts (data warehouse pattern)
- Indexes on commonly filtered columns (season, league, team, date)
- JSON columns for flexible stats storage
- Tracking of source and extraction time for data lineage
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Float, Boolean,
    ForeignKey, Text, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# =============================================================================
# DIMENSIONS
# =============================================================================

class DimLeague(Base):
    """
    Dimension table for leagues/competitions.
    
    Stores metadata about each league including source-specific identifiers.
    """
    __tablename__ = 'dim_league'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    country = Column(String(100))
    country_code = Column(String(3))
    level = Column(Integer, default=1)  # 1 = top division, 2 = second, etc.
    
    # Source-specific identifiers (stored as JSON for flexibility)
    source_ids = Column(JSON, default=dict)
    # Example: {"ClubElo": "ENG_1", "FBref": "Premier League", "MatchHistory": "E0"}
    
    season_start_month = Column(Integer, default=8)  # August
    season_end_month = Column(Integer, default=6)    # June
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    seasons = relationship("DimSeason", back_populates="league", cascade="all, delete-orphan")
    matches = relationship("FactMatch", back_populates="league")
    team_season_stats = relationship("FactTeamSeasonStats", back_populates="league")
    player_season_stats = relationship("FactPlayerSeasonStats", back_populates="league")
    
    __table_args__ = (
        Index('idx_league_country', 'country'),
        Index('idx_league_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<DimLeague(id={self.id}, name='{self.name}', country='{self.country}')>"


class DimSeason(Base):
    """
    Dimension table for seasons.
    
    Each season belongs to a league and has a specific year range.
    """
    __tablename__ = 'dim_season'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, ForeignKey('dim_league.id', ondelete='CASCADE'), nullable=False)
    year = Column(String(20), nullable=False)  # e.g., "2023-2024"
    start_date = Column(Date)
    end_date = Column(Date)
    is_current = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    league = relationship("DimLeague", back_populates="seasons")
    matches = relationship("FactMatch", back_populates="season")
    team_season_stats = relationship("FactTeamSeasonStats", back_populates="season")
    player_season_stats = relationship("FactPlayerSeasonStats", back_populates="season")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'year', name='uq_season_league_year'),
        Index('idx_season_year', 'year'),
        Index('idx_season_current', 'is_current'),
    )
    
    def __repr__(self):
        return f"<DimSeason(id={self.id}, league_id={self.league_id}, year='{self.year}')>"


class DimTeam(Base):
    """
    Dimension table for teams/clubs.
    
    Stores team metadata with normalization for name variations across sources.
    """
    __tablename__ = 'dim_team'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(50))
    alternative_names = Column(JSON, default=list)  # For name matching across sources
    # Example: ["Man United", "Manchester Utd", "MUFC"] for Manchester United
    
    country = Column(String(100))
    founded = Column(Integer)
    logo_url = Column(Text)
    
    # Source-specific identifiers
    source_ids = Column(JSON, default=dict)
    # Example: {"FBref": "33c89a78", "WhoScored": 32, "Sofascore": 35}
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    home_matches = relationship("FactMatch", foreign_keys="FactMatch.home_team_id", back_populates="home_team")
    away_matches = relationship("FactMatch", foreign_keys="FactMatch.away_team_id", back_populates="away_team")
    team_season_stats = relationship("FactTeamSeasonStats", back_populates="team")
    player_season_stats = relationship("FactPlayerSeasonStats", back_populates="team")
    
    __table_args__ = (
        Index('idx_team_name', 'name'),
        Index('idx_team_country', 'country'),
    )
    
    def __repr__(self):
        return f"<DimTeam(id={self.id}, name='{self.name}')>"


class DimPlayer(Base):
    """
    Dimension table for players.
    
    Stores player metadata with tracking across teams and seasons.
    """
    __tablename__ = 'dim_player'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    full_name = Column(String(300))
    nationality = Column(String(100))
    birth_date = Column(Date)
    position = Column(String(50))  # Primary position
    positions = Column(JSON, default=list)  # All positions player can play
    height = Column(Integer)  # in cm
    weight = Column(Integer)  # in kg
    
    # Source-specific identifiers
    source_ids = Column(JSON, default=dict)
    # Example: {"FBref": "abc123", "SoFIFA": 12345, "Understat": "player/xyz"}
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    player_season_stats = relationship("FactPlayerSeasonStats", back_populates="player")
    player_match_stats = relationship("FactPlayerMatchStats", back_populates="player")
    
    __table_args__ = (
        Index('idx_player_name', 'name'),
        Index('idx_player_nationality', 'nationality'),
        Index('idx_player_position', 'position'),
    )
    
    def __repr__(self):
        return f"<DimPlayer(id={self.id}, name='{self.name}', position='{self.position}')>"


# =============================================================================
# FACTS - MATCHES
# =============================================================================

class FactMatch(Base):
    """
    Fact table for matches/results.
    
    Core fact table containing match outcomes and basic metadata.
    Detailed statistics are in separate tables.
    """
    __tablename__ = 'fact_match'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    league_id = Column(Integer, ForeignKey('dim_league.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('dim_season.id'), nullable=False)
    home_team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    
    # Match details
    match_date = Column(DateTime, nullable=False)
    match_time = Column(String(10))  # Local time
    venue = Column(String(200))
    attendance = Column(Integer)
    referee = Column(String(100))
    
    # Score
    home_score = Column(Integer)
    away_score = Column(Integer)
    halftime_home_score = Column(Integer)
    halftime_away_score = Column(Integer)
    
    # Status
    status = Column(String(50), default='completed')  # completed, postponed, cancelled, live
    round = Column(String(50))  # Matchday/round number
    stage = Column(String(50))  # Regular Season, Playoffs, etc.
    
    # Source tracking
    source_urls = Column(JSON, default=dict)
    # Example: {"FBref": "url", "WhoScored": "url", "ESPN": "url"}
    
    extracted_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    league = relationship("DimLeague", back_populates="matches")
    season = relationship("DimSeason", back_populates="matches")
    home_team = relationship("DimTeam", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("DimTeam", foreign_keys=[away_team_id], back_populates="away_matches")
    
    team_match_stats = relationship("FactTeamMatchStats", back_populates="match", cascade="all, delete-orphan")
    player_match_stats = relationship("FactPlayerMatchStats", back_populates="match", cascade="all, delete-orphan")
    odds = relationship("FactOdds", back_populates="match", cascade="all, delete-orphan")
    events = relationship("FactEvents", back_populates="match", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_match_date', 'match_date'),
        Index('idx_match_league_season', 'league_id', 'season_id'),
        Index('idx_match_teams', 'home_team_id', 'away_team_id'),
        Index('idx_match_status', 'status'),
    )
    
    def __repr__(self):
        return f"<FactMatch(id={self.id}, home={self.home_team_id}, away={self.away_team_id}, date={self.match_date})>"


# =============================================================================
# FACTS - TEAM STATISTICS
# =============================================================================

class FactTeamMatchStats(Base):
    """
    Fact table for team-level match statistics.
    
    Contains detailed stats for each team in each match.
    """
    __tablename__ = 'fact_team_match_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    match_id = Column(Integer, ForeignKey('fact_match.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    
    # Context
    is_home = Column(Boolean, nullable=False)
    
    # Basic stats
    shots = Column(Integer)
    shots_on_target = Column(Integer)
    shots_off_target = Column(Integer)
    blocked_shots = Column(Integer)
    
    # Possession and passing
    possession = Column(Float)  # percentage
    passes = Column(Integer)
    passes_completed = Column(Integer)
    pass_accuracy = Column(Float)
    
    # Set pieces
    corners = Column(Integer)
    offsides = Column(Integer)
    
    # Discipline
    fouls = Column(Integer)
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    
    # Advanced metrics
    xg = Column(Float)  # Expected Goals
    xg_against = Column(Float)
    xg_difference = Column(Float)
    
    # Additional stats (flexible JSON for source-specific metrics)
    additional_stats = Column(JSON, default=dict)
    
    # Source tracking
    source = Column(String(50))
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    match = relationship("FactMatch", back_populates="team_match_stats")
    team = relationship("DimTeam")
    
    __table_args__ = (
        UniqueConstraint('match_id', 'team_id', name='uq_team_match_stats'),
        Index('idx_team_match_team', 'team_id'),
    )
    
    def __repr__(self):
        return f"<FactTeamMatchStats(match_id={self.match_id}, team_id={self.team_id}, is_home={self.is_home})>"


class FactTeamSeasonStats(Base):
    """
    Fact table for team-level season statistics.
    
    Aggregated stats for each team in each season.
    Supports multiple stat_types (standard, keeper, shooting, passing, etc.)
    """
    __tablename__ = 'fact_team_season_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    league_id = Column(Integer, ForeignKey('dim_league.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('dim_season.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    
    # Stat type (FBref style: standard, keeper, shooting, passing, etc.)
    stat_type = Column(String(50), nullable=False)
    
    # Basic counts
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    
    # Goals
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_difference = Column(Integer)
    
    # Points (for league tables)
    points = Column(Integer, default=0)
    position = Column(Integer)  # League position
    
    # All other stats in JSON for flexibility
    stats_json = Column(JSON, default=dict)
    # Example: {"xG": 45.6, "xGA": 38.2, "possession_avg": 52.3, ...}
    
    # Source tracking
    source = Column(String(50))
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    league = relationship("DimLeague", back_populates="team_season_stats")
    season = relationship("DimSeason", back_populates="team_season_stats")
    team = relationship("DimTeam", back_populates="team_season_stats")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'season_id', 'team_id', 'stat_type', name='uq_team_season_stats'),
        Index('idx_team_season_team', 'team_id'),
        Index('idx_team_season_type', 'stat_type'),
    )
    
    def __repr__(self):
        return f"<FactTeamSeasonStats(team_id={self.team_id}, season_id={self.season_id}, type='{self.stat_type}')>"


# =============================================================================
# FACTS - PLAYER STATISTICS
# =============================================================================

class FactPlayerMatchStats(Base):
    """
    Fact table for player-level match statistics.
    
    Contains detailed stats for each player in each match.
    """
    __tablename__ = 'fact_player_match_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    match_id = Column(Integer, ForeignKey('fact_match.id', ondelete='CASCADE'), nullable=False)
    player_id = Column(Integer, ForeignKey('dim_player.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    
    # Context
    is_home = Column(Boolean, nullable=False)
    
    # Playing time
    minutes_played = Column(Integer, default=0)
    position = Column(String(50))  # Position in this match
    jersey_number = Column(Integer)
    
    # Performance
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    
    # Passing
    passes = Column(Integer, default=0)
    passes_completed = Column(Integer, default=0)
    key_passes = Column(Integer, default=0)
    
    # Defense
    tackles = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    clearances = Column(Integer, default=0)
    
    # Discipline
    fouls_committed = Column(Integer, default=0)
    fouls_drawn = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    
    # Ratings
    rating = Column(Float)  # Match rating (e.g., WhoScored rating)
    
    # Additional stats
    additional_stats = Column(JSON, default=dict)
    
    # Source tracking
    source = Column(String(50))
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    match = relationship("FactMatch", back_populates="player_match_stats")
    player = relationship("DimPlayer", back_populates="player_match_stats")
    team = relationship("DimTeam")
    
    __table_args__ = (
        UniqueConstraint('match_id', 'player_id', name='uq_player_match_stats'),
        Index('idx_player_match_player', 'player_id'),
        Index('idx_player_match_team', 'team_id'),
    )
    
    def __repr__(self):
        return f"<FactPlayerMatchStats(match_id={self.match_id}, player_id={self.player_id})>"


class FactPlayerSeasonStats(Base):
    """
    Fact table for player-level season statistics.
    
    Aggregated stats for each player in each season.
    Supports multiple stat_types.
    """
    __tablename__ = 'fact_player_season_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    league_id = Column(Integer, ForeignKey('dim_league.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('dim_season.id'), nullable=False)
    player_id = Column(Integer, ForeignKey('dim_player.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    
    # Stat type
    stat_type = Column(String(50), nullable=False)
    
    # Basic counts
    appearances = Column(Integer, default=0)
    starts = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    
    # Performance
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    
    # All other stats in JSON
    stats_json = Column(JSON, default=dict)
    
    # Source tracking
    source = Column(String(50))
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    league = relationship("DimLeague", back_populates="player_season_stats")
    season = relationship("DimSeason", back_populates="player_season_stats")
    player = relationship("DimPlayer", back_populates="player_season_stats")
    team = relationship("DimTeam", back_populates="player_season_stats")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'season_id', 'player_id', 'team_id', 'stat_type', name='uq_player_season_stats'),
        Index('idx_player_season_player', 'player_id'),
        Index('idx_player_season_team', 'team_id'),
    )
    
    def __repr__(self):
        return f"<FactPlayerSeasonStats(player_id={self.player_id}, season_id={self.season_id})>"


# =============================================================================
# FACTS - ODDS
# =============================================================================

class FactOdds(Base):
    """
    Fact table for betting odds.
    
    Stores pre-match and closing odds from various bookmakers.
    Follows Football-Data.co.uk column conventions.
    """
    __tablename__ = 'fact_odds'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    match_id = Column(Integer, ForeignKey('fact_match.id', ondelete='CASCADE'), nullable=False)
    
    # Bookmaker identification
    bookmaker = Column(String(50), nullable=False)
    # Examples: "B365" (Bet365), "PS" (Pinnacle), "WH" (William Hill)
    
    bet_type = Column(String(50), default='1X2')
    # Types: 1X2 (match result), OU (over/under), AH (asian handicap), BTTS
    
    # Odds values
    home_odd = Column(Float)
    draw_odd = Column(Float)
    away_odd = Column(Float)
    
    # For over/under bets
    total_line = Column(Float)  # e.g., 2.5
    over_odd = Column(Float)
    under_odd = Column(Float)
    
    # For asian handicap
    handicap_line = Column(Float)
    
    # Timing
    is_closing = Column(Boolean, default=False)
    timestamp = Column(DateTime)  # When the odds were recorded
    
    # Source tracking
    source = Column(String(50))
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    match = relationship("FactMatch", back_populates="odds")
    
    __table_args__ = (
        Index('idx_odds_match', 'match_id'),
        Index('idx_odds_bookmaker', 'bookmaker'),
        Index('idx_odds_closing', 'is_closing'),
    )
    
    def __repr__(self):
        return f"<FactOdds(match_id={self.match_id}, bookmaker='{self.bookmaker}')>"


# =============================================================================
# FACTS - EVENTS
# =============================================================================

class FactEvents(Base):
    """
    Fact table for match events.
    
    Detailed event data from WhoScored or similar sources.
    Includes goals, cards, substitutions, shots, etc.
    """
    __tablename__ = 'fact_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    match_id = Column(Integer, ForeignKey('fact_match.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('dim_team.id'))
    player_id = Column(Integer, ForeignKey('dim_player.id'))
    related_player_id = Column(Integer, ForeignKey('dim_player.id'))  # For assists, etc.
    
    # Event details
    minute = Column(Integer, nullable=False)
    extra_minute = Column(Integer)  # For stoppage time
    event_type = Column(String(50), nullable=False)
    # Types: goal, card, substitution, shot, foul, corner, etc.
    
    event_subtype = Column(String(100))
    # Subtypes: goal_regular, penalty, own_goal, yellow, red, etc.
    
    description = Column(Text)
    
    # Coordinates (for shots, passes, etc.)
    x = Column(Float)  # X coordinate on pitch (0-100)
    y = Column(Float)  # Y coordinate on pitch (0-100)
    
    # Additional data
    additional_data = Column(JSON, default=dict)
    
    # Source tracking
    source = Column(String(50))
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    match = relationship("FactMatch", back_populates="events")
    team = relationship("DimTeam")
    player = relationship("DimPlayer", foreign_keys=[player_id])
    related_player = relationship("DimPlayer", foreign_keys=[related_player_id])
    
    __table_args__ = (
        Index('idx_events_match', 'match_id'),
        Index('idx_events_type', 'event_type'),
        Index('idx_events_minute', 'minute'),
    )
    
    def __repr__(self):
        return f"<FactEvents(match_id={self.match_id}, type='{self.event_type}', minute={self.minute})>"


# =============================================================================
# FACTS - SPECIALIZED SOURCES
# =============================================================================

class FactEloHistory(Base):
    """
    Fact table for ClubElo ratings history.
    
    Tracks Elo ratings for teams over time.
    """
    __tablename__ = 'fact_elo_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    
    # Rating
    date = Column(Date, nullable=False)
    elo_rating = Column(Float, nullable=False)
    rank = Column(Integer)  # Global rank
    
    # League context
    league_id = Column(Integer, ForeignKey('dim_league.id'))
    
    # Source tracking
    source = Column(String(50), default='ClubElo')
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    team = relationship("DimTeam")
    league = relationship("DimLeague")
    
    __table_args__ = (
        UniqueConstraint('team_id', 'date', name='uq_elo_team_date'),
        Index('idx_elo_team', 'team_id'),
        Index('idx_elo_date', 'date'),
        Index('idx_elo_rating', 'elo_rating'),
    )
    
    def __repr__(self):
        return f"<FactEloHistory(team_id={self.team_id}, date={self.date}, elo={self.elo_rating})>"


class FactSofifaRatings(Base):
    """
    Fact table for SoFIFA player ratings.
    
    EA FC (FIFA) player ratings from SoFIFA.
    """
    __tablename__ = 'fact_sofifa_ratings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    player_id = Column(Integer, ForeignKey('dim_player.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('dim_team.id'))
    
    # Season
    season = Column(String(20), nullable=False)  # e.g., "2024"
    
    # Ratings
    overall_rating = Column(Integer)
    potential = Column(Integer)
    
    # Positions
    preferred_positions = Column(JSON, default=list)
    
    # Attributes (stored as JSON for flexibility)
    attributes = Column(JSON, default=dict)
    # Example: {"pace": 85, "shooting": 78, "passing": 82, ...}
    
    # Source tracking
    source = Column(String(50), default='SoFIFA')
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    player = relationship("DimPlayer")
    team = relationship("DimTeam")
    
    __table_args__ = (
        UniqueConstraint('player_id', 'season', name='uq_sofifa_player_season'),
        Index('idx_sofifa_player', 'player_id'),
        Index('idx_sofifa_rating', 'overall_rating'),
    )
    
    def __repr__(self):
        return f"<FactSofifaRatings(player_id={self.player_id}, season={self.season}, rating={self.overall_rating})>"


class FactUnderstatShots(Base):
    """
    Fact table for Understat shot data.
    
    Detailed shot information with xG metrics.
    """
    __tablename__ = 'fact_understat_shots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    match_id = Column(Integer, ForeignKey('fact_match.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('dim_team.id'), nullable=False)
    player_id = Column(Integer, ForeignKey('dim_player.id'))
    
    # Shot details
    minute = Column(Integer)
    
    # xG metrics
    xg = Column(Float)
    xg_buildup = Column(Float)
    xg_chain = Column(Float)
    
    # Location
    x = Column(Float)  # X coordinate
    y = Column(Float)  # Y coordinate
    
    # Context
    situation = Column(String(50))  # open_play, set_piece, counter_attack, etc.
    shot_type = Column(String(50))  # left_foot, right_foot, head, etc.
    body_part = Column(String(50))
    
    # Outcome
    result = Column(String(50))  # goal, on_target, off_target, blocked
    is_goal = Column(Boolean, default=False)
    
    # Source tracking
    source = Column(String(50), default='Understat')
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    match = relationship("FactMatch")
    team = relationship("DimTeam")
    player = relationship("DimPlayer")
    
    __table_args__ = (
        Index('idx_understat_match', 'match_id'),
        Index('idx_understat_player', 'player_id'),
        Index('idx_understat_xg', 'xg'),
    )
    
    def __repr__(self):
        return f"<FactUnderstatShots(match_id={self.match_id}, xg={self.xg}, is_goal={self.is_goal})>"


# =============================================================================
# INGESTION LOGS
# =============================================================================

class IngestionLog(Base):
    """
    Table for tracking ingestion jobs.
    
    Provides audit trail and monitoring for data ingestion processes.
    """
    __tablename__ = 'ingestion_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job identification
    run_id = Column(String(100), nullable=False)
    source = Column(String(50), nullable=False)
    
    # Scope
    league_id = Column(Integer, ForeignKey('dim_league.id'))
    season_id = Column(Integer, ForeignKey('dim_season.id'))
    
    # Timing
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    
    # Results
    status = Column(String(50), default='running')
    # Statuses: running, completed, failed, partial
    
    rows_processed = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    
    error_message = Column(Text)
    
    # Additional metadata (renamed to avoid SQLAlchemy reservation)
    job_metadata = Column('metadata', JSON, default=dict)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    league = relationship("DimLeague")
    season = relationship("DimSeason")
    
    __table_args__ = (
        Index('idx_ingestion_run', 'run_id'),
        Index('idx_ingestion_source', 'source'),
        Index('idx_ingestion_status', 'status'),
        Index('idx_ingestion_started', 'started_at'),
    )
    
    def __repr__(self):
        return f"<IngestionLog(run_id='{self.run_id}', source='{self.source}', status='{self.status}')>"
