from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from pydantic import EmailStr


class Prediction(BaseModel):
    disease: str
    confidence: float
    severity: str
    recommendations: List[str] = Field(default_factory=list)
    treatment: List[str] = Field(default_factory=list)


class ReportBase(BaseModel):
    filename: Optional[str] = None
    disease: str
    confidence: float = Field(ge=0, le=1)
    severity: str
    recommendations: List[str] = Field(default_factory=list)
    treatment: List[str] = Field(default_factory=list)


class ReportCreate(ReportBase):
    # Optional data URL of the annotated image from the client
    annotated_image: Optional[str] = None


class ReportOut(ReportBase):
    id: int

    # Pydantic v2 configuration
    model_config = ConfigDict(from_attributes=True)


class FeedbackCreate(BaseModel):
    name: str
    email: EmailStr
    message: Optional[str] = None
    kind: Literal['feedback', 'suggestion'] = 'feedback'
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class FeedbackOut(FeedbackCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
