FROM node:20-alpine AS builder
WORKDIR /app
COPY apps/web-visualizer/package.json apps/web-visualizer/package-lock.json ./
RUN npm ci
COPY apps/web-visualizer/ ./
RUN mkdir -p ./public
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./
RUN npm install --only=production
EXPOSE 3000
CMD ["npm", "start"]
