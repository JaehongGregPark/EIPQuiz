# EIPQuiz 웹/API 서버용 Dockerfile.
#
# ultimate_parser.py 같은 오프라인 AI 파싱 스크립트(poppler 등 시스템 패키지 필요)는
# 이 이미지에 포함하지 않습니다 - 그건 로컬에서 미리 JSON을 만들어 db_uploader.py로
# 적재하는 오프라인 작업이고, 컨테이너는 이미 적재된 데이터를 서빙하는 웹 서버 역할만
# 합니다.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/staticfiles /app/media

EXPOSE 8000

CMD sh -c "python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn my_quiz_site.wsgi:application --bind 0.0.0.0:8000 --workers 2"
