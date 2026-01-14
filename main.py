
from fastapi import FastAPI, HTTPException
from collections import OrderedDict
import csv
from datetime import datetime

import logging
import math
from fastapi import Query, HTTPException
from typing import Literal

app = FastAPI(title="REST API")

TRANSACTIONS_FILE = "transactions.csv"
FX_FILE = "fx_rates.csv"

transactions = []
fx_rates = []

# loader functions --------------------------------------------------------------------
def load_transactions():
    global transactions
    transactions = []
    valid_count = 0

    try:
        with open(TRANSACTIONS_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row["transaction_id"] = int(row["transaction_id"])
                    row["user_id"] = int(row["user_id"])
                    row["amount"] = float(row["amount"])
                    transactions.append(row)
                    valid_count += 1
                except (ValueError, KeyError):
                    # Skip bad rows but continue
                    continue
        return valid_count
    except FileNotFoundError:
        print(f"File {TRANSACTIONS_FILE} not found")
        return 0
    except Exception as e:
        print("Error loading transactions:", e)
        return 0


def load_fx_rates():
    global fx_rates
    fx_rates = []

    with open(FX_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            fx_rates.append(row)

    # Set currencies dynamically (exclude 'date')
    #if fx_rates:
        #CURRENCIES = [col for col in fx_rates[0].keys() if col.lower() != "date"]

    return len(fx_rates)

# app startup --------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    load_transactions()
    load_fx_rates()


# Helper functions ---------------------------------------------------------------------
def read_transactions():
    with open(TRANSACTIONS_FILE, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)

def read_fx_rates():
    with open(FX_FILE, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)

def get_fx_rate_for_date(currency, date_str):
    fx_list = read_fx_rates()
    for row in fx_list:
        if row["date"] == date_str:
            return float(row.get(currency, 1))
    return 1  # Default 1 if not found


# Load currencies from fx_rates.csv ----------------------------------------------------
def get_currencies():
    with open("fx_rates.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)#, delimiter=";")
        first_row = next(reader)
        # Skip the 'date' column
        return [col for col in first_row.keys() if col.lower() != "date"]

CURRENCIES = get_currencies()

# Root endpoint
"""@app.get("/")
def root():
    return {
        "message": "Transactions API is running!",
        "endpoints": {
            "Total amount spent by the user": "/users/{user_id}/total",
            "Average Transaction Amount": "/stats/average",
            "Daily totals": "/stats/daily",
            "Users with total transaction amounts in 90th percentile": "/stats/whales",
            "Admin Reload": "/admin/reload"
        }
    }"""

# 1 ************************************************ total amount spent by user ****************************************************************
@app.get("/users/{user_id}/total")
def get_total_amount_spent_by_user(
    currency: str = Query(..., description="Select currency", enum=CURRENCIES)
    ):
 
    amounts = read_transactions()  # your function

    if not amounts:
        raise HTTPException(status_code=404, detail="No transactions found")

    user_map = {}

    for tr in amounts:
        if tr.get("currency") != currency:
            continue  # skip other currencies

        user_id = tr.get("user_id")
        amount = tr.get("amount")

        # skip invalid data
        if not user_id or amount in ("", None):
            continue

        try:
            user_id = int(user_id)
            amount = float(amount)
        except ValueError:
            continue  # skip invalid entries

        if user_id in user_map:
            user_map[user_id] += amount
        else:
            user_map[user_id] = amount

    if not user_map:
        raise HTTPException(status_code=404, detail="No valid transactions found")

    totals = list(user_map.values())

    return {"amount": totals }


# 2 ************************************************ average ****************************************************************
@app.get("/stats/average")
def get_average_transaction_amount(
    #currency:  Literal["USD", "EUR", "GBP", "JPY"] = Query(..., description="Select currency")
    currency: str = Query(..., description="Select currency", enum=CURRENCIES)
):

    transactions = read_transactions()

    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found")

    transaction_count = 0
    total_transaction_amount = 0.0

    for tr in transactions:
        if tr.get("currency") != currency:
            continue  # skip other currencies

        amount = tr.get("amount")
        if amount is None or amount == "":
            continue

        try:
            transaction_count += 1
            total_transaction_amount += float(amount)
        except ValueError:
            continue  # skip malformed values

    if transaction_count == 0:
        raise HTTPException(status_code=404, detail=f"No transactions found for currency {currency}")

    average = total_transaction_amount / transaction_count

    return {
        #"currency": currency,
        "amount": average
        #"transaction_count": transaction_count
    }


# 3 ************************************************ daily totals ****************************************************************
@app.get("/stats/daily")
def get_daily_totals(
    currency: str = Query(..., description="Select currency", enum=CURRENCIES)
    ):

    transactions = read_transactions()

    # debug
    """debug_rows = []

    for tr in transactions[:5]:
        debug_rows.append({
            "raw": tr,
            "time_stamp": tr.get("time_stamp"),
            "amount": tr.get("amount")
        })


    return debug_rows"""

    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found")

    daily_totals = {}

    for tr in transactions:
        if tr.get("currency") != currency:
            continue  # skip other currencies

        timestamp_str = tr.get("timestamp")
        amount = tr.get("amount")

        if not timestamp_str or amount in ("", None):
            continue

        try:
            amount = float(amount)
            date_str = datetime.fromisoformat(timestamp_str).date().isoformat()
        except ValueError:
            continue

        daily_totals[date_str] = daily_totals.get(date_str, 0.0) + amount

    if not daily_totals:
        raise HTTPException(status_code=404, detail="No valid transactions found")

    return {"daily_totals": daily_totals}

# 4 ************************************************ stats ****************************************************************
@app.get("/stats/whales")
def get_90th_percentile(
    currency: str = Query(..., description="Select currency", enum=CURRENCIES)
):
    transactions = read_transactions()

    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found")

    user_totals = {}

    # 1 Sum total amount per user
    for tr in transactions:
        if tr.get("currency") != currency:
            continue  # skip other currencies

        user_id = tr.get("user_id")
        amount = tr.get("amount")

        if not user_id or amount in ("", None):
            continue

        try:
            user_id = int(user_id)
            amount = float(amount)
        except ValueError:
            continue

        user_totals[user_id] = user_totals.get(user_id, 0.0) + amount

    if not user_totals:
        raise HTTPException(status_code=404, detail="No valid transactions found")

    # 2 Calculate 90th percentile threshold
    totals_sorted = sorted(user_totals.values())
    index = math.ceil(0.9 * len(totals_sorted)) - 1
    percentile_90 = totals_sorted[index]

    # 3 Select users in the 90th percentile
    user_ids = []
    total_amounts = []

    for user_id, total in user_totals.items():
        if total >= percentile_90:
            user_ids.append(user_id)
            total_amounts.append(total)

    return {
        "user_ids": user_ids,
        "total_amounts": total_amounts
    }

# 5 ************************************************ admin reload ****************************************************************
@app.post("/admin/reload")
def reload_data():
    try:
        tx_count = load_transactions()
        fx_count = load_fx_rates()

        return {
            "status": "success",
            "transactions_loaded": tx_count,
            "fx_rates_loaded": fx_count,
            "timestamp": datetime.utcnow().isoformat(),
            #"currencies": CURRENCIES
        }

        # Reload currencies from updated fx_rates.csv
        CURRENCIES = get_currencies()

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }




