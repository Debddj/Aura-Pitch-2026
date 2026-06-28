FROM node:20-alpine AS builder
WORKDIR /app
COPY apps/web-visualizer/package.json ./
RUN npm install
COPY apps/web-visualizer/ ./
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
