"""Content-addressed evidence storage for screenshots, DOM snapshots, and reports."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from packages.domain.models import EvidenceReference


@dataclass(frozen=True)
class EvidenceArtifact:
    reference: EvidenceReference
    content: bytes


class EvidenceStore:
    """Stores immutable evidence under content-addressed paths."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        *,
        task_id: UUID,
        kind: str,
        content: bytes,
        action_id: UUID | None = None,
        extension: str = "bin",
    ) -> EvidenceReference:
        if not content:
            raise ValueError("Evidence content cannot be empty.")
        digest = sha256(content).hexdigest()
        safe_kind = kind.strip().replace("/", "_").replace(" ", "_")
        if not safe_kind:
            raise ValueError("Evidence kind cannot be empty.")
        relative = Path(str(task_id)) / f"{digest}.{extension.lstrip('.')}"
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            existing = destination.read_bytes()
            if sha256(existing).hexdigest() != digest:
                raise IOError("Existing evidence content does not match its content hash.")
        else:
            destination.write_bytes(content)
        return EvidenceReference(
            task_id=task_id,
            action_id=action_id,
            kind=safe_kind,
            uri_or_path=str(relative),
            hash_checksum=digest,
            metadata={"size_bytes": len(content)},
        )

    def read(self, reference: EvidenceReference) -> bytes:
        path = (self.root / reference.uri_or_path).resolve()
        root = self.root.resolve()
        if root not in path.parents:
            raise IOError("Evidence reference escapes the evidence store root.")
        if not path.is_file():
            raise FileNotFoundError(reference.uri_or_path)
        content = path.read_bytes()
        if reference.hash_checksum and sha256(content).hexdigest() != reference.hash_checksum:
            raise IOError("Evidence checksum validation failed.")
        return content
