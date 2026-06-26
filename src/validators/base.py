"""Base validator shared by every API-specific validator.

Framework rule: all validators live in ``src/validators/`` and extend
:class:`BaseValidator`. Tests must not inline ``assert "field" in payload``
checks — they delegate to a validator so schema rules are reusable and
centralised.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class ValidationError(AssertionError):
    """Raised (as an assertion failure) when a payload violates the schema."""


class BaseValidator:
    """Required-field presence + per-field type checking.

    Subclasses declare:
        required_fields : field names that must be present (and non-null)
        field_types     : optional mapping of field name -> expected type(s)
    """

    required_fields: Sequence[str] = ()
    field_types: Mapping[str, type | tuple[type, ...]] = {}

    def validate(self, payload: Mapping[str, Any]) -> None:
        """Validate a single object; raises :class:`ValidationError` on failure."""
        if not isinstance(payload, Mapping):
            raise ValidationError(f"Expected an object, got {type(payload).__name__}")

        self._check_required(payload)
        self._check_types(payload)
        self.validate_custom(payload)

    def validate_many(self, payloads: Sequence[Mapping[str, Any]]) -> None:
        """Validate every object in a list, annotating which index failed."""
        for index, item in enumerate(payloads):
            try:
                self.validate(item)
            except ValidationError as exc:
                raise ValidationError(f"Item at index {index} failed: {exc}") from exc

    def _check_required(self, payload: Mapping[str, Any]) -> None:
        missing = [f for f in self.required_fields if f not in payload]
        if missing:
            raise ValidationError(f"Missing required fields: {missing}")
        null_fields = [f for f in self.required_fields if payload.get(f) is None]
        if null_fields:
            raise ValidationError(f"Required fields are null: {null_fields}")

    def _check_types(self, payload: Mapping[str, Any]) -> None:
        for field, expected in self.field_types.items():
            if field in payload and payload[field] is not None:
                if not isinstance(payload[field], expected):
                    raise ValidationError(
                        f"Field '{field}' expected {expected}, "
                        f"got {type(payload[field]).__name__}"
                    )

    def validate_custom(self, payload: Mapping[str, Any]) -> None:
        """Hook for subclass-specific rules. Default: no-op."""
