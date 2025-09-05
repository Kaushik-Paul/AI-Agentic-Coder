import gradio as gr
from accounts import Account, get_share_price

# Global account variable to maintain state
current_account = None

def create_account(initial_balance):
    global current_account
    try:
        current_account = Account("DemoUser", float(initial_balance))
        return f"Account created! Initial balance: ${float(initial_balance):.2f}", update_display()
    except Exception as e:
        return f"Error: {str(e)}", update_display()

def update_display():
    if not current_account:
        return {
            balance_display: "No account created",
            holdings_display: "No holdings",
            portfolio_display: "No portfolio",
            profit_display: "No data",
            transactions_display: "No transactions"
        }
    
    balance_text = f"${current_account.balance:.2f}"
    holdings_text = "\n".join([f"{symbol}: {qty} shares @ ${get_share_price(symbol):.2f}" 
                               for symbol, qty in current_account.holdings.items()]) or "No holdings"
    portfolio_value = current_account.get_portfolio_value()
    profit_loss = current_account.get_profit_loss()
    profit_text = f"${profit_loss:.2f} {'profit' if profit_loss >= 0 else 'loss'}"
    transactions_text = "\n".join([f"{t.type.upper()}: ${t.amount:.2f}" + 
                                  (f" {t.symbol} x{t.quantity}" if t.symbol else "") 
                                  for t in current_account.transactions]) or "No transactions"
    
    return {
        balance_display: balance_text,
        holdings_display: holdings_text,
        portfolio_display: f"${portfolio_value:.2f}",
        profit_display: profit_text,
        transactions_display: transactions_text
    }

def deposit(amount):
    if not current_account:
        return "No account created", update_display()
    try:
        current_account.deposit(float(amount))
        return f"Deposited ${float(amount):.2f}", update_display()
    except Exception as e:
        return f"Error: {str(e)}", update_display()

def withdraw(amount):
    if not current_account:
        return "No account created", update_display()
    try:
        current_account.withdraw(float(amount))
        return f"Withdrew ${float(amount):.2f}", update_display()
    except Exception as e:
        return f"Error: {str(e)}", update_display()

def buy_shares(symbol, quantity):
    if not current_account:
        return "No account created", update_display()
    try:
        current_account.buy_shares(symbol, int(quantity))
        return f"Bought {quantity} {symbol} shares", update_display()
    except Exception as e:
        return f"Error: {str(e)}", update_display()

def sell_shares(symbol, quantity):
    if not current_account:
        return "No account created", update_display()
    try:
        current_account.sell_shares(symbol, int(quantity))
        return f"Sold {quantity} {symbol} shares", update_display()
    except Exception as e:
        return f"Error: {str(e)}", update_display()

# Create Gradio interface
with gr.Blocks(title="Trading Account Demo") as app:
    gr.Markdown("# Trading Account Demo")
    gr.Markdown("Create an account and start trading!")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Account Setup")
            initial_balance = gr.Number(label="Initial Balance", value=1000, precision=2)
            create_btn = gr.Button("Create Account", variant="primary")
            status = gr.Textbox(label="Status", interactive=False)
        
        with gr.Column():
            gr.Markdown("### Account Summary")
            balance_display = gr.Textbox(label="Current Balance", interactive=False)
            holdings_display = gr.Textbox(label="Holdings", interactive=False, lines=3)
            portfolio_display = gr.Textbox(label="Portfolio Value", interactive=False)
            profit_display = gr.Textbox(label="Profit/Loss", interactive=False)
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Account Actions")
            with gr.Row():
                deposit_amount = gr.Number(label="Deposit Amount", value=100, precision=2)
                deposit_btn = gr.Button("Deposit")
            with gr.Row():
                withdraw_amount = gr.Number(label="Withdraw Amount", value=100, precision=2)
                withdraw_btn = gr.Button("Withdraw")
        
        with gr.Column():
            gr.Markdown("### Trading")
            symbol = gr.Dropdown(choices=["AAPL", "TSLA", "GOOGL"], label="Share Symbol")
            quantity = gr.Number(label="Quantity", value=1, precision=0)
            with gr.Row():
                buy_btn = gr.Button("Buy", variant="secondary")
                sell_btn = gr.Button("Sell", variant="secondary")
    
    gr.Markdown("### Transaction History")
    transactions_display = gr.Textbox(label="Transactions", interactive=False, lines=10)
    
    # Set up event handlers
    create_btn.click(create_account, inputs=[initial_balance], outputs=[status, gr.State()]).then(
        lambda: gr.update(), outputs=[status])
    
    deposit_btn.click(deposit, inputs=[deposit_amount], outputs=[status, gr.State()])
    withdraw_btn.click(withdraw, inputs=[withdraw_amount], outputs=[status, gr.State()])
    buy_btn.click(buy_shares, inputs=[symbol, quantity], outputs=[status, gr.State()])
    sell_btn.click(sell_shares, inputs=[symbol, quantity], outputs=[status, gr.State()])

# Launch the app
if __name__ == "__main__":
    app.launch(share=True)