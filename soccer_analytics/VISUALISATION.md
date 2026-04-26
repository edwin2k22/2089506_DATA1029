# ⚽ Soccer Analytics Platform - Vue d'ensemble

## 📋 Table des Matières

1. [Architecture Globale](#architecture-globale)
2. [Structure du Projet](#structure-du-projet)
3. [Schéma de Base de Données](#schéma-de-base-de-données)
4. [Services d'Ingestion Implémentés](#services-dingestion-implémentés)
5. [API REST - Endpoints](#api-rest---endpoints)
6. [Configuration](#configuration)
7. [Guide de Démarrage](#guide-de-démarrage)
8. [Plan d'Itérations](#plan-ditérations)

---

## 🏗 Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         API REST (FastAPI)                              │
│  Port: 8000 | Documentation: http://localhost:8000/docs                │
│                                                                         │
│  Endpoints: /leagues, /matches, /teams, /players, /elo, /ingestion     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Couche de Stockage (SQLAlchemy)                      │
│                                                                         │
│  SQLite (dev) / PostgreSQL (prod)                                       │
│  Schema: Dimensions + Faits (Data Warehouse Pattern)                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                    Couche d'Ingestion (soccerdata)                      │
│                                                                         │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────────────┐ │
│  │   FBref     │ MatchHistory│   ClubElo   │   À venir...            │ │
│  │  (stats)    │   (cotes)   │   (Elo)     │   WhoScored, Sofascore  │ │
│  └─────────────┴─────────────┴─────────────┴─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                    Configuration & Cache                                │
│                                                                         │
│  SOCCERDATA_DIR=/workspace/soccer_analytics/data                        │
│  ├── config/league_dict.json  → Mapping des ligues par source          │
│  └── cache/                   → Cache local soccerdata                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Flux de Données

```
[Sources Externes] → [soccerdata] → [Cache Local] → [Normalisation] 
                                                   ↓
[Monitoring] ← [Logs] ← [Upsert DB] ← [Validation] ← [DataFrame Pandas]
```

---

## 📁 Structure du Projet

```
/workspace/soccer_analytics/
│
├── ARCHITECTURE.md           # Documentation architecturale détaillée
├── README.md                 # Guide utilisateur principal
├── requirements.txt          # Dépendances Python
│
├── config/
│   └── league_dict.json      # Configuration des ligues multi-sources
│                             # → 12 ligues pré-configurées
│
├── data/
│   ├── cache/                # Cache soccerdata (auto-généré)
│   ├── config/               # Configs supplémentaires
│   └── soccer_analytics.db   # Base de données SQLite
│
├── src/
│   ├── config.py             # Settings pydantic (env vars)
│   │
│   ├── ingestion/
│   │   ├── base.py           # Classe abstraite + retry logic
│   │   ├── fbref.py          # Service FBref (stats équipe/joueur)
│   │   ├── matchhistory.py   # Service Football-Data.co.uk (cotes)
│   │   ├── clubelo.py        # Service ClubElo (ratings)
│   │   └── orchestrator.py   # Orchestrateur principal
│   │
│   ├── storage/
│   │   ├── models.py         # Modèles SQLAlchemy (14 tables)
│   │   └── database.py       # Gestion connexion DB
│   │
│   ├── api/
│   │   └── main.py           # API FastAPI (25+ endpoints)
│   │
│   └── utils/
│       └── __init__.py
│
├── logs/                     # Logs d'application
│
└── tests/                    # Tests pytest (à implémenter)
```

---

## 🗄 Schéma de Base de Données

### Dimensions (4 tables)

```sql
-- dim_league : Ligues/compétitions
CREATE TABLE dim_league (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    country VARCHAR(100),
    country_code VARCHAR(3),
    level INTEGER DEFAULT 1,
    source_ids JSON,              -- {"ClubElo": "ENG_1", "FBref": "Premier League"}
    season_start_month INTEGER,
    season_end_month INTEGER,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- dim_season : Saisons
CREATE TABLE dim_season (
    id INTEGER PRIMARY KEY,
    league_id INTEGER REFERENCES dim_league(id),
    year VARCHAR(20),             -- "2023-2024"
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN,
    UNIQUE(league_id, year)
);

-- dim_team : Équipes
CREATE TABLE dim_team (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(50),
    alternative_names JSON,       -- ["Man Utd", "Manchester United"]
    country VARCHAR(100),
    founded INTEGER,
    logo_url TEXT,
    source_ids JSON               -- {"FBref": "33c89a78", "WhoScored": 32}
);

-- dim_player : Joueurs
CREATE TABLE dim_player (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    full_name VARCHAR(300),
    nationality VARCHAR(100),
    birth_date DATE,
    position VARCHAR(50),
    positions JSON,
    height INTEGER,               -- cm
    weight INTEGER,               -- kg
    source_ids JSON
);
```

### Faits (10 tables)

```sql
-- fact_match : Matchs/résultats
CREATE TABLE fact_match (
    id INTEGER PRIMARY KEY,
    league_id INTEGER REFERENCES dim_league(id),
    season_id INTEGER REFERENCES dim_season(id),
    home_team_id INTEGER REFERENCES dim_team(id),
    away_team_id INTEGER REFERENCES dim_team(id),
    match_date TIMESTAMP NOT NULL,
    match_time VARCHAR(10),
    venue VARCHAR(200),
    attendance INTEGER,
    referee VARCHAR(100),
    home_score INTEGER,
    away_score INTEGER,
    halftime_home_score INTEGER,
    halftime_away_score INTEGER,
    status VARCHAR(50),
    round VARCHAR(50),
    stage VARCHAR(50),
    source_urls JSON,             -- {"FBref": "url", "WhoScored": "url"}
    extracted_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- fact_team_match_stats : Stats équipe par match
CREATE TABLE fact_team_match_stats (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES fact_match(id),
    team_id INTEGER REFERENCES dim_team(id),
    is_home BOOLEAN,
    shots INTEGER,
    shots_on_target INTEGER,
    possession FLOAT,
    passes INTEGER,
    passes_completed INTEGER,
    corners INTEGER,
    fouls INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    xg FLOAT,
    xg_against FLOAT,
    additional_stats JSON,
    source VARCHAR(50),
    extracted_at TIMESTAMP,
    UNIQUE(match_id, team_id)
);

-- fact_player_match_stats : Stats joueur par match
CREATE TABLE fact_player_match_stats (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES fact_match(id),
    player_id INTEGER REFERENCES dim_player(id),
    team_id INTEGER REFERENCES dim_team(id),
    is_home BOOLEAN,
    minutes_played INTEGER,
    position VARCHAR(50),
    goals INTEGER,
    assists INTEGER,
    shots INTEGER,
    passes_completed INTEGER,
    tackles INTEGER,
    rating FLOAT,
    additional_stats JSON,
    source VARCHAR(50),
    extracted_at TIMESTAMP
);

-- fact_team_season_stats : Stats équipe par saison
CREATE TABLE fact_team_season_stats (
    id INTEGER PRIMARY KEY,
    league_id INTEGER REFERENCES dim_league(id),
    season_id INTEGER REFERENCES dim_season(id),
    team_id INTEGER REFERENCES dim_team(id),
    stat_type VARCHAR(50),        -- "standard", "keeper", "shooting"
    matches_played INTEGER,
    wins INTEGER,
    draws INTEGER,
    losses INTEGER,
    goals_for INTEGER,
    goals_against INTEGER,
    points INTEGER,
    position INTEGER,
    stats_json JSON,              -- {xG: 45.6, xGA: 38.2, ...}
    source VARCHAR(50),
    extracted_at TIMESTAMP,
    UNIQUE(league_id, season_id, team_id, stat_type)
);

-- fact_player_season_stats : Stats joueur par saison
CREATE TABLE fact_player_season_stats (
    id INTEGER PRIMARY KEY,
    league_id INTEGER REFERENCES dim_league(id),
    season_id INTEGER REFERENCES dim_season(id),
    player_id INTEGER REFERENCES dim_player(id),
    team_id INTEGER REFERENCES dim_team(id),
    stat_type VARCHAR(50),
    appearances INTEGER,
    minutes_played INTEGER,
    goals INTEGER,
    assists INTEGER,
    stats_json JSON,
    source VARCHAR(50),
    extracted_at TIMESTAMP
);

-- fact_odds : Cotes bookmakers
CREATE TABLE fact_odds (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES fact_match(id),
    bookmaker VARCHAR(100),       -- "Bet365", "Pinnacle"
    bet_type VARCHAR(50),         -- "1X2", "Over/Under"
    home_odd FLOAT,
    draw_odd FLOAT,
    away_odd FLOAT,
    is_closing BOOLEAN,
    timestamp TIMESTAMP,
    source VARCHAR(50)
);

-- fact_events : Événements de match
CREATE TABLE fact_events (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES fact_match(id),
    minute INTEGER,
    event_type VARCHAR(50),       -- "goal", "card", "substitution"
    team_id INTEGER,
    player_id INTEGER,
    description TEXT,
    x FLOAT,                      -- Coordonnées pitch
    y FLOAT,
    source VARCHAR(50)
);

-- fact_elo_history : Historique Elo
CREATE TABLE fact_elo_history (
    id INTEGER PRIMARY KEY,
    team_id INTEGER REFERENCES dim_team(id),
    date DATE,
    elo_rating FLOAT,
    rank INTEGER,
    source VARCHAR(50) DEFAULT 'ClubElo'
);

-- fact_sofifa_ratings : Notes SoFIFA
CREATE TABLE fact_sofifa_ratings (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES dim_player(id),
    season VARCHAR(20),
    overall_rating INTEGER,
    potential INTEGER,
    team_id INTEGER,
    positions JSON,
    source VARCHAR(50) DEFAULT 'SoFIFA'
);

-- fact_understat_shots : Tirs Understat
CREATE TABLE fact_understat_shots (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES fact_match(id),
    team_id INTEGER,
    player_id INTEGER,
    minute INTEGER,
    xg FLOAT,
    x FLOAT,
    y FLOAT,
    situation VARCHAR(50),
    shot_type VARCHAR(50),
    body_part VARCHAR(50),
    source VARCHAR(50) DEFAULT 'Understat'
);

-- ingestion_logs : Traçabilité
CREATE TABLE ingestion_logs (
    id INTEGER PRIMARY KEY,
    source VARCHAR(50),
    league_id INTEGER,
    season_id INTEGER,
    run_id VARCHAR(100),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status VARCHAR(50),           -- "success", "partial", "failed"
    rows_processed INTEGER,
    error_message TEXT
);
```

### Index Recommandés

```sql
-- Performance sur les filtres courants
CREATE INDEX idx_match_date ON fact_match(match_date);
CREATE INDEX idx_match_league_season ON fact_match(league_id, season_id);
CREATE INDEX idx_match_teams ON fact_match(home_team_id, away_team_id);
CREATE INDEX idx_team_season_team ON fact_team_season_stats(team_id);
CREATE INDEX idx_player_season_player ON fact_player_season_stats(player_id);
CREATE INDEX idx_elo_date ON fact_elo_history(date DESC);
CREATE INDEX idx_league_country ON dim_league(country);
CREATE INDEX idx_team_name ON dim_team(name);
CREATE INDEX idx_player_name ON dim_player(name);
```

---

## 🔌 Services d'Ingestion Implémentés

### 1. FBref Service (`src/ingestion/fbref.py`)

**Données fournies:**
- Calendriers et résultats de matchs
- Stats équipe (12 types): `standard`, `keeper`, `shooting`, `passing`, `defense`, `possession`, etc.
- Stats joueur (11 types): mêmes catégories

**Méthodes principales:**
```python
class FBrefService(BaseIngestionService):
    def read_schedule(league, season) -> pd.DataFrame
    def read_team_season_stats(league, season, stat_type) -> pd.DataFrame
    def read_player_season_stats(league, season, stat_type) -> pd.DataFrame
    
    TEAM_STAT_TYPES = ['standard', 'keeper', 'shooting', 'passing', ...]
    PLAYER_STAT_TYPES = ['standard', 'shooting', 'passing', 'defense', ...]
```

**Philosophie soccerdata respectée:**
- ✅ Cache local automatique
- ✅ Retry avec backoff exponentiel
- ✅ DataFrames Pandas normalisés
- ✅ Gestion graceful des erreurs

---

### 2. MatchHistory Service (`src/ingestion/matchhistory.py`)

**Données fournies:**
- Résultats historiques
- Statistiques de match (tirs, corners, cartons)
- Cotes de bookmakers (pré-match et clôture)

**Colonnes principales:**
```
Div, Date, Time, HomeTeam, AwayTeam
FTHG, FTAG, FTR (Full-Time Goals/Result)
HTHG, HTAG, HTR (Half-Time)
HS, AS (Shots)
HST, AST (Shots on Target)
HC, AC (Corners)
HF, AF (Fouls)
HY, AY, HR, AR (Cards)
B365H, B365D, B365A (Bet365 odds)
PSH, PSD, PSA (Pinnacle odds)
...
```

**Bookmakers supportés:**
| Code | Bookmaker | Code | Bookmaker |
|------|-----------|------|-----------|
| B365 | Bet365 | WH | William Hill |
| PS | Pinnacle | VC | Victor Chandler |
| IW | Interwetten | GB | Gamebookers |
| SS | SkyBet | 1X | 1xBet |

---

### 3. ClubElo Service (`src/ingestion/clubelo.py`)

**Données fournies:**
- Ratings Elo quotidiens pour équipes mondiales
- Historique complet par équipe
- Classements par pays/niveau

**Méthodes principales:**
```python
class ClubEloService(BaseIngestionService):
    def read_by_date(date=None) -> pd.DataFrame      # Ratings à une date
    def read_team_history(team) -> pd.DataFrame      # Historique équipe
    def read_league_ratings(league, start, end)      # Ratings par ligue
```

**Caractéristiques Elo:**
- Mis à jour après chaque match
- Comparable entre ligues et époques
- Prend en compte: marge de victoire, avantage domicile, force adversaire

---

### 4. Orchestrator (`src/ingestion/orchestrator.py`)

**Rôle:** Coordonne l'ingestion multi-sources

**Fonctionnalités:**
```python
class IngestionOrchestrator:
    # Initialisation des services
    def _get_service(source_name) -> BaseIngestionService
    
    # Gestion dimensions
    def get_or_create_league(...) -> DimLeague
    def get_or_create_season(...) -> DimSeason
    def get_or_create_team(...) -> DimTeam
    
    # Méthodes d'ingestion
    def ingest_fbref_schedule(league, season) -> Tuple[int, int]
    def ingest_matchhistory(league_div, season) -> Tuple[int, int, int]
    def ingest_clubelo_ratings() -> Tuple[int, int]
    
    # Orchestration globale
    def run_full_ingestion(sources, leagues) -> Dict
```

**Caractéristiques:**
- ✅ Idempotent (safe to re-run)
- ✅ Logging détaillé par run
- ✅ Rollback en cas d'erreur
- ✅ Batch processing

---

## 📡 API REST - Endpoints

### Base URL: `http://localhost:8000`
### Documentation interactive: `http://localhost:8000/docs`

---

### 🏆 Ligues

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/leagues` | Liste toutes les ligues |
| GET | `/leagues?country=England` | Filtre par pays |
| GET | `/leagues/{id}` | Détails d'une ligue |
| GET | `/leagues/{id}/seasons` | Saisons d'une ligue |

**Exemple de réponse:**
```json
{
  "id": 1,
  "name": "Premier League",
  "country": "England",
  "country_code": "ENG",
  "level": 1,
  "is_active": true
}
```

---

### ⚽ Matchs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/matches` | Liste des matchs (paginé) |
| GET | `/matches?league_id=1&season_id=1` | Filtre par ligue/saison |
| GET | `/matches?team_id=5` | Matchs d'une équipe |
| GET | `/matches?date_from=2024-01-01` | Filtre par date |
| GET | `/matches?status=completed` | Filtre par statut |
| GET | `/matches/{id}` | Détails d'un match |
| GET | `/matches/{id}/odds` | Cotes d'un match |

**Paramètres de pagination:**
- `page` (défaut: 1)
- `page_size` (défaut: 20, max: 100)

**Exemple de réponse:**
```json
{
  "items": [...],
  "meta": {
    "total": 380,
    "page": 1,
    "page_size": 20,
    "pages": 19
  }
}
```

---

### 🏟 Équipes

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/teams` | Liste des équipes |
| GET | `/teams?country=England` | Filtre par pays |
| GET | `/teams?search=United` | Recherche par nom |
| GET | `/teams/{id}` | Détails d'une équipe |
| GET | `/teams/{id}/matches` | Historique des matchs |

---

### 👤 Joueurs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/players` | Liste des joueurs |
| GET | `/players?nationality=France` | Filtre par nationalité |
| GET | `/players?position=Forward` | Filtre par position |
| GET | `/players?search=Mbappé` | Recherche par nom |
| GET | `/players/{id}` | Détails d'un joueur |

---

### 📊 Classements Elo

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/elo` | Tous les ratings Elo |
| GET | `/elo?team_id=5` | Historique d'une équipe |
| GET | `/elo?date_from=2024-01-01` | Filtre par date |
| GET | `/elo?limit=100` | Limite de résultats |

---

### 🔧 Ingestion

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/ingestion/logs` | Logs des ingestions |
| GET | `/ingestion/logs?source=fbref` | Filtre par source |
| POST | `/ingestion/run` | Lancer une ingestion |

**Lancer une ingestion:**
```bash
curl -X POST "http://localhost:8000/ingestion/run?sources=fbref,matchhistory&leagues=ENG-Premier%20League"
```

---

## ⚙️ Configuration

### Variables d'Environnement (`.env`)

```bash
# ==========================================
# CHEMINS ET DIRECTOIRES
# ==========================================
SOCCERDATA_DIR=/workspace/soccer_analytics/data
DATABASE_URL=sqlite:///./data/soccer_analytics.db

# ==========================================
# CONFIGURATION API
# ==========================================
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
API_SECRET_KEY=change_this_in_production

# ==========================================
# SOURCES DE DONNÉES
# ==========================================
# FBref
FBREF_MAX_RETRIES=3
FBREF_RETRY_DELAY=5
FBREF_TIMEOUT=30

# WhoScored (Selenium)
WHOSCORED_USE_SELENIUM=true
WHOSCORED_HEADLESS=true
WHOSCORED_PROXY=

# MatchHistory
MATCHHISTORY_MAX_RETRIES=3
MATCHHISTORY_RETRY_DELAY=5

# ClubElo
CLUBELO_MAX_RETRIES=3
CLUBELO_RETRY_DELAY=2

# ==========================================
# SCRAPING RESPONSABLE
# ==========================================
REQUEST_DELAY=2.0
BATCH_SIZE=50
USE_CACHE=true
CACHE_MAX_AGE_DAYS=7

# ==========================================
# LOGGING
# ==========================================
LOG_LEVEL=INFO
LOG_FORMAT=json

# ==========================================
# LIGUES ET SOURCES PAR DÉFAUT
# ==========================================
DEFAULT_LEAGUES=ENG-Premier League:2023-2024,ESP-La Liga:2023-2024,ITA-Serie A:2023-2024,GER-Bundesliga:2023-2024,FRA-Ligue 1:2023-2024
ACTIVE_SOURCES=fbref,matchhistory,clubelo

# ==========================================
# ENVIRONNEMENT
# ==========================================
ENVIRONMENT=development
```

---

### Configuration des Ligues (`config/league_dict.json`)

**Structure:**
```json
{
  "leagues": {
    "ENG-Premier League": {
      "name": "Premier League",
      "country": "England",
      "country_code": "ENG",
      "level": 1,
      "ClubElo": "ENG_1",
      "MatchHistory": "E0",
      "FBref": "Premier League",
      "WhoScored": 8,
      "Sofascore": 17,
      "season_start": 8,
      "season_end": 5
    }
  }
}
```

**12 ligues pré-configurées:**

| Ligue | Pays | ClubElo | MatchHistory | FBref |
|-------|------|---------|--------------|-------|
| ENG-Premier League | England | ENG_1 | E0 | Premier League |
| ESP-La Liga | Spain | ESP_1 | SP1 | La Liga |
| ITA-Serie A | Italy | ITA_1 | I1 | Serie A |
| GER-Bundesliga | Germany | GER_1 | D1 | Bundesliga |
| FRA-Ligue 1 | France | FRA_1 | F1 | Ligue 1 |
| NED-Eredivisie | Netherlands | NED_1 | N1 | Eredivisie |
| POR-Primeira Liga | Portugal | POR_1 | P1 | Primeira Liga |
| BRA-Serie A | Brazil | BRA_1 | - | Série A |
| ARG-Primera Division | Argentina | ARG_1 | - | Liga Profesional |
| UEFA-Champions League | Europe | - | - | Champions League |
| UEFA-Europa League | Europe | - | - | Europa League |
| ENG-Championship | England | ENG_2 | E2 | Championship |

---

## 🚀 Guide de Démarrage

### 1. Installation

```bash
cd /workspace/soccer_analytics

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copier le template .env
cp .env.example .env  # ou créer manuellement

# Vérifier la configuration des ligues
cat config/league_dict.json
```

### 3. Lancer l'API

```bash
# Démarrer le serveur
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# L'API est accessible sur:
# - http://localhost:8000
# - Documentation: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

### 4. Lancer une Ingestion

**Via l'API:**
```bash
# Ingestion complète
curl -X POST "http://localhost:8000/ingestion/run"

# Ingestion ciblée
curl -X POST "http://localhost:8000/ingestion/run?sources=fbref&leagues=ENG-Premier%20League"
```

**Via Python:**
```python
from src.ingestion.orchestrator import IngestionOrchestrator

orchestrator = IngestionOrchestrator()
stats = orchestrator.run_full_ingestion(
    sources=['fbref', 'matchhistory'],
    leagues=[('ENG-Premier League', '2023-2024')]
)
print(stats)
```

### 5. Consulter les Données

```bash
# Liste des ligues
curl http://localhost:8000/leagues

# Matchs de Premier League
curl "http://localhost:8000/matches?league_id=1&page_size=10"

# Ratings Elo
curl "http://localhost:8000/elo?limit=20"

# Logs d'ingestion
curl http://localhost:8000/ingestion/logs
```

---

## 📈 Plan d'Itérations

### 🎯 v0.1 - MVP (✅ Actuel)

**Objectif:** Validation du concept avec 3 sources de base

| Fonctionnalité | Statut | Notes |
|----------------|--------|-------|
| Structure du projet | ✅ | Architecture modulaire |
| Configuration soccerdata | ✅ | Cache, proxy, retries |
| Ingestion FBref | ✅ | Calendrier + stats équipe |
| Ingestion MatchHistory | ✅ | Résultats + cotes |
| Ingestion ClubElo | ✅ | Ratings Elo |
| Schéma SQLite | ✅ | 14 tables créées |
| API REST minimale | ✅ | 25+ endpoints |
| Documentation | ✅ | README + ARCHITECTURE |

**Métriques de succès:**
- [ ] 5 ligues ingérées avec succès
- [ ] API répond < 200ms
- [ ] Cache fonctionnel (pas de requêtes redondantes)

---

### 🚀 v0.2 - Enrichissement (Prochain)

**Objectif:** Ajouter des sources avancées et améliorer la robustesse

| Fonctionnalité | Priorité | Effort |
|----------------|----------|--------|
| WhoScored (events) | Haute | Moyen |
| Sofascore (compositions) | Haute | Moyen |
| ESPN (résultats) | Moyenne | Faible |
| Migration PostgreSQL | Haute | Moyen |
| Tests unitaires pytest | Haute | Moyen |
| Validation des données | Moyenne | Faible |
| Normalisation noms équipes | Moyenne | Faible |

**Nouvelles fonctionnalités API:**
```
GET /matches/{id}/events       # Événements détaillés
GET /matches/{id}/lineups      # Compositions d'équipe
GET /teams/{id}/stats/season   # Stats agrégées saison
GET /players/{id}/stats/career # Stats carrière
```

**Améliorations techniques:**
- [ ] Alembic pour migrations DB
- [ ] Docker Compose pour dev environment
- [ ] Health checks API
- [ ] Rate limiting

---

### 🏆 v1.0 - Production

**Objectif:** Plateforme complète et industrialisée

| Fonctionnalité | Priorité | Effort |
|----------------|----------|--------|
| Toutes les sources | Haute | Élevé |
| Jobs planifiés (cron) | Haute | Moyen |
| Authentification API | Haute | Moyen |
| Monitoring avancé | Haute | Moyen |
| Pagination avancée | Moyenne | Faible |
| Dockerisation | Haute | Faible |
| Documentation complète | Haute | Moyen |
| CI/CD pipeline | Moyenne | Moyen |

**Sources additionnelles:**
- [ ] Understat (xG, tirs)
- [ ] SoFIFA (notes joueurs EA FC)
- [ ] FiveThirtyEight (projections)

**Features avancées:**
```
POST /predictions/match        # Prédictions de matchs
GET  /analytics/team/form      # Forme récente équipe
GET  /analytics/player/compare # Comparaison joueurs
GET  /export/csv               # Export données
GET  /export/api               # Webhooks
```

**Industrialisation:**
- [ ] APScheduler pour jobs récurrents
- [ ] Prometheus + Grafana pour monitoring
- [ ] JWT authentication
- [ ] Redis pour caching distribué
- [ ] Kubernetes deployment

---

## 📊 État Actuel de la Base de Données

```sql
-- Vérifier les tables créées
.tables

-- dim_league
SELECT * FROM dim_league;

-- dim_season  
SELECT * FROM dim_season;

-- fact_match (aperçu)
SELECT match_date, home_team_id, away_team_id, home_score, away_score
FROM fact_match 
ORDER BY match_date DESC 
LIMIT 10;

-- fact_elo_history
SELECT * FROM fact_elo_history 
ORDER BY date DESC 
LIMIT 20;

-- ingestion_logs
SELECT source, status, rows_processed, started_at
FROM ingestion_logs 
ORDER BY started_at DESC;
```

---

## ⚠️ Bonnes Pratiques de Scraping

### Respect des CGU

1. **FBref**: Usage personnel/non-commercial uniquement
2. **Football-Data.co.uk**: Attribution requise
3. **ClubElo**: Pas de restrictions majeures
4. **WhoScored**: Attention au scraping intensif

### Configuration Responsable

```python
# Délais entre requêtes
REQUEST_DELAY = 2.0  # secondes

# Retries avec backoff
max_retries = 3
delay = 2.0  # exponential: 2s, 4s, 8s, 16s...

# Cache activé par défaut
USE_CACHE = true
CACHE_MAX_AGE_DAYS = 7
```

### Gestion des Erreurs

```python
# Mode dégradé
on_error = "skip"  # ou "raise"

# Logging structuré
{
  "source": "fbref",
  "league": "Premier League",
  "season": "2023-2024",
  "status": "partial",
  "rows_processed": 342,
  "error": "Timeout on match X"
}
```

---

## 📝 Attribution des Données

Les données proviennent de sources tierces. Veuillez consulter les conditions d'utilisation:

| Source | URL | Usage |
|--------|-----|-------|
| FBref | https://fbref.com/ | Personnel/Recherche |
| Football-Data.co.uk | http://www.football-data.co.uk/ | Attribution requise |
| ClubElo | http://clubelo.com/ | Libre |
| WhoScored | https://www.whoscored.com/ | Restrictions |
| Sofascore | https://www.sofascore.com/ | API terms |
| ESPN | https://www.espn.com/ | Personnel |
| Understat | https://understat.com/ | Personnel |
| SoFIFA | https://sofifa.com/ | Personnel |

---

## 🤝 Prochaines Étapes Immédiates

1. **Tester l'ingestion actuelle**
   ```bash
   python -c "from src.ingestion.orchestrator import IngestionOrchestrator; o = IngestionOrchestrator(); print(o.run_full_ingestion())"
   ```

2. **Vérifier l'API**
   ```bash
   curl http://localhost:8000/leagues
   ```

3. **Implémenter les tests**
   ```bash
   pytest tests/ -v
   ```

4. **Ajouter WhoScored** (priorité v0.2)

---

*Document généré automatiquement - Dernière mise à jour: $(date)*
