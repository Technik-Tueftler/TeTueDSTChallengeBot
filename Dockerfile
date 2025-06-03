FROM FROM python:3.13-slim

ENV WORKING_DIR /user/app/TeTueDSTChallengeBot
WORKDIR $WORKING_DIR

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY files/ ./files/
COPY source/ ./source/

ENV PYTHONPATH "${PYTHONPATH}:/user/app/TeTueDSTChallengeBot"

WORKDIR /user/app/TeTueDSTChallengeBot/source/

CMD ["python", "-u", "main.py"]