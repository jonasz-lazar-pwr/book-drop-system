# Stage 1: Build Angular app
FROM node:22-alpine AS builder
WORKDIR /app

# Install dependencies and build the app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npx ng build --configuration production

# Stage 2: Serve with Nginx
FROM nginx:stable-alpine

# Install envsubst for dynamic config substitution
RUN apk add --no-cache gettext

WORKDIR /usr/share/nginx/html

# Copy built Angular app
COPY --from=builder /app/dist/frontend/browser ./

# Remove source maps and license files to reduce image size
RUN rm -rf /usr/share/nginx/html/**/*.map /usr/share/nginx/html/**/*.txt

# Copy config template for runtime env injection
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["/bin/sh", "-c", "\
    envsubst '${API_URL}' < assets/config/app.config.template.js > assets/config/app.config.js && \
    envsubst '${API_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && \
    exec nginx -g 'daemon off;'"]
