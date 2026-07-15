# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app

ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

COPY package.json ./
COPY yarn.lock* ./
# Use the lockfile if it exists; otherwise resolve fresh so the build never
# fails just because yarn.lock wasn't copied to the server.
RUN if [ -f yarn.lock ]; then yarn install --frozen-lockfile; else yarn install; fi

COPY . .
RUN yarn build

# ---- serve stage ----
FROM nginx:alpine

# SPA config + reverse-proxy /api to the backend container (same-origin, no CORS)
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location /api/ {\n\
        proxy_pass http://backend:8001;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_read_timeout 120s;\n\
    }\n\
    location / { try_files $uri $uri/ /index.html; }\n\
    location ~* \\.(js|css|png|jpg|jpeg|gif|svg|ico|woff2?)$ {\n\
        expires 7d;\n\
        add_header Cache-Control "public, max-age=604800";\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
