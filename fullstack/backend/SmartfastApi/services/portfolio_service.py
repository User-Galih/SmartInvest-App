from services.ds_logic import (
    analyze_portfolio_logic
)


def analyze_portfolio(data):

    return analyze_portfolio_logic(
        index_choice=data.index_choice,
        start_date=data.start_date,
        end_date=data.end_date,
        investment_amount=data.investment_amount,
        model_choice=data.model_choice,
        gemini_api_key=getattr(data, "gemini_api_key", None)
    )
