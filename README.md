# 범용 HTTP API 요청 프록시

클라이언트에서 `proxy_requests` 모듈의 `get`, `post`, `put`, `patch`, `delete`, `head`, `options` 함수를 호출하면, 프록시 서버가 원래 URL로 요청을 보내고 응답을 돌려줍니다. 대상 API에는 프록시 서버의 **외부 송신 IP**가 보입니다. IP allowlist가 있는 여러 API를 사용할 때 서버의 공인 송신 IP를 등록하면 됩니다. IP가 고정되어야 한다면 서버 네트워크에서도 고정 송신 IP를 사용해야 합니다.

> 회사·학교 네트워크의 보안 정책이나 TLS 검사 제한을 우회하기 전에 관리자의 허가를 확인하세요. 이 프록시는 TLS 인증서 검증을 끄지 않으며 HTTPS URL만 허용합니다.

## 프록시 서버 실행

Python 가상환경에서 프로젝트 폴더 기준으로 실행합니다.

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

`runserver`는 개발용입니다. 실제 외부 서비스에는 운영용 WSGI 서버와 HTTPS를 사용하세요.

## 사용할 API 호스트 설정

`config/settings.py`의 `ALLOWED_PROXY_TARGET_HOSTS`에 호출할 API의 **호스트명**을 추가합니다. 기본값은 빈 목록이므로, 호스트를 추가하기 전에는 대상 요청이 거부됩니다. 여러 API를 등록할 수 있습니다.

```python
ALLOWED_PROXY_TARGET_HOSTS = [
	'api.example.com',
	'api.another-service.com',
]
```

호스트명만 등록하며, URL 경로·포트가 아니라 `target_url`의 hostname과 비교됩니다. 등록되지 않은 호스트는 거부됩니다. `'*'`를 넣으면 임의의 HTTPS 호스트로 요청을 보낼 수 있으나, SSRF 및 오픈 프록시 위험이 커지므로 사용하지 않는 것을 권장합니다.

## 클라이언트 사용

`proxy_requests.py`를 클라이언트 프로젝트에 복사하고 `PROXY_SERVER` 환경 변수에 전체 프록시 endpoint를 설정합니다. 클라이언트 환경에도 `requests` 패키지가 필요합니다.

```powershell
$env:PROXY_SERVER = 'https://your-proxy.example/requests/proxy_request/'
```

이후 일반 `requests`와 비슷하게 대상 URL을 직접 지정합니다. 프록시 endpoint로 가는 전송은 내부에서 POST이며, 원래 요청 방식은 JSON envelope를 통해 프록시 서버로 전달됩니다.

```python
import json
import proxy_requests as requests
from proxy_requests import exceptions

response = requests.get(
	'https://api.example.com/v1/items',
	params={'page': 1},
	headers={'Authorization': 'Bearer YOUR_TOKEN'},
	timeout=20,
)
response.raise_for_status()
print(response.json())

response = requests.post(
	'https://api.example.com/v1/items',
	json={'name': 'sample'},
	timeout=20,
)
```

`proxy_requests`는 성공/오류 응답을 자동으로 `raise_for_status()` 하지 않습니다. 필요할 때 직접 호출하세요. 지원 옵션은 `params`, `headers`, `data`, `json`, `cookies`, `auth`, `timeout`이며, 메서드는 GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS입니다. 프록시가 반환하는 객체는 `requests.Response`입니다.

## 보안 및 동작 주의사항

- `ALLOWED_PROXY_CLIENT_IPS = ['*']`이면 누구나 프록시를 호출할 수 있습니다. 외부에 공개할 경우 인증 토큰 검증을 구현하고 방화벽에서도 허용 IP를 제한하세요.
- 허용 대상 호스트를 필요한 API로만 제한하세요. 이 서버를 통해 전달하는 인증 헤더와 API 키는 프록시 서버를 경유합니다.
- 서버는 upstream timeout을 1~60초 범위로 제한합니다. 클라이언트 timeout은 이를 감안해 더 길게 설정하세요.
- 파일 업로드, 스트리밍 업로드, `verify=False` 등은 지원하지 않습니다. 프록시는 TLS 인증서 검증을 유지합니다.
