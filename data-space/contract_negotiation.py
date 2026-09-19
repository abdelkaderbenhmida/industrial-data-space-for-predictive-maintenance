import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from exchange_logger import ExchangeLogger
from policy_manager import PolicyManager


class NegotiationState(str, Enum):
    REQUESTED = "requested"
    OFFERED = "offered"
    AGREED = "agreed"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    DECLINED = "declined"
    ERROR = "error"


class ContractOffer:
    def __init__(
        self,
        asset_id: str,
        provider_id: str,
        policy: dict[str, Any] | None = None,
        offer_id: str | None = None,
    ):
        self.offer_id = offer_id or str(uuid.uuid4())
        self.asset_id = asset_id
        self.provider_id = provider_id
        self.policy = policy or {}
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "asset_id": self.asset_id,
            "provider_id": self.provider_id,
            "policy": self.policy,
            "created_at": self.created_at.isoformat(),
        }


class ContractNegotiation:
    def __init__(
        self,
        negotiation_id: str | None = None,
        consumer_id: str | None = None,
        provider_id: str | None = None,
        offer: ContractOffer | None = None,
    ):
        self.negotiation_id = negotiation_id or str(uuid.uuid4())
        self.consumer_id = consumer_id or ""
        self.provider_id = provider_id or ""
        self.offer = offer
        self.state = NegotiationState.REQUESTED
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.history: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "negotiation_id": self.negotiation_id,
            "consumer_id": self.consumer_id,
            "provider_id": self.provider_id,
            "offer": self.offer.to_dict() if self.offer else None,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ContractNegotiationManager:
    def __init__(
        self,
        policy_manager: PolicyManager | None = None,
        logger: ExchangeLogger | None = None,
    ):
        self.policy_manager = policy_manager or PolicyManager()
        self.logger = logger or ExchangeLogger()
        self._negotiations: dict[str, ContractNegotiation] = {}
        self._offers: dict[str, ContractOffer] = {}

    def publish_offer(
        self,
        asset_id: str,
        provider_id: str,
        policy: dict[str, Any] | None = None,
    ) -> ContractOffer:
        offer = ContractOffer(asset_id=asset_id, provider_id=provider_id, policy=policy)
        self._offers[offer.offer_id] = offer
        self.logger.log_exchange(
            exchange_type="offer_published",
            provider_id=provider_id,
            asset_id=asset_id,
            details=offer.to_dict(),
        )
        return offer

    def discover_offers(self, provider_id: str | None = None) -> list[ContractOffer]:
        offers = list(self._offers.values())
        if provider_id:
            offers = [o for o in offers if o.provider_id == provider_id]
        return offers

    def request_negotiation(
        self,
        consumer_id: str,
        offer_id: str,
    ) -> ContractNegotiation:
        offer = self._offers.get(offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")

        negotiation = ContractNegotiation(
            consumer_id=consumer_id,
            provider_id=offer.provider_id,
            offer=offer,
        )
        negotiation.state = NegotiationState.REQUESTED
        self._negotiations[negotiation.negotiation_id] = negotiation

        negotiation.history.append({
            "state": NegotiationState.REQUESTED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": consumer_id,
        })

        self.logger.log_exchange(
            exchange_type="negotiation_requested",
            consumer_id=consumer_id,
            provider_id=offer.provider_id,
            asset_id=offer.asset_id,
            negotiation_id=negotiation.negotiation_id,
            details=negotiation.to_dict(),
        )
        return negotiation

    def counter_offer(
        self,
        negotiation_id: str,
        actor_id: str,
        new_policy: dict[str, Any],
    ) -> ContractNegotiation:
        negotiation = self._get_negotiation(negotiation_id)
        if negotiation.state not in (
            NegotiationState.REQUESTED,
            NegotiationState.OFFERED,
        ):
            raise ValueError(
                f"Cannot counter offer in state {negotiation.state.value}"
            )

        negotiation.offer = ContractOffer(
            asset_id=negotiation.offer.asset_id,
            provider_id=negotiation.offer.provider_id,
            policy=new_policy,
        )
        negotiation.state = NegotiationState.OFFERED
        negotiation.updated_at = datetime.now(timezone.utc)

        negotiation.history.append({
            "state": NegotiationState.OFFERED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor_id,
        })

        self.logger.log_exchange(
            exchange_type="counter_offer",
            consumer_id=negotiation.consumer_id,
            provider_id=negotiation.provider_id,
            asset_id=negotiation.offer.asset_id,
            negotiation_id=negotiation_id,
            details=negotiation.to_dict(),
        )
        return negotiation

    def accept_offer(
        self,
        negotiation_id: str,
        actor_id: str,
    ) -> ContractNegotiation:
        negotiation = self._get_negotiation(negotiation_id)
        if negotiation.state not in (
            NegotiationState.REQUESTED,
            NegotiationState.OFFERED,
        ):
            raise ValueError(
                f"Cannot accept in state {negotiation.state.value}"
            )

        policy_valid = self.policy_manager.validate_policy(
            negotiation.offer.policy,
            negotiation.consumer_id,
            negotiation.provider_id,
        )
        if not policy_valid:
            negotiation.state = NegotiationState.DECLINED
            negotiation.updated_at = datetime.now(timezone.utc)
            negotiation.history.append({
                "state": NegotiationState.DECLINED.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": "system",
                "reason": "policy validation failed",
            })
            self.logger.log_exchange(
                exchange_type="negotiation_declined",
                consumer_id=negotiation.consumer_id,
                provider_id=negotiation.provider_id,
                asset_id=negotiation.offer.asset_id,
                negotiation_id=negotiation_id,
                details={"reason": "policy validation failed"},
            )
            return negotiation

        negotiation.state = NegotiationState.AGREED
        negotiation.updated_at = datetime.now(timezone.utc)
        negotiation.history.append({
            "state": NegotiationState.AGREED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor_id,
        })

        self.logger.log_exchange(
            exchange_type="negotiation_agreed",
            consumer_id=negotiation.consumer_id,
            provider_id=negotiation.provider_id,
            asset_id=negotiation.offer.asset_id,
            negotiation_id=negotiation_id,
            details=negotiation.to_dict(),
        )
        return negotiation

    def confirm(
        self,
        negotiation_id: str,
        actor_id: str,
    ) -> ContractNegotiation:
        negotiation = self._get_negotiation(negotiation_id)
        if negotiation.state != NegotiationState.AGREED:
            raise ValueError(
                f"Cannot confirm in state {negotiation.state.value}"
            )

        negotiation.state = NegotiationState.CONFIRMED
        negotiation.updated_at = datetime.now(timezone.utc)
        negotiation.history.append({
            "state": NegotiationState.CONFIRMED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor_id,
        })

        self.logger.log_exchange(
            exchange_type="negotiation_confirmed",
            consumer_id=negotiation.consumer_id,
            provider_id=negotiation.provider_id,
            asset_id=negotiation.offer.asset_id,
            negotiation_id=negotiation_id,
            details=negotiation.to_dict(),
        )
        return negotiation

    def finalize(
        self,
        negotiation_id: str,
        actor_id: str,
    ) -> ContractNegotiation:
        negotiation = self._get_negotiation(negotiation_id)
        if negotiation.state != NegotiationState.CONFIRMED:
            raise ValueError(
                f"Cannot finalize in state {negotiation.state.value}"
            )

        negotiation.state = NegotiationState.FINALIZED
        negotiation.updated_at = datetime.now(timezone.utc)
        negotiation.history.append({
            "state": NegotiationState.FINALIZED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor_id,
        })

        self.logger.log_exchange(
            exchange_type="negotiation_finalized",
            consumer_id=negotiation.consumer_id,
            provider_id=negotiation.provider_id,
            asset_id=negotiation.offer.asset_id,
            negotiation_id=negotiation_id,
            details=negotiation.to_dict(),
        )
        return negotiation

    def decline(
        self,
        negotiation_id: str,
        actor_id: str,
        reason: str = "",
    ) -> ContractNegotiation:
        negotiation = self._get_negotiation(negotiation_id)
        negotiation.state = NegotiationState.DECLINED
        negotiation.updated_at = datetime.now(timezone.utc)
        negotiation.history.append({
            "state": NegotiationState.DECLINED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor_id,
            "reason": reason,
        })

        self.logger.log_exchange(
            exchange_type="negotiation_declined",
            consumer_id=negotiation.consumer_id,
            provider_id=negotiation.provider_id,
            asset_id=negotiation.offer.asset_id,
            negotiation_id=negotiation_id,
            details={"reason": reason},
        )
        return negotiation

    def get_negotiation(
        self,
        negotiation_id: str,
    ) -> ContractNegotiation | None:
        return self._negotiations.get(negotiation_id)

    def list_negotiations(
        self,
        consumer_id: str | None = None,
        provider_id: str | None = None,
        state: NegotiationState | None = None,
    ) -> list[ContractNegotiation]:
        results = list(self._negotiations.values())
        if consumer_id:
            results = [n for n in results if n.consumer_id == consumer_id]
        if provider_id:
            results = [n for n in results if n.provider_id == provider_id]
        if state:
            results = [n for n in results if n.state == state]
        return results

    def _get_negotiation(self, negotiation_id: str) -> ContractNegotiation:
        negotiation = self._negotiations.get(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found")
        return negotiation
