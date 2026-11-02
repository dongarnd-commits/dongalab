"""Additive DMP asset management and generated technical solution snapshots."""
from sqlalchemy import Column, String, Text, Integer, Boolean, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.notice_schema import table, ref
from app.infrastructure import capability_schema

nodes = table("dmp_asset_nodes",
    Column("kind", String(12), nullable=False),
    ref("feature_id", "dmp_features", True),
    Column("current_ordinal", Integer, nullable=False, server_default="0"),
    UniqueConstraint("feature_id"),
    CheckConstraint("kind IN ('SYSTEM','MODULE','FEATURE')", name="ck_asset_kind"),
    CheckConstraint("(kind='FEATURE') = (feature_id IS NOT NULL)", name="ck_asset_feature_target"),
    CheckConstraint("current_ordinal>=0"))
versions = table("dmp_asset_versions",
    ref("node_id", "dmp_asset_nodes"), Column("ordinal", Integer, nullable=False),
    ref("parent_id", "dmp_asset_nodes", True),
    ref("parent_version_id", "dmp_asset_versions", True),
    ref("source_revision_id", "dmp_feature_revisions", True),
    Column("digest", String(64), nullable=False),
    Column("data", JSONB, nullable=False), ref("actor_id", "local_actors"),
    UniqueConstraint("node_id", "ordinal"), UniqueConstraint("node_id", "digest"),
    CheckConstraint("ordinal>0"),
    CheckConstraint("data->>'availability' IN ('NEEDS_CONFIRMATION','VERIFIED','UNAVAILABLE','RETIRED')", name="ck_asset_supply_status"),
    CheckConstraint("data->>'availability'<>'VERIFIED' OR length(btrim(data->>'availability_evidence'))>0", name="ck_asset_supply_evidence"))
relations = table("dmp_asset_relations",
    ref("version_id", "dmp_asset_versions"), ref("target_node_id", "dmp_asset_nodes"),
    ref("target_version_id", "dmp_asset_versions"),
    Column("kind", String(20), nullable=False), Column("condition", Text, nullable=False),
    Column("verified", Boolean, nullable=False, server_default="false"),
    Column("evidence", Text, nullable=False, server_default=""),
    UniqueConstraint("version_id", "target_node_id", "kind"),
    CheckConstraint("kind IN ('DEPENDENCY','INTEGRATION','REPLACEMENT')", name="ck_asset_relation_kind"),
    CheckConstraint("length(btrim(condition))>0"),
    CheckConstraint("NOT verified OR length(btrim(evidence))>0"))
runs = table("dmp_solution_runs",
    ref("company_id", "companies"), ref("improvement_version_id", "company_improvement_versions"),
    ref("analysis_run_id", "analysis_runs"), ref("actor_id", "local_actors"),
    Column("input_digest", String(64), nullable=False), Column("rule_version", String(80), nullable=False),
    Column("input", JSONB, nullable=False), Column("data", JSONB, nullable=False),
    UniqueConstraint("improvement_version_id", "input_digest", "rule_version"))
composition_features = table("composition_asset_features",
    ref("version_id", "service_composition_versions"),
    ref("feature_revision_id", "dmp_feature_revisions"),
    ref("asset_version_id", "dmp_asset_versions", True),
    ref("system_version_id", "dmp_asset_versions", True),
    ref("module_version_id", "dmp_asset_versions", True),
    Column("role", Text, nullable=False),
    UniqueConstraint("version_id", "feature_revision_id"),
    CheckConstraint("length(btrim(role))>0"))
composition_contexts = table("composition_asset_contexts",
    ref("version_id", "service_composition_versions"),
    ref("recommendation_id", "dmp_solution_runs"),
    Column("alternative_id", String(100), nullable=False),
    Column("review_note", Text, nullable=False),
    Column("catalog_digest", String(64), nullable=False),
    UniqueConstraint("version_id"), CheckConstraint("length(btrim(review_note))>0"))
TABLES = (nodes, versions, relations, runs, composition_features, composition_contexts)
