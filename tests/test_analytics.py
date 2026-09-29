"""
Pruebas unitarias para el motor de métricas estadísticas y de riesgo.
"""
import pytest
import pandas as pd
import numpy as np
from src.analytics.metrics import RiskAnalyticsEngine


@pytest.fixture
def mock_price_data():
    """Genera una serie temporal simulada de precios para testeo determinístico."""
    dates = pd.date_range(start="2025-01-01", periods=5, freq="D")
    data = {
        "ASSET_A": [100.0, 105.0, 110.0, 100.0, 95.0],
        "ASSET_B": [50.0, 50.0, 50.0, 50.0, 50.0]
    }
    return pd.DataFrame(data, index=dates)


def test_initialization_with_empty_dataframe():
    """Debe lanzar ValueError si se pasa un DataFrame vacío."""
    with pytest.raises(ValueError):
        RiskAnalyticsEngine(price_data=pd.DataFrame())


def test_log_returns_calculation(mock_price_data):
    """Verifica el cálculo de retornos logarítmicos."""
    engine = RiskAnalyticsEngine(price_data=mock_price_data)
    returns = engine.log_returns
    
    # ASSET_B no cambia de precio, su retorno debe ser 0.0
    assert np.allclose(returns["ASSET_B"], 0.0)
    assert len(returns) == len(mock_price_data) - 1


def test_annualized_volatility_zero(mock_price_data):
    """Un activo sin variación de precio debe tener volatilidad 0."""
    engine = RiskAnalyticsEngine(price_data=mock_price_data)
    volatility = engine.calculate_annualized_volatility()
    
    assert volatility["ASSET_B"] == 0.0


def test_max_drawdown(mock_price_data):
    """Calcula la máxima caída observada desde un pico."""
    engine = RiskAnalyticsEngine(price_data=mock_price_data)
    drawdowns = engine.calculate_max_drawdown()
    
    # En ASSET_A el pico fue 110 y cayó a 95 -> (95 - 110) / 110 ≈ -0.1363
    expected_mdd = (95.0 - 110.0) / 110.0
    assert pytest.approx(drawdowns["ASSET_A"], 0.001) == expected_mdd
    # ASSET_B nunca cayó
    assert drawdowns["ASSET_B"] == 0.0