# Manage Backend

## 本機基礎設施

本專案以 Docker Compose 提供 PostgreSQL 17 與 Redis Server 8.10.1。Windows 開發環境
需先安裝 WSL 2、啟用 Docker Desktop 的 WSL integration，並在專案虛擬環境安裝
`requirements.txt` 內的套件。

先在 PowerShell 建立不納入 Git 的本機設定檔：

```powershell
Copy-Item .env.example .env
```

啟動並等待兩個服務通過 health check：

```powershell
wsl.exe -d Ubuntu-24.04 -- docker compose --env-file .env up -d --wait postgres redis
```

查看服務狀態或 logs：

```powershell
wsl.exe -d Ubuntu-24.04 -- docker compose --env-file .env ps
wsl.exe -d Ubuntu-24.04 -- docker compose --env-file .env logs postgres redis
```

`.env` 會由 Docker Compose 自動讀取，但 Python 的 `os.getenv` 不會自行載入此檔案。
在 host 執行 application 或 integration tests 前，可在目前 PowerShell process 載入設定：

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        Set-Item -Path "Env:$($matches[1])" -Value $matches[2]
    }
}
```

Host process 使用 localhost URLs：

```text
DATABASE_URL=postgresql://progresql:progresql@localhost:5432/progresql
REDIS_URL=redis://:progresql@localhost:6379/0
```

未來 application container 必須透過 Compose service DNS 注入以下值：

```text
DATABASE_URL=postgresql://progresql:progresql@postgres:5432/progresql
REDIS_URL=redis://:progresql@redis:6379/0
```

目前 Compose 僅建立基礎設施，不會初始化 application schema、table 或 data。

## 測試

載入 `.env` 後執行 integration tests：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\integration
```

執行完整 regression tests：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 停止與清除

一般停止會保留 `postgres_data` 與 `redis_data` named volumes：

```powershell
wsl.exe -d Ubuntu-24.04 -- docker compose --env-file .env down
```

只有確定要永久刪除本機 PostgreSQL／Redis data 時，才明確執行 destructive reset：

```powershell
wsl.exe -d Ubuntu-24.04 -- docker compose --env-file .env down -v
```
