# Kazakhstan NGO Pilot Discovery

This note captures the current discovery signal from a Kazakhstan-based NGO team evaluating GrantFlow for a bounded pilot.

## Account Snapshot

- Organization type: NGO / implementing organization
- Geography: Kazakhstan
- Pilot relevance: high
- Workflow maturity: moderate to high
- Likely deployment posture: bounded pilot with explicit role mapping and controlled access

## Primary Bottlenecks

Ranked from the customer conversation:

1. Review chaos
2. Approvals across multiple internal stakeholders
3. LogFrame / MEL alignment and repeated restructuring
4. First-draft speed
5. Final packaging

Interpretation:
- The team does not primarily need more draft text.
- The team needs stronger workflow control across reviews, approvals, and results-framework alignment.
- This matches GrantFlow's strongest current wedge: reviewable, traceable drafting operations rather than generic writing assistance.

## Current Team Structure

| GrantFlow pilot role | Customer-side role |
| --- | --- |
| Pilot owner | Head of Programs / Proposal Lead |
| Operator | Grant / Proposal Manager |
| Reviewer | Technical Leads, MEL Specialist, Finance / Compliance, external SME as needed |
| Approver | Country Director / Executive Director |
| Ingest / research owner | Program Officer + MEAL Analyst |

## Highest-Priority Donor Workflows

Current order of importance:

1. `un_agencies`
2. `eu`
3. `usaid`
4. `giz` as next priority

Implication for pilot scope:
- A credible pilot should not start with World Bank-only or generic-only scenarios.
- The first live cases should cover at least:
  - one UN agencies case
  - one EU case
  - one USAID case

## Current Success Metrics

The customer already tracks useful operational metrics. That is a strong pilot sign.

Primary metrics:
- time to first reviewable draft
- review loops to final version
- number of people in review
- time to final package, including annexes and matrices

Secondary metric:
- percentage of tasks closed on time in the final `7-10` days before deadline

Interpretation:
- This is suitable for a measured pilot.
- The pilot should use customer baseline, not illustrative benchmark only.

## Pilot Success Criteria

The customer described a bounded success threshold:

- reduce time to first reviewable draft by at least `25-30%`
- remove `1-2` full review cycles
- reduce duplicate or conflicting comments
- improve traceability of findings/comments
- reduce LogFrame / MEL rework
- produce a cleaner final export package with less late manual assembly

These are practical and measurable.

## Product Fit Assessment

### Strong current fit

- review chaos
- approvals and checkpoint visibility
- structured findings/comments workflow
- ToC / LogFrame / MEL working draft generation
- exportable review packages

### Partial fit

- measured pilot evidence with real customer baselines
- customer-specific access model
- final submission formatting against customer-specific templates

### Current recommendation

Proceed with a bounded pilot conversation.

The account is a better fit for:
- proposal operations control
- structured draft alignment
- reviewer workflow visibility

than for:
- fully automated proposal authoring
- fully automated final submission packaging

## Recommended Pilot Shape

Use a narrow first phase:

- `3` initial cases
- donors:
  - `un_agencies`
  - `eu`
  - `usaid`
- `1` pilot owner
- `1` operator
- `1-2` primary reviewers
- `1` approver
- `1` ingest owner

Avoid starting with:
- all donor types at once
- too many reviewers
- undefined approval authority

## Data To Collect Next

Before pilot start, capture for each selected case:

- baseline time to first reviewable draft
- baseline time to final review-ready package
- baseline review loops
- people involved in review
- current final-package assembly pain points

Also clarify:

- which comments are considered non-productive or duplicative
- which annexes/matrices are most painful today
- whether approval delay is content-driven or coordination-driven

## Recommended Next Call

The next call should decide:

1. which `3` live cases enter the pilot
2. who owns baseline capture
3. who is allowed to trigger draft runs
4. who can approve HITL checkpoints
5. which donor documents will be loaded into namespaces first

## Internal Product Note

This account reinforces the current product thesis:

- The strongest value is not "AI writes grant text."
- The strongest value is "GrantFlow reduces review chaos and makes proposal work operationally controllable."
