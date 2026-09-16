# Python Code Standard

這是一個建立Python開發環境與指令應用於Github Copilot的說明文件。

## Code Standards

請依照以下規範生成、補全或重構 Python 程式碼，以維持一致、可讀且易於維護的程式風格。

### 1. 程式碼排版

- 使用 4 個空白作為縮排，不要使用 Tab 鍵。
- 單行長度不超過 **79 個字元**；Comment 與 Docstring 建議每行最多 **72 個字元**。
- 類別與頂層函式之間需保留兩行空白。
- 類別內的方法之間保留一行空白。

```python
def calculate_total(price, quantity):
    return price * quantity


class OrderProcessor:
    def __init__(self, items):
        self.items = items

    def process(self):
        for item in self.items:
            print(item)

```

### 2. 匯入其他套件規範

- 所有**import**語句放在檔案最上方，不可分散在程式碼中。
- 每行僅匯入一個模組。
- 禁止使用 `from module import *`。
- 可使用`import numpy as np`等習慣性別名，但須確保一致性。
- 同一個模組的匯入應集中在一起，不可分散在程式碼中。
- 匯入順序：
  1. 標準函式庫
  2. 第三方套件
  3. 專案內部模組

### 3. 命名規範

- 遵循 Python 標準命名方式，請遵守下表所示的命名規範。
  | 類型 | 命名方式 | 範例 |
  | -------- | ---------------- | ------------------- |
  | Variable | snake_case | `user_name` |
  | Function | snake_case | `get_user()` |
  | Method | snake_case | `calculate_total()` |
  | Class | PascalCase | `UserService` |
  | Constant | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
  | Module | snake_case | `user_service.py` |
  | Package | snake_case | `user_service` |
- Boolean變數命名請使用 `is_`、`has_`、`can_` 等前綴，例如：`is_active`、`has_permission`、`can_edit`。
- 模塊內私有方法、屬性、變數名稱應以下劃線 `_` 開頭，例如：`_private_method`、`_private_var`。
- 除計數器或迭代器外，避免使用單字母命名。

### 4. 文件與連線(Socket)

- 文件與Socket需要使用*with*語句，以確保資源正確釋放。
- 當需要手動關閉文件或Socket時，應使用 `try...finally` 確保資源釋放。

### 5. Function設計

- 函式應專注於單一職責，**不要單純為了縮短 Function 而過度拆分**。應以*責任是否清楚*作為主要判斷依據。
- 函式名稱應清楚描述其功能，避免使用模糊或過於簡短的名稱。
- 若函式為私有函式，名稱應以下劃線 `_` 開頭，例如：`_calculate_total()`。
- 須注意使用參數數量與順序，如果需要傳入過多參數，應優先考慮使用物件，如果為可選參數，可使用字典(**kwargs**) 來傳遞。
- 若為選填參數，未必免後續調整順序導致函式呼叫出現問題，建議可以在涵式設計上區分**必填**與**選填**，並且可以在選填參數前加入 `*`，以強制使用關鍵字傳入，例如：

```python
def example_function(required_param, *, optional_param=None):
    pass
```

- 參數需有明確的型態定義(Type Hint)與回傳值型態。

```python
def calculate_total(price: float, quantity: int) -> float:
    return price * quantity
```

- 若需要註釋涵式功能與使用方式，應使用完整的 docstring，說明用途、參數、回傳值與可能例外。

```python
def calculate_total(price, quantity):
    """
    計算總價

    parameters:
    price (float): 單價
    quantity (int): 數量

    returns:
    float: 總價

    raises:
    ValueError: 當 price 或 quantity 為負數時拋出
    """
    if price < 0 or quantity < 0:
        raise ValueError("Price and quantity must be non-negative")
    return price * quantity

```

### 6. Class設計

- 類別應遵循單一職責原則，每個類別應專注於單一功能或責任。
- 請勿將單一簡單功能封裝成類別，若是僅需一個函式即可完成的功能，應直接使用函式而非類別。
- 私有屬性應使用雙下劃線 `__` 開頭，例如：`__private_attr`。
- 私有方法應使用單下劃線 `_` 開頭，例如：`_private_method`。
- 應避免可以被外部直接修改內部屬性，應透過方法來控制對內部狀態的訪問與修改。
- 類別的初始化方法 `__init__` 應盡量簡潔，僅用於初始化屬性，避免在其中執行過多邏輯。
- 若該類別未繼承其他類別，需統一使用新式類別定義，即繼承自 `object`，例如：

```python
class MyClass(object):
    def __init__(self):
        self.attribute = None
```

### 7. 條件, None與Boolean判斷

- 條件判斷應盡量簡潔明瞭，避免過於複雜的邏輯，若邏輯過於複雜，應考慮先將其拆分為多個子條件或輔助函式。

```python
has_valid_role = user.account_type in {"admin", "manager"}
can_process = (
    user.is_active
    and user.has_permission
    and not user.is_deleted
    and has_valid_role
)

if can_process:
    process_user(user)
```

- 判斷 `None` 時應使用 `is None` 或 `is not None`，而非 `== None` 或 `!= None`。
- Boolean 判斷應直接使用變數本身，而非與 `True` 或 `False` 比較，例如：`if is_active:` 而非 `if is_active == True:`。

### 8. 字串設定

- 若無特別需求，請優先使用雙引號 `" "`，而非單引號 `' '`。
- 若字串內包含雙引號，則可使用單引號包裹字串，反之亦然。
- 使用f-string 來格式化字串，例如：`f"Hello, {name}!"`；不要使用.format() 或 % 進行字串格式化。

### 9. Collection 操作

- 優先使用Python提供的內建資料結構與方法，例如：`list`、`dict`、`set` 等，避免自行實現已有功能。
- 應用Comprehension時須考慮可讀性，如果過於複雜則一律採用傳統迴圈。
- Dict操作須清楚表達意圖，例如使用 `dict.get(key, default)` 來避免 KeyError，如果key需要於多處使用，應先將其賦值成**常數**，但該常數應具有明確的命名以表達其用途，例如: `USER_ROLE_KEY = "user_role"`。

### 10. 例外處理

- 儘量捕捉特定的例外，而非使用通用的 `except Exception`。
- 請勿將例外處理當作程式流程控制的手段。
- 請勿無條件忽略例外，應至少記錄或處理必要的情況。
- 例外處理需要提供足夠的上下文資訊，以便於除錯與問題追蹤。
- 例外處理應盡量保持簡潔，避免過度包裹程式碼。

### 11. Logging

- 根據專案需求，設定適當的日誌等級與輸出方式，例如使用 `logging` 模組來記錄資訊、警告與錯誤。
- 日誌訊息應包含足夠的上下文資訊，以便於除錯與問題追蹤，而非單純使用`print`。
- 可透過DEBUG等級的日誌來記錄詳細的除錯資訊。

### 12. 其他細節

- 避免使用魔法數字或字串，應將其定義為具名常數。
- 除非有特殊要求或因應擴展性，否則不要過度使用Design Pattern。
- 減少重複性程式碼，提取共用邏輯至函式或模組。
- 避免過深的巢狀結構，應適當拆分程式碼以提升可讀性。
- 請勿修改無關的程式碼，只能調整需求範圍內的程式碼。
- 移除不必要的程式碼與註解。
- 系統設定文件須優先使用**Context Manager**來管理資源，確保設定的正確性與一致性。
- 請勿生成不相關的程式碼、回應或檔案，應專注於需求本身需要的文件。
- 應優先檢查調整區域的影響，若未調整區域則不需要進行檢查，減少不必要的工作量。
