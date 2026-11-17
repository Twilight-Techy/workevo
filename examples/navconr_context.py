"""Opt-in real Navconr exact-evidence integration. Runs offline on fictional text."""

from __future__ import annotations

import tempfile
from pathlib import Path

from workevo import ContextRequirement, NavconrContext


def main() -> None:
    # Optional dependency belongs to the host application, not workevo core.
    from navconr import Index
    from navconr import Limits as NavigationLimits

    with tempfile.TemporaryDirectory(prefix="evolver-navconr-") as directory:
        root = Path(directory)
        sources = root / "sources"
        sources.mkdir()
        original = "# Record contract\nPreserve leading zeros in identifiers.\n"
        (sources / "contract.md").write_text(original)
        with Index(root / "index.sqlite") as index:
            data = index.ingest(sources)
            revision = data.revision
            session = index.session(revision, limits=NavigationLimits(source_bytes=16384, steps=32))
            position = original.encode().index(b"Preserve")
            span = next(
                span for span in session.data.spans.values() if span.start <= position < span.end
            )

            def read(pinned_revision, span_id):
                if pinned_revision != revision:
                    raise ValueError("revision changed")
                item = session.read([span_id])[0]
                if not item.evidence:
                    raise ValueError("exact evidence unavailable")
                return item.evidence.text

            context = NavconrContext(
                read, index_revision=revision, spans={"record-contract": span.id}
            )
            requirement = ContextRequirement(
                key="record-contract", revision=revision, max_bytes=4096
            )
            result = context.resolve(requirement)
            assert result == original.encode()[span.start : span.end].decode()
            assert "Preserve leading zeros" in result
            print(
                {
                    "index_revision": revision,
                    "context_hash": context.identity,
                    "exact_bytes": len(result.encode()),
                }
            )


if __name__ == "__main__":
    main()
