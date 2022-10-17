FROM node:15.11.0-buster-slim as build-step

RUN mkdir -p /app
WORKDIR /app

COPY ./frontend /app/

RUN sed -i "s|API_RELATIVE = \"\";|API_RELATIVE = \"api\";|g" app.config.js

RUN npm install
RUN npm run build


FROM python:3.7

COPY --from=build-step /app/dist /var/www/html/

ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && \
    apt-get install -y \
    nginx

RUN pip3 install --upgrade pip

RUN mkdir -p /app
WORKDIR /app

COPY ./backend /app/backend

RUN pip3 install -r ./backend/requirements.txt

EXPOSE 80
EXPOSE 443

ENV LISTEN_PORT 80

STOPSIGNAL SIGQUIT

COPY ./docker/nginx.conf /etc/nginx/nginx.conf

COPY ./docker/start.sh ./start.sh
RUN chmod a+x ./start.sh

CMD ["./start.sh"]
