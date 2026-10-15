import pytest
from isolation import require_test_database

def pytest_collection_finish(session):
 if any(item.get_closest_marker('integration') for item in session.items):
  try:require_test_database()
  except RuntimeError as exc:raise pytest.UsageError(str(exc)) from None
