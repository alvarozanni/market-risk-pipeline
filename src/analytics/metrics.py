"""
Módulo de Analítica: Modelado estadístico, cálculo de retornos y métricas de riesgo.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd


class RiskAnalyticsEngine:
    """Motor para el procesamiento cuantitativo y cálculo de métricas financieras."""

    TRADING_DAYS_PER_YEAR = 252

    def __init__(self, price_data: pd.DataFrame):
        if price_data.empty:
            raise ValueError("El DataFrame de precios no puede estar vacío.")
        self.prices = price_data.copy()
        # Retornos logarítmicos diarios: ln(P_t / P_{t-1})
        self.log_returns = np.log(self.prices / self.prices.shift(1)).dropna()

    def calculate_annualized_volatility(self) -> pd.Series:
        """Calcula la volatilidad anualizada a partir del desvío estándar de retornos."""
        daily_std = self.log_returns.std()
        return daily_std * np.sqrt(self.TRADING_DAYS_PER_YEAR)

    def calculate_moving_averages(self, windows: tuple = (20, 50)) -> Dict[str, pd.DataFrame]:
        """Calcula medias móviles simples (SMA) para las ventanas especificadas."""
        sma_dict = {}
        for w in windows:
            sma_dict[f"SMA_{w}"] = self.prices.rolling(window=w).mean()
        return sma_dict

    def calculate_max_drawdown(self) -> pd.Series:
        """
        Calcula la máxima pérdida observada desde un pico histórico (Maximum Drawdown).
        """
        cumulative_max = self.prices.cummax()
        drawdown = (self.prices - cumulative_max) / cumulative_max
        return drawdown.min()

    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calcula la matriz de correlación de Pearson entre los retornos de los activos."""
        return self.log_returns.corr()

    def generate_risk_summary(self) -> pd.DataFrame:
        """Consolida las métricas clave de riesgo y rendimiento en un DataFrame."""
        ann_vol = self.calculate_annualized_volatility()
        max_dd = self.calculate_max_drawdown()
        
        # Rendimiento acumulado total en el período analizado
        total_return = (self.prices.iloc[-1] / self.prices.iloc[0]) - 1

        summary = pd.DataFrame({
            "Rendimiento_Total": total_return,
            "Volatilidad_Anualizada": ann_vol,
            "Max_Drawdown": max_dd
        })
        return summary


if __name__ == "__main__":
    # Test de integración rápido uniendo Ingesta + Analítica
    from src.ingestion.fetcher import MarketDataFetcher

    print("Descargando datos para test...")
    fetcher = MarketDataFetcher(tickers=["AAPL", "MSFT", "GOOGL"])
    df_prices = fetcher.download_history(period="1y")

    engine = RiskAnalyticsEngine(price_data=df_prices)

    print("\n--- Resumen de Métricas de Riesgo ---")
    print(engine.generate_risk_summary().round(4))

    print("\n--- Matriz de Correlación entre Activos ---")
    print(engine.calculate_correlation_matrix().round(4))