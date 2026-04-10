"""
Portfolio service: business logic for portfolio aggregation & metrics
"""
from datetime import datetime, timedelta
from typing import Optional

from app.schemas.schemas import (
    ConcentrationItem,
    ConcentrationResponse,
    PortfolioCompareBody,
    PortfolioCompareResponse,
    PortfolioKPIResponse,
    PortfolioTrendPoint,
    PortfolioTrendResponse,
    RiskDistributionResponse,
)


def compute_portfolio_kpi(date_from: Optional[str], date_to: Optional[str], segment: Optional[str]) -> PortfolioKPIResponse:
    # Demo dùng dữ liệu giả
    return PortfolioKPIResponse(
        total_exposure=10_000_000,
        avg_pd=0.03,
        expected_loss=250_000,
        npl_ratio=0.05,
        var_99=500_000,
    )


def risk_distribution(group_by: Optional[str]) -> RiskDistributionResponse:
    buckets = {"low": 0.5, "medium": 0.3, "high": 0.2}
    chart_data = [
        {"bucket": "low", "value": 0.5, "count": 50},
        {"bucket": "medium", "value": 0.3, "count": 30},
        {"bucket": "high", "value": 0.2, "count": 20},
    ]
    score_buckets = [
        {"range": "0-20", "count": 5},
        {"range": "20-40", "count": 10},
        {"range": "40-60", "count": 25},
        {"range": "60-80", "count": 35},
        {"range": "80-100", "count": 25},
    ]
    score_stats = {"mean": 58.0, "median": 60.0, "std_dev": 18.5}
    return RiskDistributionResponse(
        buckets=buckets,
        chart_data=chart_data,
        score_buckets=score_buckets,
        score_stats=score_stats,
    )


def concentration(top_n: int = 10) -> ConcentrationResponse:
    items = [
        ConcentrationItem(name=f"Customer {i}", exposure=1_000_000 / i) for i in range(1, top_n + 1)
    ]
    return ConcentrationResponse(items=items)


def portfolio_trend(metric: str, interval: str) -> PortfolioTrendResponse:
    now = datetime.utcnow()
    points = [
        PortfolioTrendPoint(timestamp=now - timedelta(days=i), value=0.01 * (i + 1)) for i in range(10)
    ]
    return PortfolioTrendResponse(metric=metric, points=list(reversed(points)))


def portfolio_compare(body: PortfolioCompareBody) -> PortfolioCompareResponse:
    # Demo diff
    return PortfolioCompareResponse(diff_metrics={"expected_loss_diff": 10_000, "npl_diff": 0.01})
