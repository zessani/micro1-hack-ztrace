FROM python:3.12-alpine
WORKDIR /srv
RUN mkdir -p v2 && echo '{"version": "2.4.1", "fields": ["id", "slug", "title"]}' > v2/schema.json
EXPOSE 80
CMD ["python", "-m", "http.server", "80", "--directory", "/srv"]
