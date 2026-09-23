# syntax=docker/dockerfile:1
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# ── deps ──────────────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/types/package.json packages/types/
COPY packages/api-client/package.json packages/api-client/
COPY packages/ui/package.json packages/ui/
COPY packages/config/package.json packages/config/
COPY apps/orders/package.json apps/orders/
RUN pnpm install --frozen-lockfile --ignore-scripts

# ── builder ───────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /repo
# deps stage holds only package.json files + node_modules (incl. per-package pnpm symlink dirs)
COPY --from=deps /repo/ ./
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @smartserve/types build && \
    pnpm --filter @smartserve/api-client build && \
    pnpm --filter @smartserve/orders build

# ── runner ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

# Monorepo standalone output nests the app under apps/orders/
COPY --from=builder --chown=nextjs:nodejs /repo/apps/orders/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/orders/.next/static ./apps/orders/.next/static
COPY --from=builder /repo/apps/orders/public ./apps/orders/public

USER nextjs
EXPOSE 3001
ENV PORT=3001
ENV HOSTNAME="0.0.0.0"
CMD ["node", "apps/orders/server.js"]
