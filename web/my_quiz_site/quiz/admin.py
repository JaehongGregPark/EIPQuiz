from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Category, Exam, Question, Choice, QuestionImage

# 상단 타이틀 설정
admin.site.site_header = "기출문제 통합 관리 시스템 (CMS)"
admin.site.site_title = "운영자 전용"
admin.site.index_title = "환영합니다! 운영 대시보드입니다."

class QuestionImageInline(admin.TabularInline):
    model = QuestionImage
    extra = 1

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    # list_display에서 함수 이름이 views의 함수와 겹치지 않게 주의하세요.
    list_display = ['title', 'category', 'created_at', 'bulk_edit_link']
    list_filter = ['category']

    def bulk_edit_link(self, obj):
        url = reverse('exam_bulk_edit', args=[obj.id])
        return format_html('<a class="button" href="{}" style="background: #79aec8; color: white; padding: 3px 10px; border-radius: 4px;">🎯 일괄 편집</a>', url)
    
    bulk_edit_link.short_description = "일괄작업"

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['number', 'content_summary', 'has_image_check', 'has_answer_check']
    list_filter = ['exam', 'created_at'] # exam 필터를 추가하면 관리가 편합니다.
    inlines = [ChoiceInline, QuestionImageInline]
    search_fields = ['content', 'number']
    ordering = ['number']
    
    def has_image_check(self, obj):
        return obj.images.exists()
    has_image_check.boolean = True
    has_image_check.short_description = "이미지 여부"

    def content_summary(self, obj):
        if obj.content:
            return obj.content[:30] + "..."
        return "(내용 없음)"
    content_summary.short_description = '문제 지문'

    def has_answer_check(self, obj):
        if obj.answer:
            return format_html('<span style="color: green;">{}</span>', "✔ 입력됨")
        return format_html('<span style="color: red;">{}</span>', "✘ 미입력")

# 이미 Inline으로 Question에 포함되어 있으므로, 
# 별도로 메뉴에 노출하고 싶지 않다면 아래 두 줄은 주석 처리해도 됩니다.
admin.site.register(Choice)
admin.site.register(QuestionImage)

