from datetime import date, timedelta
from typing import Annotated, Literal, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError
from annotated_types import Lt, Ge


class MovieListItemSchema(BaseModel):
    id: int
    name: str = Field(max_length=255)
    date: date
    score: float
    overview: str


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


class ActorBase(BaseModel):
    name: str


class Actor(ActorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CountryBase(BaseModel):
    code: str


class Country(CountryBase):
    id: int
    name: str | None

    model_config = ConfigDict(from_attributes=True)


class GenresBase(BaseModel):
    name: str


class Genres(GenresBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class LanguagesBase(BaseModel):
    name: str


class Languages(LanguagesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(MovieListItemSchema):
    date: Annotated[date, Lt(date.today() + timedelta(days=365))]
    score: Annotated[float, Ge(0), Lt(100)]
    overview: str
    status: Literal["Released", "Post Production", "In Production"]
    budget: Annotated[float, Ge(0)]
    revenue: Annotated[float, Ge(0)]
    country: Country
    genres: List[Genres]
    actors: List[Actor]
    languages: List[Languages]

    model_config = ConfigDict(from_attributes=True)


class MovieCreateSchema(BaseModel):
    name: str = Field(max_length=255)
    date: date
    score: Annotated[float, Ge(0), Lt(100)]
    overview: str
    status: Literal["Released", "Post Production", "In Production"]
    budget: Annotated[float, Ge(0)]
    revenue: Annotated[float, Ge(0)]
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]
    model_config = ConfigDict(from_attributes=True)


class MovieCreateResponseSchema(MovieDetailSchema):
    id: int


class MovieUpdateSchema(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    overview: str | None = None
    date: Optional[date] = None
    score: Annotated[float, Ge(0), Lt(100)] | None = None
    status: Literal["Released", "Post Production", "In Production"] | None = None
    budget: Annotated[float, Ge(0)] | None = None
    revenue: Annotated[float, Ge(0)] | None = None
    country: str | None = None
    genres: List[str] | None = None
    actors: List[str] | None = None
    languages: List[str] | None = None

    @field_validator("date")
    def validate_date(cls, v):
        if v is not None:
            max_date = date.today() + timedelta(days=365)
            if v > max_date:
                raise ValidationError(f"{v} is not valid")


class MovieUpdateResponseSchema(BaseModel):
    detail: str
