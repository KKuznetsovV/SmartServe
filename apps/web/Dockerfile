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
COPY apps/web/package.json apps/web/
RUN pnpm install --frozen-lockfile --ignore-scripts

# ── builder ───────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/packages/types/node_modules packages/types/node_modules 2>/dev/null || true
COPY --from=deps /repo/packages/api-client/node_modules packages/api-client/node_modules 2>/dev/null || true
COPY --from=deps /repo/apps/web/node_modules apps/web/node_modules 2>/dev/null || true
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @smartserve/types build && \
    pnpm --filter @smartserve/api-client build && \
    pnpm --filter @smartserve/web build

# ── runner ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /repo/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
