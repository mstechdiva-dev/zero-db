# Migrations (history)

`supabase/schema.sql` is now the complete schema and already includes everything in these files.
**A new database only needs `schema.sql`.** If a database has old or mismatched tables, run
`supabase/reset.sql` and then `schema.sql`. See `SETUP.md`, section 1.

These files record how the schema got here, in order. They are only useful for a database that was
built from the earlier `schema.sql` and holds data you want to keep without resetting.
