import requests
import json
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt # CSRF 보호 비활성화 (개발/테스트용)
from django.conf import settings
import ipaddress

@csrf_exempt # CSRF 보호 비활성화 (개발/테스트용)
def proxy_request(request):
    # 1. 요청 검증
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    # 2. 클라이언트 IP 검증 (Whitelist)
    # 클라이언트 IP 가져오기 (X-Forwarded-For 헤더 고려)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.META.get('REMOTE_ADDR')

    allowed_ips = getattr(settings, 'ALLOWED_PROXY_CLIENT_IPS', ['*'])

    if '*' not in allowed_ips:
        is_allowed = False
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            for allowed_ip in allowed_ips:
                if '*' in allowed_ip:
                    # CIDR notation 지원 (예: 192.168.1.0/24)
                    if '/' in allowed_ip:
                        network = ipaddress.ip_network(allowed_ip)
                        if client_ip_obj in network:
                            is_allowed = True
                            break
                    elif client_ip == allowed_ip:
                        is_allowed = True
                        break
                else:
                    if client_ip == allowed_ip:
                        is_allowed = True
                        break
        except ValueError:
            is_allowed = False

        if not is_allowed:
            return JsonResponse({'error': f'Access denied from IP: {client_ip}'}, status=403)

    # 3. 요청 페이로드 파싱
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    # 4. 외부 API 요청 준비
    try:
        params = payload.get('params', {})
        headers = payload.get('headers', {})
        
        # 헤더 정리: 프록시 전달 시 충돌을 일으킬 수 있는 헤더 제거
        headers_to_send = headers.copy()
        for key in list(headers_to_send.keys()):
            if key.lower() in ('content-type', 'accept-encoding', 'transfer-encoding', 'content-length'):
                del headers_to_send[key]
        
        # 압축 요청 방지 (프록시에서 압축된 데이터를 처리하기 어렵기 때문)
        headers_to_send['Accept-Encoding'] = 'identity'

        data = payload.get('data')
        json_data = payload.get('json')
        cookies = payload.get('cookies', {})
        timeout = payload.get('timeout', None)
        auth = payload.get('auth')
        
        # auth가 리스트로 들어올 경우 튜플로 변환 (requests.request 요구사항)
        if auth and isinstance(auth, list):
            auth = tuple(auth)

        # 5. 외부 API 요청 실행
        # stream=True를 사용하여 대용량 응답도 효율적으로 처리할 수 있도록 함
        response = requests.request(
            method,
            target_url,
            params=params,
            headers=headers_to_send,
            data=data,
            json=json_data,
            cookies=cookies,
            auth=auth,
            timeout=timeout,
            stream=True
        )

        # 6. 응답 처리
        # 응답 헤더 정리: 프록시 응답 시 충돌을 일으킬 수 있는 헤더 제거
        response_headers = dict(response.headers)
        for key in list(response_headers.keys()):
            if key.lower() in ('content-encoding', 'transfer-encoding', 'content-length'):
                del response_headers[key]

        # StreamingHttpResponse를 사용하여 응답 데이터를 스트리밍 방식으로 전달
        def generate_content():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        return StreamingHttpResponse(
            generate_content(),
            content_type=response_headers.get('Content-Type', 'application/octet-stream'),
            status=response.status_code,
            headers=response_headers
        )

    except requests.exceptions.Timeout:
        return JsonResponse({'error': '프록시 요청 시간 초: Timeout'}, status=408)
    except requests.exceptions.ConnectionError:
        return JsonResponse({'error': '프록시 연결 오류: Connection Error'}, status=502)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f"프록���에서 외부 요청 실패: {e}"}, status=502)
    except Exception as e:
        return JsonResponse({'error': f"프록시에서 기타 예외 발생: {e}"}, status=500)
