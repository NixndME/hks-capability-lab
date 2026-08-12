from fastapi import APIRouter

from .. import matrix

router = APIRouter()


@router.get("/api/matrix")
def get_matrix():
    return {"rows": matrix.build_matrix()}
