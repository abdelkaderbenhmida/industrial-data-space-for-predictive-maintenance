import time
from enum import Enum


class NegotiationState(str, Enum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"
    ERROR = "ERROR"


class ContractNegotiation:
    def __init__(
        self,
        negotiation_id: str,
        initiator_connector_id: str,
        counter_party_connector_id: str,
        counter_party_address: str,
        asset_id: str,
        policy: dict | None = None,
    ):
        self.negotiation_id = negotiation_id
        self.initiator_connector_id = initiator_connector_id
        self.counter_party_connector_id = counter_party_connector_id
        self.counter_party_address = counter_party_address
        self.asset_id = asset_id
        self.policy = policy or {}
        self.state = NegotiationState.REQUESTED
        self.created_at = time.time()
        self.updated_at = time.time()

    def confirm(self):
        self.state = NegotiationState.CONFIRMED
        self.updated_at = time.time()

    def decline(self):
        self.state = NegotiationState.DECLINED
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "negotiationId": self.negotiation_id,
            "initiatorConnectorId": self.initiator_connector_id,
            "counterPartyConnectorId": self.counter_party_connector_id,
            "counterPartyAddress": self.counter_party_address,
            "assetId": self.asset_id,
            "policy": self.policy,
            "state": self.state.value,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class ContractNegotiationManager:
    def __init__(self):
        self.negotiations: dict[str, ContractNegotiation] = {}

    def start_negotiation(
        self,
        initiator_connector_id: str,
        counter_party_connector_id: str,
        counter_party_address: str,
        asset_id: str,
        policy: dict | None = None,
    ) -> ContractNegotiation:
        import uuid
        negotiation_id = str(uuid.uuid4())
        negotiation = ContractNegotiation(
            negotiation_id=negotiation_id,
            initiator_connector_id=initiator_connector_id,
            counter_party_connector_id=counter_party_connector_id,
            counter_party_address=counter_party_address,
            asset_id=asset_id,
            policy=policy,
        )
        self.negotiations[negotiation_id] = negotiation
        return negotiation

    def get_negotiation(self, negotiation_id: str) -> ContractNegotiation | None:
        return self.negotiations.get(negotiation_id)

    def confirm_negotiation(self, negotiation_id: str) -> ContractNegotiation | None:
        negotiation = self.negotiations.get(negotiation_id)
        if negotiation:
            negotiation.confirm()
        return negotiation

    def decline_negotiation(self, negotiation_id: str) -> ContractNegotiation | None:
        negotiation = self.negotiations.get(negotiation_id)
        if negotiation:
            negotiation.decline()
        return negotiation

    def list_negotiations(self, state: NegotiationState | None = None) -> list[dict]:
        negotiations = list(self.negotiations.values())
        if state:
            negotiations = [n for n in negotiations if n.state == state]
        return [n.to_dict() for n in negotiations]
