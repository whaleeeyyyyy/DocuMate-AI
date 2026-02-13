# /frontend/Dockerfile
# 1) build stage
FROM node:20-alpine AS build

WORKDIR /app

# only copy package manifests first to leverage docker cache
COPY package.json package-lock.json* yarn.lock* /app/
# choose npm or yarn; using npm by default
RUN npm ci

# copy rest of the frontend
COPY . /app

# build — VITE will read VITE_API_BASE_URL at build time
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# 2) serve with nginx
FROM nginx:1.25-alpine

# remove default static
RUN rm -rf /usr/share/nginx/html/*

# copy build artifacts
COPY --from=build /app/dist /usr/share/nginx/html

# copy a minimal nginx config if you want to add fallback for SPA (optional)
# Example included below as comment in case you want to use it.
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
