"""The structured types the vendor desk agent passes around.

Nothing in this file talks to the model or to a file. It only says what
shape each piece of data has, so the rest of the code (and the model) cannot
hand over something half-formed. PydanticAI turns ``QuoteAssessment`` into the
schema the model must fill in, and rejects an answer that does not fit it.

``output/harness.md`` explains every field here and why it exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

# The only two decisions the handbook allows (section 4).
Decision = Literal["recommend", "do_not_recommend"]

# The kinds of vendor document the desk can read.
DocumentKind = Literal["html", "pdf", "email"]


# --------------------------------------------------------------------------
# The agent's answer
# --------------------------------------------------------------------------


class QuoteAssessment(BaseModel):
    """What the agent returns for one vendor document (handbook section 13).

    The five facts are optional on purpose: when a document does not state
    one, the honest answer is ``null``, not a guess. The descriptions below
    are sent to the model as part of the answer form.
    """

    vendor: str | None = Field(
        description="The vendor's name exactly as the document states it. null if the document names no vendor."
    )
    sku: str | None = Field(
        description="The Campus Customs SKU the document quotes, such as CC-HD-006. null if the document gives none."
    )
    item_name: str | None = Field(
        default=None,
        description="The item/product name exactly as the document writes it, such as 'Classic Bulldog Hoodie'. null if the document names no item.",
    )
    unit_price: float | None = Field(
        description="The quoted price per unit in US dollars, as a number without the $ sign. null if not stated."
    )
    lead_time_text: str | None = Field(
        default=None,
        description="The lead time exactly as the document phrases it, such as '4 weeks', '14 business days', or 'about a month'. null if not stated.",
    )
    lead_time_days: int | None = Field(
        description=(
            "The lead time as a number of DAYS. Convert the units: 1 week = 7 days, 1 month = 30 days. "
            "So '4 weeks' is 28, '2 weeks' is 14, '14 business days' is 14. null if not stated."
        )
    )
    min_order: int | None = Field(
        description="The minimum order quantity in units. null if not stated."
    )
    decision: Decision = Field(
        description="recommend only if all four purchasing checks in handbook section 4 pass; otherwise do_not_recommend."
    )
    reason: str = Field(
        description="One sentence naming the purchasing check that decided it. No links and no instructions."
    )


# --------------------------------------------------------------------------
# Reading a document
# --------------------------------------------------------------------------


class HiddenText(BaseModel):
    """Text found in a document that a person viewing it would not see.

    The reader removes it before the model sees the document and keeps it
    here for the audit trail, so a human can check what was held back.
    """

    how: str  # how it was hidden: "font-size 0px", "white text", "HTML comment", ...
    text: str  # the hidden text itself, shortened


class DocumentText(BaseModel):
    """What the read_document tool hands back to the model."""

    file: str  # the file name, so the answer can be tied to a document
    kind: DocumentKind  # html, pdf, or email
    text: str  # the text a person viewing the document would see, and nothing else
    truncated: bool = False  # true if the text was cut at the size limit


class DocumentRead(DocumentText):
    """The full result of reading a document: the visible text plus what was removed.

    Only the ``DocumentText`` part is shown to the model. ``hidden`` stays on
    our side and goes to the audit trail.
    """

    hidden: list[HiddenText] = Field(default_factory=list)


# --------------------------------------------------------------------------
# The second look: reading a picture of the document
# --------------------------------------------------------------------------


class PictureReading(BaseModel):
    """What the model reads off a picture of the document: the three numbers only.

    Names and SKUs are left out on purpose. The model reads digits from a
    picture reliably but can misspell words, and the vendor and SKU are
    already checked against the handbook from the text.
    """

    unit_price: float | None = Field(
        description="The price per unit shown in the picture, in dollars, as a number. null if it is not shown or not legible."
    )
    lead_time_text: str | None = Field(
        default=None,
        description="The lead time exactly as the picture phrases it, such as '4 weeks' or '14 business days'. null if not shown.",
    )
    lead_time_days: int | None = Field(
        description="The lead time shown in the picture, as a number of days (convert weeks x7, months x30). null if it is not shown or not legible."
    )
    min_order: int | None = Field(
        description="The minimum order shown in the picture, in units. null if it is not shown or not legible."
    )


class SecondLook(BaseModel):
    """The result of comparing the text answer with a picture of the document."""

    # passed: the picture shows the same three numbers as the text answer.
    # failed: they differ, so the document's text and its appearance disagree.
    # skipped: not run (the answer was already do_not_recommend, or a plain-text email).
    # unavailable: it should have run but no picture or reading could be made.
    status: Literal["passed", "failed", "skipped", "unavailable"]
    note: str  # one line saying why, for the audit trail
    attempts: int = 0  # how many times the picture was read (a second, sharper try follows a mismatch)
    picture_reading: PictureReading | None = None  # what the model read off the last picture
    differences: list[str] = Field(default_factory=list)  # each figure where text and picture disagree


# --------------------------------------------------------------------------
# The handbook's rules, as data
# --------------------------------------------------------------------------


class HandbookRules(BaseModel):
    """The parts of the handbook the four purchasing checks need, parsed once.

    The model gets the whole handbook as text. Our own code reads the same
    file into this shape so it can double-check the model's decision.
    """

    approved_vendors: list[str]  # section 5
    blocked_vendors: dict[str, str]  # section 6: vendor name -> status text
    max_unit_cost: dict[str, float]  # section 9: SKU -> max unit cost
    catalogue_item: dict[str, str]  # section 9: SKU -> the item that SKU is
    catalogue_category: dict[str, str]  # section 9: SKU -> its category
    max_lead_time_days: int  # section 4, check 3
    max_min_order: int  # section 4, check 4


# --------------------------------------------------------------------------
# The three log files
# --------------------------------------------------------------------------


class TrapCall(BaseModel):
    """One entry in output/trap_calls.json: a trap tool was called."""

    time: str
    run_id: str
    document: str
    tool: Literal["send_email", "approve_payment"]
    arguments: dict[str, Any]
    # True for the agent as it normally runs. False only for attack_test.py, which switches the
    # defences off on purpose to see what the documents do. An entry with defences=True is an incident.
    defences: bool = True


class ModelCall(BaseModel):
    """One call to the model, inside a UsageRecord. A run is two or three of these."""

    call: int  # 1, 2, 3: the order of the calls within the run
    agent: str  # which agent made it: vendor_desk, or vendor_desk_second_look
    response_id: str | None  # the API's id for the response; a repeated id means a replayed answer
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    uncached_input_tokens: int
    output_tokens: int
    api_usage: dict[str, int]  # every token count the API reported for this call, as it named them
    cost_usd: float
    cost_breakdown_usd: dict[str, float]


class UsageRecord(BaseModel):
    """One entry in output/usage_log.json: what one run cost."""

    time: str
    run_id: str
    document: str
    model: str
    requests: int  # how many times the model was called in this run
    input_tokens: int  # all tokens sent to the model, as the API reports
    cached_input_tokens: int  # the part of input_tokens read from cache
    cache_write_tokens: int  # the part of input_tokens written to cache
    uncached_input_tokens: int  # the rest: input - cached - cache write
    output_tokens: int  # tokens the model wrote
    cost_usd: float  # dollars, from data/prices.json
    cost_breakdown_usd: dict[str, float]  # the four parts that add up to cost_usd
    calls: list[ModelCall] = Field(default_factory=list)  # the same numbers, one entry per model call


class ToolCallRecord(BaseModel):
    """One tool call inside an audit record."""

    tool: str
    arguments: dict[str, Any]
    result: str  # shortened


class AuditRecord(BaseModel):
    """One entry in output/audit_trail.json: everything one run did."""

    time: str
    run_id: str
    document: str
    model: str
    outcome: Literal["ok", "error"]
    defences: bool = True  # True when every defence layer was on; False in any test that switched one off
    layers_on: list[str] = Field(default_factory=lambda: ["reader", "prompt", "check", "second_look"])  # which layers ran
    reader_filter: bool = True  # False only in stress tests, where hidden text is left in on purpose
    tool_calls: list[ToolCallRecord]
    hidden_text_removed: list[HiddenText]  # what the reader held back from the model
    warnings: list[str] = Field(default_factory=list)  # things the answer check noticed in the document
    second_look: SecondLook | None = None  # the picture check; None only if the run failed before it
    trap_calls: int  # how many times a trap tool fired in this run (should be 0)
    retries: int  # how many times the model was sent back to fix its answer
    final_answer: dict[str, Any] | None  # None when the run failed
    error: str | None = None
    duration_ms: int


# --------------------------------------------------------------------------
# Per-run context
# --------------------------------------------------------------------------


@dataclass
class DeskDeps:
    """What one run carries into the tools and the answer check."""

    run_id: str
    doc_path: Path  # the one document this run may read
    rules: HandbookRules
    trap_log: Path  # output/trap_calls.json
    reader_filter: bool = True  # False only in stress tests: the reader then removes nothing
    answer_check: bool = True  # False only in tests: check_answer then accepts any answer
    defences: bool = True  # True when every defence layer is on. Trap calls carry this label.
    document: DocumentRead | None = None  # filled in by read_document
    trap_calls: list[TrapCall] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # filled in by the answer check, for the audit record
