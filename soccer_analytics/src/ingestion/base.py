"""
Base ingestion service for soccer data sources.

Provides common functionality for all data source ingestors:
- Retry logic with exponential backoff
- Logging and error handling
- Data normalization utilities
- Cache management integration

Philosophy: Following soccerdata's approach of graceful error handling,
responsible scraping with delays, and consistent DataFrame outputs.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
import pandas as pd
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, RetryError
)

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


class SourceUnavailableError(IngestionError):
    """Raised when a data source is unavailable."""
    pass


class DataValidationError(IngestionError):
    """Raised when ingested data fails validation."""
    pass


def with_retry(max_retries: int = 3, delay: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Decorator for adding retry logic to ingestion methods.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_fn = retry(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=delay, max=60),
                retry=retry_if_exception_type(exceptions),
                reraise=False,
            )(func)
            try:
                return retry_fn(*args, **kwargs)
            except RetryError as e:
                # Re-raise the RetryError so tests can catch it
                raise e
            except exceptions as e:
                # If we exhausted retries, raise the last exception
                raise e
        return wrapper
    return decorator


class BaseIngestionService(ABC):
    """
    Abstract base class for all data source ingestion services.
    
    Provides common functionality:
    - Configuration access
    - Retry logic
    - Logging
    - Data validation hooks
    - Normalization utilities
    
    Subclasses must implement:
    - source_name: Class attribute with source identifier
    - _fetch_data: Abstract method for fetching data from source
    """
    
    source_name: str = "base"
    
    def __init__(self, config: Any, session: Any = None):
        """
        Initialize ingestion service.
        
        Args:
            config: Application configuration object
            session: Optional database session for direct writes
        """
        self.config = config
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.source_name}")
    
    @abstractmethod
    def _fetch_data(self, league: str, season: str, **kwargs) -> pd.DataFrame:
        """
        Fetch data from the source.
        
        Must be implemented by subclasses.
        
        Args:
            league: League identifier
            season: Season identifier
            **kwargs: Additional source-specific parameters
        
        Returns:
            pandas DataFrame with ingested data
        """
        pass
    
    def fetch_with_retry(
        self,
        league: str,
        season: str,
        max_retries: Optional[int] = None,
        delay: Optional[float] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Fetch data with automatic retry on failure.
        
        Uses exponential backoff between retries to avoid overwhelming
        the source server (responsible scraping practice).
        
        Args:
            league: League identifier
            season: Season identifier
            max_retries: Override default max retries
            delay: Override default initial delay
            **kwargs: Additional parameters for _fetch_data
        
        Returns:
            pandas DataFrame with ingested data
        
        Raises:
            SourceUnavailableError: If source remains unavailable after retries
        """
        retries = max_retries or getattr(self.config, f'{self.source_name}_max_retries', 3)
        retry_delay = delay or getattr(self.config, f'{self.source_name}_retry_delay', 2.0)
        
        @with_retry(max_retries=retries, delay=retry_delay)
        def do_fetch():
            # Respect rate limiting
            if hasattr(self.config, 'request_delay'):
                time.sleep(self.config.request_delay)
            
            self.logger.info(f"Fetching {self.source_name} data for {league} - {season}")
            return self._fetch_data(league, season, **kwargs)
        
        try:
            return do_fetch()
        except RetryError as e:
            self.logger.error(
                f"Failed to fetch {self.source_name} data after {retries} retries: {e}"
            )
            raise SourceUnavailableError(
                f"Source {self.source_name} unavailable after {retries} attempts"
            ) from e
        except Exception as e:
            self.logger.error(f"Error fetching {self.source_name} data: {e}")
            raise
    
    def validate_dataframe(self, df: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
        """
        Validate that DataFrame has required columns.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
        
        Returns:
            Validated DataFrame
        
        Raises:
            DataValidationError: If required columns are missing
        """
        if df is None or df.empty:
            self.logger.warning("Received empty DataFrame")
            return df
        
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise DataValidationError(
                f"Missing required columns: {missing}. Available: {list(df.columns)}"
            )
        
        return df
    
    def normalize_team_names(self, df: pd.DataFrame, column: str = 'team') -> pd.DataFrame:
        """
        Normalize team names for consistent matching across sources.
        
        Common normalizations:
        - Lowercase
        - Remove special characters
        - Standardize common variations (Man United / Manchester Utd / MUFC)
        
        Args:
            df: DataFrame containing team names
            column: Name of column with team names
        
        Returns:
            DataFrame with normalized team names
        """
        if column not in df.columns:
            return df
        
        # Basic normalization
        df[column] = df[column].str.strip()
        df[column] = df[column].str.replace(r'[^\w\s-]', '', regex=True)
        df[column] = df[column].str.replace(r'\s+', ' ', regex=True)
        
        # Common substitutions (can be extended via config)
        substitutions = {
            'manchester united': 'man utd',
            'man utd': 'man utd',
            'man u': 'man utd',
            'tottenham hotspur': 'tottenham',
            'spurs': 'tottenham',
            'liverpool fc': 'liverpool',
            'fc liverpool': 'liverpool',
        }
        
        df[column] = df[column].str.lower().replace(substitutions)
        
        return df
    
    def normalize_dates(self, df: pd.DataFrame, column: str = 'date') -> pd.DataFrame:
        """
        Normalize date columns to pandas datetime.
        
        Args:
            df: DataFrame containing dates
            column: Name of column with dates
        
        Returns:
            DataFrame with normalized dates
        """
        if column not in df.columns:
            return df
        
        df[column] = pd.to_datetime(df[column], errors='coerce')
        return df
    
    def remove_duplicates(
        self,
        df: pd.DataFrame,
        subset: Optional[List[str]] = None,
        keep: str = 'last'
    ) -> pd.DataFrame:
        """
        Remove duplicate rows from DataFrame.
        
        Args:
            df: DataFrame to deduplicate
            subset: Columns to consider for duplicates (None = all columns)
            keep: Which duplicate to keep ('first', 'last', False)
        
        Returns:
            Deduplicated DataFrame
        """
        if df is None or df.empty:
            return df
        
        initial_count = len(df)
        df = df.drop_duplicates(subset=subset, keep=keep)
        removed = initial_count - len(df)
        
        if removed > 0:
            self.logger.debug(f"Removed {removed} duplicate rows")
        
        return df
    
    def log_ingestion_stats(
        self,
        run_id: str,
        league_id: Optional[int],
        season_id: Optional[int],
        rows_processed: int,
        rows_inserted: int = 0,
        rows_updated: int = 0,
        rows_failed: int = 0,
        status: str = 'completed',
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Log ingestion statistics to database.
        
        Creates audit trail for monitoring and debugging.
        
        Args:
            run_id: Unique identifier for this ingestion run
            league_id: Database ID of league (if applicable)
            season_id: Database ID of season (if applicable)
            rows_processed: Total rows processed
            rows_inserted: New rows inserted
            rows_updated: Existing rows updated
            rows_failed: Rows that failed to process
            status: Final status (running, completed, failed, partial)
            error_message: Error message if failed
            metadata: Additional metadata as dict
        """
        if self.session is None:
            self.logger.warning("No database session available for logging")
            return
        
        from src.storage.models import IngestionLog
        from datetime import datetime
        
        log_entry = IngestionLog(
            run_id=run_id,
            source=self.source_name,
            league_id=league_id,
            season_id=season_id,
            started_at=datetime.now(),
            ended_at=datetime.now(),
            status=status,
            rows_processed=rows_processed,
            rows_inserted=rows_inserted,
            rows_updated=rows_updated,
            rows_failed=rows_failed,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        try:
            self.session.add(log_entry)
            self.session.commit()
        except Exception as e:
            self.logger.error(f"Failed to log ingestion stats: {e}")
            self.session.rollback()
    
    def get_source_specific_config(self) -> Dict[str, Any]:
        """
        Get configuration specific to this source.
        
        Returns:
            Dict of source-specific configuration values
        """
        prefix = self.source_name.lower()
        config_dict = {}
        
        for key, value in vars(self.config).items():
            if key.startswith(prefix):
                config_dict[key] = value
        
        return config_dict
