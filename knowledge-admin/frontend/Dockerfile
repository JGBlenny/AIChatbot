FROM node:18-alpine as builder

WORKDIR /app

# 安裝依賴
COPY package*.json ./
RUN npm install

# 複製原始碼
COPY . .

# 建置
RUN npm run build

# 生產環境
FROM nginx:alpine

# 複製建置結果
COPY --from=builder /app/dist /usr/share/nginx/html

# 複製 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
