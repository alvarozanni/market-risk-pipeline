"""
Módulo de Ingesta: Consulta y normalización de series de tiempo de mercado.
"""
from typing import List
import pandas as pd
import yfinance as yf


class MarketDataFetcher:
    """Cliente para la obtención y validación de datos históricos de activos."""

    def __init__(self, tickers: List[str]):
        if not tickers:
            raise ValueError("Debe especificarse al menos un ticker.")
        self.tickers = [t.upper().strip() for t in tickers]

    def download_history(
        self, period: str = "1y", interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Descarga precios de cierre ajustados para la lista de tickers.
        Retorna un DataFrame indexado por fecha con columnas por ticker.
        """
        raw_data = yf.download(
            tickers=self.tickers,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

        if raw_data.empty:
            raise RuntimeError("No se pudieron obtener datos para los tickers solicitados.")

        # Manejo de columnas cuando se consulta 1 ticker vs múltiples
        if len(self.tickers) == 1:
            close_prices = raw_data[["Close"]].rename(columns={"Close": self.tickers[0]})
        else:
            close_prices = raw_data["Close"]

        # Limpieza básica: ordenar por fecha y descartar duplicados
        close_prices = close_prices.sort_index()
        close_prices = close_prices.loc[~close_prices.index.duplicated(keep="first")]

        # Descartar filas vacías
        close_prices = close_prices.dropna(how="all")

        return close_prices


if __name__ == "__main__":
    test_tickers = ["AAPL", "MSFT", "GOOGL"]
    fetcher = MarketDataFetcher(tickers=test_tickers)
    df = fetcher.download_history(period="6mo")
    print("\n--- Vista preliminar de datos ingeridos ---")
    print(df.tail())