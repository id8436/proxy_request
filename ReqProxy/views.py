import json
import fnmatch
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def proxy_request(request):
    # The client always sends a POST envelope; payload['method'] is the upstream method.
    if request.method != 'POST':
        return JsonResponse({'error': 'Proxy requests must use POST'}, status=405)

    target_url = None
    method = 'GET'
    params = {}
    payload = {}
    if request.method == 'GET':
        target_url = request.GET.get('target_url')
        params = request.GET.copy()
        params.pop('target_url', None)
        params = params.dict()
        payload = {}
        method = 'GET'
    else:
        try:
            payload = json.loads(request.body or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({'error': 'JSON body must be an object'}, status=400)
        target_url = payload.get('target_url')
        method = str(payload.get('method', 'GET')).upper()
        params = payload.get('params', {})

    if not isinstance(target_url, str) or not target_url:
        return JsonResponse({'error': 'target_url is required'}, status=400)

    if method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
        return JsonResponse({'error': 'Unsupported target HTTP method'}, status=400)

    allowed_hosts = [
        str(host).lower() for host in getattr(settings, 'ALLOWED_PROXY_TARGET_HOSTS', [])
    ]
    try:
        parsed_url = urlsplit(target_url)
        hostname = (parsed_url.hostname or '').lower()
        host_is_allowed = any(
            rule == '*' or fnmatch.fnmatchcase(hostname, rule)
            for rule in allowed_hosts
        )
        if (parsed_url.scheme != 'https' or not parsed_url.hostname
                or parsed_url.username or parsed_url.password
                or not host_is_allowed):
            return JsonResponse({'error': 'target_url must use HTTPS and an allowed API host'}, status=400)
    except (AttributeError, TypeError, ValueError):
        return JsonResponse({'error': 'Invalid target_url'}, status=400)

    headers = payload.get('headers', {})
    if not isinstance(headers, dict) or not all(isinstance(key, str) for key in headers):
        return JsonResponse({'error': 'headers must be an object'}, status=400)
    auth = payload.get('auth')
    if isinstance(auth, list):
        if len(auth) != 2 or not all(isinstance(value, str) for value in auth):
            return JsonResponse({'error': 'auth must contain a username and password'}, status=400)
        auth = tuple(auth)
    elif auth is not None:
        return JsonResponse({'error': 'auth must be a two-item list or null'}, status=400)
    headers_to_send = {
        key: value for key, value in headers.items()
        if key.lower() not in ('host', 'content-length', 'transfer-encoding', 'connection', 'accept-encoding')
    }

    try:
        response = requests.request(
            method,
            target_url,
            params=params,
            headers=headers_to_send,
            data=payload.get('data'),
            json=payload.get('json'),
            cookies=payload.get('cookies'),
            auth=auth,
            timeout=min(max(float(payload.get('timeout', 15)), 1), 60),
            stream=True,
            allow_redirects=False,
        )

        excluded_headers = {'content-encoding', 'transfer-encoding', 'content-length', 'connection'}
        response_headers = {
            key: value for key, value in response.headers.items()
            if key.lower() not in excluded_headers
        }
        response_headers.setdefault('Content-Type', 'application/octet-stream')

        def generate_content():
            try:
                yield from response.iter_content(chunk_size=8192)
            finally:
                response.close()

        return StreamingHttpResponse(
            generate_content(),
            status=response.status_code,
            headers=response_headers,
        )
    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'Proxy request timed out'}, status=408)
    except requests.exceptions.RequestException as exc:
        return JsonResponse({'error': f'Upstream request failed: {exc}'}, status=502)
    except (TypeError, ValueError) as exc:
        error = {'error': 'Invalid request options'}
        if settings.DEBUG:
            error['detail'] = str(exc)
        return JsonResponse(error, status=400)
