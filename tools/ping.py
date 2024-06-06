import requests
import time

st = time.time()
r = requests.post('https://api.telegram.org')
print(round(time.time() - st, 3), r)