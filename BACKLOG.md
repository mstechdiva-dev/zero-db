# SchemaZero — Backlog & Future Ideas

Ideas captured here are not committed to — just worth remembering.

---

## Ideas

### Schema Design Advisor
A conversational flow where a user describes their data story and SchemaZero recommends an optimal schema design after asking a few clarifying questions.

**Why it's interesting:** Natural extension of the schema expertise already in the product. The agent infrastructure (declarative `.md` agent definitions, Claude integration, chat UI) makes it low-effort to prototype.

**Why it's parked:** Solves a softer pain point than the core. Schema design advice is available everywhere (LLMs, Stack Overflow, teammates). The defensible value of SchemaZero is real-time monitoring and impact analysis on existing production schemas — not upfront design help.

**When it might make sense:** If users churn during onboarding because they don't know how to structure their schema to get value from monitoring. Could work as a conversion/onboarding tool rather than a standalone feature.
