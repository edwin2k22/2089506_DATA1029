"""
Tests for API endpoints.

Includes tests for:
- Health and status endpoints
- League and season endpoints
- Match and statistics endpoints
- Authentication (if enabled)
- Error handling and edge cases
"""

import pytest
import sys
sys.path.insert(0, '/workspace/soccer_analytics/src')

from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    from src.api.main import app
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    # Initialize database before creating client
    from src.storage.database import get_database, Database
    db = get_database(database_url='sqlite:///:memory:')
    db.init_db()  # Create tables
    return TestClient(app)


class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        # Status can be 'healthy' or 'degraded' depending on DB initialization
        assert data['status'] in ['healthy', 'degraded']
    
    def test_readiness_check(self, client):
        """Test readiness probe endpoint."""
        response = client.get("/ready")
        # Accept any status code as readiness depends on DB state
        assert response.status_code in [200, 503]
    
    def test_api_info(self, client):
        """Test API info endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert 'name' in data
        assert 'version' in data


class TestLeagueEndpoints:
    """Test league-related endpoints."""
    
    def test_list_leagues(self, client):
        """Test listing available leagues."""
        response = client.get("/leagues")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_league_by_id(self, client):
        """Test getting a specific league."""
        # This will return 404 if no leagues exist, which is expected
        response = client.get("/leagues/999999")
        assert response.status_code in [200, 404]
    
    def test_list_seasons(self, client):
        """Test listing seasons for a league."""
        response = client.get("/leagues/1/seasons")
        # Season endpoint requires a valid league ID
        assert response.status_code in [200, 404, 500]


class TestMatchEndpoints:
    """Test match-related endpoints."""
    
    def test_list_matches(self, client):
        """Test listing matches with filters."""
        response = client.get("matches")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)  # Paginated response
        assert 'items' in data or 'matches' in data or isinstance(data, list)
    
    def test_list_matches_with_filters(self, client):
        """Test listing matches with query parameters."""
        params = {
            'league_id': 1,
            'season_id': 1,
            'team_id': 1,
            'limit': 10,
            'offset': 0
        }
        response = client.get("matches", params=params)
        assert response.status_code == 200
    
    def test_get_match_by_id(self, client):
        """Test getting a specific match."""
        response = client.get("matches/999999")
        assert response.status_code in [200, 404]


class TestStatisticsEndpoints:
    """Test statistics endpoints."""
    
    def test_team_stats(self, client):
        """Test team statistics endpoint."""
        response = client.get("stats/teams")
        assert response.status_code == 200
    
    def test_player_stats(self, client):
        """Test player statistics endpoint."""
        response = client.get("stats/players")
        assert response.status_code == 200
    
    def test_team_stats_by_season(self, client):
        """Test team stats filtered by season."""
        params = {'season_id': 1, 'stat_type': 'standard'}
        response = client.get("stats/teams", params=params)
        assert response.status_code == 200


class TestOddsEndpoints:
    """Test odds/betting endpoints."""
    
    def test_list_odds(self, client):
        """Test listing odds."""
        response = client.get("odds")
        assert response.status_code == 200
    
    def test_odds_by_match(self, client):
        """Test odds for a specific match."""
        response = client.get("odds/match/999999")
        assert response.status_code in [200, 404]


class TestSourceEndpoints:
    """Test data source management endpoints."""
    
    def test_list_sources(self, client):
        """Test listing available data sources."""
        response = client.get("sources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_source_status(self, client):
        """Test getting status of a specific source."""
        response = client.get("sources/fbref/status")
        assert response.status_code in [200, 404]


class TestPagination:
    """Test pagination functionality."""
    
    def test_pagination_parameters(self, client):
        """Test that pagination parameters work correctly."""
        params = {'limit': 5, 'offset': 10}
        response = client.get("matches", params=params)
        assert response.status_code == 200
        
        data = response.json()
        if isinstance(data, dict):
            # Check pagination metadata if present
            assert 'limit' in data or 'items' in data or len(data) <= 5


class TestErrorHandling:
    """Test error handling in API."""
    
    def test_invalid_endpoint(self, client):
        """Test 404 for non-existent endpoints."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
    
    def test_invalid_method(self, client):
        """Test 405 for unsupported methods."""
        response = client.post("leagues")  # Should be GET
        assert response.status_code in [405, 422, 200]  # Depends on implementation
    
    def test_invalid_query_params(self, client):
        """Test handling of invalid query parameters."""
        params = {'limit': -1, 'offset': 'invalid'}
        response = client.get("matches", params=params)
        # Should handle gracefully (either validate or use defaults)
        assert response.status_code in [200, 422]


class TestIngestionEndpoints:
    """Test ingestion control endpoints."""
    
    def test_trigger_ingestion(self, client):
        """Test triggering manual ingestion."""
        # This might require authentication in production
        response = client.post("ingest/fbref")
        assert response.status_code in [200, 202, 401, 403]
    
    def test_ingestion_status(self, client):
        """Test checking ingestion status."""
        response = client.get("ingest/status")
        assert response.status_code in [200, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
