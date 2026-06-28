import fitz  # PyMuPDF: PDF 처리용
import re    # 정규표현식: 텍스트 분리용
import json
import os
from tkinter import filedialog, messagebox
import tkinter as tk

def select_pdf_file():
    """
    윈도우 파일 선택 창을 띄워 PDF 경로를 가져오는 함수
    """
    root = tk.Tk()
    root.withdraw() # 메인 윈도우 창은 숨김
    
    # PDF 파일만 선택할 수 있도록 필터링
    file_path = filedialog.askopenfilename(
        title="분석할 정보처리기사 PDF 파일을 선택하세요",
        filetypes=[("PDF 파일", "*.pdf")]
    )
    return file_path

def manual_extract_engine(pdf_path):
    """
    선택된 PDF에서 텍스트와 이미지를 추출하는 엔진
    """
    try:
        doc = fitz.open(pdf_path)
        all_questions = []
        
        # 이미지 저장용 폴더 생성 (선택한 PDF 파일 이름으로 폴더 생성)
        base_name = os.path.basename(pdf_path).replace(".pdf", "")
        img_dir = f"extracted_{base_name}"
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)

        print(f"[{base_name}] 분석 시작...")

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")

            # 1. 텍스트 분리 (숫자. 으로 시작하는 패턴 찾기)
            # 정보처리기사 특성상 '1. ', '21. ' 등 숫자 뒤 점을 기준으로 자름
            items = re.split(r'\n(?=\d+\.)', text)

            for item in items:
                item = item.strip()
                if not item: continue

                # 문제 번호 추출 (예: "1." 에서 "1"만 가져오기)
                first_line = item.split('\n')[0]
                q_num_match = re.match(r'^(\d+)\.', first_line)
                
                if q_num_match:
                    q_no = q_num_match.group(1)
                    
                    # 보기(①~④) 분리
                    parts = re.split(r'(①|②|③|④)', item)
                    question_body = parts[0].strip()
                    options = []
                    if len(parts) > 1:
                        for i in range(1, len(parts), 2):
                            options.append(parts[i] + parts[i+1].replace('\n', ' ').strip())

                    all_questions.append({
                        "no": q_no,
                        "content": question_body,
                        "options": options,
                        "page": page_num + 1
                    })

            # 2. 이미지 추출
            images = page.get_images()
            for i, img in enumerate(images):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                # 이미지 파일명 결정 (예: page1_img1.png)
                img_name = f"page{page_num+1}_img{i+1}.png"
                pix.save(os.path.join(img_dir, img_name))
        
        return all_questions, base_name

    except Exception as e:
        messagebox.showerror("오류", f"파일 처리 중 문제가 발생했습니다:\n{e}")
        return None, None

# --- 프로그램 실행 시작점 ---
if __name__ == "__main__":
    # 1. 파일 선택 창 띄우기
    selected_path = select_pdf_file()
    
    if selected_path:
        # 2. 분석 실행
        data, name = manual_extract_engine(selected_path)
        
        if data:
            # 3. 결과를 JSON 파일로 저장
            output_file = f"result_{name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("성공", f"분석이 완료되었습니다!\n결과 파일: {output_file}\n이미지 폴더: extracted_{name}")
    else:
        print("파일 선택이 취소되었습니다.")