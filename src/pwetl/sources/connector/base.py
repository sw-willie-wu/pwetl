"""Mixin for hash-based diff on streaming connectors."""

import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Sequence, Set


class HashDiffConnectorMixin:
    """Mixin that deduplicates records across polls using SHA-256 hashes.

    In streaming mode, each poll returns the full dataset. Without dedup,
    every record is re-emitted via self.next(), causing duplicate rows in
    the Pathway table. This mixin tracks hashes of previously emitted
    records and only emits new/changed ones.
    """

    _previous_hashes: Set[str]
    _diff_ignore_fields: frozenset

    def __init_hash_diff__(
        self,
        diff_ignore_fields: Optional[Sequence[str]] = None,
    ) -> None:
        """Initialize hash diff state. Call from subclass __init__.

        Args:
            diff_ignore_fields: Field names to exclude from hash computation.
                Useful when source data contains volatile fields (e.g.
                timestamps) that change on every poll but don't represent
                meaningful data changes.
        """
        self._previous_hashes = set()
        self._diff_ignore_fields = frozenset(diff_ignore_fields or ())

    def _record_hash(self, record: Dict[str, Any]) -> str:
        """Compute a deterministic SHA-256 hex digest for a record."""
        if self._diff_ignore_fields:
            record = {
                k: v for k, v in record.items()
                if k not in self._diff_ignore_fields
            }
        serialized = json.dumps(record, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _emit_diff(
        self,
        data: List[Dict[str, Any]],
        validate_fn: Optional[Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]],
    ) -> int:
        """Compare data against previous hashes, emit only new records.

        Args:
            data: Full list of records from current poll.
            validate_fn: Optional validation/transform function.

        Returns:
            Number of records emitted.
        """
        current_hashes: Set[str] = set()
        emitted = 0

        for record in data:
            h = self._record_hash(record)
            current_hashes.add(h)

            if h in self._previous_hashes:
                continue

            if validate_fn:
                validated = validate_fn(record)
                if validated is None:
                    continue
                self.next(**validated)  # type: ignore[attr-defined]
            else:
                self.next(**record)  # type: ignore[attr-defined]

            emitted += 1

        self._previous_hashes = current_hashes
        return emitted
