"""Conjunctions router — stub for S1.4 router mounting. Full implementation in S6.4."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_conjunctions():
    return []
