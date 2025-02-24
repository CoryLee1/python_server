# 使用 Python 3.10 作为基础镜像
FROM python:3.10

# 设置容器工作目录
WORKDIR /app

# 复制所有代码文件到容器
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 运行 Python 服务器
CMD ["python", "server.py"]
