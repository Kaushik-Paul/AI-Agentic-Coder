import typing


def get_share_price(symbol: str) -> float:
    """Mock price provider."""
    prices = {"AAPL": 150.0, "TSLA": 700.0, "GOOGL": 2800.0}
    if symbol in prices:
        return prices[symbol]
    raise ValueError(f"Unknown symbol: {symbol}")


class Account:
    """Simple trading simulation account."""

    def __init__(self, initial_balance: float = 0) -> None:
        if initial_balance < 0:
            raise ValueError("Initial balance cannot be negative")
        self._balance: float = float(initial_balance)
        self._initial_deposit: float = float(initial_balance)
        self._holdings: typing.Dict[str, int] = {}  # symbol -> quantity
        self._transactions: typing.List[typing.Dict[str, typing.Any]] = []

    # Internal helper to record a transaction
    def _record_txn(self, txn_type: str, symbol: str, quantity: int, price: float, amount: float) -> None:
        self._transactions.append(
            {
                "type": txn_type,
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "amount": amount,
            }
        )

    def deposit(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount
        self._record_txn("DEPOSIT", "", 0, 0.0, amount)

    def withdraw(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self._balance:
            raise ValueError("Insufficient funds")
        self._balance -= amount
        self._record_txn("WITHDRAW", "", 0, 0.0, -amount)

    def buy_shares(self, symbol: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        price = get_share_price(symbol)
        cost = price * quantity
        if cost > self._balance:
            raise ValueError("Insufficient balance to buy shares")
        self._balance -= cost
        self._holdings[symbol] = self._holdings.get(symbol, 0) + quantity
        self._record_txn("BUY", symbol, quantity, price, -cost)

    def sell_shares(self, symbol: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if symbol not in self._holdings or self._holdings[symbol] < quantity:
            raise ValueError("Not enough shares to sell")
        price = get_share_price(symbol)
        proceeds = price * quantity
        self._balance += proceeds
        self._holdings[symbol] -= quantity
        if self._holdings[symbol] == 0:
            del self._holdings[symbol]
        self._record_txn("SELL", symbol, quantity, price, proceeds)

    def get_holdings(self) -> typing.Dict[str, int]:
        return dict(self._holdings)

    def get_portfolio_value(self) -> float:
        value = self._balance
        for symbol, qty in self._holdings.items():
            value += get_share_price(symbol) * qty
        return value

    def get_profit_loss(self) -> float:
        current = self.get_portfolio_value()
        return current - self._initial_deposit

    def get_transaction_history(self) -> typing.List[typing.Dict[str, typing.Any]]:
        return list(self._transactions)