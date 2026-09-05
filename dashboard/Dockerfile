# Stage 1: Build the React app
FROM node:22-alpine AS build

# Add the build argument for the environment variable
ARG VITE_DASHBOARD_BASE_URL
ARG VITE_AUTH_MODE=firebase
ARG VITE_TELEMETRY=on
ARG VITE_BILLING=on
ARG VITE_MCP_URL
ARG VITE_LOCAL_UID
ARG VITE_BRAND=waveassist
ENV VITE_AUTH_MODE=$VITE_AUTH_MODE VITE_TELEMETRY=$VITE_TELEMETRY \
    VITE_BILLING=$VITE_BILLING VITE_MCP_URL=$VITE_MCP_URL \
    VITE_LOCAL_UID=$VITE_LOCAL_UID VITE_BRAND=$VITE_BRAND

# Set the environment variable within the build container
ENV VITE_DASHBOARD_BASE_URL=${VITE_DASHBOARD_BASE_URL}

# Set the working directory
WORKDIR /app

# Copy the package.json and package-lock.json files
COPY package*.json ./

# Install the dependencies
COPY patches ./patches
ARG VITE_WAVEASSIST_FIREBASE_CONFIG
ENV VITE_WAVEASSIST_FIREBASE_CONFIG=${VITE_WAVEASSIST_FIREBASE_CONFIG}

ARG VITE_GITZOID_FIREBASE_CONFIG
ENV VITE_GITZOID_FIREBASE_CONFIG=${VITE_GITZOID_FIREBASE_CONFIG}

ARG VITE_WAVEASSIST_POSTHOG_KEY
ENV VITE_WAVEASSIST_POSTHOG_KEY=${VITE_WAVEASSIST_POSTHOG_KEY}

ARG VITE_GITZOID_POSTHOG_KEY
ENV VITE_GITZOID_POSTHOG_KEY=${VITE_GITZOID_POSTHOG_KEY}

RUN npm ci

# Copy the rest of the application files
COPY . .

# Ensure that the environment variable is available during the build process
RUN echo "VITE_DASHBOARD_BASE_URL=${VITE_DASHBOARD_BASE_URL}" > .env

# Build the app using Vite
RUN npm run build

# Stage 2: Serve the React app using NGINX
FROM nginx:alpine

# Copy the build output to the NGINX directory
COPY --from=build /app/dist /usr/share/nginx/html

# Remove default NGINX configuration file
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom NGINX configuration file
COPY nginx.conf /etc/nginx/conf.d

# Expose port 3000
EXPOSE 3000

# Start NGINX
CMD ["nginx", "-g", "daemon off;"]
