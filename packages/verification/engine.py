"""Post-execution verification contracts."""

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from packages.domain.models import TaskAction, VerificationResult


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    check: Callable[[TaskAction], tuple[bool, dict[str, Any]]]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Verification check name cannot be empty.")
        if not callable(self.check):
            raise TypeError("Verification check callback must be callable.")


class VerificationEngine:
    def verify(
        self,
        task_id: UUID,
        action: TaskAction,
        *,
        checks: list[VerificationCheck],
    ) -> VerificationResult:
        if not checks:
            raise ValueError("At least one verification check is required.")
        names = [item.name.strip() for item in checks]
        if len(names) != len(set(names)):
            raise ValueError("Verification check names must be unique.")

        results: list[dict[str, Any]] = []
        all_success = True
        for item in checks:
            success, actual = item.check(action)
            if not isinstance(success, bool):
                raise TypeError(f"Verification check {item.name!r} must return a boolean success flag.")
            results.append({"check": item.name.strip(), "success": success, "actual": actual})
            all_success = all_success and success

        confidence = 1.0 if all_success else sum(
            1 for result in results if result["success"]
        ) / len(results)

        return VerificationResult(
            task_id=task_id,
            action_id=action.action_id,
            success=all_success,
            verification_type="COMPOSITE",
            query_or_check="; ".join(names),
            expected_state={"checks": names},
            actual_state={"results": results},
            confidence_score=confidence,
        )
