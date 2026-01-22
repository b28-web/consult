FROM node:20-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Enable corepack for pnpm
RUN corepack enable

# Copy package files
COPY workers/intake/package.json workers/intake/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy worker source
COPY workers/intake/src ./src
COPY workers/intake/wrangler.toml workers/intake/tsconfig.json ./

# Run wrangler dev
EXPOSE 8787

CMD ["pnpm", "wrangler", "dev", "--local", "--port", "8787", "--ip", "0.0.0.0"]
