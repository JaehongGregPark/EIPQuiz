# image_matcher.py (수정본)
import os
import django
from django.core.files import File

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_quiz_site.settings")
django.setup()

from quiz.models import Question, QuestionImage, Choice

def bulk_upload_images(image_dir):
    files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    for file_name in files:
        try:
            name_part = os.path.splitext(file_name)[0]
            parts = name_part.split('_') # [시험지ID, 문제번호, (선택)보기번호]

            exam_id = int(parts[0])
            q_num = int(parts[1])
            
            question = Question.objects.get(exam_id=exam_id, number=q_num)

            # 1. 보기 이미지 처리 (파일명에 숫자가 3개인 경우: 5_45_1.jpg)
            if len(parts) == 3:
                choice_idx = int(parts[2]) - 1 # 리스트 인덱스는 0부터 시작
                choices = question.choices.all().order_by('id') # 등록 순서대로 가져옴
                
                if choice_idx < len(choices):
                    target_choice = choices[choice_idx]
                    with open(os.path.join(image_dir, file_name), 'rb') as f:
                        target_choice.image_file.save(file_name, File(f), save=True)
                    print(f"🎨 보기 매칭: {file_name} -> {question.number}번 문제 {parts[2]}번 보기")
                
            # 2. 지문 이미지 처리 (파일명에 숫자가 2개인 경우: 5_45.jpg)
            else:
                with open(os.path.join(image_dir, file_name), 'rb') as f:
                    q_image = QuestionImage(question=question)
                    q_image.image_file.save(file_name, File(f), save=True)
                print(f"📝 지문 매칭: {file_name} -> {question.number}번 문제 지문")

        except Exception as e:
            print(f"❌ 실패: {file_name} ({e})")

if __name__ == "__main__":
    path = input("이미지 폴더명 입력: ")
    bulk_upload_images(path)