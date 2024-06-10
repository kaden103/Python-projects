import sys
import requests

# pull index 1 form command line to enter argument
for s in sys.argv[1]:
        try:#pull bitcoin website with api for data
            response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
            value = response.json()['bpi']['USD']['rate_float']#once we get data mine down to the current rate of value for bitcoin in real time
            bitcoin = float(sys.argv[1]) * value #take user bitcoin amount and calculate it
            print(f'${bitcoin:,.4f}')#format the user
        except requests.RequestException:
                sys.exit()

