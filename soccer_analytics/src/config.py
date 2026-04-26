"""
Configuration module for Soccer Analytics Platform.

This module handles all configuration settings using environment variables
and provides a centralized configuration object for the application.

Philosophy: Following soccerdata's approach of configurable, cache-aware settings
with proper separation between environment-specific and application settings.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Following soccerdata philosophy:
    - Cache-aware configuration (SOCCERDATA_DIR)
    - Source-specific retry and timeout settings
    - Responsible scraping with configurable delays
    """
    
    # =========================================================================
    # PATHS AND DIRECTORIES
    # =========================================================================
    
    soccerdata_dir: Path = Field(
        default=Path("/workspace/soccer_analytics/data"),
        description="Main directory for soccerdata (cache + config)"
    )
    
    database_url: str = Field(
        default="sqlite:///./data/soccer_analytics.db",
        description="Database connection URL"
    )
    
    # =========================================================================
    # API CONFIGURATION
    # =========================================================================
    
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    debug: bool = Field(default=True)
    api_secret_key: str = Field(default="change_this_in_production")
    
    # =========================================================================
    # SOURCE-SPECIFIC SETTINGS
    # =========================================================================
    
    # FBref
    fbref_max_retries: int = Field(default=3)
    fbref_retry_delay: int = Field(default=5)
    fbref_timeout: int = Field(default=30)
    
    # WhoScored
    whoscored_use_selenium: bool = Field(default=True)
    whoscored_headless: bool = Field(default=True)
    whoscored_proxy: Optional[str] = Field(default=None)
    whoscored_max_retries: int = Field(default=3)
    whoscored_retry_delay: int = Field(default=10)
    
    # Sofascore
    sofascore_max_retries: int = Field(default=3)
    sofascore_retry_delay: int = Field(default=5)
    
    # ESPN
    espn_max_retries: int = Field(default=3)
    espn_retry_delay: int = Field(default=5)
    
    # MatchHistory
    matchhistory_max_retries: int = Field(default=3)
    matchhistory_retry_delay: int = Field(default=5)
    
    # ClubElo
    clubelo_max_retries: int = Field(default=3)
    clubelo_retry_delay: int = Field(default=2)
    
    # SoFIFA
    sofifa_max_retries: int = Field(default=3)
    sofifa_retry_delay: int = Field(default=5)
    
    # Understat
    understat_max_retries: int = Field(default=3)
    understat_retry_delay: int = Field(default=5)
    
    # =========================================================================
    # SCRAPING SETTINGS
    # =========================================================================
    
    request_delay: float = Field(
        default=2.0,
        description="Delay between requests to respect site ToS (seconds)"
    )
    
    batch_size: int = Field(
        default=50,
        description="Maximum matches to ingest per batch"
    )
    
    use_cache: bool = Field(
        default=True,
        description="Enable/disable local caching"
    )
    
    cache_max_age_days: int = Field(
        default=7,
        description="Force cache refresh after X days"
    )
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: Optional[Path] = Field(default=None)
    
    # =========================================================================
    # DEFAULT LEAGUES AND SOURCES
    # =========================================================================
    
    default_leagues: str = Field(
        default="ENG-Premier League:2023-2024,ESP-La Liga:2023-2024,ITA-Serie A:2023-2024,GER-Bundesliga:2023-2024,FRA-Ligue 1:2023-2024",
        description="Comma-separated list of leagues to ingest (format: LEAGUE:SEASON)"
    )
    
    active_sources: str = Field(
        default="fbref,matchhistory,clubelo",
        description="Comma-separated list of active data sources"
    )
    
    # =========================================================================
    # ENVIRONMENT
    # =========================================================================
    
    environment: str = Field(default="development")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file
    
    @property
    def config_dir(self) -> Path:
        """Return the configuration directory path."""
        return self.soccerdata_dir / "config"
    
    @property
    def cache_dir(self) -> Path:
        """Return the cache directory path."""
        return self.soccerdata_dir / "cache"
    
    @property
    def league_dict_path(self) -> Path:
        """Return the path to league_dict.json."""
        return self.config_dir / "league_dict.json"
    
    def get_active_sources_list(self) -> List[str]:
        """Return list of active source names."""
        return [s.strip().lower() for s in self.active_sources.split(",")]
    
    def get_default_leagues_list(self) -> List[tuple]:
        """
        Return list of (league, season) tuples from default_leagues.
        
        Format: "LEAGUE1:SEASON1,LEAGUE2:SEASON2" -> [("LEAGUE1", "SEASON1"), ...]
        """
        leagues = []
        for item in self.default_leagues.split(","):
            if ":" in item:
                league, season = item.rsplit(":", 1)
                leagues.append((league.strip(), season.strip()))
        return leagues
    
    def load_league_dict(self) -> Dict[str, Any]:
        """
        Load the league dictionary from JSON file.
        
        Returns empty dict with structure if file doesn't exist.
        """
        if not self.league_dict_path.exists():
            return {"leagues": {}}
        
        with open(self.league_dict_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def save_league_dict(self, data: Dict[str, Any]) -> None:
        """Save the league dictionary to JSON file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.league_dict_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def setup_directories(self) -> None:
        """
        Create necessary directories for the application.
        
        This follows soccerdata's convention of having a central SOCCERDATA_DIR
        with subdirectories for config and cache.
        """
        dirs_to_create = [
            self.soccerdata_dir,
            self.config_dir,
            self.cache_dir,
            Path("logs"),
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

# Initialize directories on module load
settings.setup_directories()
