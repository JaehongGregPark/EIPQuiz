import fitz  # PyMuPDF 라이브러리
import re    # 정규표현식 (문자열 패턴 찾기 도구)
import json
import os

def extract_from_pdf(pdf_path):
    # 1. PDF 파일 열기
    doc = fitz.open(pdf_path)
    
    all_data = []
    image_counter = 1
    
    # 이미지 저장 폴더 생성
    if not os.path.exists("extracted_images"):
        os.makedirs("extracted_images")

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # --- [A] 텍스트 추출 및 구조화 ---
        text = page.get_text("text") # 페이지 전체 텍스트 가져오기
        
        # 정규표현식 패턴 설정
        # (예: "1. 다음 중..." 형태를 찾아서 나눕니다)
        # ^\d+\. : 줄 시작이 '숫자.'으로 시작하는 패턴
        items = re.split(r'\n(?=\d+\.)', text) 

        for item in items:
            item = item.strip()
            if not item: continue

            # 문제 번호와 내용을 분리
            lines = item.split('\n')
            q_num_match = re.match(r'^(\d+)\.', lines[0])
            
            if q_num_match:
                q_no = q_num_match.group(1)
                
                # 보기(①, ②, ③, ④) 분리 로직
                # 텍스트 안에 원문자가 있으면 그 기점으로 나눕니다.
                parts = re.split(r'(①|②|③|④)', item)
                
                question_body = parts[0].strip() # 원문자 나오기 전까지가 문제 지문
                options = []
                if len(parts) > 1:
                    # 원문자와 내용을 합쳐서 보기 리스트 만들기
                    for i in range(1, len(parts), 2):
                        options.append(parts[i] + parts[i+1].strip())

                # 결과 데이터 구성
                all_data.append({
                    "no": q_no,
                    "type": "PILGI", # 기본 필기(객관식)로 설정
                    "question": question_body,
                    "options": options,
                    "page": page_num + 1
                })

        # --- [B] 이미지 추출 및 저장 ---
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"] # 이미지 데이터(바이트)
            image_ext = base_image["ext"]    # 확장자 (png, jpg 등)
            
            # 이미지 파일 저장
            img_filename = f"extracted_images/q_img_{page_num+1}_{img_index+1}.{image_ext}"
            with open(img_filename, "wb") as f:
                f.write(image_bytes)
            
            print(f"이미지 추출 완료: {img_filename}")

    return all_data

# --- 실행 영역 ---
if __name__ == "__main__":
    pdf_name = "sample_exam.pdf" # 여기에 분석할 파일명 넣기
    
    if os.path.exists(pdf_name):
        results = extract_from_pdf(pdf_name)
        
        # JSON 파일로 저장
        with open("raw_data.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        print(f"\n추출 완료! 총 {len(results)}개의 문제 구조를 파악했습니다.")
    else:
        print("파일을 찾을 수 없습니다.")