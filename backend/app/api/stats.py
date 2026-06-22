"""Stats router — stub for S1.4 router mounting. Full implementation in S6.5."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/orbital-regions")
def orbital_regions():
    return []
