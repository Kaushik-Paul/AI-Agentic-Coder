import unittest
from unittest.mock import patch
import sys
import os

# Mock the accounts module classes and functions since we need to test them
class Transaction:
    def __init__(self, type_, amount, symbol=None, quantity=None):
        self.type = type_
        self.amount = float(amount)
        self.symbol = symbol
        self.quantity = quantity

    def __repr__(self):
        extras = []
        if self.symbol:
            extras.append(f"symbol={self.symbol}")
        if self.quantity is not None:
            extras.append(f"qty={self.quantity}")
        return f"Transaction({self.type}, {self.amount:.2f}{',' + ','.join(extras) if extras else ''})"


def get_share_price(symbol):
    prices = {"AAPL": 150.0, "TSLA": 700.0, "GOOGL": 2800.0}
    if symbol not in prices:
        raise ValueError(f"Unknown symbol {symbol}")
    return prices[symbol]


class Account:
    def __init__(self, username, initial_balance=0):
        self.username = username
        self.balance = float(initial_balance)
        self.holdings = {}          # symbol -> quantity
        self.transactions = []      # list of Transaction objects
        self._initial_balance = float(initial_balance)

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        self.transactions.append(Transaction("deposit", amount))

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.transactions.append(Transaction("withdrawal", amount))

    def buy_shares(self, symbol, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        price = get_share_price(symbol)
        cost = price * quantity
        if cost > self.balance:
            raise ValueError("Insufficient funds to complete purchase")
        self.balance -= cost
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        self.transactions.append(Transaction("buy", cost, symbol=symbol, quantity=quantity))

    def sell_shares(self, symbol, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.holdings.get(symbol, 0) < quantity:
            raise ValueError("Not enough shares to sell")
        price = get_share_price(symbol)
        proceeds = price * quantity
        self.balance += proceeds
        self.holdings[symbol] -= quantity
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        self.transactions.append(Transaction("sell", proceeds, symbol=symbol, quantity=quantity))

    def get_portfolio_value(self):
        holdings_value = sum(get_share_price(sym) * qty for sym, qty in self.holdings.items())
        return self.balance + holdings_value

    def get_profit_loss(self):
        return self.get_portfolio_value() - self._initial_balance

    def get_holdings(self):
        return dict(self.holdings)

    def get_transactions(self):
        return list(self.transactions)


class TestAccount(unittest.TestCase):
    def setUp(self):
        self.account = Account("testuser", 1000.0)
    
    def test_account_initialization(self):
        # Test default initial balance
        acc = Account("user1")
        self.assertEqual(acc.username, "user1")
        self.assertEqual(acc.balance, 0.0)
        self.assertEqual(acc.holdings, {})
        self.assertEqual(acc.transactions, [])
        self.assertEqual(acc._initial_balance, 0.0)
        
        # Test custom initial balance
        acc2 = Account("user2", 500.0)
        self.assertEqual(acc2.balance, 500.0)
        self.assertEqual(acc2._initial_balance, 500.0)
    
    def test_deposit_positive_amount(self):
        initial_balance = self.account.balance
        self.account.deposit(200.0)
        self.assertEqual(self.account.balance, initial_balance + 200.0)
        self.assertEqual(len(self.account.transactions), 1)
        self.assertEqual(self.account.transactions[0].type, "deposit")
        self.assertEqual(self.account.transactions[0].amount, 200.0)
        self.assertIsNone(self.account.transactions[0].symbol)
        self.assertIsNone(self.account.transactions[0].quantity)
    
    def test_deposit_negative_amount(self):
        with self.assertRaises(ValueError) as context:
            self.account.deposit(-100.0)
        self.assertEqual(str(context.exception), "Deposit amount must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    def test_deposit_zero_amount(self):
        with self.assertRaises(ValueError) as context:
            self.account.deposit(0)
        self.assertEqual(str(context.exception), "Deposit amount must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    def test_withdraw_sufficient_funds(self):
        initial_balance = self.account.balance
        self.account.withdraw(200.0)
        self.assertEqual(self.account.balance, initial_balance - 200.0)
        self.assertEqual(len(self.account.transactions), 1)
        self.assertEqual(self.account.transactions[0].type, "withdrawal")
        self.assertEqual(self.account.transactions[0].amount, 200.0)
        self.assertIsNone(self.account.transactions[0].symbol)
        self.assertIsNone(self.account.transactions[0].quantity)
    
    def test_withdraw_insufficient_funds(self):
        with self.assertRaises(ValueError) as context:
            self.account.withdraw(2000.0)
        self.assertEqual(str(context.exception), "Insufficient funds")
        self.assertEqual(len(self.account.transactions), 0)
        self.assertEqual(self.account.balance, 1000.0)  # Balance unchanged
    
    def test_withdraw_negative_amount(self):
        with self.assertRaises(ValueError) as context:
            self.account.withdraw(-100.0)
        self.assertEqual(str(context.exception), "Withdrawal amount must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    def test_withdraw_zero_amount(self):
        with self.assertRaises(ValueError) as context:
            self.account.withdraw(0)
        self.assertEqual(str(context.exception), "Withdrawal amount must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    @patch("__main__.get_share_price", return_value=100.0)
    def test_buy_shares_sufficient_funds(self, mock_get_price):
        initial_balance = self.account.balance
        self.account.buy_shares("AAPL", 5)
        
        self.assertEqual(self.account.balance, initial_balance - 500.0)
        self.assertEqual(self.account.holdings["AAPL"], 5)
        self.assertEqual(len(self.account.transactions), 1)
        self.assertEqual(self.account.transactions[0].type, "buy")
        self.assertEqual(self.account.transactions[0].amount, 500.0)
        self.assertEqual(self.account.transactions[0].symbol, "AAPL")
        self.assertEqual(self.account.transactions[0].quantity, 5)
    
    @patch("__main__.get_share_price", return_value=300.0)
    def test_buy_shares_insufficient_funds(self, mock_get_price):
        with self.assertRaises(ValueError) as context:
            self.account.buy_shares("AAPL", 5)
        self.assertEqual(str(context.exception), "Insufficient funds to complete purchase")
        self.assertEqual(len(self.account.transactions), 0)
        self.assertNotIn("AAPL", self.account.holdings)
    
    def test_buy_shares_negative_quantity(self):
        with self.assertRaises(ValueError) as context:
            self.account.buy_shares("AAPL", -5)
        self.assertEqual(str(context.exception), "Quantity must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    def test_buy_shares_zero_quantity(self):
        with self.assertRaises(ValueError) as context:
            self.account.buy_shares("AAPL", 0)
        self.assertEqual(str(context.exception), "Quantity must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    @patch("__main__.get_share_price", side_effect=ValueError("Unknown symbol UNKNOWN"))
    def test_buy_shares_unknown_symbol(self, mock_get_price):
        with self.assertRaises(ValueError) as context:
            self.account.buy_shares("UNKNOWN", 5)
        self.assertEqual(str(context.exception), "Unknown symbol UNKNOWN")
    
    @patch("__main__.get_share_price", return_value=100.0)
    def test_buy_shares_existing_holdings(self, mock_get_price):
        # Buy initial shares
        self.account.buy_shares("AAPL", 5)
        self.assertEqual(self.account.holdings["AAPL"], 5)
        
        # Buy more shares
        self.account.buy_shares("AAPL", 3)
        self.assertEqual(self.account.holdings["AAPL"], 8)
        self.assertEqual(len(self.account.transactions), 2)
    
    @patch("__main__.get_share_price", return_value=100.0)
    def test_sell_shares_success(self, mock_get_price):
        # First buy some shares
        self.account.buy_shares("AAPL", 10)
        initial_balance = self.account.balance
        
        # Then sell some
        self.account.sell_shares("AAPL", 3)
        
        self.assertEqual(self.account.balance, initial_balance + 300.0)
        self.assertEqual(self.account.holdings["AAPL"], 7)
        self.assertEqual(len(self.account.transactions), 2)
        
        # Check the sell transaction
        sell_transaction = self.account.transactions[1]
        self.assertEqual(sell_transaction.type, "sell")
        self.assertEqual(sell_transaction.amount, 300.0)
        self.assertEqual(sell_transaction.symbol, "AAPL")
        self.assertEqual(sell_transaction.quantity, 3)
    
    @patch("__main__.get_share_price", return_value=100.0)
    def test_sell_shares_all_holdings(self, mock_get_price):
        # Buy 5 shares
        self.account.buy_shares("AAPL", 5)
        initial_balance = self.account.balance
        
        # Sell all 5 shares
        self.account.sell_shares("AAPL", 5)
        
        self.assertEqual(self.account.balance, initial_balance + 500.0)
        self.assertNotIn("AAPL", self.account.holdings)  # Holdings should be removed
        self.assertEqual(len(self.account.transactions), 2)
    
    @patch("__main__.get_share_price", return_value=100.0)
    def test_sell_shares_insufficient_holdings(self, mock_get_price):
        # Buy 5 shares
        self.account.buy_shares("AAPL", 5)
        
        # Try to sell 10 shares (too many)
        with self.assertRaises(ValueError) as context:
            self.account.sell_shares("AAPL", 10)
        self.assertEqual(str(context.exception), "Not enough shares to sell")
        self.assertEqual(self.account.holdings["AAPL"], 5)  # Holdings unchanged
        self.assertEqual(len(self.account.transactions), 1)  # Only the buy transaction
    
    def test_sell_shares_no_holdings(self):
        with self.assertRaises(ValueError) as context:
            self.account.sell_shares("AAPL", 5)
        self.assertEqual(str(context.exception), "Not enough shares to sell")
        self.assertEqual(len(self.account.transactions), 0)
    
    def test_sell_shares_negative_quantity(self):
        with self.assertRaises(ValueError) as context:
            self.account.sell_shares("AAPL", -5)
        self.assertEqual(str(context.exception), "Quantity must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    def test_sell_shares_zero_quantity(self):
        with self.assertRaises(ValueError) as context:
            self.account.sell_shares("AAPL", 0)
        self.assertEqual(str(context.exception), "Quantity must be positive")
        self.assertEqual(len(self.account.transactions), 0)
    
    @patch("__main__.get_share_price", return_value=150.0)
    def test_get_portfolio_value_no_holdings(self, mock_get_price):
        self.assertEqual(self.account.get_portfolio_value(), 1000.0)  # Just cash balance
    
    @patch("__main__.get_share_price", side_effect=[150.0, 150.0, 700.0])
    def test_get_portfolio_value_with_holdings(self, mock_get_price):
        # Buy some shares
        self.account.buy_shares("AAPL", 2)  # Cost: 300, remaining balance: 700
        self.account.buy_shares("TSLA", 1)  # Cost: 700, remaining balance: 0
        
        # With mock prices, portfolio value should be:
        # Cash: 0 + Holdings: (150 * 2) + (700 * 1) = 300 + 700 = 1000
        value = self.account.get_portfolio_value()
        self.assertEqual(value, 1000.0)
    
    @patch("__main__.get_share_price", side_effect=[100.0, 200.0])
    def test_get_profit_loss(self, mock_get_price):
        # Buy shares that double in value (in our mock)
        self.account.buy_shares("AAPL", 5)  # Cost: 500, remaining balance: 500
        
        # Mock price changes to 200 (doubling holdings value)
        profit = self.account.get_profit_loss()
        
        # Portfolio is now: Cash (500) + Holdings (200 * 5 = 1000) = 1500
        # Profit = 1500 - 1000 = 500
        self.assertEqual(profit, 500.0)
    
    def test_get_holdings(self):
        # Test empty holdings
        self.assertEqual(self.account.get_holdings(), {})
        
        # Add some holdings
        self.account.holdings["AAPL"] = 5
        self.account.holdings["TSLA"] = 2
        
        holdings = self.account.get_holdings()
        self.assertEqual(holdings, {"AAPL": 5, "TSLA": 2})
        
        # Ensure it's a copy (not reference)
        holdings["GOOGL"] = 10
        self.assertNotIn("GOOGL", self.account.holdings)
    
    def test_get_transactions(self):
        # Test empty transactions
        self.assertEqual(self.account.transactions, [])
        
        # Add some transactions
        self.account.deposit(100)
        self.account.withdraw(50)
        
        transactions = self.account.get_transactions()
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].type, "deposit")
        self.assertEqual(transactions[1].type, "withdrawal")
        
        # Ensure it's a copy (not reference)
        transactions.append(Transaction("test", 0))
        self.assertEqual(len(self.account.transactions), 2)


class TestTransaction(unittest.TestCase):
    def test_transaction_creation_minimal(self):
        tx = Transaction("deposit", 100.0)
        self.assertEqual(tx.type, "deposit")
        self.assertEqual(tx.amount, 100.0)
        self.assertIsNone(tx.symbol)
        self.assertIsNone(tx.quantity)
    
    def test_transaction_creation_with_symbol_and_quantity(self):
        tx = Transaction("buy", 500.0, "AAPL", 5)
        self.assertEqual(tx.type, "buy")
        self.assertEqual(tx.amount, 500.0)
        self.assertEqual(tx.symbol, "AAPL")
        self.assertEqual(tx.quantity, 5)
    
    def test_transaction_creation_with_symbol_only(self):
        tx = Transaction("sell", 300.0, "TSLA")
        self.assertEqual(tx.type, "sell")
        self.assertEqual(tx.amount, 300.0)
        self.assertEqual(tx.symbol, "TSLA")
        self.assertIsNone(tx.quantity)
    
    def test_transaction_repr(self):
        # Deposit transaction
        tx1 = Transaction("deposit", 100.0)
        expected1 = "Transaction(deposit, 100.00)"
        self.assertEqual(repr(tx1), expected1)
        
        # Buy transaction with symbol and quantity
        tx2 = Transaction("buy", 500.0, "AAPL", 5)
        expected2 = "Transaction(buy, 500.00,symbol=AAPL,qty=5)"
        self.assertEqual(repr(tx2), expected2)
        
        # Transaction with symbol only
        tx3 = Transaction("sell", 300.0, "TSLA")
        expected3 = "Transaction(sell, 300.00,symbol=TSLA)"
        self.assertEqual(repr(tx3), expected3)
    
    def test_transaction_amount_conversion(self):
        tx = Transaction("deposit", 100)  # Integer input
        self.assertIsInstance(tx.amount, float)
        self.assertEqual(tx.amount, 100.0)


class TestGetSharePrice(unittest.TestCase):
    def test_get_share_price_known_symbols(self):
        self.assertEqual(get_share_price("AAPL"), 150.0)
        self.assertEqual(get_share_price("TSLA"), 700.0)
        self.assertEqual(get_share_price("GOOGL"), 2800.0)
    
    def test_get_share_price_unknown_symbol(self):
        with self.assertRaises(ValueError) as context:
            get_share_price("UNKNOWN")
        self.assertEqual(str(context.exception), "Unknown symbol UNKNOWN")
    
    def test_get_share_price_case_sensitivity(self):
        # Test that symbols are case sensitive
        with self.assertRaises(ValueError) as context:
            get_share_price("aapl")  # lowercase should fail
        self.assertEqual(str(context.exception), "Unknown symbol aapl")


if __name__ == '__main__':
    unittest.main(verbosity=2)