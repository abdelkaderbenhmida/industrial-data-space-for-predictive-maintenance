import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ExchangeLogEntry:
    def __init__(
        self,
        exchange_type: str,
        consumer_id: str = "",
        provider_id: str = "",
        asset_id: str = "",
        negotiation_id: str = "",
        details: dict[str, Any] | None = None,
    ):
        self.log_id = str(uuid.uuid4())
        self.exchange_type = exchange_type
        self.consumer_id = consumer_id
        self.provider_id = provider_id
        self.asset_id = asset_id
        self.negotiation_id = negotiation_id
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_id": self.log_id,
            "exchange_type": self.exchange_type,
            "consumer_id": self.consumer_id,
            "provider_id": self.provider_id,
            "asset_id": self.asset_id,
            "negotiation_id": self.negotiation_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class ExchangeLogger:
    def __init__(
        self,
        log_dir: str | Path | None = None,
        log_to_file: bool = True,
        log_to_console: bool = True,
    ):
        self.log_dir = Path(log_dir) if log_dir else Path("exchange_logs")
        self.log_to_file = log_to_file
        self.log_to_console = log_to_console
        self._entries: list[ExchangeLogEntry] = []

        if self.log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_exchange(
        self,
        exchange_type: str,
        consumer_id: str = "",
        provider_id: str = "",
        asset_id: str = "",
        negotiation_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> ExchangeLogEntry:
        entry = ExchangeLogEntry(
            exchange_type=exchange_type,
            consumer_id=consumer_id,
            provider_id=provider_id,
            asset_id=asset_id,
            negotiation_id=negotiation_id,
            details=details,
        )
        self._entries.append(entry)

        if self.log_to_console:
            print(
                f"[{entry.timestamp.isoformat()}] "
                f"{entry.exchange_type} | "
                f"consumer={entry.consumer_id} "
                f"provider={entry.provider_id} "
                f"asset={entry.asset_id}"
            )

        if self.log_to_file:
            self._write_entry(entry)

        return entry

    def _write_entry(self, entry: ExchangeLogEntry):
        date_str = entry.timestamp.strftime("%Y-%m-%d")
        log_file = self.log_dir / f"exchanges_{date_str}.jsonl"
        with open(log_file, "a") as f:
            f.write(entry.to_json() + "\n")

    def get_entries(
        self,
        exchange_type: str | None = None,
        consumer_id: str | None = None,
        provider_id: str | None = None,
        asset_id: str | None = None,
        negotiation_id: str | None = None,
        since: datetime | None = None,
    ) -> list[ExchangeLogEntry]:
        results = self._entries
        if exchange_type:
            results = [e for e in results if e.exchange_type == exchange_type]
        if consumer_id:
            results = [e for e in results if e.consumer_id == consumer_id]
        if provider_id:
            results = [e for e in results if e.provider_id == provider_id]
        if asset_id:
            results = [e for e in results if e.asset_id == asset_id]
        if negotiation_id:
            results = [e for e in results if e.negotiation_id == negotiation_id]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results

    def load_from_file(
        self,
        date_str: str | None = None,
    ) -> list[ExchangeLogEntry]:
        entries = []
        if date_str:
            files = [self.log_dir / f"exchanges_{date_str}.jsonl"]
        else:
            files = sorted(self.log_dir.glob("exchanges_*.jsonl"))

        for log_file in files:
            if not log_file.exists():
                continue
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    entry = ExchangeLogEntry(
                        exchange_type=data["exchange_type"],
                        consumer_id=data.get("consumer_id", ""),
                        provider_id=data.get("provider_id", ""),
                        asset_id=data.get("asset_id", ""),
                        negotiation_id=data.get("negotiation_id", ""),
                        details=data.get("details"),
                    )
                    entry.log_id = data["log_id"]
                    entry.timestamp = datetime.fromisoformat(data["timestamp"])
                    entries.append(entry)
        return entries

    def get_summary(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for entry in self._entries:
            type_counts[entry.exchange_type] = (
                type_counts.get(entry.exchange_type, 0) + 1
            )
        return {
            "total_exchanges": len(self._entries),
            "by_type": type_counts,
        }

    def clear(self):
        self._entries.clear()
