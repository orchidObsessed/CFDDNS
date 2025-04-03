# ┌──────────────────────────────────────────────────────────────────
# │ Contibutor(s) : William Waddell (me@folded.dev)
# │ Description. .: Compares the zone's existing A record against
# │               │ the current public IP. If they do not match, the
# │               │ zone is updated.
# │               │ 
# │               │ 
# │               │ 
# ├───────────────┴──────────────────────────────────────────────────
# │ Imports & constants
# └───┐

from urllib.parse import urlencode
from urllib.request import urlopen, Request
from json import dumps, loads
from datetime import datetime
from pathlib import Path
from sys import exit
from os import environ

CLOUDFLARE_API = "https://api.cloudflare.com/client/v4/zones"
TIMEOUT = 30

# ┌──────────────────────────────────────────────────────────────────
# │ Body
# └───┐

def __http_request(
    url: str,
    method: str,
    headers: dict = {},
    data: dict = {},
    params: dict = {}
) -> dict:
    """
    Form and submit an HTTP request.
    
    Parameters
    ----------
    `url` : str
        The full URL of the endpoint.
    `method` : str
        One of `GET`, `PUT`, `POST`, `DELETE`.
    `headers` : dict, optional
        Any headers to include alongside the request.
    `data` : dict, optional
        Any data to include in the body of the request.
    `params` : dict, optional
        Any URL parameters.
    `auth` : tuple, optional
        Optional authentication section.
    
    Returns
    -------
    dict[str: str]
        A dict with keys `status`, `headers`, `content`.
    
    Notes
    -----
     - When no `Content-Type` is specified, the default behaviour is a param-encoded string for `data`.
     - `auth` is always b64-encoded.
    """
    
    # Add params to the URL
    if params:
        url = f"{url}?{urlencode(params)}"
    
    # Build the request
    formed_request = Request(
        url = url,
        method = method.upper(),
        headers = headers if headers else {},
        data = dumps(data).encode() if data else {}
    )
    
    try:
        with urlopen(formed_request, timeout=TIMEOUT) as uo:
            content = uo.read().decode()
            status: int = uo.status
            headers = uo.headers
        return {
            'status': status,
            'headers': headers,
            'content': content
        }
    
    except Exception as e:
        print(f"Unexpected exception during HTTP request: {e.__class__.__name__} at {e.__traceback__.tb_lineno}: {e}")
        exit(1)

def _read_envs() -> tuple[str, str]:
    """
    Read environment information, from a .env file first, and
    environment variables second.
    
    If any key is not found, raise an error and exit.
    
    Returns variables in the order `[key, zone, id]`.
    """
    
    # A trick to get the directory where this file lives
    cwd = Path(*Path(__file__).parts[:-1])
    
    # Check if there is a .env file in that directory
    dotenv = cwd / Path(".env")
    if dotenv.exists() and dotenv.is_file():
        print(f".env file found at {dotenv}")
        
        # Read file, format lines
        with dotenv.open() as fo:
            lines = [l.strip().split('=', 1) for l in fo.readlines()]
        
        # Convert lines to variables
        try: api_key = [l[1] for l in lines if l[0] == "api_key"][0]
        except IndexError as e:
            print(f"Key 'api_key' missing from .env file!")
            exit(1)
        try: zone_name = [l[1] for l in lines if l[0] == "zone_name"][0]
        except IndexError as e:
            print(f"Key 'zone_name' missing from .env file!")
            exit(1)
        try: zone_id = [l[1] for l in lines if l[0] == "zone_id"][0]
        except IndexError as e:
            print(f"Key 'zone_id' missing from .env file!")
            exit(1)
        
        return api_key, zone_name, zone_id
    
    else:
        print(f"No .env file found at {dotenv}, reading environment instead")
        
        try:
            return environ['api_key'], environ['zone_name'], environ['zone_id']
        
        except KeyError as e:
            print(f"Key '{e}' missing from environment variables!")
            exit(1)
    return

def check_public_ip() -> str:
    """
    Finds and returns the public IP as seen by this device.
    
    This is done by sending a GET request to `api.ipify.org`. 
    """
    
    # Do the request
    req = __http_request("https://api.ipify.org", "GET", params={'format': 'json'})
    
    # If 200, parse and return the IP
    if req['status'] == 200:
        ans = loads(req['content'])['ip']
        return ans
    
    # Otherwise, exit
    else:
        print(f"Non-200 response when checking public IP: {req}")
        exit(1)

def check_zone_apex(
    api_key: str,
    name: str,
    zone_id: str
) -> tuple[str, str]:
    """
    Use Cloudflare's API to find the apex record for `zone_id`,
    and return its IP and ID.
    
    To avoid needing to provide the apex record's ID, we use
    the list method, querying for A records whose name is JUST
    the zone's name.
    """
    
    # Complete the URL
    url = f"{CLOUDFLARE_API}/{zone_id}/dns_records"
    
    # Do the request
    req = __http_request(
        url = url,
        method = "GET",
        headers = {"Authorization": f"Bearer {api_key}"},
        params = {"name": name,
                  "type": "A"}
    )
    
    # If 200, return the record content
    if req['status'] == 200:
        ans = loads(req['content'])['result'][0]
        r_ip, r_id = ans['content'], ans['id']
        return r_ip, r_id

    # Otherwise, complain and exit
    else:
        print(f"Got non-200 response: {req}")
        exit(1)

def update_zone_apex(
    api_key: str,
    zone_id: str,
    record_id: str,
    old_ip: str,
    new_ip: str
) -> None:
    """
    Use Cloudflare's API to update the apex record for `zone_id`
    with `new_ip`, and create a comment with the old IP.
    """
    
    # Complete the URL
    url = f"{CLOUDFLARE_API}/{zone_id}/dns_records/{record_id}"
    
    # Get date info
    dstr = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    
    # Do the request
    req = __http_request(
        url = url,
        method = "PATCH",
        headers = {"Authorization": f"Bearer {api_key}",
                   "Content-Type": 'application/json'},
        data = {"comment": f"Updated from {old_ip} on {dstr}",
                "content": new_ip}
    )
    
    # If 200, print and return
    if req['status'] == 200:
        print("Record content and comment updated successfully!")
        return
    
    # Otherwise, complain and exit
    else:
        print(f"Non-200 response while updating record: {req}")
        exit(1)

# ┌──────────────────────────────────────────────────────────────────
# │ Main fencing
# └───┐

if __name__ == "__main__":
    # Get variables
    api_key, name, zone_id = _read_envs()
    print("Found environment variables:")
    print(f"API key: {api_key[:3]}...{api_key[-3:]}")
    print(f"Zone   : {name}")
    print(f"Zone ID: {zone_id[:3]}...{zone_id[-3:]}")
    print(f"{'='*20}\n")
    
    # Get apparent versus recorded IPs
    public_ip = check_public_ip()
    existing_ip, record_id = check_zone_apex(api_key, name, zone_id)

    # If they don't match, update
    if public_ip != existing_ip:
        print(f"IPs do not match (apparent={public_ip} | recorded={existing_ip})")
        update_zone_apex(api_key, zone_id, record_id, existing_ip, public_ip)
        exit(0)
    
    # Otherwise, do nothing
    else:
        print(f"IPs are consistent (apparent={public_ip} | recorded={existing_ip})")
        exit(0)