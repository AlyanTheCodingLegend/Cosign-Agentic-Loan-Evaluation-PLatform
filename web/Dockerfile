# Web app image. NEXT_PUBLIC_* values are inlined into the browser bundle at build time, so pass
# them as build arguments (they are public by design; never pass the service role key):
#   docker build -t ghcr.io/<owner>/cosign-web:0.1.0 \
#     --build-arg NEXT_PUBLIC_API_BASE_URL=https://<api-slug>-app.alternatefutures.ai \
#     --build-arg NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co \
#     --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key> web
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
# next.config.ts imports @next/env, so the full node_modules is kept.
COPY --from=build --chown=node:node /app ./
USER node
EXPOSE 3000
CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
