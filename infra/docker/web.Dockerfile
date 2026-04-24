FROM node:22-alpine

WORKDIR /app

COPY package.json /app/package.json
COPY apps/web /app/apps/web
COPY packages/contracts /app/packages/contracts

RUN npm install
RUN npm run contracts:generate:web

WORKDIR /app/apps/web

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
