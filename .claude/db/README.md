# db/ — SQL Scripts

`DB_DIR` (declared in `.claude/rules/PATH.md`). SQL Server 2025 Express scripts written by `db-developer`, kept in the Claude area (`.claude\db`):

```text
db/
├── README.md        (this file)
├── migrations/      ordered schema/data changes + reverse scripts
├── procs/           stored procedures
├── views/           views
├── queries/         ad-hoc and report queries
└── logs/            sqlcmd output (not committed)
```

## Rules

- **Only `db-developer` writes here.** Other agents read the scripts; a needed change goes back to `db-developer` as a fix.
- **Script first, run second:** every change is a file here before it is executed against any database.
- Every script runs **unchanged in SSMS** (`GO` batch separators) and starts with a header comment: purpose, target database, requirement ID (`DB-n`), author agent.
- Scripts are **idempotent** (`IF NOT EXISTS`, `CREATE OR ALTER`) and wrap data changes in a transaction with error handling.
- Never edit a migration that has already been applied — add a new one with its reverse script.
- No SQL Server Agent on Express: do not write Agent jobs.
- No passwords, real connection strings, or customer data in any script.
- Executing a script against a real database is a `db-developer` step with explicit confirmation of server and database; **prod needs same-turn user approval**.
