"""Portable verified skill bundles; import does not promote an artifact."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import model_validator

from .contracts import Record, Skill, StudyConfig, Summary, digest, implementation_identity
from .errors import Incompatible
from .evaluation import Evaluator
from .runner import Registry
from .store import Store


class Bundle(Record):
    skill: Skill
    revision: str
    config: StudyConfig
    validation: Summary
    final_test: Summary | None = None
    limitations: tuple[str, ...] = (
        "Validation is selection evidence, not an untouched test.",
        "Imported evidence is provenance, not a trusted local measurement.",
    )

    @model_validator(mode="after")
    def integrity(self) -> Bundle:
        if self.skill.revision != self.revision or self.skill.family != self.config.family:
            raise ValueError("skill identity mismatch")
        if (
            self.validation.revision != self.revision
            or self.validation.identity != self.config.identity
            or self.validation.split != "validation"
            or not self.validation.eligible
        ):
            raise ValueError("invalid validation evidence")
        if self.final_test and (
            self.final_test.revision != self.revision
            or self.final_test.identity != self.config.identity
            or self.final_test.split != "test"
            or not self.final_test.complete
        ):
            raise ValueError("invalid final-test evidence")
        return self


def atomic_write(path: Path, text: str) -> None:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def export_skill(store: Store, study: str, evaluator: Evaluator, path: Path) -> Bundle:
    config, state, _ = store.study(study)
    if not state["frozen"] or state["champion"] is None:
        raise Incompatible("export requires a frozen champion")
    revision = state["champion"]
    validation = evaluator.summarize(store, study, revision, "validation")
    row = store.db.execute("SELECT body FROM final_reports WHERE study=?", (study,)).fetchone()
    test = Summary.model_validate(json.loads(row[0])["summary"]) if row else None
    bundle = Bundle(
        skill=store.skill(revision),
        revision=revision,
        config=config,
        validation=validation,
        final_test=test,
    )
    atomic_write(path, bundle.model_dump_json(indent=2) + "\n")
    markdown = f"# {bundle.skill.skill_id}\n\n{bundle.skill.instructions}\n\n" + (
        f"Family: {bundle.skill.family}\n\nRevision: `{revision}`\n\n"
        f"Validation correctness: {validation.quality:.1%} on {len(validation.evaluations)} recorded trials.\n\n"
        "This document accompanies skill.json; the JSON bundle defines executable behavior, dependencies, context requirements and evidence.\n"
    )
    atomic_write(path.with_name("SKILL.md"), markdown)
    store.event(study, "exported", {"revision": revision, "bundle_hash": digest(bundle)})
    return bundle


def import_skill(
    store: Store, path: Path, registry: Registry, *, context_hash: str | None = None
) -> Bundle:
    if path.stat().st_size > 4 * 1024 * 1024:
        raise Incompatible("bundle exceeds import size limit")
    bundle = Bundle.model_validate_json(path.read_bytes())
    registry.validate(bundle.skill)
    if bundle.config.registry_hash != registry.identity:
        raise Incompatible("operator environment differs from bundle")
    if context_hash is not None and context_hash != bundle.config.context_hash:
        raise Incompatible("context environment differs from bundle")
    with store.transaction():
        store.put("skill", bundle.skill)
        store.put("bundle", bundle)
    return bundle


def lookup(
    store: Store, family: str, registry: Registry, *, context_hash: str, min_quality: float = 0
) -> list[dict[str, Any]]:
    results = []
    for row in store.db.execute("SELECT hash FROM artifacts WHERE kind='bundle'"):
        bundle = Bundle.model_validate(store.get(row[0], "bundle"))
        if (
            bundle.config.implementation_hash == implementation_identity()
            and bundle.skill.family == family
            and bundle.config.registry_hash == registry.identity
            and bundle.config.context_hash == context_hash
            and bundle.validation.quality >= min_quality
        ):
            results.append(
                {
                    "revision": bundle.revision,
                    "skill_id": bundle.skill.skill_id,
                    "quality": bundle.validation.quality,
                    "evidence_trust": "imported_provenance",
                }
            )
    return sorted(results, key=lambda r: (-float(r["quality"]), str(r["revision"])))
