# Password Authentication

MaintainNexus uses persisted bcrypt credentials in the `staff_credentials`
table. Run migrations first, then seed missing demo accounts:

```bash
python -m database.run_migrations
python -m database.seed_credentials
```

The seed command prints plaintext defaults only to its terminal output. It
does not store them. Every seeded account starts with
`must_change_password = true` and must use `PATCH /api/v1/auth/change-password`
after signing in.

## Default Credentials

| ID | Role | Default password |
| --- | --- | --- |
| TECH-101 through TECH-120 | technician | `Tech-<number>-2026` |
| tech-demo | technician | `TechDemo-2026` |
| engineer-demo | engineer | `EngineerDemo-2026` |
| supervisor-demo | supervisor | `SupervisorDemo-2026` |
| executive-demo | executive | `ExecutiveDemo-2026` |
| ENG-1 through ENG-3 | engineer | `Eng-<number>-2026` |
| SUP-1 through SUP-3 | supervisor | `Sup-<number>-2026` |
| EXEC-1 through EXEC-3 | executive | `Exec-<number>-2026` |

There are 33 seeded identities: 20 technicians, four existing demo accounts,
and three accounts in each of the other three role groups. The technician
roster is generated deterministically, so `TECH-101` through `TECH-120` keep
their identity across process restarts.

## Client Flow

The mobile app routes a first-login account to its change-password screen
through the existing Navigator listener, then exposes the same screen from
Settings. The web app uses `/change-password`, available after login and from
the profile page. Neither client stores a plaintext password; mobile session
restore requires signing in again.