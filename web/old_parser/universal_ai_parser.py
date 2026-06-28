import os
import json
# 새로운 라이브러리로 변경
from google import genai
from google.genai import types
from pdf2image import convert_from_path
from docx import Document
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

# ==========================================
# 1. AI 설정 (최신 SDK 방식)
# ==========================================
API_KEY = "YOUR_GEMINI_API_KEY_HERE"
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-1.5-flash" # 모델명 수정

def select_any_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="분석할 파일을 선택하세요",
        filetypes=[("모든 문서", "*.pdf *.docx *.txt")]
    )

def get_ai_response(content_list):
    """모델명을 명확히 지정하고 에러 발생 시 상세 내용을 출력합니다."""
    prompt = """
    너는 전문 시험문제 분석가야. 제공된 내용을 분석해서 JSON 배열로 응답해줘.
    형식: [{"no": "번호", "content": "지문", "options": ["①..","②..","③..","④.."], "answer": null}]
    반드시 다른 설명 없이 순수한 JSON 배열만 응답해.
    """
    
    try:
        # 모델명을 'gemini-1.5-flash-latest'로 변경 시도 (가장 최신 버전 명시)
        # 만약 이것도 안된다면 'models/gemini-1.5-flash' 로 시도하세요.
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[prompt] + content_list
        )
        
        if response and response.text:
            text = response.text
            # AI 응답에서 마크다운 태그 제거
            clean_json = text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        
        return []
        
    except Exception as e:
        # 에러 발생 시 어떤 모델을 찾으려 했는지 출력하여 원인을 파악합니다.
        print(f"상세 에러 내용: {e}")
        return []
    
def process_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    print(f"[{os.path.basename(file_path)}] 분석 시작...")

    if ext == '.pdf':
        # Poppler 경로 설정 (본인 경로에 맞게 수정)
        poppler_path = r'C:\poppler\Library\bin' 
        pages = convert_from_path(file_path, 300, poppler_path=poppler_path)
        
        all_data = []
        for i, page in enumerate(pages):
            print(f"> {i+1}페이지 처리 중...")
            # AI에게 이미지를 직접 전달
            all_data.extend(get_ai_response([page]))
        return all_data

    elif ext == '.docx':
        doc = Document(file_path)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        return get_ai_response([full_text])

    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return get_ai_response([f.read()])

    return None

if __name__ == "__main__":
    file_path = select_any_file()
    if file_path:
        final_results = process_file(file_path)
        if final_results:
            output_name = f"final_data_{os.path.basename(file_path)}.json"
            with open(output_name, "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("성공", f"분석 완료! {len(final_results)}개 추출됨")