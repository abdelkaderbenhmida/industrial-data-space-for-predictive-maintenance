import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPolicyManagerIntegration:
    def _make_valid_policy(self):
        return {
            "permissions": [
                {
                    "target": "asset-sensor-data",
                    "action": "read",
                    "constraints": {
                        "allowed_consumers": ["urn:factory:factory-a", "urn:factory:factory-b"],
                    },
                }
            ],
            "prohibitions": [],
            "obligations": [],
        }

    def test_create_policy_and_validate(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        policy = pm.create_policy(
            permissions=[{
                "target": "asset-1",
                "action": "read",
                "constraints": {},
            }]
        )
        assert policy.policy_id is not None
        result = pm.validate_policy(
            policy.to_dict(),
            consumer_id="urn:factory:factory-a",
            provider_id="urn:factory:factory-b",
        )
        assert result is True

    def test_create_dataset_policy_and_check_access(self):
        from policy_manager import PolicyManager, Permission
        pm = PolicyManager()
        policy = pm.create_dataset_policy(
            asset_id="sensor-data-001",
            provider_id="urn:factory:factory-a",
            allowed_consumers=["urn:factory:factory-b"],
            permission=Permission.READ,
        )
        assert pm.check_access("sensor-data-001", "urn:factory:factory-b", "read") is True
        assert pm.check_access("sensor-data-001", "urn:factory:factory-c", "read") is False

    def test_validate_empty_policy_returns_false(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        assert pm.validate_policy({}, "consumer", "provider") is False

    def test_validate_policy_no_permissions_returns_false(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        assert pm.validate_policy(
            {"permissions": [], "prohibitions": [], "obligations": []},
            "consumer", "provider",
        ) is False

    def test_validate_policy_restricted_consumer(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        policy = self._make_valid_policy()
        assert pm.validate_policy(policy, "urn:factory:factory-a", "provider") is True
        assert pm.validate_policy(policy, "urn:factory:factory-c", "provider") is False

    def test_add_obligation_to_policy(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        policy = pm.create_policy()
        obligation = pm.add_obligation(
            policy.policy_id,
            "notification",
            constraint={"channel": "email"},
        )
        assert "obligation_id" in obligation
        assert obligation["type"] == "notification"
        retrieved = pm.get_policy(policy.policy_id)
        assert len(retrieved.obligations) == 1

    def test_revoke_access(self):
        from policy_manager import PolicyManager, Permission
        pm = PolicyManager()
        pm.create_dataset_policy(
            asset_id="data-1",
            provider_id="provider-1",
            allowed_consumers=["consumer-a", "consumer-b"],
            permission=Permission.READ,
        )
        assert pm.check_access("data-1", "consumer-a") is True
        assert pm.check_access("data-1", "consumer-b") is True
        revoked = pm.revoke_access("data-1", "consumer-a")
        assert revoked is True
        remaining_rules = pm._access_rules.get("data-1", [])
        assert len(remaining_rules) == 0

    def test_revoke_nonexistent_consumer_returns_false(self):
        from policy_manager import PolicyManager, Permission
        pm = PolicyManager()
        pm.create_dataset_policy(
            asset_id="data-1",
            provider_id="provider-1",
            allowed_consumers=["consumer-a"],
            permission=Permission.READ,
        )
        revoked = pm.revoke_access("data-1", "consumer-x")
        assert revoked is False

    def test_export_policy(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        policy = pm.create_policy(
            permissions=[{"target": "a", "action": "read", "constraints": {}}]
        )
        exported = pm.export_policy(policy.policy_id)
        assert exported is not None
        assert exported["policy_id"] == policy.policy_id

    def test_export_nonexistent_policy_returns_none(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        assert pm.export_policy("nonexistent") is None

    def test_get_asset_policy(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        policy = pm.create_dataset_policy(
            asset_id="asset-x",
            provider_id="provider-1",
        )
        found = pm.get_asset_policy("asset-x")
        assert found is not None
        assert found.policy_id == policy.policy_id

    def test_get_asset_policy_returns_none_for_unknown(self):
        from policy_manager import PolicyManager
        pm = PolicyManager()
        assert pm.get_asset_policy("nonexistent-asset") is None


class TestExchangeLoggerIntegration:
    def test_log_exchange_stores_entry(self):
        from exchange_logger import ExchangeLogger
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        entry = logger.log_exchange(
            exchange_type="offer_published",
            provider_id="provider-1",
            asset_id="asset-1",
        )
        assert entry.exchange_type == "offer_published"
        assert entry.provider_id == "provider-1"
        assert len(logger._entries) == 1

    def test_log_exchange_with_all_fields(self):
        from exchange_logger import ExchangeLogger
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        entry = logger.log_exchange(
            exchange_type="negotiation_requested",
            consumer_id="consumer-1",
            provider_id="provider-1",
            asset_id="asset-1",
            negotiation_id="neg-123",
            details={"key": "value"},
        )
        assert entry.consumer_id == "consumer-1"
        assert entry.negotiation_id == "neg-123"
        assert entry.details == {"key": "value"}

    def test_get_entries_filters_by_type(self):
        from exchange_logger import ExchangeLogger
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        logger.log_exchange(exchange_type="offer_published")
        logger.log_exchange(exchange_type="negotiation_requested")
        logger.log_exchange(exchange_type="offer_published")
        offers = logger.get_entries(exchange_type="offer_published")
        assert len(offers) == 2
        negs = logger.get_entries(exchange_type="negotiation_requested")
        assert len(negs) == 1

    def test_get_entries_filters_by_consumer(self):
        from exchange_logger import ExchangeLogger
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        logger.log_exchange(exchange_type="a", consumer_id="c1")
        logger.log_exchange(exchange_type="a", consumer_id="c2")
        logger.log_exchange(exchange_type="a", consumer_id="c1")
        results = logger.get_entries(consumer_id="c1")
        assert len(results) == 2

    def test_log_exchange_to_file(self):
        from exchange_logger import ExchangeLogger
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ExchangeLogger(log_dir=tmpdir, log_to_file=True, log_to_console=False)
            logger.log_exchange(exchange_type="test_event", asset_id="a1")
            log_files = list(Path(tmpdir).glob("exchanges_*.jsonl"))
            assert len(log_files) == 1
            with open(log_files[0]) as f:
                lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 1
            import json
            entry = json.loads(lines[0])
            assert entry["exchange_type"] == "test_event"

    def test_load_from_file(self):
        from exchange_logger import ExchangeLogger
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ExchangeLogger(log_dir=tmpdir, log_to_file=True, log_to_console=False)
            logger.log_exchange(exchange_type="e1")
            logger.log_exchange(exchange_type="e2")
            loaded = logger.load_from_file()
            assert len(loaded) == 2

    def test_get_summary(self):
        from exchange_logger import ExchangeLogger
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        logger.log_exchange(exchange_type="offer")
        logger.log_exchange(exchange_type="offer")
        logger.log_exchange(exchange_type="accept")
        summary = logger.get_summary()
        assert summary["total_exchanges"] == 3
        assert summary["by_type"]["offer"] == 2
        assert summary["by_type"]["accept"] == 1

    def test_clear(self):
        from exchange_logger import ExchangeLogger
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        logger.log_exchange(exchange_type="test")
        assert len(logger._entries) == 1
        logger.clear()
        assert len(logger._entries) == 0

    def test_entry_to_json_roundtrip(self):
        from exchange_logger import ExchangeLogger, ExchangeLogEntry
        import json
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        entry = logger.log_exchange(
            exchange_type="test",
            consumer_id="c1",
            provider_id="p1",
        )
        json_str = entry.to_json()
        parsed = json.loads(json_str)
        assert parsed["exchange_type"] == "test"
        assert parsed["consumer_id"] == "c1"


class TestContractNegotiationIntegration:
    def _setup_manager(self):
        from policy_manager import PolicyManager
        from exchange_logger import ExchangeLogger
        from contract_negotiation import ContractNegotiationManager
        pm = PolicyManager()
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        return ContractNegotiationManager(policy_manager=pm, logger=logger)

    def _make_valid_policy(self):
        return {
            "permissions": [
                {
                    "target": "sensor-data-001",
                    "action": "read",
                    "constraints": {
                        "allowed_consumers": ["urn:factory:factory-a"],
                    },
                }
            ],
            "prohibitions": [],
            "obligations": [],
        }

    def test_publish_offer(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(
            asset_id="sensor-data-001",
            provider_id="urn:factory:factory-b",
            policy=self._make_valid_policy(),
        )
        assert offer.offer_id is not None
        assert offer.asset_id == "sensor-data-001"
        assert offer.provider_id == "urn:factory:factory-b"

    def test_discover_offers(self):
        manager = self._setup_manager()
        manager.publish_offer(asset_id="a1", provider_id="p1")
        manager.publish_offer(asset_id="a2", provider_id="p2")
        all_offers = manager.discover_offers()
        assert len(all_offers) == 2
        p1_offers = manager.discover_offers(provider_id="p1")
        assert len(p1_offers) == 1

    def test_request_negotiation(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(
            asset_id="sensor-data-001",
            provider_id="urn:factory:factory-b",
        )
        neg = manager.request_negotiation(
            consumer_id="urn:factory:factory-a",
            offer_id=offer.offer_id,
        )
        assert neg.negotiation_id is not None
        assert neg.state.value == "requested"
        assert neg.consumer_id == "urn:factory:factory-a"

    def test_request_negotiation_unknown_offer_raises(self):
        manager = self._setup_manager()
        with pytest.raises(ValueError, match="not found"):
            manager.request_negotiation(consumer_id="c1", offer_id="nonexistent")

    def test_full_negotiation_happy_path(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(
            asset_id="sensor-data-001",
            provider_id="urn:factory:factory-b",
            policy=self._make_valid_policy(),
        )
        neg = manager.request_negotiation(
            consumer_id="urn:factory:factory-a",
            offer_id=offer.offer_id,
        )
        assert neg.state.value == "requested"
        neg = manager.accept_offer(neg.negotiation_id, actor_id="urn:factory:factory-b")
        assert neg.state.value == "agreed"
        neg = manager.confirm(neg.negotiation_id, actor_id="urn:factory:factory-a")
        assert neg.state.value == "confirmed"
        neg = manager.finalize(neg.negotiation_id, actor_id="urn:factory:factory-b")
        assert neg.state.value == "finalized"

    def test_counter_offer_flow(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(
            asset_id="sensor-data-001",
            provider_id="urn:factory:factory-b",
        )
        neg = manager.request_negotiation(
            consumer_id="urn:factory:factory-a",
            offer_id=offer.offer_id,
        )
        new_policy = self._make_valid_policy()
        neg = manager.counter_offer(
            neg.negotiation_id,
            actor_id="urn:factory:factory-b",
            new_policy=new_policy,
        )
        assert neg.state.value == "offered"
        neg = manager.accept_offer(neg.negotiation_id, actor_id="urn:factory:factory-a")
        assert neg.state.value == "agreed"

    def test_decline_negotiation(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(asset_id="a1", provider_id="p1")
        neg = manager.request_negotiation(consumer_id="c1", offer_id=offer.offer_id)
        neg = manager.decline(neg.negotiation_id, actor_id="c1", reason="Too expensive")
        assert neg.state.value == "declined"

    def test_invalid_state_transition_raises(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(asset_id="a1", provider_id="p1")
        neg = manager.request_negotiation(consumer_id="c1", offer_id=offer.offer_id)
        neg = manager.decline(neg.negotiation_id, actor_id="c1")
        with pytest.raises(ValueError, match="Cannot confirm"):
            manager.confirm(neg.negotiation_id, actor_id="c1")

    def test_negotiation_history_tracked(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(
            asset_id="a1",
            provider_id="p1",
            policy=self._make_valid_policy(),
        )
        neg = manager.request_negotiation(consumer_id="urn:factory:factory-a", offer_id=offer.offer_id)
        neg = manager.accept_offer(neg.negotiation_id, actor_id="p1")
        neg = manager.confirm(neg.negotiation_id, actor_id="urn:factory:factory-a")
        neg = manager.finalize(neg.negotiation_id, actor_id="p1")
        assert len(neg.history) == 4
        assert neg.history[0]["state"] == "requested"
        assert neg.history[1]["state"] == "agreed"
        assert neg.history[2]["state"] == "confirmed"
        assert neg.history[3]["state"] == "finalized"

    def test_list_negotiations_filters(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(asset_id="a1", provider_id="p1")
        manager.request_negotiation(consumer_id="c1", offer_id=offer.offer_id)
        manager.request_negotiation(consumer_id="c2", offer_id=offer.offer_id)
        all_negs = manager.list_negotiations()
        assert len(all_negs) == 2
        c1_negs = manager.list_negotiations(consumer_id="c1")
        assert len(c1_negs) == 1

    def test_negotiation_with_invalid_policy_gets_declined(self):
        from policy_manager import PolicyManager
        from exchange_logger import ExchangeLogger
        from contract_negotiation import ContractNegotiationManager
        pm = PolicyManager()
        logger = ExchangeLogger(log_to_file=False, log_to_console=False)
        manager = ContractNegotiationManager(policy_manager=pm, logger=logger)
        offer = manager.publish_offer(
            asset_id="a1",
            provider_id="p1",
            policy={"permissions": [], "prohibitions": [], "obligations": []},
        )
        neg = manager.request_negotiation(consumer_id="c1", offer_id=offer.offer_id)
        neg = manager.accept_offer(neg.negotiation_id, actor_id="p1")
        assert neg.state.value == "declined"

    def test_logger_records_negotiation_events(self):
        manager = self._setup_manager()
        offer = manager.publish_offer(asset_id="a1", provider_id="p1")
        manager.request_negotiation(consumer_id="c1", offer_id=offer.offer_id)
        entries = manager.logger.get_entries()
        assert len(entries) == 2
        types = {e.exchange_type for e in entries}
        assert "offer_published" in types
        assert "negotiation_requested" in types
