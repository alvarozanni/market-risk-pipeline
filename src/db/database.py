"""
Módulo de Persistencia: Gestión de SQLite para series de tiempo y métricas de riesgo.
"""
import sqlite3
from typing import List, Optional
import pandas as pd


class MarketDatabase:
    """Administrador de almacenamiento y consultas SQL para el pipeline de mercado."""

    def __init__(self, db_path: str = "market_data.db"):
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        """Inicializa las tablas y los índices para optimizar búsquedas por activo y fecha."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de precios históricos diarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    close_price REAL NOT NULL,
                    UNIQUE(ticker, date)
                );
            """)

            # Tabla de métricas de riesgo calculadas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    calculation_date TEXT NOT NULL,
                    total_return REAL NOT NULL,
                    annualized_volatility REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    UNIQUE(ticker, calculation_date)
                );
            """)

            # Índices para acelerar el filtrado por ticker y rango de fechas
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prices_ticker_date 
                ON daily_prices (ticker, date);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_ticker 
                ON risk_metrics (ticker);
            """)
            conn.commit()

    def save_prices(self, prices_df: pd.DataFrame) -> int:
        """
        Persiste el DataFrame de precios (fechas en índice, columnas = tickers).
        Utiliza UPSERT para evitar duplicados.
        """
        records = []
        for date, row in prices_df.iterrows():
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]
            for ticker, price in row.items():
                if pd.notna(price):
                    records.append((str(ticker), date_str, float(price)))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO daily_prices (ticker, date, close_price)
                VALUES (?, ?, ?)
                ON CONFLICT(ticker, date) DO UPDATE SET close_price = excluded.close_price;
            """, records)
            conn.commit()
            return cursor.rowcount

    def save_risk_summary(self, summary_df: pd.DataFrame, calc_date: str) -> None:
        """Persiste las métricas consolidadas de riesgo calculadas por activo."""
        records = []
        for ticker, row in summary_df.iterrows():
            records.append((
                str(ticker),
                calc_date,
                float(row["Rendimiento_Total"]),
                float(row["Volatilidad_Anualizada"]),
                float(row["Max_Drawdown"])
            ))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO risk_metrics (ticker, calculation_date, total_return, annualized_volatility, max_drawdown)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ticker, calculation_date) DO UPDATE SET
                    total_return = excluded.total_return,
                    annualized_volatility = excluded.annualized_volatility,
                    max_drawdown = excluded.max_drawdown;
            """, records)
            conn.commit()

    def get_price_history(self, ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """Recupera la serie temporal de precios filtrada."""
        query = "SELECT date, close_price FROM daily_prices WHERE ticker = ?"
        params = [ticker.upper()]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date ASC"

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            return df

    def get_latest_metrics(self) -> pd.DataFrame:
        """Recupera el snapshot más reciente de métricas de riesgo por activo."""
        query = """
            SELECT ticker, calculation_date, total_return, annualized_volatility, max_drawdown
            FROM risk_metrics
            WHERE id IN (
                SELECT MAX(id) FROM risk_metrics GROUP BY ticker
            )
            ORDER BY ticker ASC;
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)


if __name__ == "__main__":
    from datetime import date
    from src.ingestion.fetcher import MarketDataFetcher
    from src.analytics.metrics import RiskAnalyticsEngine

    print("1. Descargando datos...")
    fetcher = MarketDataFetcher(["AAPL", "MSFT"])
    prices = fetcher.download_history(period="3mo")

    print("2. Calculando métricas...")
    engine = RiskAnalyticsEngine(prices)
    summary = engine.generate_risk_summary()

    print("3. Persistiendo en SQLite...")
    db = MarketDatabase("test_market.db")
    db.save_prices(prices)
    db.save_risk_summary(summary, calc_date=str(date.today()))

    print("4. Leyendo de la base de datos (verificación):")
    print("\n--- Precios guardados (AAPL últimos 5) ---")
    print(db.get_price_history("AAPL").tail())

    print("\n--- Métricas persistidas ---")
    print(db.get_latest_metrics())