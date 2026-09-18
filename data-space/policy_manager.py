import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    USE = "use"
    DISTRIBUTED_USE = "distributed_use"


class Constraint(str, Enum):
    TIME_WINDOW = "time_window"
    MAX_RECORDS = "max_records"
    ALLOWED_PURPOSE = "allowed_purpose"
    GEOGRAPHIC = "geographic"
    RATE_LIMIT = "rate_limit"


class Policy:
    def __init__(
        self,
        permissions: list[dict[str, Any]] | None = None,
        prohibitions: list[dict[str, Any]] | None = None,
        obligations: list[dict[str, Any]] | None = None,
        policy_id: str | None = None,
    ):
        self.policy_id = policy_id or str(uuid.uuid4())
        self.permissions = permissions or []
        self.prohibitions = prohibitions or []
        self.obligations = obligations or []
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "permissions": self.permissions,
            "prohibitions": self.prohibitions,
            "obligations": self.obligations,
            "created_at": self.created_at.isoformat(),
        }


class PolicyManager:
    def __init__(self):
        self._policies: dict[str, Policy] = {}
        self._access_rules: dict[str, list[dict[str, Any]]] = {}

    def create_policy(
        self,
        permissions: list[dict[str, Any]] | None = None,
        prohibitions: list[dict[str, Any]] | None = None,
        obligations: list[dict[str, Any]] | None = None,
    ) -> Policy:
        policy = Policy(
            permissions=permissions,
            prohibitions=prohibitions,
            obligations=obligations,
        )
        self._policies[policy.policy_id] = policy
        return policy

    def create_dataset_policy(
        self,
        asset_id: str,
        provider_id: str,
        allowed_consumers: list[str] | None = None,
        permission: Permission = Permission.READ,
        constraints: dict[str, Any] | None = None,
    ) -> Policy:
        constraints = constraints or {}
        permission_entry = {
            "target": asset_id,
            "action": permission.value,
            "constraints": constraints,
        }
        if allowed_consumers:
            permission_entry["constraints"]["allowed_consumers"] = allowed_consumers

        policy = Policy(permissions=[permission_entry])
        self._policies[policy.policy_id] = policy

        self._access_rules[asset_id] = [{
            "provider_id": provider_id,
            "permission": permission.value,
            "constraints": constraints,
        }]
        return policy

    def validate_policy(
        self,
        policy_dict: dict[str, Any],
        consumer_id: str,
        provider_id: str,
    ) -> bool:
        if not policy_dict:
            return False

        permissions = policy_dict.get("permissions", [])
        if not permissions:
            return False

        for perm in permissions:
            constraints = perm.get("constraints", {})

            allowed_consumers = constraints.get("allowed_consumers", [])
            if allowed_consumers and consumer_id not in allowed_consumers:
                return False

            time_window = constraints.get("time_window")
            if time_window:
                now = datetime.now(timezone.utc)
                start = datetime.fromisoformat(time_window["start"])
                end = datetime.fromisoformat(time_window["end"])
                if not (start <= now <= end):
                    return False

            allowed_purposes = constraints.get("allowed_purpose", [])
            if allowed_purposes:
                consumer_purpose = constraints.get("consumer_purpose", "")
                if consumer_purpose not in allowed_purposes:
                    return False

        prohibitions = policy_dict.get("prohibitions", [])
        for prohibition in prohibitions:
            if prohibition.get("target") == perm.get("target"):
                return False

        return True

    def check_access(
        self,
        asset_id: str,
        consumer_id: str,
        action: str = "read",
    ) -> bool:
        rules = self._access_rules.get(asset_id, [])
        if not rules:
            return True

        for rule in rules:
            if rule["permission"] == action:
                constraints = rule["constraints"]
                allowed_consumers = constraints.get("allowed_consumers", [])
                if allowed_consumers and consumer_id not in allowed_consumers:
                    continue
                return True
        return False

    def add_obligation(
        self,
        policy_id: str,
        obligation_type: str,
        constraint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        policy = self._policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        obligation = {
            "obligation_id": str(uuid.uuid4()),
            "type": obligation_type,
            "constraint": constraint or {},
        }
        policy.obligations.append(obligation)
        return obligation

    def get_policy(self, policy_id: str) -> Policy | None:
        return self._policies.get(policy_id)

    def get_asset_policy(self, asset_id: str) -> Policy | None:
        for policy in self._policies.values():
            for perm in policy.permissions:
                if perm.get("target") == asset_id:
                    return policy
        return None

    def revoke_access(
        self,
        asset_id: str,
        consumer_id: str,
    ) -> bool:
        rules = self._access_rules.get(asset_id, [])
        original_len = len(rules)
        self._access_rules[asset_id] = [
            r for r in rules
            if consumer_id not in r["constraints"].get("allowed_consumers", [])
        ]
        return len(self._access_rules[asset_id]) < original_len

    def export_policy(self, policy_id: str) -> dict[str, Any] | None:
        policy = self._policies.get(policy_id)
        if not policy:
            return None
        return policy.to_dict()
