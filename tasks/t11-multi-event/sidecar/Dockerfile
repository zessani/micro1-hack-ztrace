FROM python:3.12-alpine
WORKDIR /srv
RUN mkdir -p v1 && echo '{"version": "3.1.0", "templates": ["ticket_opened", "ticket_replied", "ticket_closed"]}' > v1/templates.json
EXPOSE 80
CMD ["python", "-m", "http.server", "80", "--directory", "/srv"]
