# Clash Royale Analytics

## Setup

### 1. Environment Configuration

Create a `.env` file in the project root with the following configuration:

```env
# MongoDB Credentials
MONGO_ROOT_USER=root
MONGO_ROOT_PWD=YOUR_SECURE_ROOT_PASSWORD
MONGO_APP_DB=clash_royale
MONGO_APP_USER=data_scraper
MONGO_APP_PWD=YOUR_SECURE_USER_PASSWORD
MONGO_INITDB_DATABASE=clash_royale
MONGO_HOST=mongo
MONGO_PORT=27017

# MongoDB Backup Configuration
BACKUP_HOUR=03
BACKUP_MINUTE=30
BACKUP_RETENTION_DAYS=7

# Redis credentials
REDIS_PASSWORD=YOUR_SECURE_REDIS_PASSWORD

# Clash Royale API Keys
DATA_SCRAPER_API_KEY = ey31asd23...
APP_API_KEY = ey41eas...
```

### Environment Variables Explained

#### MongoDB Configuration
- `MONGO_ROOT_USER`: MongoDB root administrator username (default: `root`)
- `MONGO_ROOT_PWD`: Secure password for the MongoDB root user
- `MONGO_APP_DB`: Database name for the application (default: `clash_royale`)
- `MONGO_APP_USER`: Application user for database operations (default: `data_scraper`)
- `MONGO_APP_PWD`: Secure password for the application user
- `MONGO_INITDB_DATABASE`: Database to initialize with the application user (must match `MONGO_APP_DB`)
- `MONGO_HOST`: Hostname of the MongoDB service (default: mongo when running in Docker Compose)
- `MONGO_PORT`: Port number where MongoDB is exposed (default: 27017)


#### Backup Configuration
- `BACKUP_HOUR`: Hour (0-23) when daily backups run (default: `03` = 3 AM)
- `BACKUP_MINUTE`: Minute (0-59) when daily backups run (default: `30`)
- `BACKUP_RETENTION_DAYS`: Number of days to keep backup files (default: `7`)

#### Redis credentials
- `REDIS_PASSWORD`: Secure password for the redis database

#### Clash Royale API Keys
- `DATA_SCRAPER_API_KEY`: API Key used to run the cyclic tracking and refreshing of selected player(s)
- `APP_API_KEY`: API Key used to query on-demand data for an active user

It’s possible to use the same key for both parameters/roles, but for modulation purposes and to comply with the request limitations stated by Clash Royale, it’s advised to use separate keys. Get your API Keys from the official Clash Royale API website: https://developer.clashroyale.com

// TODO (potentially) add the option to use multiple keys with a key rotation for the Clash Royale API calls
Make it a shared module for both data scraping and the api 

### 2. Docker Setup

Start all services by running:

```bash
docker compose up -d
```

### 3. Restoring Data

Example Commands for restoring data 

#### On Linux/macOS/WSL
```bash
cd db
./restore.sh ./backups/clash_royale_YYYY-MM-DD_HH-MM-SS
```

#### On Windows PowerShell
```bash
cd db
.\restore.ps1 .\backups\clash_royale_YYYY-MM-DD_HH-MM-SS
```