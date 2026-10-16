"""Operator-invoked local source import; system audit, not an invented user review."""
from app.core.config import ROOT
from app.infrastructure.database import get_session_factory
from app.infrastructure.dmp_inventory import read_inventory
from app.capability.application import CapabilityApplication

def main():
    source=ROOT/'_local_inputs/dmp_features_649.json'
    _,digest,matches=read_inventory(source)
    if not matches: raise SystemExit('SOURCE_HASH_MISMATCH: source unchanged; compare before import')
    factory=get_session_factory()
    with factory.begin() as session:
        result=CapabilityApplication(session).import_inventory(source.read_bytes())
    print({'import_id':result['id'],'count':result['feature_count'],'replay':result['replay'],'digest':digest})
if __name__=='__main__': main()
