import pytest

from financepype.markets.orderbook.orderbook import Orderbook


@pytest.fixture
def orderbook() -> Orderbook:
    return Orderbook()


def test_orderbook_initialization(orderbook: Orderbook) -> None:
    """Test that an orderbook is properly initialized."""
    assert isinstance(orderbook, Orderbook)
