"""Small requests-compatible client wrapper for the Django API proxy.

Set PROXY_SERVER to the full proxy endpoint, for example:
https://proxy.example/requests/proxy_request/
"""

import os

import requests
from requests import exceptions

__all__ = ['exceptions', 'request', 'get', 'post', 'put', 'patch', 'delete', 'head', 'options']


proxy_url = os.environ.get('PROXY_SERVER')
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
    response = requests.post(
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


