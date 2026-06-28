import os
import json
import django
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# 1. Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_quiz_site.settings")
django.setup()

from quiz.models import Category, Exam, Question, Choice

def get_user_input(default_title):
    """분류 선택 및 제목 수정을 위한 팝업 창을 띄웁니다."""
    user_data = {"category": None, "title": None}
    
    dialog = tk.Toplevel()
    dialog.title("시험 정보 입력")
    dialog.geometry("400x300")
    dialog.resizable(False, False)
    
    # 창을 화면 중앙에 배치
    dialog.grab_set() 

    # 1. 분류 선택 (라디오 버튼)
    tk.Label(dialog, text="1. 분류를 선택하세요:", font=('NanumGothic', 10, 'bold')).pack(pady=10)
    category_var = tk.StringVar(value="정처기필기")
    categories = ["정처기필기", "정처기실기", "빅분기필기", "빅분기실기"]
    
    for cat in categories:
        tk.Radiobutton(dialog, text=cat, variable=category_var, value=cat).pack(anchor="w", padx=100)

    # 2. 제목 입력 (Entry)
    tk.Label(dialog, text="\n2. 시험지 제목을 입력하세요:", font=('NanumGothic', 10, 'bold')).pack(pady=5)
    title_entry = tk.Entry(dialog, width=40)
    title_entry.insert(0, default_title) # 파일명을 기본값으로 삽입
    title_entry.pack(pady=5)

    def on_confirm():
        user_data["category"] = category_var.get()
        user_data["title"] = title_entry.get().strip()
        dialog.destroy()

    tk.Button(dialog, text="데이터 등록 시작", command=on_confirm, bg="#4CAF50", fg="white", width=20).pack(pady=20)

    dialog.wait_window() # 창이 닫힐 때까지 대기
    return user_data

def insert_quiz_data():
    root = tk.Tk()
    root.withdraw()
    
    # 1. 파일 선택
    file_path = filedialog.askopenfilename(
        title="DB에 넣을 JSON 파일을 선택하세요",
        filetypes=[("JSON 파일", "*.json")]
    )
    
    if not file_path:
        return

    # 2. 파일명에서 기본 제목 추출
    default_title = os.path.splitext(os.path.basename(file_path))[0]

    # 3. 사용자 입력 받기 (분류 선택 및 제목 수정)
    user_input = get_user_input(default_title)
    
    category_name = user_input["category"]
    exam_title = user_input["title"]

    if not category_name or not exam_title:
        messagebox.showwarning("알림", "입력이 취소되었습니다.")
        return

    # 4. JSON 로드 및 DB 작업
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        category, _ = Category.objects.get_or_create(name=category_name)
        exam = Exam.objects.create(category=category, title=exam_title)

        count = 0
        for item in data:
            content = item.get('content') or ''
            if len(content.strip()) < 5: continue

            question = Question.objects.create(
                exam=exam,
                number=item.get('no'),
                content=content,
                answer=item.get('answer')
            )

            options = item.get('options', [])
            target_answer = str(item.get('answer', ''))

            for idx, option_text in enumerate(options, 1):
                is_this_answer = False
                # 정답 번호(1, 2, 3, 4) 또는 텍스트가 포함된 경우 체크
                if target_answer == str(idx) or target_answer in option_text:
                    is_this_answer = True

                Choice.objects.create(
                    question=question,
                    choice_text=option_text,
                    is_answer=is_this_answer
                )
            count += 1
        
        messagebox.showinfo("성공", f"[{category_name} > {exam_title}]\n{count}개의 문제가 등록되었습니다!")

    except Exception as e:
        messagebox.showerror("오류", f"작업 중 오류 발생: {e}")

if __name__ == "__main__":
    insert_quiz_data()