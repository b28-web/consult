FROM node:20-slim

WORKDIR /app

# Install curl for healthcheck and ca-certificates for TLS
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Enable corepack for pnpm
RUN corepack enable

# Copy package files
COPY workers/intake/package.json ./

# Install dependencies (no lockfile for standalone worker build)
RUN pnpm install

# Copy worker source
COPY workers/intake/src ./src
COPY workers/intake/wrangler.toml workers/intake/tsconfig.json ./

# Create entrypoint that writes .dev.vars from environment
RUN echo '#!/bin/sh\n\
echo "NEON_DATABASE_URL=$NEON_DATABASE_URL" > .dev.vars\n\
echo "INTAKE_API_KEY=$INTAKE_API_KEY" >> .dev.vars\n\
exec pnpm wrangler dev --local --port 8787 --ip 0.0.0.0\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Run wrangler dev
EXPOSE 8787

# Use remote mode to avoid local TLS issues with Neon
CMD ["/bin/sh", "-c", "echo \"NEON_DATABASE_URL=$NEON_DATABASE_URL\" > .dev.vars && echo \"INTAKE_API_KEY=$INTAKE_API_KEY\" >> .dev.vars && exec pnpm wrangler dev --remote --port 8787 --ip 0.0.0.0"]
