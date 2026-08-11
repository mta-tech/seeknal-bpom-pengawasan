# Business Glossary — Stable Domain Semantics

This file stores stable business meaning.
It should define concepts, not serve as an answer catalog.

---

## 1. Registration Systems

The database contains more than one registration system.

The system distinction is a **registration-system distinction**, not a geography distinction.
Do not equate system names with domestic vs imported categories unless the question is explicitly about a different business concept that uses those attributes.

Implication:

- the agent must treat cross-system concepts carefully,
- must not assume the same code means the same thing across systems,
- and must not force unified answers when the systems expose different granularity.

---

## 2. Core Business Entities

### NIE / Issued License

Represents an issued registration/license identity.

### Application / Submission

Represents a submitted application lifecycle object.

### Company / Trader

Represents the business entity associated with the registered object.

### Product / Item Record

Represents a specific regulated item record rather than an application or issued license identity.

The agent must lock which entity is being discussed before choosing fields or filters.

---

## 3. Business Event Semantics

Many user words refer to business events rather than raw database values.

Examples of event families:

- issued,
- active,
- submitted,
- approved,
- cancelled,
- in process,
- expired,
- completed.

These are not interchangeable.
The agent must lock the event before choosing:

- status filters,
- date columns,
- or lifecycle logic.

---

## 4. Coded vs Direct Concepts

Not every business term should be resolved the same way.

Some concepts are:

- coded classifications,
- some are direct fields,
- some are master-data attributes,
- some require discovery,
- some require cross-system comparison.

The agent should not escalate every concept into dictionary lookup or discovery.

---

## 5. Cross-System Asymmetry

Some concepts exist in both systems but are not represented identically.

Possible differences include:

- different code values,
- different category names,
- different field names,
- different granularity,
- partial overlap,
- or non-equivalent semantic scope.

When this happens, the agent must:

1. resolve per system,
2. decide whether a combined answer is valid,
3. keep the limitation visible if equivalence is not exact.

---

## 6. Exact State vs Family State

Some user phrases name one exact lifecycle state.
Others describe a family of related states.

The agent must not collapse an exact-state question into a family-state answer unless the user explicitly broadens the scope.

Likewise, it must not pretend a family-state phrase is exact if multiple distinct states still fit.

---

## 7. Stable Business Meaning Only

This glossary should contain:

- concept definitions,
- semantic boundaries,
- system distinctions,
- and reasoning-critical business rules.

It should not become:

- a product example library,
- a shortcut code table for every named item,
- or a collection of question-specific answer hints.

Specific product-code tables and named-product examples belong in `docs/audit_context/` as evaluation material, not in the runtime glossary. At runtime, every code is resolved through `code_translation_protocol.md`, never read from this file.

