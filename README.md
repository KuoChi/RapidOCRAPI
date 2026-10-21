<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/RapidAI/RapidOCRAPI/releases/download/v0.2.0/rapidocr_api_logo_v2_dark.png" width="60%" height="60%">
    <source media="(prefers-color-scheme: light)" srcset="https://github.com/RapidAI/RapidOCRAPI/releases/download/v0.2.0/rapidocr_api_logov2_white.png" width="60%" height="60%">
    <img alt="Shows an illustrated sun in light mode and a moon with stars in dark mode." src="https://github.com/RapidAI/RapidOCRAPI/releases/download/v0.2.0/rapidocr_api_logov2_white.png">
  </picture>

 <br/>
  <a href=""><img src="https://img.shields.io/badge/Python->=3.6-aff.svg"></a>
  <a href=""><img src="https://img.shields.io/badge/OS-Linux%2C%20Win%2C%20Mac-pink.svg"></a>
  <a href="https://github.com/RapidAI/RapidOCRAPI/graphs/contributors"><img src="https://img.shields.io/github/contributors/RapidAI/RapidOCRAPI?color=9ea"></a>
  <a href="https://github.com/RapidAI/RapidOCRAPI/stargazers"><img src="https://img.shields.io/github/stars/RapidAI/RapidOCRAPI?color=ccf" ></a>
  <a href="https://pypistats.org/packages/rapidocr_api"><img src="https://img.shields.io/pypi/dm/rapidocr_api?style=flat&label=rapidocr_api"></a>
  <a href="https://pypi.org/project/rapidocr_api/"><img alt="PyPI" src="https://img.shields.io/pypi/v/rapidocr_api"></a>
  <a href="https://choosealicense.com/licenses/apache-2.0/"><img src="https://img.shields.io/badge/License-Apache%202-dfd.svg"></a>
  <a href="https://semver.org/"><img alt="SemVer2.0" src="https://img.shields.io/badge/SemVer-2.0-brightgreen"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

</div>

### 📖 简介

- 该包是将[rapidocr](./rapidocr/install.md)库做了API封装，采用[FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/)实现。
- 定位是一个快速调用`rapidocr`的API接口，没有考虑多进程处理并发请求，如果有这需求的小伙伴，可以看看[gunicorn](https://gunicorn.org/)等。

### 📌 版本依赖关系

|`rapidocr_api`|`rapidocr`|
|:---|:---|
|`v0.2.x`|`rapidocr>1.0.0,<3.0.0`|
|`v0.1.x`|`rapidocr_onnxruntime`|

### 🛠️ 安装

```bash linenums="1"
pip install rapidocr_api
```

### 🚀 使用

#### ▶️ 启动服务

```bash
# 默认参数启动
rapidocr_api

# 指定参数：端口与进程数量；
rapidocr_api -ip 0.0.0.0 -p 9005 -workers 2
```

#### 📞 调用服务

💻 命令行使用：

```bash
curl -F image_file=@1.png http://0.0.0.0:9003/ocr
```

🐍 Python脚本使用：

```python
import requests

url = 'http://localhost:9003/ocr'
img_path = 'tests/test_files/ch_en_num.jpg'

with open(img_path, 'rb') as f:
    file_dict = {'image_file': (img_path, f, 'image/png')}
    response = requests.post(url, files=file_dict, timeout=60)

print(response.json())
```

#### 🎛️ `use_det` / `use_cls` / `use_rec` 参数

`/ocr` 接受三个可选的表单字段，分别控制检测、方向分类、识别三个步骤：

- 未传时使用 `rapidocr` 配置中的默认值（三者均为 `true`）。
- 可传 `true` / `false`（也接受 `1`/`0`、`yes`/`no`、`on`/`off`）；无法解析的值返回 `422`。
- 每个请求的参数互不影响，并发请求使用不同参数也不会互相干扰。

返回格式为 `{"0": {...}, "1": {...}, ...}`，每一项包含的字段取决于参数组合：

|`use_det`|`use_rec`|返回字段|说明|
|:---|:---|:---|:---|
|`true`|`true`|`rec_txt`、`dt_boxes`、`score`|默认，完整 OCR 结果|
|`true`|`false`|`dt_boxes`、`score`|仅检测；`score` 为检测框的置信度，不是识别置信度|
|`false`|`true`|`rec_txt`、`score`|跳过检测，把整张图当作单行文字识别|
|`false`|`false`|无（返回 `{}`）|只做方向分类，API 不返回分类结果|

- `use_cls` 只决定识别前是否先做方向分类，不影响返回字段。
- `use_det=false` 只适合已裁切好的单行文字图片；对多行图片识别结果会很差。

```bash
# 仅检测文字框
curl -F image_file=@1.png -F use_rec=false http://0.0.0.0:9003/ocr

# 对单行文字图片直接识别
curl -F image_file=@line.png -F use_det=false http://0.0.0.0:9003/ocr
```

### 🐳 Docker 部署

```bash
# 构建镜像（使用仓库内源码，构建时会下载模型到镜像中）
docker build -t rapidocr-api .

# 运行
docker run -d --name rapidocr-api -p 9003:9003 rapidocr-api

# 测试
curl -F image_file=@tests/test_files/ch_en_num.jpg http://localhost:9003/ocr
```

- 构建时需要能访问 PyPI 与模型下载源；模型已打包进镜像，运行时不需要外网。
- 镜像内置 `HEALTHCHECK`（请求 `GET /`），不依赖 `curl` / `wget`。
- 默认以 1 个 uvicorn worker 运行：每种参数组合各有一个 `RapidOCR` 实例，单个 worker 即可并发处理请求，增加 worker 只会多占内存。
- 内存参考：空闲约 65 MiB；16 个并发请求时峰值约 1.25 GiB，建议内存上限设为 1.5–2 GB。
- 如果所在环境对 Docker 网段有限制，请在 Docker daemon 的 `bip` / `default-address-pools` 中指定可用网段，不要依赖默认值。

### ☁️ Coolify 部署

1. **New Resource → Public Repository**，填入仓库地址与分支。
2. **Build Pack** 选 **Dockerfile**，Dockerfile 位置保持 `/Dockerfile`。
3. **Ports Exposes** 填 `9003`，**Domains** 填要使用的域名（HTTPS 由 Coolify 的 Traefik 处理）。
4. **Health check**：Coolify 界面的健康检查需要容器内有 `curl` / `wget`，本镜像没有，请在界面上关闭，改用 Dockerfile 内的 `HEALTHCHECK`。
5. **资源限制**：内存建议 1.5–2 GB。
6. 部署完成后测试：

    ```bash
    curl -F image_file=@tests/test_files/ch_en_num.jpg https://<你的域名>/ocr
    ```

#### 🔐 使用 Basic Auth 保护 API

API 本身没有任何认证。若绑定在公开域名上，建议用 Traefik basicauth 保护，账号密码通过 Coolify 环境变量传入，不写进仓库：

1. 在本地生成 bcrypt 哈希：

    ```bash
    htpasswd -nbB ocr '<密码>'
    # 输出类似 ocr:$2y$05$xxxxxxxx...
    ```

2. **Environment Variables** 新增 `OCR_BASIC_AUTH_USERS`，值为上一步的整行输出，并**勾选 Is Literal**（否则哈希中的 `$` 会被当成变量展开）。
3. **General → Container Labels**：改为手动管理 labels，并**关闭 “Escape special characters in labels”**（否则 `${...}` 不会被替换）。
4. 新增 middleware label，并把它加到 HTTPS router 的 middlewares（只加在 `https-0-...`，不要加在 `http-0-...`，避免账号密码在跳转 HTTPS 前以明文发送）：

    ```text
    traefik.http.middlewares.rapidocr-auth.basicauth.users=${OCR_BASIC_AUTH_USERS}
    traefik.http.routers.https-0-<应用 uuid>.middlewares=gzip,rapidocr-auth
    ```

5. Redeploy 后验证：未带账号密码返回 `401`，`curl -u ocr:<密码> ...` 返回 `200`。

注意：

- 改为手动管理 labels 后，Coolify 不再自动更新 labels，修改域名或端口时需要自行调整 router 相关的 label。
- 关闭 escape 会作用于该应用的所有 labels；之后若启用 www / non-www 跳转（其 label 含 `$`），需要重新检查。
- 以上流程依据 Coolify v4.4.7 的行为整理；也可以直接使用 Coolify 内置的 HTTP Basic Authentication（General → Security），无需手动维护 labels。

### 📚 文档

完整文档请移步：[docs](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr_api/usage/)
