# Multi-stage build: Vite compile in node:alpine, then serve the static dist
# with `serve` (small, sane SPA defaults — index.html fallback, no nginx config
# to maintain). Port 5173 so the rest of the stack doesn't need to change.

FROM node:20-alpine AS build
WORKDIR /app

COPY package.json ./
# `npm install` rather than `npm ci` — we don't ship a lockfile in the demo.
RUN npm install --no-audit --no-fund

COPY tsconfig.json tsconfig.node.json vite.config.ts index.html ./
COPY src ./src

# Bake the backend URL into the bundle. Override at build time:
#   docker build --build-arg API_BASE_URL=https://api.example.com .
ARG API_BASE_URL=http://localhost:8002
ENV VITE_API_BASE_URL=${API_BASE_URL}

RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
RUN npm install --global serve@14
COPY --from=build /app/dist ./dist

EXPOSE 5173
# `-s` enables SPA mode (serves index.html for unknown paths). The frontend
# is single-page so this matters if we ever add client-side routing.
CMD ["serve", "-s", "dist", "-l", "5173", "--no-clipboard"]
