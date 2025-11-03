# Database Migrations

This directory contains sequential database migration scripts for the AI Chatbot system.

## Migration Numbering

Migrations are numbered sequentially from 09-24. Migration #10 is intentionally skipped as it was for the `suggested_knowledge` feature which was later removed.

### Current Active Migrations (Oct 12, 2025)

- **09**: Knowledge multi-intent classification
- **11**: Add source tracking to knowledge candidates
- **12**: Remove suggested_knowledge feature
- **13**: Add auto test scenario creation trigger
- **14**: Add rejected scenario retry logic
- **15**: Update candidates view for rejected scenarios
- **16**: Fix candidates view filter
- **17**: Fix candidates view to check all scenarios

### Historical Migrations (Renumbered)

- **18**: Deprecate collection tables
- **19**: Create suggested_knowledge (DEPRECATED - feature removed in #12)
- **20**: Add semantic similarity to unclear questions
- **21**: Fix semantic similarity function
- **22**: Fix duplicate test scenario creation
- **23**: AI knowledge generation
- **24**: Fix knowledge check function

## Applying Migrations

Migrations should be applied in numerical order. Use the schema_migrations table to track which migrations have been executed:

```sql
SELECT * FROM schema_migrations ORDER BY id;
```

## Recording Migration Execution

After applying a migration manually, record it:

```sql
INSERT INTO schema_migrations (migration_file, description)
VALUES ('XX-migration-name.sql', 'Brief description of what this migration does');
```

## Notes

- Migrations 11-17 represent the current active codebase state as of Oct 12, 2025
- Migrations 18-24 are older migrations that were renumbered to avoid conflicts
- Migration #10 (suggested_knowledge) was deprecated when the feature was removed
- The base schema is in `database/init/` directory
