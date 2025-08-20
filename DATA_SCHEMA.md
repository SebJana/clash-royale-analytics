# Data Schema Documentation

This document describes the structure and format of data stored and accessible through the Clash Royale Analytics system.

## Database Collections

The MongoDB database contains the following main collections:

### 1. Players Collection

Stores information about tracked players.

```javascript
{
  "_id": ObjectId("..."),
  "playerTag": "#YYRJQY28",
  "active": true,
  "insertedAt": "2024-01-15 10-30-00"
}
```

**Fields:**
- `playerTag` (string) - Unique Clash Royale player identifier
- `active` (boolean) - Whether the player is currently being tracked
- `insertedAt` (string) - Timestamp when player was added to tracking

### 2. Battles Collection

Stores detailed battle log information for tracked players.

```javascript
{
  "_id": ObjectId("..."),
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
          "maxLevel": 14,
          "starLevel": 0,
          "iconUrls": {
            "medium": "https://api-assets.clashroyale.com/cards/300/..."
          },
          "rarity": "Rare",
          "elixirCost": 4,
          "type": "Troop"
        }
        // ... 7 more cards (8 total)
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
        // Similar card structure
      ]
    }
  ],
  "referencePlayerTag": "#YYRJQY28"
}
```

**Key Fields:**
- `battleTime` (ISO 8601 string) - When the battle occurred
- `arena` (string) - Arena name where battle took place
- `gameMode` (string) - Game mode (e.g., "PvP", "2v2", "Challenge")
- `gameResult` (string) - "victory", "defeat", or "draw"
- `team` (array) - Player's team information
- `opponent` (array) - Opponent team information  
- `referencePlayerTag` (string) - The tracked player this battle belongs to

**Player Object Structure:**
- `tag` (string) - Player tag
- `name` (string) - Player display name
- `startingTrophies` (number) - Trophies before battle
- `trophyChange` (number) - Trophy change from battle
- `crowns` (number) - Crown towers destroyed
- `cards` (array) - 8-card deck used in battle

**Card Object Structure:**
- `name` (string) - Card name (e.g., "Hog Rider")
- `id` (number) - Unique card identifier
- `level` (number) - Card level in this battle
- `maxLevel` (number) - Maximum possible level for this card
- `starLevel` (number) - Star level (cosmetic upgrade)
- `iconUrls` (object) - URLs to card artwork
- `rarity` (string) - "Common", "Rare", "Epic", "Legendary", "Champion"
- `elixirCost` (number) - Elixir cost to play the card
- `type` (string) - "Troop", "Spell", "Building"

## API Response Formats

### Player Statistics Response

```javascript
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
  "achievements": [
    {
      "name": "Team Player",
      "stars": 3,
      "value": 1000,
      "target": 1000,
      "info": "Win 1000 battles"
    }
  ],
  "cards": [
    {
      "name": "Hog Rider",
      "level": 11,
      "maxLevel": 14,
      "count": 1247,
      "iconUrls": {},
      "starLevel": 0
    }
  ],
  "currentDeck": [
    // 8 cards in current battle deck
  ],
  "currentFavouriteCard": {
    "name": "Hog Rider",
    "id": 26000021,
    "maxLevel": 14,
    "iconUrls": {}
  },
  "starPoints": 2450
}
```

### Battle History Response

```javascript
{
  "player_tag": "#YYRJQY28",
  "battles": [
    // Array of battle objects (as described in Battles Collection)
  ]
}
```

### Unique Decks Response

```javascript
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
    ]
  ]
}
```

### Cards Database Response

```javascript
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
    }
    // ... more cards
  ]
}
```

## Database Indexes

For optimal query performance, the following indexes are created:

### Players Collection
- `{ playerTag: 1 }` - Unique index for fast player lookups

### Battles Collection
- `{ referencePlayerTag: 1, battleTime: -1 }` - Unique compound index for battle queries
- `{ referencePlayerTag: 1, gameResult: 1 }` - Index for win/loss analysis
- `{ referencePlayerTag: 1, gameResult: 1, battleTime: -1 }` - Performance analysis over time
- `{ referencePlayerTag: 1, gameMode: 1, battleTime: -1 }` - Game mode preferences

## Data Types and Validation

### Player Tags
- Format: `#[A-Z0-9]{8,11}` using Supercell alphabet `0289PYLQGRJCUV`
- Always stored with the `#` prefix
- URL-encoded as `%23` in API requests

### Timestamps
- Battle times: ISO 8601 format (e.g., `2024-01-15T14:30:00.000Z`)
- Insert times: Custom format (e.g., `2024-01-15 14-30-00`)

### Trophy Values
- Range: 0 to ~8000+ (depending on current game balance)
- Trophy changes can be positive (wins) or negative (losses)

### Card Levels
- Common cards: 1-15
- Rare cards: 1-13  
- Epic cards: 1-10
- Legendary cards: 1-7
- Champion cards: 1-7

### Game Results
- `"victory"` - Player won the battle
- `"defeat"` - Player lost the battle  
- `"draw"` - Battle ended in a tie

### Game Modes
Common values include:
- `"PvP"` - Standard ladder matches
- `"2v2"` - 2v2 casual battles
- `"Challenge"` - Special challenges
- `"Tournament"` - Tournament matches
- `"ClanWar"` - Clan war battles

### Arenas
Examples:
- `"Training Camp"`
- `"Goblin Stadium"`
- `"Bone Pit"`
- `"Legendary Arena"`

## Query Patterns

### Common Aggregations

**Win Rate Calculation:**
```javascript
// MongoDB aggregation
db.battles.aggregate([
  { $match: { referencePlayerTag: "#YYRJQY28" } },
  { $group: {
    _id: "$gameResult",
    count: { $sum: 1 }
  }}
])
```

**Deck Usage Analysis:**
```javascript
// Get most used cards
db.battles.aggregate([
  { $match: { referencePlayerTag: "#YYRJQY28" } },
  { $unwind: "$team" },
  { $match: { "team.tag": "#YYRJQY28" } },
  { $unwind: "$team.cards" },
  { $group: {
    _id: "$team.cards.name",
    usage_count: { $sum: 1 }
  }},
  { $sort: { usage_count: -1 } }
])
```

**Performance by Arena:**
```javascript
db.battles.aggregate([
  { $match: { referencePlayerTag: "#YYRJQY28" } },
  { $group: {
    _id: { arena: "$arena", result: "$gameResult" },
    count: { $sum: 1 }
  }}
])
```

## Data Retention and Growth

### Storage Estimates
- Each battle document: ~2-4 KB
- Player with 10 battles/day: ~30-60 KB/day
- 100 tracked players: ~3-6 MB/day
- Annual storage for 100 active players: ~1-2 GB

### Backup Schedule
- Daily backups at configured time (default: 3:30 AM)
- Retention period: configurable (default: 7 days)
- Backup location: `./db/backups/`

## Data Privacy and Security

### Player Data
- Only public battle log data is collected
- No private player information is stored
- Player tags are public identifiers in Clash Royale

### API Keys
- Stored in environment variables only
- Never logged or exposed in responses
- Should be kept confidential and rotated regularly

### Database Security
- MongoDB secured with authentication
- Database isolated in Docker network
- Regular backup encryption recommended for production