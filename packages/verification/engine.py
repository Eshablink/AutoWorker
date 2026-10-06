"""Post-execution verification contracts."""

from dataclasses import dataclass
from typing import Any, Callable

from packages.domain.models import TaskAction, VerificationResult


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    check: Callable[[TaskAction], tuple[bool, dict[str, Any]]]


class VerificationEngine:
    def verify(
        self,
        task_id,
        action: TaskAction,
        *,
        checks: list[VerificationCheck],
    ) -> VerificationResult:
        if not checks:
            raise ValueError("At least one verification check is required.")

        results: list[dict[str, Any]] = []
        all_success = True
        for item in checks:
            success, actual = item.check(action)
            results.append({"check": item.name, "success": success, "actual": actual})
            all_success = all_success and success

        confidence = 1.0 if all_success else sum(
            1 for result in results if result["success"]
        ) / len(results)

        return VerificationResult(
            task_id=task_id,
            action_id=action.action_id,
            success=all_success,
            verification_type="COMPOSITE",
            query_or_check="; ".join(item.name for item in checks),
            expected_state={"checks": [item.name for item in checks]},
            actual_state={"results": results},
            confidence_score=confidence,
        )
