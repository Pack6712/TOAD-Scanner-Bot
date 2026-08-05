import json
import urllib.request
import urllib.error

from config import ADMIN_SECRET


data = json.dumps({
    "secret": ADMIN_SECRET
}).encode("utf-8")


request = urllib.request.Request(
    "http://127.0.0.1:8001/api/admin/login",
    data=data,
    headers={
        "Content-Type": "application/json"
    },
    method="POST",
)


try:
    response = urllib.request.urlopen(request)

    print("STATUS:", response.status)
    print("BODY:", response.read().decode())

except urllib.error.HTTPError as error:
    print("STATUS:", error.code)
    print("BODY:", error.read().decode())

except Exception as error:
    print("ERROR:", repr(error))
