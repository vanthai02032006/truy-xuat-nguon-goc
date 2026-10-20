from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RootOriginItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_code: str
    product_name: str
    farm_name: str
    land_plot_id: int | None = None
    land_plot_name: str | None = None
    land_plot_address: str | None = None
    harvest_date: datetime | None = None
    initial_quantity: float | None = None
    remaining_quantity: float | None = None
    unit: str | None = "kg"
    generation_depth: int = 0


class RootOriginsResponse(BaseModel):
    target_batch_id: int
    target_batch_code: str
    root_count: int
    roots: list[RootOriginItem]


class HoldingOrgInfo(BaseModel):
    id: int | None = None
    name: str
    code: str | None = None


class DescendantItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_code: str
    product_name: str
    generation: str
    generation_level: int
    relation_type: str
    quantity_transferred: float
    holding_organization: HoldingOrgInfo
    current_location: str
    initial_quantity: float | None = None
    remaining_quantity: float | None = None
    unit: str | None = "kg"
    status: str | None = None
    is_depleted: bool
    parent_batch_id: int


class DescendantsResponse(BaseModel):
    source_batch_id: int
    source_batch_code: str
    descendant_count: int
    descendants: list[DescendantItem]


class DagGraphNode(BaseModel):
    id: int
    batch_code: str
    product_name: str
    node_type: str  # "ROOT", "ANCESTOR", "FOCUS", "DESCENDANT"
    holding_org_name: str
    location: str | None = None
    remaining_quantity: float | None = None
    unit: str | None = "kg"
    status: str | None = None
    is_depleted: bool = False


class DagGraphEdge(BaseModel):
    source_batch_id: int
    target_batch_id: int
    relation_type: str
    quantity: float


class DagGraphResponse(BaseModel):
    focus_batch: DagGraphNode
    roots: list[RootOriginItem]
    ancestors: list[DagGraphNode]
    descendants: list[DescendantItem]
    nodes: list[DagGraphNode]
    edges: list[DagGraphEdge]


class SeedLineageDagResponse(BaseModel):
    message: str
    total_batches: int
    total_organizations: int
    total_relations: int
    sample_batches: list[dict]
    answer_key: dict

