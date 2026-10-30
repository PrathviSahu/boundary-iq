from typing import List, Optional
from pydantic import BaseModel, Field

class RuleExplanation(BaseModel):
    law_name: str
    law_number: Optional[str] = None
    summary: str

class EvidenceBoundary(BaseModel):
    grounded_in_data: List[str] = Field(
        default_factory=list,
        description="Source-verified facts from Cricsheet ball-by-ball data."
    )
    unavailable_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence that is NOT in the dataset and never assumed (e.g. DRS ball tracking, pitch map, snicko)."
    )

class EventExplanation(BaseModel):
    delivery_index: int
    over_display: str
    headline: str = Field(description="Short punchy headline for the event.")
    what_happened: str = Field(description="Clear explanation of the delivery outcome.")
    simple_cricket_explanation: str = Field(description="Explanation of why the cricket decision or action occurred.")
    why_it_matters: str = Field(description="Match tactical stakes, required rate impact or momentum shift.")
    fantasy_impact_explanation: str = Field(description="Detailed explanation of how players and fantasy scores shifted.")
    cricket_rule: RuleExplanation
    evidence: EvidenceBoundary
    data_limitations: List[str] = Field(
        default_factory=list,
        description="Explicit notice of data limitations."
    )
    fan_takeaway: str = Field(description="One-sentence takeaway for cricket fans.")
    engine_source: str = Field(default="deterministic_rules_engine", description="gemini_ai or deterministic_rules_engine")
