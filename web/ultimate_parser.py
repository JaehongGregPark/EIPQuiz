import os
import json
import time
from google import genai
from pypdf import PdfReader
from docx import Document
from pdf2image import convert_from_path
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

# 1. 설정 (모델은 2.0-flash-exp 또는 1.5-flash-latest 추천)
API_KEY = "YOUR_GEMINI_API_KEY"

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-2.5-flash" 

def get_ai_response_(prompt_content):
    """모델명을 명확히 지정하고 에러 발생 시 상세 내용을 출력합니다."""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_ID, # 위에서 설정한 "gemini-2.0-flash" 사용
                contents=prompt_content
            )
            if response and response.text:
                text = response.text
                clean_json = text.replace('```json', '').replace('```', '').strip()
                return json.loads(clean_json)
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg:
                print("   [치명적] API 키가 차단되었습니다. 새 키를 발급받으세요.")
                return None # 키 문제면 즉시 중단
            elif "400" in err_msg:
                print(f"   [경고] 모델명 오류 발생: {MODEL_ID}. 이름을 확인하세요.")
                return None
            elif "429" in err_msg:
                print(f"   (제한 감지: {20 + attempt*10}초 휴식 후 재시도...)")
                time.sleep(20 + attempt*10)
            else:
                print(f"   (기타 오류: {e})")
                break
    return []

def get_ai_response(prompt_content):
    """모델명을 확인하고, 404 발생 시 실제 사용 가능한 모델 목록을 출력합니다."""
    global MODEL_ID
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt_content
            )
            if response and response.text:
                text = response.text
                clean_json = text.replace('```json', '').replace('```', '').strip()
                return json.loads(clean_json)
        
        except Exception as e:
            err_msg = str(e).lower()
            
            # 404 오류 처리
            if "404" in err_msg or "not_found" in err_msg:
                print(f"\n[오류] 호출한 모델명('{MODEL_ID}')이 존재하지 않습니다.")
                print("현재 API 키로 사용 가능한 모델 목록:")
                
                try:
                    # 최신 SDK 방식에 맞춰 모델 목록 출력
                    models = client.models.list()
                    available_names = []
                    for m in models:
                        # m 자체가 문자열이거나 객체일 수 있으므로 안전하게 처리
                        name = m.name if hasattr(m, 'name') else str(m)
                        available_names.append(name)
                        print(f" - {name}")
                    
                    print("\n위 목록 중 하나를 복사하여 MODEL_ID에 넣으세요.")
                except Exception as list_err:
                    print(f"모델 목록 조회 실패: {list_err}")
                
                return [] # None 대신 빈 리스트를 반환하여 TypeError 방지

            elif "429" in err_msg:
                print(f"   (제한 감지: {20 + attempt*10}초 휴식 후 재시도...)")
                time.sleep(20 + attempt*10)
            else:
                print(f"   (기타 오류: {e})")
                break
    return []

def process_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    base_name = os.path.basename(file_path)
    print(f"[{base_name}] 분석 시작...")
    
    all_questions = []
    prompt = """
    정보처리기사 시험 문제야. 아래 데이터를 읽고 JSON 배열로 변환해줘.
    - 그림이나 표(Table)가 있다면 텍스트나 마크다운으로 최대한 상세히 묘사해서 content에 넣어줘.
    - 형식: [{"no": "번호", "content": "지문", "options": ["①..","②..","③..","④.."], "answer": null}]
    """

    # [CASE 1] PDF (이미지+텍스트 하이브리드)
    if ext == '.pdf':
        poppler_path = r'C:\poppler\Library\bin'
        # 텍스트 추출용
        reader = PdfReader(file_path)
        # 이미지 추출용 (DPI를 150으로 낮춰 토큰 절약)
        images = convert_from_path(file_path, 150, poppler_path=poppler_path)

        for i, (page_txt, page_img) in enumerate(zip(reader.pages, images)):
            print(f"> {i+1} / {len(images)} 페이지 분석 중 (시각 분석 포함)...")
            text = page_txt.extract_text()
            # AI에게 텍스트와 이미지를 동시에 전달하여 누락 방지
            all_questions.extend(get_ai_response([prompt, text, page_img]))
            time.sleep(15) # 무료 티어 안전 장치

    # [CASE 2] Word (.docx)
    elif ext == '.docx':
        doc = Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        all_questions.extend(get_ai_response([prompt, text]))

    # [CASE 3] 이미지 (.png, .jpg)
    elif ext in ['.png', '.jpg', '.jpeg']:
        img = Image.open(file_path)
        all_questions.extend(get_ai_response([prompt, img]))

    # [CASE 4] 텍스트 (.txt)
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            all_questions.extend(get_ai_response([prompt, f.read()]))

    return all_questions, base_name

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(filetypes=[("모든 문서", "*.pdf *.docx *.txt *.png *.jpg")])
    
    if path:
        results, original_name = process_document(path)
        if results:
            # 요구사항 반영: 원본파일명.json으로 저장
            output_name = f"{os.path.splitext(original_name)[0]}.json"
            with open(output_name, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("성공", f"파일 생성됨: {output_name}\n총 {len(results)}문제 추출")