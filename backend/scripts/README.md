# Scripts

Utility scripts for College List AI.

## Available Scripts

### seed_universities.py
Pre-populates the database with top universities for popular majors.

```bash
cd backend
python scripts/seed_universities.py
```

### seed_need_blind.py
Updates the database with **verified need-blind admission data** from authoritative sources.

**Data includes:**
- Schools need-blind for **ALL** students (domestic + international): Harvard, Yale, Princeton, MIT, Amherst, Bowdoin, Dartmouth
- Schools need-blind for **DOMESTIC only**: Stanford, Columbia, Duke, Cornell, etc.
- Schools explicitly **need-AWARE** for international students: Penn State, CMU, NYU, etc.

```bash
cd backend
python scripts/seed_need_blind.py
```

> **Note:** Run this script after seeding universities to ensure accurate financial aid data.

### refresh_database.py
Background job to refresh stale data (run via cron).

```bash
cd backend
python scripts/refresh_database.py --limit 50
```

**Cron example (run daily at 3am):**
```cron
0 3 * * * cd /path/to/backend && python scripts/refresh_database.py --limit 50
```

