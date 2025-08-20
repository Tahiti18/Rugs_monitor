import os
import sqlite3
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./rugs.db")

def load_df():
    with sqlite3.connect(DB_PATH) as c:
        df = pd.read_sql_query("SELECT round_id, timestamp, bust_multiplier FROM rounds ORDER BY id ASC", c)
    return df

def simulate(df, base_bet=1.0, strategy="fixed", target=2.0, bankroll=1000.0, max_steps=10000):
    bal = bankroll
    bet = base_bet
    bets = 0
    for mult in df['bust_multiplier'].values[:max_steps]:
        # Bet placed every round for simplicity; plug your entry filter here.
        if strategy == "fixed":
            stake = base_bet
        elif strategy == "martingale":
            stake = bet
        else:
            stake = base_bet

        # Outcome: win if multiplier >= target
        win = mult >= target
        if win:
            # typical crash payout is stake*(target-1) minus site edge; we ignore rake and use naive net
            bal += stake*(target-1)
            if strategy == "martingale":
                bet = base_bet
        else:
            bal -= stake
            if strategy == "martingale":
                bet *= 2  # explodes quickly

        bets += 1
        if bal <= 0:
            break
    return dict(final_balance=bal, bets=bets, pnl=bal-bankroll)

if __name__ == "__main__":
    df = load_df()
    if df.empty:
        print("No data yet. Run the scraper first.")
        raise SystemExit(0)

    for strat in ["fixed", "martingale"]:
        res = simulate(df, base_bet=1.0, strategy=strat, target=2.0, bankroll=1000.0)
        print(strat, res)
