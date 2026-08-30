"""C4 — finite marking lattices and monotonic information-flow joins."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .errors import AuthorizationError, MarkingError


@dataclass(frozen=True, slots=True, init=False)
class MarkingSchemeDefinition:
    """A validated finite lattice.

    ``levels`` describes a total order from least to most restrictive.  For a
    partial order, pass ``labels`` and explicit ``relations`` pairs in the form
    ``(lower, upper)``.  Every pair must have one join and one meet.
    """

    scheme_id: str
    labels: tuple[str, ...]
    relations: frozenset[tuple[str, str]]
    bottom: str
    top: str
    _closure: Mapping[str, frozenset[str]]

    def __init__(
        self,
        scheme_id: str,
        levels: Sequence[str] | None = None,
        *,
        labels: Iterable[str] | None = None,
        relations: Iterable[tuple[str, str]] | None = None,
    ) -> None:
        if not isinstance(scheme_id, str) or not scheme_id.strip():
            raise MarkingError("scheme_id must be a non-empty string")
        if levels is not None and labels is not None:
            raise MarkingError("provide levels or labels, not both")
        ordered = tuple(levels or ())
        members = tuple(labels if labels is not None else ordered)
        if not members:
            raise MarkingError("a marking scheme requires at least one label")
        if any(not isinstance(label, str) or not label for label in members):
            raise MarkingError("marking labels must be non-empty strings")
        if len(set(members)) != len(members):
            raise MarkingError("marking labels must be unique")

        direct: set[tuple[str, str]] = {(label, label) for label in members}
        if levels is not None:
            direct.update(zip(ordered, ordered[1:]))
        for relation in relations or ():
            if (
                not isinstance(relation, Sequence)
                or isinstance(relation, (str, bytes))
                or len(relation) != 2
            ):
                raise MarkingError("relations must be (lower, upper) tuples")
            lower, upper = relation
            if lower not in members or upper not in members:
                raise MarkingError(f"relation references an unknown label: {relation!r}")
            direct.add((lower, upper))

        closure: dict[str, set[str]] = {label: {label} for label in members}
        for lower, upper in direct:
            closure[lower].add(upper)
        changed = True
        while changed:
            changed = False
            for lower in members:
                expanded = set(closure[lower])
                for intermediate in tuple(closure[lower]):
                    expanded.update(closure[intermediate])
                if expanded != closure[lower]:
                    closure[lower] = expanded
                    changed = True

        for left in members:
            for right in members:
                if left != right and right in closure[left] and left in closure[right]:
                    raise MarkingError("marking order must be antisymmetric")

        bottoms = [label for label in members if all(other in closure[label] for other in members)]
        tops = [label for label in members if all(label in closure[other] for other in members)]
        if len(bottoms) != 1 or len(tops) != 1:
            raise MarkingError("marking definition must have unique bottom and top labels")

        def minimal(candidates: set[str]) -> set[str]:
            return {
                candidate
                for candidate in candidates
                if not any(
                    other != candidate and candidate in closure[other]
                    for other in candidates
                )
            }

        def maximal(candidates: set[str]) -> set[str]:
            return {
                candidate
                for candidate in candidates
                if not any(
                    other != candidate and other in closure[candidate]
                    for other in candidates
                )
            }

        for left in members:
            for right in members:
                upper_bounds = closure[left] & closure[right]
                lower_bounds = {
                    label
                    for label in members
                    if left in closure[label] and right in closure[label]
                }
                if len(minimal(upper_bounds)) != 1 or len(maximal(lower_bounds)) != 1:
                    raise MarkingError(
                        f"labels {left!r} and {right!r} do not form a lattice pair"
                    )

        object.__setattr__(self, "scheme_id", scheme_id)
        object.__setattr__(self, "labels", members)
        object.__setattr__(self, "relations", frozenset(direct))
        object.__setattr__(self, "bottom", bottoms[0])
        object.__setattr__(self, "top", tops[0])
        object.__setattr__(
            self,
            "_closure",
            MappingProxyType({key: frozenset(value) for key, value in closure.items()}),
        )

    @classmethod
    def from_dict(cls, definition: Mapping[str, Any]) -> "MarkingSchemeDefinition":
        scheme_id = definition.get("schemeId", definition.get("scheme_id"))
        if "orderedLabels" in definition:
            return cls(str(scheme_id), levels=tuple(definition["orderedLabels"]))
        raw_relations = definition.get("relations", ())
        relations: list[tuple[str, str]] = []
        for relation in raw_relations:
            if isinstance(relation, Mapping):
                relations.append((str(relation["lower"]), str(relation["upper"])))
            else:
                relations.append(tuple(relation))  # type: ignore[arg-type]
        return cls(
            str(scheme_id),
            labels=tuple(definition["labels"]),
            relations=relations,
        )

    def _require_label(self, label: str) -> None:
        if label not in self._closure:
            raise MarkingError(f"unknown {self.scheme_id!r} label: {label!r}")

    def leq(self, lower: str, upper: str) -> bool:
        self._require_label(lower)
        self._require_label(upper)
        return upper in self._closure[lower]

    def dominates(self, higher: str, lower: str) -> bool:
        return self.leq(lower, higher)

    def join(self, *labels: str) -> str:
        if not labels:
            return self.bottom
        for label in labels:
            self._require_label(label)
        upper_bounds = set(self.labels)
        for label in labels:
            upper_bounds.intersection_update(self._closure[label])
        minimal = {
            candidate
            for candidate in upper_bounds
            if not any(
                other != candidate and self.leq(other, candidate)
                for other in upper_bounds
            )
        }
        if len(minimal) != 1:
            raise MarkingError(f"join is not unique for labels {labels!r}")
        result = next(iter(minimal))
        if not all(self.leq(label, result) for label in labels):
            raise MarkingError("internal error: join would downgrade an input marking")
        return result

    def meet(self, *labels: str) -> str:
        if not labels:
            return self.top
        for label in labels:
            self._require_label(label)
        lower_bounds = {
            candidate
            for candidate in self.labels
            if all(self.leq(candidate, label) for label in labels)
        }
        maximal = {
            candidate
            for candidate in lower_bounds
            if not any(
                other != candidate and self.leq(candidate, other)
                for other in lower_bounds
            )
        }
        if len(maximal) != 1:
            raise MarkingError(f"meet is not unique for labels {labels!r}")
        return next(iter(maximal))


@dataclass(frozen=True, slots=True)
class MarkingSet:
    values: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def __getitem__(self, scheme_id: str) -> str:
        return self.values[scheme_id]


@dataclass(frozen=True, slots=True)
class DisclosureDecision:
    allowed: bool
    reason: str
    payload: Any = None


class MarkingEngine:
    def __init__(self, schemes: Iterable[MarkingSchemeDefinition]) -> None:
        definitions = tuple(schemes)
        mapping = {scheme.scheme_id: scheme for scheme in definitions}
        if not mapping:
            raise MarkingError("at least one marking scheme is required")
        if len(mapping) != len(definitions):
            raise MarkingError("marking scheme identifiers must be unique")
        self._schemes = MappingProxyType(mapping)

    @property
    def schemes(self) -> Mapping[str, MarkingSchemeDefinition]:
        return self._schemes

    def validate(self, markings: MarkingSet) -> None:
        unknown = set(markings.values) - set(self._schemes)
        if unknown:
            raise MarkingError(f"unknown marking schemes: {sorted(unknown)!r}")
        for scheme_id, label in markings.values.items():
            self._schemes[scheme_id]._require_label(label)

    def join(self, *marking_sets: MarkingSet) -> MarkingSet:
        for marking_set in marking_sets:
            self.validate(marking_set)
        combined: dict[str, str] = {}
        for scheme_id, scheme in self._schemes.items():
            labels = [
                marking_set.values.get(scheme_id, scheme.bottom)
                for marking_set in marking_sets
            ]
            combined[scheme_id] = scheme.join(*labels)
        return MarkingSet(combined)

    def is_authorized(self, markings: MarkingSet, clearance: MarkingSet) -> bool:
        self.validate(markings)
        self.validate(clearance)
        for scheme_id, required in markings.values.items():
            granted = clearance.values.get(scheme_id)
            if granted is None or not self._schemes[scheme_id].dominates(granted, required):
                return False
        return True

    def require_authorized(self, markings: MarkingSet, clearance: MarkingSet) -> None:
        if not self.is_authorized(markings, clearance):
            raise AuthorizationError("clearance does not dominate the content marking")

    def disclose(
        self,
        payload: Any,
        markings: MarkingSet,
        clearance: MarkingSet,
    ) -> DisclosureDecision:
        if not self.is_authorized(markings, clearance):
            return DisclosureDecision(False, "insufficient marking clearance", None)
        return DisclosureDecision(True, "clearance dominates all markings", payload)


LatticeSolver = MarkingSchemeDefinition
