import os
import json
import google.generativeai as genai
from pdf2image import convert_from_path
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

# ==========================================
# 1. AI 설정 (본인의 API 키를 입력하세요)
# ==========================================
API_KEY = "YOUR_GEMINI_API_KEY_HERE"
genai.configure(api_key=API_KEY)
# 이미지 분석에 최적화된 flash 모델 사용 (무료/고속)
model = genai.GenerativeModel('gemini-1.5-flash')

def select_pdf_file():
    """윈도우 탐색기를 띄워 PDF 파일을 선택합니다."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="AI로 분석할 정보처리기사 PDF를 선택하세요",
        filetypes=[("PDF 파일", "*.pdf")]
    )
    return file_path

def run_ai_parser(pdf_path):
    """PDF를 이미지로 변환하여 AI에게 전달하고 JSON으로 추출합니다."""
    try:
        print(f"[{os.path.basename(pdf_path)}] 분석을 시작합니다. 잠시만 기다려주세요...")
        
        # 2. PDF를 이미지로 변환 (300DPI 고화질)
        # ※ poppler 설치 경로가 다를 경우 poppler_path="경로" 추가 필요
        pages = convert_from_path(pdf_path, 300)
        
        all_questions = []

        for i, page in enumerate(pages):
            print(f">>> {i+1}페이지 분석 중...")
            
            # 임시 이미지 파일로 저장
            temp_img = f"temp_page_{i+1}.png"
            page.save(temp_img, "PNG")

            # 3. AI에게 보낼 명령 (프롬프트)
            # 이미지 속의 표와 보기를 정확히 구분하도록 지시합니다.
            prompt = """
            이 이미지는 정보처리기사 기출문제지야. 
            문제를 분석해서 다음 JSON 배열 형식으로만 응답해줘.
            
            1. no: 문제 번호 (숫자만)
            2. content: 문제 내용 전체 (표가 있다면 텍스트나 마크다운으로 포함)
            3. options: 1~4번 보기 내용을 리스트로 (예: ["①내용", "②내용", ...])
            4. answer: 이미지에 정답이 체크되어 있다면 해당 번호, 없으면 null
            5. explanation: 해설이 있다면 포함, 없으면 null
            
            응답은 반드시 순수한 JSON 배열([]) 형식이어야 해. 다른 설명은 하지 마.
            """

            # 4. AI에게 이미지와 프롬프트 전송
            img = Image.open(temp_img)
            response = model.generate_content([prompt, img])
            
            # AI 응답에서 JSON 데이터만 추출
            raw_text = response.text.replace('```json', '').replace('```', '').strip()
            
            try:
                page_data = json.loads(raw_text)
                all_questions.extend(page_data)
            except Exception as e:
                print(f"{i+1}페이지 데이터 변환 실패: {e}")
            
            # 사용한 임시 이미지 삭제
            os.remove(temp_img)

        return all_questions

    except Exception as e:
        messagebox.showerror("오류", f"AI 분석 중 오류가 발생했습니다:\n{e}")
        return None

# ==========================================
# 5. 실행 영역
# ==========================================
if __name__ == "__main__":
    selected_pdf = select_pdf_file()
    
    if selected_pdf:
        results = run_ai_parser(selected_pdf)
        
        if results:
            # 결과 저장 (PDF 파일명과 동일한 이름의 JSON 생성)
            base_name = os.path.basename(selected_pdf).replace(".pdf", "")
            output_name = f"clean_result_{base_name}.json"
            
            with open(output_name, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("성공", f"AI 분석 완료!\n파일 저장됨: {output_name}")
    else:
        print("파일 선택이 취소되었습니다.")