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

# MongoDB Backup Configuration
BACKUP_HOUR=03
BACKUP_MINUTE=30
BACKUP_RETENTION_DAYS=7
```

### Environment Variables Explained

#### MongoDB Configuration
- `MONGO_ROOT_USER`: MongoDB root administrator username (default: `root`)
- `MONGO_ROOT_PWD`: Secure password for the MongoDB root user
- `MONGO_APP_DB`: Database name for the application (default: `clash_royale`)
- `MONGO_APP_USER`: Application user for database operations (default: `data_scraper`)
- `MONGO_APP_PWD`: Secure password for the application user
- `MONGO_INITDB_DATABASE`: Database to initialize with the application user (must match `MONGO_APP_DB`)

#### Backup Configuration
- `BACKUP_HOUR`: Hour (0-23) when daily backups run (default: `03` = 3 AM)
- `BACKUP_MINUTE`: Minute (0-59) when daily backups run (default: `30`)
- `BACKUP_RETENTION_DAYS`: Number of days to keep backup files (default: `7`)

### 2. Docker Setup

Start the MongoDB and backup services:

```bash
docker compose up -d
```

### 3. Restoring Data

Example Commands for restoring data 

#### On Linux/macOS/WSL
```bash
cd db
./restore.sh ./backups/clash_royale_2025-08-13_16-40-01
```

#### On Windows PowerShell
```bash
cd db
.\restore.ps1 .\backups\clash_royale_2025-08-13_16-40-01
```