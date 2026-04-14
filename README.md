# RBACMatrix AI

Smart AI-Based MFA + RBAC Server Management System
Flask only · No Firebase · No React · SQLite (swappable to PostgreSQL)

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Copy your model.pkl to project root
cp /path/to/model.pkl .

# 3. Seed demo accounts
python seed.py

# 4. Run
python app.py
# → http://localhost:5000
```

## Accounts
| Role        | Email                      | Password   |
|-------------|----------------------------|------------|
| Super Admin | sanjay22522g@gmail.com     | rbac@2006  |
| Admin       | admin@rbac.com             | admin123   |
| User        | user@rbac.com              | user123    |

## Change Super Admin credentials
Edit `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` in `config.py`,
delete `rbacmatrix.db`, then run `python seed.py` again.

## Switch to PostgreSQL
Set `DB_TYPE = "postgresql"` in `config.py` and fill in `POSTGRES_CONFIG`.
Nothing else changes.

## Risk Model
Your `model.pkl` is used with exact same features:
`device, location, loginCount, hour, failedAttempts`
- 0 = Safe → login directly
- 1 = Risky → OTP email sent

## Location Detection
Uses your exact chain: ipify.org → ipapi.co → ipwho.is (fallback)
