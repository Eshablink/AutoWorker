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
