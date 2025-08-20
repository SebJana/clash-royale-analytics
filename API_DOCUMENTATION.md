# API Documentation

This document provides comprehensive documentation for all available API endpoints in the Clash Royale Analytics system.

## Base URL

When running locally with Docker: `http://localhost:8000`

## Authentication

The API currently doesn't require authentication for client requests. The system handles Clash Royale API authentication internally using the configured API keys.

## Endpoints

### 1. Health Check

#### `GET /ping`

Check if the API service is running and responsive.

**Response:**
```json
{
  "message": "pong"
}
```

**Status Codes:**
- `200 OK` - Service is running

---

### 2. Player Management

#### `POST /tracked-players/{player_tag}`

Add a player to the continuous tracking system. The data scraper will automatically fetch battle logs for this player every hour.

**Parameters:**
- `player_tag` (path) - Clash Royale player tag (e.g., `%23YYRJQY28` for `#YYRJQY28`)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/tracked-players/%23YYRJQY28"
```

**Response:**
```json
{
  "message": "Player #YYRJQY28 added to tracking"
}
```

**Status Codes:**
- `200 OK` - Player successfully added
- `400 Bad Request` - Invalid player tag format
- `404 Not Found` - Player tag doesn't exist in Clash Royale
- `409 Conflict` - Player is already being tracked
- `403 Forbidden` - API access issues
- `429 Too Many Requests` - Rate limit exceeded

#### `GET /tracked-players`

Get a list of all players currently being tracked by the system.

**Example Request:**
```bash
curl "http://localhost:8000/tracked-players"
```

**Response:**
```json
{
  "tracked_players": ["#YYRJQY28", "#ABC123XYZ", "#DEF456UVW"],
  "count": 3
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved tracked players
- `500 Internal Server Error` - Database connection issues

---

### 3. Player Data

#### `GET /player-stats/{player_tag}`

Get current player statistics and profile information directly from the Clash Royale API.

**Parameters:**
- `player_tag` (path) - Clash Royale player tag (URL encoded)

**Example Request:**
```bash
curl "http://localhost:8000/player-stats/%23YYRJQY28"
```

**Response:**
```json
{
  "tag": "#YYRJQY28",
  "name": "PlayerName",
  "expLevel": 13,
  "trophies": 5200,
  "bestTrophies": 5400,
  "wins": 1250,
  "losses": 980,
  "battleCount": 2230,
  "threeCrownWins": 890,
  "challengeCardsWon": 15420,
  "challengeMaxWins": 12,
  "tournamentCardsWon": 350,
  "tournamentBattleCount": 45,
  "role": "member",
  "donations": 125,
  "donationsReceived": 134,
  "totalDonations": 45890,
  "warDayWins": 78,
  "clanCardsCollected": 12340,
  "clan": {
    "tag": "#CLAN123",
    "name": "Clan Name",
    "badgeId": 16000000
  },
  "arena": {
    "id": 54000015,
    "name": "Legendary Arena"
  },
  "leagueStatistics": {
    "currentSeason": {
      "trophies": 5200,
      "bestTrophies": 5400
    },
    "previousSeason": {
      "id": "2023-12",
      "trophies": 5100,
      "bestTrophies": 5350
    }
  },
  "badges": [],
  "achievements": [],
  "cards": [],
  "currentDeck": [],
  "currentFavouriteCard": {
    "name": "Hog Rider",
    "id": 26000021,
    "maxLevel": 14,
    "iconUrls": {}
  },
  "starPoints": 2450
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved player stats
- `404 Not Found` - Player not found
- `403 Forbidden` - API token issues
- `429 Too Many Requests` - Rate limit exceeded
- `502 Bad Gateway` - Network error contacting Clash Royale API

#### `GET /battles/{player_tag}/last/{amount}`

Get the most recent battle logs for a tracked player from the local database.

**Parameters:**
- `player_tag` (path) - Clash Royale player tag (URL encoded)
- `amount` (path) - Number of battles to retrieve (integer)

**Example Request:**
```bash
curl "http://localhost:8000/battles/%23YYRJQY28/last/5"
```

**Response:**
```json
{
  "player_tag": "#YYRJQY28",
  "battles": [
    {
      "battleTime": "20241201T120000.000Z",
      "arena": "Legendary Arena",
      "gameMode": "PvP",
      "gameResult": "victory",
      "team": [
        {
          "tag": "#YYRJQY28",
          "name": "PlayerName",
          "startingTrophies": 5200,
          "trophyChange": 32,
          "crowns": 2,
          "cards": [
            {
              "name": "Hog Rider",
              "id": 26000021,
              "level": 11,
              "maxLevel": 14
            }
          ]
        }
      ],
      "opponent": [
        {
          "tag": "#OPPONENT1",
          "name": "OpponentName",
          "startingTrophies": 5180,
          "trophyChange": -30,
          "crowns": 1,
          "cards": [
            {
              "name": "Golem",
              "id": 26000009,
              "level": 10,
              "maxLevel": 14
            }
          ]
        }
      ],
      "referencePlayerTag": "#YYRJQY28"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved battles
- `404 Not Found` - Player not found or no battles available
- `500 Internal Server Error` - Database error

---

### 4. Game Data

#### `GET /cards`

Get information about all cards available in Clash Royale.

**Example Request:**
```bash
curl "http://localhost:8000/cards"
```

**Response:**
```json
{
  "items": [
    {
      "name": "Hog Rider",
      "id": 26000021,
      "maxLevel": 14,
      "iconUrls": {
        "medium": "https://api-assets.clashroyale.com/cards/300/..."
      },
      "rarity": "Rare",
      "elixirCost": 4,
      "type": "Troop"
    },
    {
      "name": "Fireball",
      "id": 28000000,
      "maxLevel": 14,
      "iconUrls": {
        "medium": "https://api-assets.clashroyale.com/cards/300/..."
      },
      "rarity": "Rare",
      "elixirCost": 4,
      "type": "Spell"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved cards
- `403 Forbidden` - API token issues
- `429 Too Many Requests` - Rate limit exceeded
- `502 Bad Gateway` - Network error

#### `POST /decks/unique`

Get unique deck combinations used by a player within a specific date range.

**Request Body:**
```json
{
  "player_tag": "#YYRJQY28",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/decks/unique" \
  -H "Content-Type: application/json" \
  -d '{"player_tag": "#YYRJQY28", "start_date": "2024-01-01", "end_date": "2024-01-31"}'
```

**Response:**
```json
{
  "player_tag": "#YYRJQY28",
  "count": 3,
  "unique decks": [
    [
      "Hog Rider",
      "Fireball",
      "Zap",
      "Musketeer",
      "Ice Spirit",
      "Skeletons",
      "Cannon",
      "Log"
    ],
    [
      "Giant",
      "Wizard",
      "Fireball",
      "Zap",
      "Minions",
      "Skeleton Army",
      "Tombstone",
      "Arrows"
    ],
    [
      "X-Bow",
      "Tesla",
      "Ice Spirit",
      "Skeletons",
      "Log",
      "Fireball",
      "Archers",
      "Knight"
    ]
  ]
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved unique decks
- `404 Not Found` - No decks found for the player in the specified date range
- `500 Internal Server Error` - Database error

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error description"
}
```

### Common Status Codes

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request parameters
- `403 Forbidden` - Authentication/authorization issues with Clash Royale API
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `502 Bad Gateway` - External API error

## Rate Limits

The system respects Clash Royale API rate limits. If you encounter 429 errors, wait before making additional requests.

## Player Tag Format

Player tags must be URL encoded when used in path parameters:
- `#YYRJQY28` becomes `%23YYRJQY28`
- `#ABC123XYZ` becomes `%23ABC123XYZ`

## Data Freshness

- **Player Stats**: Retrieved in real-time from Clash Royale API
- **Battle Data**: Updated hourly for tracked players
- **Card Information**: Retrieved in real-time from Clash Royale API
- **Unique Decks**: Based on stored battle data (hourly updates)

## Pagination

Currently, the API doesn't implement pagination. The `/battles/{player_tag}/last/{amount}` endpoint allows you to specify the number of battles to retrieve.