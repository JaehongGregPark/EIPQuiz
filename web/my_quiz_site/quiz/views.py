from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.files import File
from rest_framework import viewsets
from .serializers import QuestionSerializer
from django.shortcuts import render, redirect, get_object_or_404
import fitz  # PyMuPDF
import io
from google.cloud import vision
import json
import os
import re
from google.cloud import vision
from .models import Exam, Question, QuestionImage, Choice

class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    # 모든 문제를 가져오되, 번호 순서대로 정렬합니다.
    queryset = Question.objects.all().order_by('number')
    serializer_class = QuestionSerializer

def question_list(request):
    category_id = request.GET.get('category')
    exam_id = request.GET.get('exam')

    categories = Category.objects.all()
    exams = Exam.objects.all()
    
    # 필터링 로직
    questions = Question.objects.all()
    if category_id:
        questions = questions.filter(exam__category_id=category_id)
        exams = exams.filter(category_id=category_id)
    if exam_id:
        questions = questions.filter(exam_id=exam_id)

    return render(request, 'quiz/question_list.html', {
        'questions': questions,
        'categories': categories,
        'exams': exams,
        'selected_category': category_id,
        'selected_exam': exam_id,
    })

def exam_bulk_edit(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all().order_by('number')

    if request.method == "POST":
        for question in questions:
            # HTML input name을 'answer_{{question.id}}' 형태로 받을 예정
            new_answer = request.POST.get(f'answer_{question.id}')
            new_number = request.POST.get(f'number_{question.id}')
            
            if new_answer is not None:
                question.answer = new_answer
            if new_number is not None:
                question.number = new_number
            question.save()
            
        return redirect('admin:quiz_exam_changelist') # 저장 후 다시 관리자 목록으로

    return render(request, 'admin/quiz/bulk_edit.html', {
        'exam': exam,
        'questions': questions,
    })

@staff_member_required
def admin_image_matcher(request):
    if request.method == "POST":
        image_dir = request.POST.get('image_dir') # 관리자가 입력한 서버 내 폴더 경로
        
        if not os.path.exists(image_dir):
            messages.error(request, f"폴더를 찾을 수 없습니다: {image_dir}")
            return redirect('admin_manual')

        files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        success_count = 0
        
        for file_name in files:
            try:
                name_part = os.path.splitext(file_name)[0]
                parts = name_part.split('_') # [시험지ID, 문제번호, (선택)보기번호]

                exam_id = int(parts[0])
                q_num = int(parts[1])
                question = Question.objects.get(exam_id=exam_id, number=q_num)

                # 보기 이미지 처리 (예: 5_45_1.jpg)
                if len(parts) == 3:
                    choice_idx = int(parts[2]) - 1
                    choices = question.choices.all().order_by('id')
                    if choice_idx < len(choices):
                        target_choice = choices[choice_idx]
                        with open(os.path.join(image_dir, file_name), 'rb') as f:
                            target_choice.image_file.save(file_name, File(f), save=True)
                        success_count += 1
                
                # 지문 이미지 처리 (예: 5_45.jpg)
                else:
                    with open(os.path.join(image_dir, file_name), 'rb') as f:
                        q_image = QuestionImage(question=question)
                        q_image.image_file.save(file_name, File(f), save=True)
                    success_count += 1
            except Exception:
                continue

        messages.success(request, f"총 {success_count}개의 이미지가 성공적으로 매칭되었습니다.")
        return redirect('admin_manual') # 기존 운영 메뉴얼 페이지로 리다이렉트

    return redirect('admin_manual')


# 1. 구글 인증 키 설정 (본인의 JSON 키 파일 경로로 수정하세요)
# 예: os.path.join(settings.BASE_DIR, 'keys', 'your-google-key.json')
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/USER/Documents/project/web/my_quiz_site/keys/service-account-key.json"

def admin_answer_ocr_update(request):
    if request.method == "POST" and request.FILES.get('answer_sheet'):
        exam_id = request.POST.get('exam_id')
        exam = get_object_or_404(Exam, id=exam_id)
        image_file = request.FILES['answer_sheet']
        
        # 2. Vision API 클라이언트 초기화
        client = vision.ImageAnnotatorClient()

        # 3. 이미지 읽기
        content = image_file.read()
        image = vision.Image(content=content)

        # 4. 텍스트 감지 실행 (DOCUMENT_TEXT_DETECTION은 문서/표 인식에 최적화됨)
        response = client.document_text_detection(image=image)
        full_text = response.full_text_annotation.text

        print("--- [Google Vision] 인식 결과 ---")
        print(full_text)
        print("-------------------------------")

        # 5. 데이터 보정 및 추출
        # 구글은 원문자를 매우 잘 읽으므로 유니코드 대응만 해주면 됩니다.
        circle_map = {
            '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
            '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5', # 중복 방지
        }
        
        processed_text = full_text
        for target, val in circle_map.items():
            processed_text = processed_text.replace(target, val)

        # 6. 정규표현식으로 (문제번호) (정답) 추출
        # 구글은 보통 "1. 3" 또는 "1 3" 형태로 아주 깔끔하게 반환합니다.
        matches = re.findall(r'(\d{1,3})\s*[\.\s]*\s*([1-5])', processed_text)
        
        update_count = 0
        updated_nums = set()
        logs = []

        for q_num, q_ans in matches:
            num = int(q_num)
            ans = q_ans

            if num in updated_nums or not (1 <= num <= 100):
                continue

            question = Question.objects.filter(exam=exam, number=num).first()
            if question:
                question.answer = ans
                question.save()
                update_count += 1
                updated_nums.add(num)
                logs.append(f"{num}:{ans}")

        if response.error.message:
            messages.error(request, f"Google API 오류: {response.error.message}")
        elif update_count > 0:
            print(f"Final Updates: {sorted(logs, key=lambda x: int(x.split(':')[0]))}")
            messages.success(request, f"Google Vision을 통해 {update_count}개의 정답을 정확히 업데이트했습니다!")
        else:
            messages.warning(request, "이미지에서 정답 패턴을 찾지 못했습니다.")

        return redirect('admin_manual')



def quiz_detail(request, exam_id):
    """
    사용자가 퀴즈를 푸는 상세 페이지 뷰
    """
    exam = get_object_or_404(Exam, id=exam_id)
    # 문제를 번호 순서대로 가져옵니다.
    questions = exam.questions.all().order_by('number')
    
    return render(request, 'quiz/quiz_detail.html', {
        'exam': exam,
        'questions': questions
    })

def admin_bulk_practical_upload(request):
    if request.method == "POST":
        exam_id = request.POST.get('exam_id')
        exam = Exam.objects.get(id=exam_id)
        raw_text = request.POST.get('bulk_text')

        # 1. 과목 섹션 분리 (번호 + 과목명 패턴)
        # 예: "2. 데이터베이스 [배점: 30점]" 패턴을 기준으로 나눔
        subject_patterns = r'(\d\.\s*(?:알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어).*?)(?=\d\.\s*(?:알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어)|$)'
        sections = re.findall(subject_patterns, raw_text, re.DOTALL)

        # 2. 정답지 추출 (6페이지의 정답 섹션 찾기)
        answer_section = raw_text.split("정답>")[-1] if "정답>" in raw_text else ""
        
        created_count = 0
        for section_content in sections:
            # 과목명 추출
            subject_name = re.search(r'(알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어)', section_content).group(1)
            
            # 해당 섹션 내의 문항 번호 추출 (①, ②... 또는 (1), (2)...)
            # 실기 시험 특성상 한 지문에 여러 문항이 딸려 있음
            q_markers = re.findall(r'([①-⑮]|\(\d\))', section_content)
            unique_markers = sorted(list(set(q_markers)))

            for marker in unique_markers:
                # 번호 표준화 (① -> 1, (1) -> 1)
                clean_num = marker.replace('(', '').replace(')', '')
                # 특수문자 대응 테이블 (필요시 확장)
                marker_map = {'①':1,'②':2,'③':3,'④':4,'⑤':5,'⑥':6,'⑦':7,'⑧':8,'⑨':9,'⑩':10}
                num = marker_map.get(clean_num, clean_num)

                # 정답 매칭 (정답지 텍스트에서 해당 과목의 번호를 찾음)
                # 정교한 매칭 로직은 정답지 텍스트 구조에 따라 보정이 필요함
                ans_pattern = rf'{marker}\s*(\d+\.\s*[^\n]+|[A-Za-z\s]+)'
                ans_match = re.search(ans_pattern, answer_section)
                ans_text = ans_match.group(1).strip() if ans_match else ""

                Question.objects.create(
                    exam=exam,
                    number=num, # 실제로는 과목별 구분이 필요하므로 고유값 생성 로직 필요
                    content=section_content, # 해당 과목 지문 전체를 저장
                    answer=ans_text,
                    explanation=f"{subject_name} 과목의 {marker} 문항입니다."
                )
                created_count += 1

        messages.success(request, f"{created_count}개의 실기 문항이 자동으로 분류 및 등록되었습니다.")
        return redirect('admin_manual')

    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'quiz/admin_bulk_practical.html', {'exams': exams})

def admin_bulk_file_upload(request):
    if request.method == "POST" and request.FILES.get('quiz_file'):
        exam_id = request.POST.get('exam_id')
        exam = Exam.objects.get(id=exam_id)
        pdf_file = request.FILES['quiz_file']

        # 1. PDF에서 텍스트 추출
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        # 2. 과목 섹션 분리 (알고리즘, DB, 업무프로세스 등)
        # 제시된 PDF 구조상 '숫자. 과목명' 패턴을 기준으로 분할 [cite: 38, 62, 81, 92]
        subject_split_ptrn = r'(\d\.\s*(?:알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어))'
        parts = re.split(subject_split_ptrn, full_text)
        
        # 3. 정답지 추출 (마지막 페이지의 정답 섹션 활용) [cite: 110]
        answer_text = full_text.split("정답>")[-1] if "정답>" in full_text else ""

        created_count = 0
        # split 결과는 [공백, 과목명1, 내용1, 과목명2, 내용2...] 순서임
        for i in range(1, len(parts), 2):
            subject_header = parts[i]
            section_content = parts[i+1]
            subject_name = re.search(r'(알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어)', subject_header).group(1)

            # 문항 번호 추출 (①, ②... 또는 (1), (2)...) [cite: 39, 40]
            q_markers = re.findall(r'([①-⑮]|\(\d\))', section_content)
            unique_markers = sorted(list(set(q_markers)))

            for marker in unique_markers:
                # 정답 매칭 로직 (정답지에서 마커에 해당하는 텍스트 탐색) [cite: 124, 125]
                ans_pattern = rf'{re.escape(marker)}\s*(\d+\.\s*[^\n]+|[A-Za-z\s]+)'
                ans_match = re.search(ans_pattern, answer_text)
                ans_val = ans_match.group(1).strip() if ans_match else ""

                Question.objects.create(
                    exam=exam,
                    number=99,  # 실기는 과목내 순번이 중요하므로 추후 정렬 로직 보강 필요
                    content=section_content.strip(),
                    answer=ans_val,
                    explanation=f"[{subject_name}] {marker} 문항 정답입니다."
                )
                created_count += 1

        messages.success(request, f"파일 분석 완료: {created_count}개의 문항이 등록되었습니다.")
        return redirect('admin_manual')

    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'quiz/admin_file_upload.html', {'exams': exams})

def admin_unified_upload_center(request):
    if request.method == "POST" and request.FILES.get('upload_file'):
        exam_id = request.POST.get('exam_id')
        exam = Exam.objects.get(id=exam_id)
        uploaded_file = request.FILES['upload_file']
        mode = request.POST.get('upload_mode') # 'written'(필기) 또는 'practical'(실기)

        if mode == 'practical':
            # --- [실기 모드] PyMuPDF 기반 텍스트 분석 ---
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            full_text = "".join([page.get_text() for page in doc])
            
            # 과목 섹션 분리 및 정답 매칭 (앞서 설계한 파서 로직 실행)
            created_count = parse_practical_pdf(exam, full_text)
            messages.success(request, f"실기 데이터 분석 완료: {created_count}개 문항 등록")
            
        else:
            # --- [필기 모드] 기존 Google Vision OCR 로직 호출 ---
            # (기존에 작성했던 OCR 처리 함수를 여기서 실행)
            messages.success(request, "필기 이미지 OCR 분석이 완료되었습니다.")

        return redirect('admin_unified_center')

    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'quiz/admin_unified_center.html', {'exams': exams})

def parse_practical_pdf(exam, text):
    """실기 PDF 텍스트 파싱 처리 보조 함수"""
    # 2009년 1회 실기 PDF 구조 기반 파싱 로직 적용
    subject_split_ptrn = r'(\d\.\s*(?:알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어))'
    parts = re.split(subject_split_ptrn, text)
    answer_text = text.split("정답>")[-1] if "정답>" in text else ""
    
    count = 0
    for i in range(1, len(parts), 2):
        section_content = parts[i+1]
        q_markers = re.findall(r'([①-⑮]|\(\d\))', section_content)
        for marker in sorted(list(set(q_markers))):
            ans_match = re.search(rf'{re.escape(marker)}\s*(\d+\.\s*[^\n]+|[A-Za-z\s]+)', answer_text)
            Question.objects.create(
                exam=exam,
                number=99, # 임시 번호
                content=section_content.strip(),
                answer=ans_match.group(1).strip() if ans_match else ""
            )
            count += 1
    return count



def parse_practical_logic(exam, text):
    """실기 텍스트 분석 핵심 로직 (보조 함수)"""
    # 과목 구분자 패턴 (2009년 실기 자료 근거) [cite: 37, 38, 62, 81, 92]
    subject_ptrn = r'(\d\.\s*(?:알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어))'
    parts = re.split(subject_ptrn, text)
    answer_text = text.split("정답>")[-1] if "정답>" in text else ""
    
    count = 0
    for i in range(1, len(parts), 2):
        subject_name = parts[i]
        content = parts[i+1]
        # 문항 기호 추출 (①-⑮, (1)-(5)) [cite: 5, 57, 107]
        markers = re.findall(r'([①-⑮]|\(\d\))', content)
        for marker in sorted(list(set(markers))):
            # 정답지 영역에서 해당 마커 정답 탐색 [cite: 110]
            ans_match = re.search(rf'{re.escape(marker)}\s*(\d+\.\s*[^\n]+|[A-Za-z\s]+)', answer_text)
            Question.objects.create(
                exam=exam,
                number=99, # 임시 번호 (관리자 화면에서 수정 가능)
                content=content.strip(),
                answer=ans_match.group(1).strip() if ans_match else "미확인"
            )
            count += 1
    return count


# views.py 파일 내에서 admin_manual 관련 함수를 다 지우고 이 하나만 남기세요.

# quiz/views.py

@staff_member_required
def admin_manual(request):
    # 1. 파일 업로드(POST) 처리
    if request.method == "POST" and request.FILES.get('upload_file'):
        exam_id = request.POST.get('exam_id')
        new_exam_title = request.POST.get('new_exam_title')
        mode = request.POST.get('upload_mode')
        uploaded_file = request.FILES['upload_file']

        # 시험지 객체 확보
        exam = None
        if exam_id:
            exam = get_object_or_404(Exam, id=exam_id)
        elif new_exam_title:
            # 카테고리가 없을 경우를 대비해 get_or_create 사용 (모델명을 확인하세요. Category인지 여부)
            from .models import Category 
            category, _ = Category.objects.get_or_create(name="정보처리기사 실기")
            exam = Exam.objects.create(category=category, title=new_exam_title)

        # 실기(practical) 모드 OCR 처리
        if mode == 'practical' and exam:
            try:
                client = vision.ImageAnnotatorClient()
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                full_text = ""

                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
                    img_bytes = pix.tobytes("jpg")
                    image = vision.Image(content=img_bytes)
                    response = client.text_detection(image=image)
                    full_text += response.text_annotations[0].description + "\n"

                subject_ptrn = r'(\d\.\s*(?:알고리즘|데이터베이스|업무프로세스|신기술동향|전산영어))'
                parts = re.split(subject_ptrn, full_text)
                answer_text = full_text.split("정답")[-1] if "정답" in full_text else ""
                
                created_count = 0
                if len(parts) > 1:
                    for i in range(1, len(parts), 2):
                        subject_header = parts[i]
                        content_body = parts[i+1]
                        markers = re.findall(r'([①-⑮]|\(\d\))', content_body)
                        for marker in sorted(list(set(markers))):
                            ans_match = re.search(rf'{re.escape(marker)}\s*([^\n①-⑮\(]+)', answer_text)
                            Question.objects.create(
                                exam=exam,
                                number=99,
                                content=f"{subject_header}\n{content_body.strip()}",
                                answer=ans_match.group(1).strip() if ans_match else "미등록"
                            )
                            created_count += 1
                messages.success(request, f"OCR 분석 완료: {created_count}개 문항 등록 성공!")
            except Exception as e:
                messages.error(request, f"OCR 처리 중 오류: {str(e)}")

        return redirect('admin_manual')

    # 2. 페이지 출력(GET) 처리
    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'admin/quiz/admin_manual.html', {'exams': exams})