# Market Analytics & Risk Engine

![Tests](https://github.com/alvarozanni/market-risk-pipeline/actions/workflows/ci.yml/badge.svg)

Pipeline de procesamiento cuantitativo, persistencia de series temporales y API REST orientada al análisis de riesgo financiero para activos de mercado.

## 🚀 Arquitectura del Sistema

```mermaid
flowchart LR
    A[Yahoo Finance API] --> B[MarketDataFetcher]
    B --> C[RiskAnalyticsEngine]
    C --> D[(SQLite Database)]
    D --> E[FastAPI Endpoints]
    E --> F[Swagger Docs / Client]