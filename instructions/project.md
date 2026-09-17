# Project Instructions

提供不同的AI平台可以參考此檔案中的指令與定義，進行相關的操作與設定。

## Framework Decisions
此專案主要根據以下程式語言與主要框架進行開發，如果開發過程中需要使用到第三方套件，可不必受限於此，但應確保與主要框架的相容性。

- Programming Language: Python 3.14
- Framework: FastAPI 0.141.1
- PostgreSQL 17
- Redis 8.1.0

## Environment
1. Python開發環境請使用虛擬環境`venv`進行開發，並且確保依賴套件已安裝且都有寫入`requirements.txt`。
2. 資料庫請使用 PostgreSQL並且以Docker Container 方式運行，在開發環境的`環境配置檔`中進行相關設定，連線資訊可以從該配置檔中取得，連線密碼亦可從中取得。
3. Redis 請以 Docker Container 方式運行，並在開發環境的`環境配置檔`中進行相關設定，連線資訊可以從該配置檔中取得，連線密碼亦可從中取得。
4. 因後續完成將以Docker Container 方式運行整個專案，請確保所有服務皆能在 Docker 環境中正常運作，相關環境參數請使用`os.getenv("<ENV_VARIABLE_NAME>", "<DEFAULT_VALUE>")`。

## References
| Title | Path |
|---|---|
| Python Code Standard | `instructions/python-code-standard.md` |
| Project Architecture | `instructions/architecture.md` |
| SQL Standard | `instructions/sql-standard.md` |

## 其他
此專案所產生文件皆應遵循上述指令與定義，且請使用`繁體中文`顯示，專業且清楚地呈現專案相關資訊。
專業語法可以使用`英文`撰寫，，並且格式需要統一，確保專案文件的一致性與可讀性。