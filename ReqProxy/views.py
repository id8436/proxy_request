import requests
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt # CSRF 보호 비활성화 (개발/테스트용)

@csrf_exempt # CSRF 보호 비활성화 (개발/테스트용)
def proxy_request(request):
    # 1. 요청 검증
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    # 2. 요청 페이로드 파싱
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    # 3. 필수 파라미터 검증
    target_url = payload.get('target_url')
    method = payload.get('method', 'GET').upper()  # 기본값은 GET

    if not target_url:
        return JsonResponse({'error': 'target_url is required'}, status=400)

    # 4. 외부 API 요청
    try:
        # 4.1. 요청 파라미터 준비
        params = payload.get('params', {})
        # 헤더 정리. Requests가 data나 json 파라미터를 보고 Content-Type을 자동으로 설정해서 충돌함;
        # 헤더 정리
        headers = payload.get('headers', {})
        headers_to_send = headers.copy()
        for key in list(headers_to_send.keys()):
            if key.lower() in ('content-type', 'accept-encoding'):
                del headers_to_send[key]
        # 압축 요청 방지
        headers_to_send['Accept-Encoding'] = 'identity'

        data = payload.get('data')
        json_data = payload.get('json')

        # 4.2. 요청
        response = requests.request(
            method,
            target_url,
            params=params,
            headers=headers_to_send,
            data=data,  # form-data
            json=json_data,  # json data
            stream=False
        )
        response.raise_for_status()  # HTTP 에러 발생 시 예외 발생

        # 5. 응답 스트리밍
        #   - 대용량 파일 전송에 적합
        #   - Transfer-Encoding: chunked 방식으로 응답
        content = response.content  # gzip 압축 이미 해제된 바이너리. 압축된 상태에선 이상하게 전달이 안된다;;
        # Content-Type 중복 제거
        response_headers = dict(response.headers)
        content_type = response_headers.pop('Content-Type', None)
        return HttpResponse(content,
                            content_type=content_type,
                            status=response.status_code,
                            headers=response_headers)


    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f"프록시에서 외부 요청 실패. {e}"}, status=500)
    except Exception as e:
        return JsonResponse({'error': f"프록시에서 기타 예외 발생. {e}"}, status=500)

