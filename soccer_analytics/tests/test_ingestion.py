"""
Tests for ingestion services.

Includes tests for:
- Base service functionality (retry, normalization, validation)
- Individual source services (FBref, WhoScored, Sofascore, ESPN, etc.)
- Error handling and edge cases
- Data normalization utilities
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
sys.path.insert(0, '/workspace/soccer_analytics/src')

# Import directly from base module to avoid orchestrator import issues
from ingestion.base import (
    BaseIngestionService,
    IngestionError,
    SourceUnavailableError,
    DataValidationError,
    with_retry,
)


class TestBaseIngestionService:
    """Test base ingestion service functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock()
        config.data_dir = "/tmp/test_data"
        config.request_delay = 0.1
        config.fbref_max_retries = 3
        config.fbref_retry_delay = 0.5
        return config
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def concrete_service(self, mock_config, mock_session):
        """Create a concrete implementation of the base service for testing."""
        class TestService(BaseIngestionService):
            source_name = "test"
            
            def _fetch_data(self, league, season, **kwargs):
                return pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        
        return TestService(config=mock_config, session=mock_session)
    
    def test_service_initialization(self, concrete_service):
        """Test that service initializes correctly."""
        assert concrete_service.source_name == "test"
        assert concrete_service.config is not None
        assert concrete_service.session is not None
    
    def test_validate_dataframe_success(self, concrete_service):
        """Test DataFrame validation with required columns present."""
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'home_team': ['Team A', 'Team B'],
            'away_team': ['Team C', 'Team D'],
            'score': ['1-0', '2-1']
        })
        
        required = ['date', 'home_team', 'away_team']
        result = concrete_service.validate_dataframe(df, required)
        
        assert result is not None
        assert len(result) == 2
    
    def test_validate_dataframe_missing_columns(self, concrete_service):
        """Test DataFrame validation fails with missing columns."""
        df = pd.DataFrame({'col1': [1, 2]})
        
        with pytest.raises(DataValidationError) as exc_info:
            concrete_service.validate_dataframe(df, ['col1', 'missing_col'])
        
        assert 'missing_col' in str(exc_info.value)
    
    def test_validate_dataframe_empty(self, concrete_service):
        """Test DataFrame validation handles empty DataFrames."""
        df = pd.DataFrame()
        result = concrete_service.validate_dataframe(df, ['col1'])
        
        assert result is not None
        assert result.empty
    
    def test_normalize_team_names(self, concrete_service):
        """Test team name normalization."""
        df = pd.DataFrame({
            'team': [
                'Manchester United',
                'Man Utd',
                'Tottenham Hotspur',
                'Liverpool FC',
                '  Spurs  '
            ]
        })
        
        result = concrete_service.normalize_team_names(df, 'team')
        
        # Check normalizations applied
        teams = result['team'].tolist()
        assert 'man utd' in teams
        assert 'tottenham' in teams
        assert 'liverpool' in teams
    
    def test_normalize_dates(self, concrete_service):
        """Test date normalization."""
        df = pd.DataFrame({
            'date': ['2024-01-15', '2024-02-20', 'invalid_date']
        })
        
        result = concrete_service.normalize_dates(df, 'date')
        
        assert pd.api.types.is_datetime64_any_dtype(result['date'])
        # Invalid dates should be NaT
        assert pd.isna(result['date'].iloc[2])
    
    def test_remove_duplicates(self, concrete_service):
        """Test duplicate removal."""
        df = pd.DataFrame({
            'id': [1, 1, 2, 2, 3],
            'value': ['a', 'a', 'b', 'c', 'd']
        })
        
        result = concrete_service.remove_duplicates(df, subset=['id'])
        
        assert len(result) == 3  # Should keep one row per unique id
    
    def test_fetch_with_retry_success(self, concrete_service, mock_config):
        """Test successful fetch with retry logic."""
        df = concrete_service.fetch_with_retry(
            league='ENG-Premier League',
            season='2023-2024',
            max_retries=2,
            delay=0.1
        )
        
        assert df is not None
        assert not df.empty
    
    def test_log_ingestion_stats(self, concrete_service, mock_session):
        """Test logging of ingestion statistics."""
        concrete_service.log_ingestion_stats(
            run_id='test-run-123',
            league_id=1,
            season_id=2,
            rows_processed=100,
            rows_inserted=80,
            rows_updated=15,
            rows_failed=5,
            status='completed'
        )
        
        # Verify session methods were called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_log_ingestion_stats_no_session(self, mock_config):
        """Test logging without database session."""
        class TestService(BaseIngestionService):
            source_name = "test"
            def _fetch_data(self, league, season, **kwargs):
                return pd.DataFrame()
        
        service = TestService(config=mock_config, session=None)
        
        # Should not raise, just log warning
        service.log_ingestion_stats(
            run_id='test-run-456',
            league_id=1,
            season_id=2,
            rows_processed=50
        )


class TestRetryDecorator:
    """Test the retry decorator functionality."""
    
    def test_retry_on_failure(self):
        """Test that function retries on failure."""
        call_count = 0
        
        @with_retry(max_retries=3, delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary error")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Test that exception is raised after max retries."""
        @with_retry(max_retries=2, delay=0.01)
        def always_fails():
            raise ConnectionError("Always fails")
        
        from tenacity import RetryError
        with pytest.raises(RetryError):
            always_fails()


class TestIngestionErrors:
    """Test custom exception classes."""
    
    def test_ingestion_error(self):
        """Test IngestionError."""
        error = IngestionError("Test error message")
        assert str(error) == "Test error message"
    
    def test_source_unavailable_error(self):
        """Test SourceUnavailableError."""
        error = SourceUnavailableError("Source is down")
        assert str(error) == "Source is down"
        assert isinstance(error, IngestionError)
    
    def test_data_validation_error(self):
        """Test DataValidationError."""
        error = DataValidationError("Invalid data format")
        assert str(error) == "Invalid data format"
        assert isinstance(error, IngestionError)


class TestWhoscoredService:
    """Test WhoScored ingestion service."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock()
        config.data_dir = "/tmp/test_data"
        config.whoscored_max_retries = 3
        config.whoscored_retry_delay = 0.5
        config.whoscored_headless = True
        config.whoscored_request_delay = 0.1
        return config
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @patch('ingestion.whoscored.SoccerDataWhoScored')
    def test_whoscored_initialization(self, mock_reader, mock_config, mock_session):
        """Test WhoScored service initialization."""
        from ingestion.whoscored import WhoscoredService
        
        mock_reader_instance = Mock()
        mock_reader.return_value = mock_reader_instance
        
        service = WhoscoredService(config=mock_config, session=mock_session)
        
        assert service.source_name == "whoscored"
        assert service.reader is not None
        mock_reader.assert_called_once()
    
    @patch('ingestion.whoscored.SoccerDataWhoScored')
    def test_whoscored_fetch_schedule(self, mock_reader, mock_config, mock_session):
        """Test fetching schedule from WhoScored."""
        from ingestion.whoscored import WhoscoredService
        import pandas as pd
        
        mock_reader_instance = Mock()
        mock_reader_instance.read_schedule.return_value = pd.DataFrame({
            'match_id': [1, 2],
            'date': ['2024-01-01', '2024-01-02'],
            'home_team': ['Team A', 'Team B'],
            'away_team': ['Team C', 'Team D']
        })
        mock_reader.return_value = mock_reader_instance
        
        service = WhoscoredService(config=mock_config, session=mock_session)
        df = service._fetch_data('ENG-Premier League', '2023-2024', stat_type='schedule')
        
        assert len(df) == 2
        assert 'match_id' in df.columns
        mock_reader_instance.read_schedule.assert_called_once()


class TestSofascoreService:
    """Test Sofascore ingestion service."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock()
        config.data_dir = "/tmp/test_data"
        config.sofascore_max_retries = 3
        config.sofascore_retry_delay = 0.5
        config.sofascore_request_delay = 0.1
        return config
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @patch('ingestion.sofascore.SoccerDataSofascore')
    def test_sofascore_initialization(self, mock_reader, mock_config, mock_session):
        """Test Sofascore service initialization."""
        from ingestion.sofascore import SofascoreService
        
        mock_reader_instance = Mock()
        mock_reader.return_value = mock_reader_instance
        
        service = SofascoreService(config=mock_config, session=mock_session)
        
        assert service.source_name == "sofascore"
        assert service.reader is not None
        mock_reader.assert_called_once()
    
    @patch('ingestion.sofascore.SoccerDataSofascore')
    def test_sofascore_fetch_schedule(self, mock_reader, mock_config, mock_session):
        """Test fetching schedule from Sofascore."""
        from ingestion.sofascore import SofascoreService
        import pandas as pd
        
        mock_reader_instance = Mock()
        mock_reader_instance.read_schedule.return_value = pd.DataFrame({
            'match_id': [1, 2],
            'date': ['2024-01-01', '2024-01-02'],
            'home_team': ['Team A', 'Team B'],
            'away_team': ['Team C', 'Team D']
        })
        mock_reader.return_value = mock_reader_instance
        
        service = SofascoreService(config=mock_config, session=mock_session)
        df = service._fetch_data('ENG-Premier League', '2023-2024', stat_type='schedule')
        
        assert len(df) == 2
        assert 'match_id' in df.columns
        mock_reader_instance.read_schedule.assert_called_once()


class TestEspnService:
    """Test ESPN ingestion service."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock()
        config.data_dir = "/tmp/test_data"
        config.espn_max_retries = 3
        config.espn_retry_delay = 0.5
        config.espn_request_delay = 0.1
        return config
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @patch('ingestion.espn.SoccerDataESPN')
    def test_espn_initialization(self, mock_reader, mock_config, mock_session):
        """Test ESPN service initialization."""
        from ingestion.espn import EspnService
        
        mock_reader_instance = Mock()
        mock_reader.return_value = mock_reader_instance
        
        service = EspnService(config=mock_config, session=mock_session)
        
        assert service.source_name == "espn"
        assert service.reader is not None
        mock_reader.assert_called_once()
    
    @patch('ingestion.espn.SoccerDataESPN')
    def test_espn_fetch_schedule(self, mock_reader, mock_config, mock_session):
        """Test fetching schedule from ESPN."""
        from ingestion.espn import EspnService
        import pandas as pd
        
        mock_reader_instance = Mock()
        mock_reader_instance.read_schedule.return_value = pd.DataFrame({
            'match_id': [1, 2],
            'date': ['2024-01-01', '2024-01-02'],
            'home_team': ['Team A', 'Team B'],
            'away_team': ['Team C', 'Team D']
        })
        mock_reader.return_value = mock_reader_instance
        
        service = EspnService(config=mock_config, session=mock_session)
        df = service._fetch_data('ENG-Premier League', '2023-2024', stat_type='schedule')
        
        assert len(df) == 2
        assert 'match_id' in df.columns
        mock_reader_instance.read_schedule.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
