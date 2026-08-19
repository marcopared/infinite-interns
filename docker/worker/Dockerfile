FROM python:3.13-slim

RUN useradd --create-home --uid 10001 intern
USER intern
WORKDIR /workspace

CMD ["python", "-c", "print('InfiniteInterns worker base')"]
