"""Small requests-compatible client wrapper for the Django API proxy.

Set PROXY_SERVER to the full proxy endpoint, for example:
https://proxy.example/requests/proxy_request/
"""
# 프록시에서 url만 정확하게 지정한다. https://proxy.example/requests/proxy_request/ 형태로.
# import os
# proxy_url = os.environ.get('PROXY_SERVER')
proxy_url = 'http://100.74.225.97:8000/requests/proxy_request/'
# 사용처에선 import proxy_requests as requests 형식으로 임포트 해서 사용한다.

import requests as _real_requests
from requests import exceptions

__all__ = ['exceptions', 'request', 'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'requests']


_SUPPORTED_OPTIONS = {
    'params', 'headers', 'data', 'json', 'cookies', 'auth', 'timeout',
}

def request(method, url, **kwargs):
    if not proxy_url:
        raise RuntimeError('Set the PROXY_SERVER environment variable to the proxy endpoint')

    unsupported = set(kwargs) - _SUPPORTED_OPTIONS
    if unsupported:
        names = ', '.join(sorted(unsupported))
        raise TypeError(f'Unsupported requests option(s) for proxy: {names}')

    upstream_timeout = kwargs.get('timeout', 15)
    if not isinstance(upstream_timeout, (int, float)) or isinstance(upstream_timeout, bool):
        raise TypeError('Proxy timeout must be a number of seconds')

    payload = {
        'target_url': url,
        'method': method.upper(),
        **kwargs,
    }
    # Allow time for the upstream request plus the proxy-to-client round trip.
    response = _real_requests.post(
        proxy_url,
        json=payload,
        timeout=max(float(upstream_timeout), 1) + 10,
    )
    return response


def get(url, **kwargs):
    return request('GET', url, **kwargs)


def post(url, data=None, json=None, **kwargs):
    return request('POST', url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    return request('PUT', url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    return request('PATCH', url, data=data, **kwargs)


def delete(url, **kwargs):
    return request('DELETE', url, **kwargs)


def head(url, **kwargs):
    return request('HEAD', url, **kwargs)


def options(url, **kwargs):
    return request('OPTIONS', url, **kwargs)



def _run_diagnostics():
    """프록시 연결과 GET/JSON/form 요청 전달을 점검한다."""
    tests = [
        (
            'GET + params',
            lambda: get(
                'https://httpbin.org/get',
                params={'check': 'proxy'},
                headers={'Accept': 'application/json'},
            ),
        ),
        (
            'POST + JSON',
            lambda: post(
                'https://httpbin.org/post',
                json={'check': 'proxy', 'value': 123},
            ),
        ),
        (
            'POST + form data',
            lambda: post(
                'https://httpbin.org/post',
                data={'check': 'proxy', 'value': 'form'},
            ),
        ),
    ]

    for label, send_request in tests:
        print(f'=== {label} ===')
        try:
            response = send_request()
            print(f'HTTP {response.status_code}')
            response.raise_for_status()
            try:
                print(response.json())
            except ValueError:
                print(response.text)
        except exceptions.RequestException as error:
            print(f'Request failed: {error}')
            if error.response is not None:
                print(f'Proxy response: {error.response.text}')


if __name__ == '__main__':
    _run_diagnostics()
    # Simple demo: perform a GET request via the proxy wrapper
    # This will internally send a POST to the proxy server.

    # 사용처에선 다음과 같은 방식으로.
    import proxy_requests as requests
    try:
        response = requests.get('https://httpbin.org/get', params={'demo': 'proxy'})
        print(f'HTTP {response.status_code}')
        print('Response JSON:', response.json())
    except Exception as e:
        print('Error during demo request:', e)


class _ProxyRequests:
    """A thin wrapper that forwards HTTP method calls to the proxy.
    
    This allows 'from proxy_requests import requests' to work as a drop-in replacement.
    """
    def __getattr__(self, name):
        if name in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
            return lambda url, **kwargs: request(name.upper(), url, **kwargs)
        return getattr(_real_requests, name)

# Expose the wrapper as ``requests`` for convenient import
requests = _ProxyRequests()
