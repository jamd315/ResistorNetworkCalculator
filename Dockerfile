FROM python:3-slim
EXPOSE 80
WORKDIR /usr/src/app
RUN mkdir uploads
RUN pip3 install --no-cache-dir flask Werkzeug gunicorn numpy
COPY . .
CMD ["bash", "run.sh"]
