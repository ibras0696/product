# syntax=docker/dockerfile:1.7
FROM node:24.13.0-alpine AS base

WORKDIR /app
RUN chown node:node /app

FROM base AS dependencies
COPY --chown=node:node package.json package-lock.json ./
USER node
RUN --mount=type=cache,target=/home/node/.npm,uid=1000,gid=1000 npm ci

FROM dependencies AS development
COPY --chown=node:node . .
USER node
EXPOSE 8080
CMD ["npm", "run", "dev"]

FROM dependencies AS build
COPY --chown=node:node . .
RUN npm run format:check \
    && npm run lint \
    && npm run typecheck \
    && npm run boundaries \
    && npm run test:run \
    && npm run build

FROM nginxinc/nginx-unprivileged:1.28.2-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "--quiet", "--tries=1", "--spider", "http://127.0.0.1:8080/"]
