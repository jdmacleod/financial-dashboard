-- Create restricted application role
CREATE ROLE hearthledger_app LOGIN PASSWORD 'changeme'; -- pragma: allowlist secret
GRANT CONNECT ON DATABASE hearthledger TO hearthledger_app;
GRANT USAGE ON SCHEMA public TO hearthledger_app;
-- Table-level grants are applied per-table in Alembic migrations.
-- The audit_log table will receive only SELECT, INSERT.
