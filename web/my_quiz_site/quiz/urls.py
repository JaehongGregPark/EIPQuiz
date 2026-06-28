from django.urls import path
from . import views

urlpatterns = [
    # localhost:8000/api/ 로 접속했을 때 실행될 뷰
    path('', views.question_list, name='question_list'),
    path('bulk-edit/<int:exam_id>/', views.exam_bulk_edit, name='exam_bulk_edit'),
    path('admin-image-matcher/', views.admin_image_matcher, name='admin_image_matcher'),
    path('admin-manual/', views.admin_manual, name='admin_manual'),
    path('admin-ocr-update/', views.admin_answer_ocr_update, name='admin_answer_ocr_update'),
    path('quiz/<int:exam_id>/', views.quiz_detail, name='quiz_detail'),
    path('admin/bulk-practical-upload/', views.admin_bulk_practical_upload, name='admin_bulk_practical_upload'),
    #path('api/admin-manual/', views.admin_manual, name='admin_manual'),
]