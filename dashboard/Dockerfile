# Stage 1: Build the React app
FROM --platform=linux/amd64 node:alpine AS build

# Add the build argument for the environment variable
ARG VITE_DASHBOARD_BASE_URL

# Set the environment variable within the build container
ENV VITE_DASHBOARD_BASE_URL=${VITE_DASHBOARD_BASE_URL}

# Set the working directory
WORKDIR /app

# Copy the package.json and package-lock.json files
COPY package*.json ./

# Install the dependencies
RUN npm install

# Copy the rest of the application files
COPY . .

# Ensure that the environment variable is available during the build process
RUN echo "VITE_DASHBOARD_BASE_URL=${VITE_DASHBOARD_BASE_URL}" > .env

# Build the app using Vite
RUN npm run build

# Stage 2: Serve the React app using NGINX
FROM --platform=linux/amd64 nginx:alpine

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
