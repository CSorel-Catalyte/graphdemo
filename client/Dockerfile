FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Fix permissions for node_modules/.bin
RUN chmod +x node_modules/.bin/*

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]