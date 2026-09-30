# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Builder
FROM deps AS builder
WORKDIR /app
COPY . .
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_PUBLIC_API_URL=http://backend:8000

# Set the correct working directory for standalone output
WORKDIR /app/.next/standalone

# Copy the standalone server files and static assets from builder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Expose port and start the server
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
