FROM node:18-alpine
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Create a non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application files
COPY . .

# Build the Next.js application
RUN npm run build

# Set ownership for the nextjs user
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "start"]
