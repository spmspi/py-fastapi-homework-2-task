from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from flake8.formatting import default
from fastapi import Request
from sqlalchemy import select, func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, session, selectinload
from starlette import status
from starlette.responses import JSONResponse

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    Country,
    MovieUpdateSchema,
    CountryBase,
    MovieUpdateResponseSchema,
)

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    request: Request,
    page: Annotated[
        int,
        Query(ge=1, description="Page number"),
    ] = 1,
    per_page: Annotated[
        int,
        Query(
            ge=1,
            le=20,
        ),
    ] = 10,
    db: AsyncSession = Depends(get_db),
):

    offset = (page - 1) * per_page
    limit = per_page
    stmt = select(MovieModel).order_by(desc(MovieModel.id)).offset(offset).limit(limit)
    total_items = await db.scalar(func.count(MovieModel.id))
    movies = await db.scalars(stmt)
    all_movies = movies.all()

    if not all_movies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No movies found."
        )

    total_pages = int(total_items) // per_page + 1
    base_path = request.url.path.split("/")[3:]

    prev_page = (
        (f"/{'/'.join(base_path)}?page={page - 1}&per_page={per_page}")
        if page > 1
        else None
    )

    next_page = (
        (f"/{'/'.join(base_path)}?page={page + 1}&per_page={per_page}")
        if page < total_pages
        else None
    )

    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE,
            detail=[
                {
                    "loc": ["query", "page"],
                    "msg": "Ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge",
                }
            ],
        )

    return {
        "movies": all_movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_detail_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
    )
    movie = await db.scalar(stmt)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    return movie


@router.post("/movies/", status_code=201, response_model=MovieDetailSchema)
async def create_movie(
    request: Request,
    movie: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MovieModel).where(
        MovieModel.name == movie.name, MovieModel.date == movie.date
    )
    movie_db = await db.scalar(stmt)

    if movie_db:
        raise HTTPException(
            409,
            f"A movie with the name '{movie.name}' "
            f"and release date '{movie.date}' already exists.",
        )

    stmt = select(CountryModel).where(CountryModel.code == movie.country)
    country_db = await db.scalar(stmt)
    if not country_db:
        country_db = CountryModel(code=movie.country)
        db.add(country_db)

    genres_list = []
    for genre in movie.genres:
        stmt = select(GenreModel).where(GenreModel.name == genre)
        genre_db = await db.scalar(stmt)
        if not genre_db:
            genre_db = GenreModel(name=genre)
            db.add(genre_db)
        genres_list.append(genre_db)

    actors_list = []
    for actor in movie.actors:
        stmt = select(ActorModel).where(ActorModel.name == actor)
        actor_db = await db.scalar(stmt)

        if not actor_db:
            actor_db = ActorModel(name=actor)
            db.add(actor_db)
        actors_list.append(actor_db)

    languages_list = []
    for language in movie.languages:
        stmt = select(LanguageModel).where(LanguageModel.name == language)
        language_db = await db.scalar(stmt)
        if not language_db:
            language_db = LanguageModel(name=language)
            db.add(language_db)
        languages_list.append(language_db)

    db_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country=country_db,
        genres=genres_list,
        actors=actors_list,
        languages=languages_list,
    )

    db.add(db_movie)
    await db.commit()
    await db.refresh(db_movie)
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == db_movie.id)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
    )
    movie_db = await db.scalar(stmt)

    return db_movie


@router.patch("/movies/{movie_id}/")
async def update_movie(
    data: MovieUpdateSchema,
    request: Request,
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
    )
    movie = await db.scalar(stmt)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    if data.name is not None:
        movie.name = data.name
    if data.overview is not None:
        movie.overview = data.overview
    if data.score is not None:
        movie.score = data.score
    if data.budget is not None:
        movie.budget = data.budget
    if data.revenue is not None:
        movie.revenue = data.revenue
    if data.date is not None:
        movie.date = data.date
    if data.country is not None:
        movie.country.code = data.country

    if data.genres is not None:
        genres_list = []
        for genre in data.genres:
            stmt = select(GenreModel).where(GenreModel.name == genre)
            genre_db = await db.scalar(stmt)
            if not genre_db:
                genre_db = GenreModel(name=genre)
                db.add(genre_db)
            genres_list.append(genre_db)
        movie.genres = genres_list

    if data.actors is not None:
        actors_list = []
        for actor in data.actors:
            stmt = select(ActorModel).where(ActorModel.name == actor)
            actor_db = await db.scalar(stmt)

            if not actor_db:
                actor_db = ActorModel(name=actor)
                db.add(actor_db)
            actors_list.append(actor_db)
        movie.actors = actors_list

    if data.languages is not None:
        languages_list = []
        for language in data.languages:
            stmt = select(LanguageModel).where(LanguageModel.name == language)
            language_db = await db.scalar(stmt)
            if not language_db:
                language_db = LanguageModel(name=language)
                db.add(language_db)
            languages_list.append(language_db)
        movie.languages = languages_list

    await db.commit()
    await db.refresh(movie)
    return JSONResponse(
        status_code=200, content={"detail": "Movie updated successfully."}
    )


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    movie_db = await db.scalar(stmt)
    if not movie_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    await db.delete(movie_db)
    await db.commit()
