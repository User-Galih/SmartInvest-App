from fastapi import (
    APIRouter,
    HTTPException
)

from schemas.portfolio_schema import IHSGRequest
from services.ihsg_service import (
    predict_ihsg_with_portfolio
)

router = APIRouter()


@router.post(
    "/predict-ihsg"
)
def predict_ihsg_route(request: IHSGRequest):

    try:
        return predict_ihsg_with_portfolio(
            index_choice=request.index_choice,
            start_date=request.start_date,
            end_date=request.end_date,
            investment_amount=request.investment_amount,
            user_id=request.user_id,
            gemini_api_key=request.gemini_api_key
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
