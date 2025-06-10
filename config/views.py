import requests
import json # 혹시 몰라서 json 임포트
from django.http import HttpResponse, JsonResponse
# from .views import proxy_request  # 만약 proxy_request 함수가 같은 파일에 있다면 임포트 필요 없음
# from urllib.parse import urlparse # URL 파싱은 이 뷰에서 필요 없으니 뺄게

def test_example_connection_verbose(request):
    """
    메인 페이지에서 example.com으로 직접 요청을 보내서
    프록시 서버 자체의 외부 통신 상태를 점검하는 뷰 (상세 에러 응답 포함)
    """
    # 서버 로그에는 간단히 시작만 찍자 (선택 사항)
    # print("--- test_example_connection_verbose 뷰 실행: example.com 연결 테스트 시작 ---")

    test_url = "https://www.example.com" # 테스트할 고정 URL

    # 1. requests를 사용해서 example.com으로 직접 요청 보내기
    try:
        # GET 요청으로 테스트. timeout 설정해서 무한 대기 방지
        # verify=True가 기본값. 여기서 에러 나면 SSL 문제!
        response = requests.get(test_url, timeout=15) # 15초 타임아웃 설정
        response.raise_for_status() # 200 OK 아니면 예외 발생

        # 서버 로그에는 성공 정보 간단히 찍기 (선택 사항)
        # print(f"--- example.com 연결 성공! 상태 코드: {response.status_code} ---")

        # 2. 성공하면 응답 상태 코드와 성공 메시지 반환 (JSON 형태로)
        return JsonResponse(
            {
                'status': '성공',
                'test_url': test_url,
                'status_code': response.status_code,
                'message': '프록시 서버에서 example.com에 성공적으로 접근했습니다.'
            },
            status=200 # OK
        )

    except requests.exceptions.Timeout:
         # 서버 로그에 타임아웃 정보 간단히 찍기 (선택 사항)
         # print(f"--- example.com 연결 실패: 타임아웃 ---")
         return JsonResponse(
            {
                'status': '실패',
                'test_url': test_url,
                'error_type': 'Timeout',
                'error_message': '외부 URL 요청 시간 초과 (Timeout) - 서버가 example.com에 연결하거나 응답받는데 너무 오래 걸렸습니다.',
            },
            status=504 # Gateway Timeout
         )
    except requests.exceptions.SSLError as e:
         # SSLError는 따로 잡아서 상세 정보 포함
         # 서버 로그에 SSLError 정보 간단히 찍기 (선택 사항)
         # print(f"--- example.com 연결 실패: SSLError ---")
         # print(f"에러 상세: {e}")
         return JsonResponse(
            {
                'status': '실패',
                'test_url': test_url,
                'error_type': 'SSLError',
                'error_message': f'SSL/TLS 연결 오류 발생: {e} - 주로 인증서 문제(네트워크 중간 가로챔 등)일 가능성이 높습니다.',
            },
            status=500 # Internal Server Error
         )
    except requests.exceptions.ConnectionError as e:
        # ConnectionError (DNS, 연결 거부 등)
        # 서버 로그에 ConnectionError 정보 간단히 찍기 (선택 사항)
        # print(f"--- example.com 연결 실패: ConnectionError ---")
        # print(f"에러 상세: {e}")
        return JsonResponse(
            {
                'status': '실패',
                'test_url': test_url,
                'error_type': 'ConnectionError',
                'error_message': f'연결 오류 발생: {e} - DNS 문제(이름 확인 실패), 방화벽 차단, 서버 다운 등일 수 있습니다.',
            },
            status=500 # Internal Server Error
        )
    except requests.exceptions.RequestException as e:
        # requests 관련 그 외 모든 에러 (HTTPError 등)
        # 서버 로그에 requests 에러 정보 간단히 찍기 (선택 사항)
        # print(f"--- example.com 연결 실패: requests 에러 ---")
        # print(f"에러 상세: {e}")
        return JsonResponse(
            {
                'status': '실패',
                'test_url': test_url,
                'error_type': 'RequestException',
                'error_message': f'requests 라이브러리 오류 발생: {e}',
            },
            status=500 # Internal Server Error
         )
    except Exception as e:
        # 예상치 못한 다른 모든 에러들
        # 서버 로그에 예상치 못한 에러 정보 간단히 찍기 (선택 사항)
        # print(f"--- example.com 연결 테스트 중 예상치 못한 에러 발생 ---")
        # print(f"에러 상세: {e}")
        return JsonResponse(
            {
                'status': '실패',
                'test_url': test_url,
                'error_type': 'UnexpectedError',
                'error_message': f'예상치 못한 서버 에러 발생: {e}',
            },
            status=500
        )