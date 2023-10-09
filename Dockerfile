FROM python:3.8-slim-buster

ARG BRANCH_NAME
ENV BRANCH_NAME=$BRANCH_NAME
ARG COMMIT_HASH
ENV COMMIT_HASH=$COMMIT_HASH
ENV DSCLOUD_APP_VERSION=${BRANCH_NAME}.${COMMIT_HASH}

WORKDIR /app

RUN apt-get -y update
RUN apt-get -y install git

COPY requirements.txt requirements.txt
RUN pip3 uninstall cassio
RUN pip3 uninstall langchain
RUN pip3 install -r requirements.txt --no-cache-dir

COPY . .

CMD [ "uvicorn", "app:app" , "--host", "0.0.0.0", "--port", "5555", "--reload" ]
