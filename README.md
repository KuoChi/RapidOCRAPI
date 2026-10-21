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

### 📖 簡介

- 本套件將 [rapidocr](https://github.com/RapidAI/RapidOCR) 函式庫包裝成 API，使用 [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) 實作。
- 定位是一個快速呼叫 `rapidocr` 的 API 介面。單一 worker 就能同時處理多個請求：每種 `use_*` 參數組合各有一個 `RapidOCR` 實例，同時進來的請求彼此不會干擾（詳見下方參數說明）。

### 📌 版本相依性

|`rapidocr_api`|`rapidocr`|
|:---|:---|
|本儲存庫 `coolify-deploy` 分支|`rapidocr==3.10.0`，另需安裝 `onnxruntime`|
|`v0.2.x`（PyPI）|`rapidocr>1.0.0,<3.0.0`|
|`v0.1.x`（PyPI）|`rapidocr_onnxruntime`|

### 🛠️ 安裝

建議使用 Docker 部署，請見下方「🐳 Docker 部署」。

如果要直接在本機執行，請從本儲存庫的原始碼安裝相依套件。PyPI 上的 `rapidocr_api` 沒有包含本儲存庫的修正，也不會安裝 `onnxruntime`：

```bash linenums="1"
git clone -b coolify-deploy https://github.com/KuoChi/RapidOCRAPI.git
cd RapidOCRAPI
pip install -c constraints.txt -r requirements.txt onnxruntime
```

### 🚀 使用

#### ▶️ 啟動服務

在儲存庫根目錄執行：

```bash
# 使用預設參數啟動
python -m rapidocr_api.main

# 指定參數：IP 與連接埠
python -m rapidocr_api.main -ip 0.0.0.0 -p 9005
```

- `-workers` 預設為 1，一般不需要調整：單一 worker 就能同時處理多個請求，增加 worker 只會多佔記憶體。
- 預設模型已包含在 `rapidocr` 套件中，執行時不需要連外。

#### 📞 呼叫服務

💻 命令列使用：

```bash
curl -F image_file=@1.png http://0.0.0.0:9003/ocr
```

🐍 Python 腳本使用：

```python
import requests

url = 'http://localhost:9003/ocr'
img_path = 'tests/test_files/ch_en_num.jpg'

with open(img_path, 'rb') as f:
    file_dict = {'image_file': (img_path, f, 'image/png')}
    response = requests.post(url, files=file_dict, timeout=60)

print(response.json())
```

#### 🎛️ `use_det` / `use_cls` / `use_rec` 參數

`/ocr` 接受三個選填的表單欄位，分別控制偵測、方向分類、辨識三個步驟：

- 沒有傳入時，使用 `rapidocr` 設定中的預設值（三者都是 `true`）。
- 可傳入 `true` / `false`（也接受 `1`/`0`、`yes`/`no`、`on`/`off`）；無法解析的值會回傳 `422`，格式與 FastAPI 原生驗證錯誤相同，會一次列出所有有問題的欄位。
- 每個請求的參數互不影響，同時進來的請求使用不同參數也不會互相干擾。

回傳格式為 `{"0": {...}, "1": {...}, ...}`，每一筆包含哪些欄位取決於參數組合：

|`use_det`|`use_rec`|回傳欄位|說明|
|:---|:---|:---|:---|
|`true`|`true`|`rec_txt`、`dt_boxes`、`score`|預設，完整的 OCR 結果|
|`true`|`false`|`dt_boxes`、`det_score`|只做偵測；`det_score` 是偵測框的信心分數，與辨識的信心分數 `score` 區分|
|`false`|`true`|`rec_txt`、`score`|跳過偵測，把整張圖當成單行文字辨識|
|`false`|`false`|無（回傳 `{}`）|只做方向分類，API 不回傳分類結果|

- `use_cls` 只決定辨識前是否先做方向分類，不影響回傳欄位。
- `use_det=false` 只適合已經裁切好的單行文字圖片；對多行圖片的辨識結果會很差。
- 沒有傳 `image_file` 或 `image_data`，或圖片無法解碼（非圖片、base64 錯誤、檔案被截斷）時，回傳 `400`。

```bash
# 只偵測文字框
curl -F image_file=@1.png -F use_rec=false http://0.0.0.0:9003/ocr

# 對單行文字圖片直接辨識
curl -F image_file=@line.png -F use_det=false http://0.0.0.0:9003/ocr
```

### 🐳 Docker 部署

```bash
# 建置映像檔（使用儲存庫內的原始碼）
docker build -t rapidocr-api .

# 執行
docker run -d --name rapidocr-api -p 9003:9003 rapidocr-api

# 測試
curl -F image_file=@tests/test_files/ch_en_num.jpg http://localhost:9003/ocr
```

- 建置時需要能連到 PyPI；預設模型已包含在 `rapidocr` 套件中，執行時不需要連外。
- 映像檔內建 `HEALTHCHECK`（請求 `GET /`），不依賴 `curl` / `wget`。
- 容器以 UID 10001 的非 root 使用者（`app`）執行；程式與模型都只需讀取，也可搭配唯讀檔案系統執行。
- 預設以 1 個 uvicorn worker 執行：每種參數組合各有一個 `RapidOCR` 實例，單一 worker 就能同時處理多個請求，增加 worker 只會多佔記憶體。
- 同時進行的推論數量由環境變數 `ocr_max_concurrency` 控制，預設等於 `os.cpu_count()`；超過的請求會排隊等候。注意：容器的 CPU 限制（例如 `--cpus`、Coolify 的 CPU limit）不會反映在 `os.cpu_count()` 上，有設 CPU 限制時請手動設定這個值。
- 記憶體參考值（12 顆 CPU 的機器，40 個請求同時進來，以 cgroup `memory.peak` 量測峰值）：

    |`ocr_max_concurrency`|峰值記憶體|160 個請求耗時|
    |:---|:---|:---|
    |12（預設）|約 2.7 GiB|約 37 秒|
    |4|約 2.0 GiB|約 59 秒|
    |2|約 1.6 GiB|約 69 秒|

- 閒置時約 65 MiB；處理過請求後記憶體不會完全釋放（實測約 1.2–1.7 GiB）。記憶體上限請依 `ocr_max_concurrency` 對應的峰值再預留餘裕，使用預設值時建議 3 GB 以上。
- 如果所在環境對 Docker 網段有限制，請在 Docker daemon 的 `bip` / `default-address-pools` 指定可用的網段，不要依賴預設值。

### ☁️ Coolify 部署

1. **New Resource → Public Repository**，填入儲存庫網址與分支。
2. **Build Pack** 選 **Dockerfile**，Dockerfile 位置維持 `/Dockerfile`。
3. **Ports Exposes** 填 `9003`，**Domains** 填要使用的網域（HTTPS 由 Coolify 的 Traefik 處理）。
4. **Health check**：Coolify 介面上的健康檢查需要容器內有 `curl` / `wget`，本映像檔沒有，請在介面上關閉，改用 Dockerfile 內的 `HEALTHCHECK`。
5. **資源限制**：記憶體上限依 `ocr_max_concurrency` 設定，參考上方「🐳 Docker 部署」的數值，使用預設值時建議 3 GB 以上。如果有設 CPU 上限，請在 **Environment Variables** 一併設定 `ocr_max_concurrency`，例如設成與 CPU 上限相同的數字。
6. 部署完成後測試：

    ```bash
    curl -F image_file=@tests/test_files/ch_en_num.jpg https://<你的網域>/ocr
    ```

#### 🔐 使用 Basic Auth 保護 API

API 本身沒有任何驗證機制。如果綁定在公開網域上，建議用 Traefik basicauth 保護，帳號密碼透過 Coolify 環境變數帶入，不寫進儲存庫：

1. 在本機產生 bcrypt 雜湊值：

    ```bash
    htpasswd -nbB ocr '<密碼>'
    # 輸出類似 ocr:$2y$05$xxxxxxxx...
    ```

2. **Environment Variables** 新增 `OCR_BASIC_AUTH_USERS`，值為上一步輸出的整行內容，並**勾選 Is Literal**（否則雜湊值中的 `$` 會被當成變數展開）。
3. **General → Container Labels**：改為手動管理 labels，並**關閉「Escape special characters in labels」**（否則 `${...}` 不會被替換）。
4. 新增 middleware label，並把它加到 HTTPS router 的 middlewares（只加在 `https-0-...`，不要加在 `http-0-...`，避免帳號密碼在轉址到 HTTPS 之前以明文送出）：

    ```text
    traefik.http.middlewares.rapidocr-auth.basicauth.users=${OCR_BASIC_AUTH_USERS}
    traefik.http.routers.https-0-<應用程式 uuid>.middlewares=gzip,rapidocr-auth
    ```

5. Redeploy 後驗證：沒帶帳號密碼會回傳 `401`，`curl -u ocr:<密碼> ...` 會回傳 `200`。

注意：

- 改為手動管理 labels 後，Coolify 不會再自動更新 labels；修改網域或連接埠時，需要自行調整 router 相關的 label。
- 關閉 escape 會套用到這個應用程式的所有 labels；之後如果啟用 www / non-www 轉址（這類 label 含有 `$`），需要重新檢查。
- 以上流程依據 Coolify v4.4.7 的行為整理；也可以直接使用 Coolify 內建的 HTTP Basic Authentication（General → Security），不需要手動維護 labels。

### 🧪 測試

在儲存庫根目錄執行：

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

測試涵蓋未傳旗標、8 種 `use_*` 組合的回傳欄位、不合法的值回傳 `422`、沒有圖片或圖片無法解碼時回傳 `400`、`image_data`（base64）上傳、旗標不會殘留到下一個請求，以及並發請求的結果內容比對。

### 📚 文件

完整文件請參考：[docs](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr_api/usage/)
