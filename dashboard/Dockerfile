# Stage 1: Build the React app
FROM node:alpine AS build

# Set the working directory
WORKDIR /app

# Copy the package.json and package-lock.json files
COPY package*.json ./

# Install the dependencies
RUN npm install

# Copy the app files
COPY . .

# Build the app
RUN npm run build

# Stage 2: Serve the React app using http-server
FROM node:alpine

# Install http-server
RUN npm install -g http-server

# Copy the build output to the http-server directory
COPY --from=build /app/dist /usr/src/app

# Expose port 3000
EXPOSE 3000

# Start http-server
CMD ["http-server", "/usr/src/app", "-p", "3000"]
