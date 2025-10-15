#!/usr/bin/env python3
import requests
import pandas as pd
import json

url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
print("Fetching data from:", url)

response = requests.get(url)
print("Status code:", response.status_code)

if response.status_code != 200:
    print("Error response:", response.text)
    exit(1)

data = response.json()
print("Number of items:", len(data))

print("First item keys:", list(data[0].keys())[:10])  # Show first 10 keys
