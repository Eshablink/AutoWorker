from packages.audit.evidence import EvidenceStore


def test_evidence_store_is_content_addressed(tmp_path):
    store = EvidenceStore(tmp_path)
    ref = store.write(task_id=__import__("uuid").uuid4(), kind="screenshot", content=b"frame")
    assert ref.hash_checksum
    assert store.read(ref) == b"frame"


def test_evidence_store_rejects_empty_content(tmp_path):
    store = EvidenceStore(tmp_path)
    try:
        store.write(task_id=__import__("uuid").uuid4(), kind="screenshot", content=b"")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("Expected empty evidence to fail")


def test_evidence_store_blocks_path_traversal(tmp_path):
    from uuid import uuid4
    from packages.domain.models import EvidenceReference

    store = EvidenceStore(tmp_path)
    reference = EvidenceReference(
        task_id=uuid4(),
        kind="screenshot",
        uri_or_path="../outside",
    )
    try:
        store.read(reference)
    except OSError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("Expected path traversal to be blocked")
