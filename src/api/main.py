"""
API REST: Endpoints para consulta de series temporales y métricas de riesgo financiero.
"""
from datetime import date
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.ingestion.fetcher import MarketDataFetcher
from src.analytics.metrics import RiskAnalyticsEngine
from src.db.database import MarketDatabase

app = FastAPI(
    title="Market Analytics & Risk Pipeline API",
    description="API REST para ingesta automatizada, modelado de riesgo y análisis de activos de mercado.",
    version="1.0.0"
)

# Instancia global de la base de datos
db = MarketDatabase("market_data.db")


# --- Esquemas Pydantic para tipado de requests y responses ---
class PipelineRunRequest(BaseModel):
    tickers: List[str] = Field(default=["AAPL", "MSFT", "GOOGL"], example=["AAPL", "MSFT", "GOOGL"])
    period: str = Field(default="1y", example="1y")


class PriceRecord(BaseModel):
    date: str
    close_price: float


class RiskMetricRecord(BaseModel):
    ticker: str
    calculation_date: str
    total_return: float
    annualized_volatility: float
    max_drawdown: float


# --- Endpoints ---
@app.get("/", tags=["Health Check"])
def health_check():
    return {
        "status": "online",
        "service": "Market Analytics Pipeline",
        "docs_url": "/docs"
    }


@app.post("/api/pipeline/run", tags=["Pipeline Execution"])
def run_pipeline(payload: PipelineRunRequest):
    """
    Ejecuta el pipeline completo de ingesta, cálculo analítico y persistencia relacional.
    """
    try:
        # 1. Ingesta
        fetcher = MarketDataFetcher(tickers=payload.tickers)
        prices_df = fetcher.download_history(period=payload.period)

        # 2. Análisis Cuantitativo
        engine = RiskAnalyticsEngine(price_data=prices_df)
        summary_df = engine.generate_risk_summary()

        # 3. Persistencia
        db.save_prices(prices_df)
        db.save_risk_summary(summary_df, calc_date=str(date.today()))

        return {
            "status": "success",
            "tickers_processed": payload.tickers,
            "period": payload.period,
            "total_dates_recorded": len(prices_df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prices/{ticker}", response_model=List[PriceRecord], tags=["Market Data"])
def get_price_history(
    ticker: str,
    start_date: Optional[str] = Query(None, description="Formato YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Formato YYYY-MM-DD")
):
    """
    Obtiene la serie temporal de precios para un ticker específico con rango de fechas opcional.
    """
    df = db.get_price_history(ticker=ticker, start_date=start_date, end_date=end_date)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No se encontraron precios para el ticker '{ticker.upper()}'. Ejecute el pipeline primero.")
    return df.to_dict(orient="records")


@app.get("/api/metrics", response_model=List[RiskMetricRecord], tags=["Risk Analytics"])
def get_risk_metrics():
    """
    Retorna el último cálculo consolidado de métricas de riesgo (volatilidad, drawdown, retorno total).
    """
    df = db.get_latest_metrics()
    if df.empty:
        raise HTTPException(status_code=404, detail="No hay métricas registradas en la base de datos.")
    return df.to_dict(orient="records")


@app.get("/api/metrics/correlation", tags=["Risk Analytics"])
def get_correlation_matrix(
    tickers: List[str] = Query(default=["AAPL", "MSFT", "GOOGL"], description="Lista de tickers a correlacionar")
):
    """
    Calcula dinámicamente la matriz de correlación de Pearson entre los activos solicitados.
    """
    try:
        fetcher = MarketDataFetcher(tickers=tickers)
        prices = fetcher.download_history(period="6mo")
        engine = RiskAnalyticsEngine(prices)
        corr_matrix = engine.calculate_correlation_matrix().round(4)
        return corr_matrix.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))