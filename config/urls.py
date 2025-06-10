from django.contrib import admin
from django.urls import path, include
from config import views # 또는 네 뷰 함수가 있는 파일에서 임포트

urlpatterns = [
    path('admin/', admin.site.urls),
    path('requests/', include('ReqProxy.urls')),
    path('', views.test_example_connection_verbose, name='test_external_connectivity_verbose'),  # 그냥 요청 자체가 잘 작동하는지 확인용.

]
