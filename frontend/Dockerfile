# Stage 1: Build the React TypeScript application
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependency specification locks
COPY package*.json ./
RUN npm ci

# Copy client source code
COPY . .

# Build Vite application with production settings
# Inject VITE_API_URL=/api/v1 so backend API calls route through Nginx proxy handler
RUN ENV VITE_API_URL=/api/v1 npm run build

# Stage 2: Serve compiled HTML/JS files via Nginx server
FROM nginx:stable-alpine

# Copy custom reverse proxy config into Nginx directories
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build folder from Stage 1 builder to default Nginx index directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose Nginx port
EXPOSE 80

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
