import sys
import requests

# pull index 1 form command line to enter argument
for s in sys.argv[1]:
        try:
                # pull bitcoin website with api for data
            response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
                # Once we get the data from the search, then mine down to the current rate of value for bitcoin in real time
            value = response.json()['bpi']['USD']['rate_float']
                # Take user bitcoin amount and calculate it
            bitcoin = float(sys.argv[1]) * value 
                # Format the users data to currencey format
            print(f'${bitcoin:,.4f}')
                # Format the user
        except requests.RequestException:
                sys.exit()

