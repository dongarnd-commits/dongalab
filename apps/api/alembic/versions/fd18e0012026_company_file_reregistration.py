"""Approved PR14 v1.4.2: immutable registrations may share inactive content."""
from alembic import op
from sqlalchemy import text
revision='fd18e0012026'
down_revision='fc07d0012026'
branch_labels=None
depends_on=None

def upgrade():
 op.execute('ALTER TABLE company_files DROP CONSTRAINT company_files_company_id_digest_key')
 op.execute('CREATE INDEX ix_company_files_company_digest ON company_files (company_id,digest)')
 op.execute("""CREATE FUNCTION guard_company_active_file_registration() RETURNS trigger LANGUAGE plpgsql AS $$
 BEGIN
  PERFORM id FROM companies WHERE id=NEW.company_id FOR UPDATE;
  IF EXISTS(SELECT 1 FROM company_files f WHERE f.company_id=NEW.company_id AND f.digest=NEW.digest
    AND NOT EXISTS(SELECT 1 FROM company_file_events e WHERE e.file_id=f.id)) THEN
   RAISE EXCEPTION 'DUPLICATE_ACTIVE_COMPANY_FILE' USING ERRCODE='23505';
  END IF;
  RETURN NEW;
 END $$""")
 op.execute('CREATE TRIGGER guard_company_active_file_registration BEFORE INSERT ON company_files FOR EACH ROW EXECUTE FUNCTION guard_company_active_file_registration()')

def downgrade():
 if op.get_bind().scalar(text('SELECT EXISTS(SELECT 1 FROM company_files GROUP BY company_id,digest HAVING count(*)>1)')):
  raise RuntimeError('COMPANY_FILE_REGISTRATION_HISTORY_EXISTS')
 op.execute('DROP TRIGGER guard_company_active_file_registration ON company_files')
 op.execute('DROP FUNCTION guard_company_active_file_registration()')
 op.execute('DROP INDEX ix_company_files_company_digest')
 op.execute('ALTER TABLE company_files ADD CONSTRAINT company_files_company_id_digest_key UNIQUE (company_id,digest)')
