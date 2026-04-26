# Architecture Soccer Analytics Platform

## Vue d'ensemble

Application Python de gestion et d'analyse de données footballistiques multi-sources, basée sur la librairie `soccerdata`.

### Principes directeurs (Philosophie soccerdata)

1. **DataFrames Pandas** : Tous les échanges de données utilisent des DataFrames avec noms/identifiants cohérents
2. **Cache local** : Téléchargement à la demande avec mise en cache pour éviter les requêtes redondantes
3. **Scraping responsable** : Respect des CGU, délais entre requêtes, gestion graceful des erreurs
4. **Configuration JSON** : league_dict.json pour ajouter des ligues personnalisées
5. **Séparation des responsabilités** : Ingestion → Nettoyage → Stockage → Exposition

## Architecture globale

```
┌─────────────────────────────────────────────────────────────────┐
│                        API REST (FastAPI)                       │
│  /leagues, /seasons, /matches, /teams, /players, /odds, ...    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Couche de Stockage (PostgreSQL)              │
│  Dimensions: leagues, seasons, teams, players                   │
│  Faits: matches, team_stats, player_stats, odds, events        │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Couche d'Ingestion (soccerdata)              │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐  │
│  │  FBref   │WhoScored │Sofascore │  ESPN    │MatchHistory │  │
│  ├──────────┼──────────┼──────────┼──────────┼──────────────┤  │
│  │ ClubElo  │ SoFIFA   │Understat │          │              │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration & Cache                        │
│  - SOCCERDATA_DIR/config/league_dict.json                       │
│  - Cache local (parquet/csv)                                    │
│  - Variables d'environnement                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Schéma de base de données

```sql
-- Dimensions
dim_league (id, name, country, source_ids, created_at, updated_at)
dim_season (id, league_id, year, start_month, end_month, is_current)
dim_team (id, name, short_name, country, founded, logo_url)
dim_player (id, name, nationality, birth_date, position, height, weight)

-- Faits principales
fact_match (
    id, league_id, season_id, match_date, home_team_id, away_team_id,
    home_score, away_score, status, venue, attendance,
    referee, source_urls, extracted_at
)

fact_team_match_stats (
    id, match_id, team_id, is_home,
    shots, shots_on_target, possession, corners, fouls,
    yellow_cards, red_cards, xg, xg_against,
    source, extracted_at
)

fact_player_match_stats (
    id, match_id, player_id, team_id, is_home,
    minutes_played, goals, assists, shots, passes_completed,
    tackles, interceptions, rating, position,
    source, extracted_at
)

fact_team_season_stats (
    id, league_id, season_id, team_id, stat_type,
    matches_played, wins, draws, losses,
    goals_for, goals_against, points,
    stats_json, source, extracted_at
)

fact_player_season_stats (
    id, league_id, season_id, player_id, team_id, stat_type,
    appearances, minutes_played, goals, assists,
    stats_json, source, extracted_at
)

fact_odds (
    id, match_id, bookmaker, bet_type,
    home_odd, draw_odd, away_odd,
    is_closing, timestamp, source
)

fact_events (
    id, match_id, minute, event_type, team_id, player_id,
    description, x, y, source
)

fact_elo_history (
    id, team_id, date, elo_rating, rank, source
)

fact_sofifa_ratings (
    id, player_id, season, overall_rating, potential,
    team_id, positions, source
)

fact_understat_shots (
    id, match_id, team_id, player_id, minute,
    xg, x, y, situation, shot_type, body_part,
    source
)

-- Logs d'ingestion
ingestion_logs (
    id, source, league_id, season_id, run_id,
    started_at, ended_at, status, rows_processed,
    error_message
)
```

## Plan d'itérations

### v0.1 - MVP (2-3 semaines)
- [x] Structure du projet et configuration de base
- [ ] Installation et configuration de soccerdata
- [ ] Ingestion FBref (schedule + team stats standard)
- [ ] Ingestion MatchHistory (résultats + cotes de base)
- [ ] Schéma SQLite simplifié
- [ ] API REST minimale (listes ligues, matchs, stats équipe)
- [ ] Documentation de base

### v0.2 - Enrichissement (3-4 semaines)
- [ ] Ajout WhoScored (events détaillés)
- [ ] Ajout Sofascore (compositions, stats joueurs)
- [ ] Ajout ClubElo (historique ratings)
- [ ] Migration vers PostgreSQL
- [ ] Système de cache amélioré
- [ ] Gestion des ligues personnalisées (league_dict.json)
- [ ] Tests unitaires pytest

### v1.0 - Production (4-6 semaines)
- [ ] Toutes les sources intégrées (ESPN, Understat, SoFIFA)
- [ ] Jobs planifiés avec traçabilité
- [ ] Authentification API
- [ ] Monitoring et logs structurés
- [ ] Pagination et filtres avancés
- [ ] Documentation complète
- [ ] Dockerisation
