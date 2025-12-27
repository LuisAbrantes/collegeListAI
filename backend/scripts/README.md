# Scripts

Utility scripts for College List AI.

## Available Scripts

### seed_universities.py
Pre-populates the database with top universities for popular majors.

```bash
cd backend
python -m scripts.seed_universities
```

### refresh_database.py
Background job to refresh stale data (run via cron).

```bash
cd backend
python -m scripts.refresh_database --limit 50
```

**Cron example (run daily at 3am):**
```cron
0 3 * * * cd /path/to/backend && python -m scripts.refresh_database --limit 50
```
