from django.urls import path
from .views import * #해당 앱의 뷰를 불러온다.

app_name = 'requests' #이름공간을 위한, 인덱싱을 위한 변수이다. 이걸 작성하면 인덱스는 '앱이름:인덱스'로 바뀐다.

urlpatterns = [
    path('do/', do_request, name='do'),
]