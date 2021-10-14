import requests
import json
import os
import time
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# TODO: Make sure that you have a STOCK_DATABASE_ID environment variable set
STOCK_DATABASE_ID = os.getenv('STOCK_DATABASE_ID', '')
# TODO: Make sure that you have a NOTION_SECRET environment variable set
NOTION_TOKEN = os.getenv('NOTION_SECRET', '')
# TODO: Make sure that you have a YAHOO_ACCESS_KEY environment variable set
YAHOO_ACCESS_KEY = os.getenv('YAHOO_ACCESS_KEY', '')


TITLE = 'Name'  # Your column name
AMOUNT = 'Amount'
CURRENT_VALUE = 'Current Price of 1 Stock'

# This is where we keep the Current Price of 1 Stock of each ticker
ticker_current_value_map = {}
# This is where we keep the ticker of each page
page_id_ticker_map = {}


def get_rows(database_id: str):  # Get all the rows of the database
    has_more = True
    rows = []
    next_cursor = None

    # Notion uses "Pagination", which is a technique to split large amounts of data into smaller chunks.
    # Each requests has a has_more attribute which indicates if there are more pages to be fetched.
    # The next_cursor variable is the cursor for the next page.
    # More information about pagination: https://developers.notion.com/reference/pagination
    while has_more:

        # In the first iteration we don't have a cursor, so we don't pass it as a parameter
        if next_cursor is not None:
            params = {'start_cursor': next_cursor}
        else:
            params = {}

        # The actual API request
        response = requests.post('https://api.notion.com/v1/databases/{}/query'.format(database_id), params, headers={
            'Authorization': 'Bearer '+NOTION_TOKEN, 'Notion-Version': '2021-08-16'})

        # If the request was not successful, we print the error and return the row array
        if not response.ok:
            print('Error:', response.status_code)
            print('Error:', response.content)
            return rows

        # Parse the response as JSON
        data = response.json()
        # Extract has_more and next_cursor attributes
        has_more = data['has_more']
        next_cursor = data['next_cursor']

        # Extend our row array with the new results
        rows.extend(data['results'])

        # If you want to see the complete response, uncomment the following line
        # print(json.dumps(data, indent=4))

    return rows


def get_yahoo_quotes(ticker: str):  # Get the current market value of the stock
    url = "https://yfapi.net/v6/finance/quote"
    querystring = {"symbols": ticker, "lang": "en", "region": "IN"}
    headers = {
        'x-api-key': YAHOO_ACCESS_KEY,
    }

    response = requests.request(
        "GET", url, headers=headers, params=querystring)

    if not response.ok:
        return 0

    data = response.json()
    # If the response is empty, return 0
    if len(data['quoteResponse']) == 0:
        return 0
    # If you want to see the complete response, uncomment the following line
    # print(json.dumps(data, indent=4))

    return data['quoteResponse']['result']


# Initialise the ticker_current_value_map and ticker_current_value_map maps
def initialise_values_of_maps(rows: list):
    for row in rows:
        # If you change the column type, you need to update this line
        ticker_value = row['properties'][TITLE]['title'][0]['text']['content']
        current_value = row['properties'][CURRENT_VALUE]['number']
        if current_value == None:
            current_value = row['properties'][AMOUNT]['rollup']['number']
        ticker_current_value_map[ticker_value] = current_value
        page_id_ticker_map[row['id']] = ticker_value
        # print(ticker_value, current_value)


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def get_all_quotes():  # Get the current market value of all the tickers
    ticker = ""
    current_value = []
    i = 0
    # Yahoo Finance API has a limit of 10 tickers per request
    for ticker_value in chunker(list(ticker_current_value_map.keys()), 10):
        for value in ticker_value:
            ticker = ticker + value + ".NS,"

        ticker = ticker[:-1]
        # print(ticker)
        # Get the current market value of the stock
        current_value = current_value + get_yahoo_quotes(ticker)
        ticker = ""

    # print(json.dumps(current_value, indent=4))
    return current_value


def update_ticker_current_value_map():  # Update the ticker_current_value_map to latest quotes
    latest_quotes = get_all_quotes()
    for i in range(len(latest_quotes)):
        ticker_current_value_map[list(ticker_current_value_map.keys())[
            i]] = latest_quotes[i]['regularMarketPrice']
        # If you want to see the latest quote of the tickers, uncomment the following line
        # print(list(ticker_current_value_map.keys())
        #       [i], latest_quotes[i]['regularMarketPrice'])


# update the current market value of a stock
def update_current_value_of_1_stock(page_id: str):
    # Payload for the API request
    payload = {
        'properties': {
            'Current Price of 1 Stock': {
                'number': ticker_current_value_map[page_id_ticker_map[page_id]]
            },
        },
    }
    # The actual API request
    # Read more about updating pages: https://developers.notion.com/reference/patch-page
    response = requests.patch('https://api.notion.com/v1/pages/{}'.format(page_id), json=payload, headers={
        'Authorization': 'Bearer '+NOTION_TOKEN, 'Notion-Version': '2021-08-16'})

    # Something failed:(
    # You could try to handle the error better
    if not response.ok:
        print('Error:', response.status_code)
        print('Error:', response.content)


# Update all the current market value of all the tickers
def update_all_current_values(rows: list):
    for row in rows:
        page_id = row['id']
        update_current_value_of_1_stock(page_id)


if __name__ == '__main__':
    # Id of your Database. Looks like this: f1f5071d-8d2a-47aa-9ddc-02b8aad3f6bc
    # Use list_databases.py to get the id of your database
    # Your database should look like this: https://safelyy.notion.site/f1f5071d8d2a47aa9ddc02b8aad3f6bc
    # You can duplicate it, create one manually or try to create one with the API. See create_database.py for an example!

    database_id = STOCK_DATABASE_ID
    # Get all rows from the database
    rows = get_rows(database_id)

    # The initial mapping of page_id to category, we don't update the cover here
    initialise_values_of_maps(rows)
    # Get the current market value of all stocks
    update_ticker_current_value_map()
    # Update the current market value of all stocks in the database
    update_all_current_values(rows)
