FROM oven/bun:1 AS build

WORKDIR /app

COPY web/package.json ./
COPY web/tsconfig.json ./
COPY web/tsconfig.app.json ./
COPY web/tsconfig.node.json ./
COPY web/vite.config.ts ./
RUN bun install

COPY web/index.html ./
COPY web/src ./src
RUN bun run build

FROM nginx:1.27-alpine

COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

