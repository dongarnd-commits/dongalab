"""Actual frozen migration execution; no tables or columns excluded from checks."""
import importlib.util
from app.core.config import ROOT
from sqlalchemy import text
from alembic.operations import Operations
from alembic.migration import MigrationContext
BEFORE_PROPOSAL=('6d5ba2015303_notice_first_slice.py','a44df74db1ac_bizinfo_ingestion.py','b730cf01a649_capability_catalog.py','c941a0042026_common_analysis_lineage.py','d752a0012026_immutable_matching_inputs.py')
AFTER_COMPANY=('fa85b0012026_company_business_sources.py','fb96c0012026_information_requests.py','fc07d0012026_recorded_authorization.py')
def load(name):
 spec=importlib.util.spec_from_file_location('v14_test_'+name,ROOT/'apps/api/alembic/versions'/name);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class ThroughLatest:
 def __init__(self,module,following):self.module=module;self.following=following;self.op=module.op
 def upgrade(self):
  self.module.upgrade()
  for name in self.following:load(name).upgrade()
 def downgrade(self):
  # Check the original Company history guard before any following DDL is removed.
  c=self.op.get_bind()
  if c.scalar(text('SELECT EXISTS(SELECT 1 FROM companies)')):raise RuntimeError('COMPANY_HISTORY_EXISTS')
  for name in reversed(self.following):load(name).downgrade()
  self.module.downgrade()
def proposal_baseline(connection):
 with Operations.context(MigrationContext.configure(connection)):
  for name in BEFORE_PROPOSAL:load(name).upgrade()
