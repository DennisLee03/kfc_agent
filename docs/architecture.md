# KFC 優惠券推薦 AI Agent - 系統架構文檔

## 1. FSM 狀態機設計

### 狀態定義

```
State (Enum):
├── IDLE          # 初始狀態
├── ASKING_INFO   # 收集用戶資訊
├── SHOW_MENU     # 顯示菜單
├── FILTERING     # 過濾優惠券
├── RESULTS       # 顯示結果
└── DONE          # 完成對話
```

### 狀態轉換圖 (FSM Diagram)

```
┌─────────────────────────────────────────────────────────────────┐
│                         KFC Agent FSM                            │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────┐
                    │   IDLE   │ (初始狀態)
                    └────┬─────┘
                         │
                         │ 啟動 Agent
                         │ process("")
                         ▼
                  ┌──────────────┐
           ┌─────▶│ ASKING_INFO  │◀──────┐
           │      └──────┬───────┘       │
           │             │               │
           │             ├───────────────┘ 資訊不完整
           │             │                 繼續詢問
           │             │
           │             │ want_menu=true
           │             │ (用戶不知道吃什麼)
           │             ▼
           │      ┌─────────────┐
           │      │ SHOW_MENU   │
           │      └──────┬──────┘
           │             │
           │             │ 顯示完畢
           │             │
           └─────────────┘
                         │
                         │ got_info
                         │ (資訊完整 + 用戶說「好了」)
                         ▼
                  ┌─────────────┐
                  │  FILTERING  │ (過濾優惠券)
                  └──────┬──────┘
                         │
                         │ 自動
                         ▼
                  ┌─────────────┐
                  │   RESULTS   │ (顯示推薦結果)
                  └──────┬──────┘
                         │
                         ├─────────────┐
                         │             │
                 用戶滿意          用戶說「重來」
                         │             │
                         ▼             │
                  ┌─────────────┐     │
                  │    DONE     │     │
                  └─────────────┘     │
                                      │
                                      ▼
                               重置到 IDLE
```

### 狀態轉換表

| 當前狀態 | 事件/條件 | 下一狀態 | 動作 |
|---------|----------|---------|------|
| IDLE | 啟動 Agent | ASKING_INFO | 顯示歡迎訊息 + 品項列表 |
| ASKING_INFO | want_menu=true | SHOW_MENU | 顯示完整菜單 |
| ASKING_INFO | got_info (資訊完整 + 觸發詞) | FILTERING | 開始過濾優惠券 |
| ASKING_INFO | 資訊不完整 | ASKING_INFO | 顯示已記錄資訊，提示繼續 |
| SHOW_MENU | 顯示完畢 | ASKING_INFO | 等待用戶輸入偏好 |
| FILTERING | 自動 | RESULTS | 顯示過濾後的推薦 |
| RESULTS | 用戶滿意 | DONE | 結束對話 |
| RESULTS | 用戶說「重來」 | IDLE | 重置狀態，重新開始 |

---

## 2. 系統整體流程圖

```
┌─────────────────────────────────────────────────────────────────┐
│                      系統啟動流程                                 │
└─────────────────────────────────────────────────────────────────┘

開始
 │
 ▼
檢查優惠券快取
 │
 ├─── 快取不存在或過期？
 │         │
 │        YES ────────────┐
 │         │              │
 │        NO              ▼
 │         │        調用 KFC API
 │         │              │
 │         │              ▼
 │         │        使用 LLM 解析
 │         │        (parse_coupon_with_llm)
 │         │              │
 │         │              ▼
 │         │        儲存到快取
 │         │              │
 │         └──────────────┘
 │                        │
 ▼                        ▼
載入優惠券資料 (coupons.json)
 │
 ▼
初始化 KFCAgent(coupons)
 │
 ▼
啟動對話流程 (FSM)


┌─────────────────────────────────────────────────────────────────┐
│                      對話流程 (User Interaction)                  │
└─────────────────────────────────────────────────────────────────┘

用戶輸入
 │
 ▼
┌────────────────────────────┐
│   LLM 意圖提取              │
│  (call_llm + EXTRACT_INFO)  │
└────────┬───────────────────┘
         │
         ▼
    提取結果：
    {
      num_people: int | null,
      preferences: [str],
      want_menu: bool
    }
         │
         ▼
    合併到 context
    (累積用戶資訊)
         │
         ├──── want_menu=true? ───┐
         │                         │
         NO                       YES
         │                         │
         ▼                         ▼
    資訊完整且用戶說「好了」?   顯示完整菜單
         │                         │
         │                         └──── 返回 ASKING_INFO
        YES
         │
         ▼
    ┌─────────────────┐
    │  過濾優惠券      │
    │  (filtering)     │
    └────┬────────────┘
         │
         ▼
    For each coupon:
    ├─ 檢查是否包含偏好品項
    │  (模糊匹配: pref in item or item in pref)
    ├─ 計算符合度分數 (match_score)
    └─ 計算人數差異 (people_diff)
         │
         ▼
    排序：
    1. match_score 降序
    2. people_diff 升序
    3. price 升序
         │
         ▼
    過濾：保留 match_score > 0
         │
         ▼
    ┌─────────────────┐
    │  顯示推薦結果    │
    │  (top N)         │
    └────┬────────────┘
         │
         ▼
    等待用戶反饋
    (滿意/重來)


┌─────────────────────────────────────────────────────────────────┐
│                    LLM 意圖提取流程                               │
└─────────────────────────────────────────────────────────────────┘

用戶輸入 (user_input)
 │
 ▼
構建 Prompt (EXTRACT_INFO_PROMPT)
 │
 ├─ 同義詞映射規則
 ├─ 示例 (few-shot learning)
 └─ 嚴格規則 (防止幻覺)
 │
 ▼
呼叫 LLM API
(Ollama gemma3:4b)
 │
 ▼
解析 JSON 回應
 │
 ├─ 清理 markdown 標記
 ├─ 正則提取 JSON
 └─ json.loads()
 │
 ▼
回傳結構化資料
{
  num_people: 3,
  preferences: ["炸雞", "蛋撻"],
  want_menu: false
}
```

---

## 3. 優惠券匹配算法

```
┌─────────────────────────────────────────────────────────────────┐
│                    優惠券匹配流程                                 │
└─────────────────────────────────────────────────────────────────┘

輸入：
├─ user_preferences: ["炸雞", "蛋撻"]
├─ num_people: 3
└─ coupons: [...]

For each coupon in coupons:
 │
 ├─ matched_items = []
 ├─ matched_preferences = []
 │
 └─ For each pref in user_preferences:
     │
     └─ For each item in coupon.items:
         │
         ├─ 模糊匹配：pref in item OR item in pref
         │
         └─ 如果匹配：
             ├─ matched_items.append(item)
             └─ matched_preferences.append(pref)
 │
 ▼
計算分數：
├─ match_score = len(set(matched_preferences))  # 符合幾個偏好
├─ people_diff = abs(coupon.serves - num_people)  # 人數差異
└─ people_suitable = (people_diff <= 1)
 │
 ▼
記錄結果：
{
  ...coupon,
  matched_items: [...],
  match_score: 2,
  people_diff: 0,
  people_suitable: true
}

排序規則：
1. match_score 降序 (符合越多偏好越好)
2. people_diff 升序 (人數越接近越好)
3. price 升序 (價格越低越好)

過濾：
只保留 match_score > 0 的優惠券
```

---

## 4. 資料流圖 (Data Flow)

```
┌─────────────────────────────────────────────────────────────────┐
│                      資料流向                                     │
└─────────────────────────────────────────────────────────────────┘

KFC API
  │
  ▼ (fetch_raw)
raw.json
[{code, fcode, price, items_raw, category, img}, ...]
  │
  ▼ (parse_coupon_with_llm)
coupons.json
[{id, name, price, items, serves, description, ...}, ...]
  │
  ▼
KFCAgent.__init__(coupons)
  │
  ▼
self.coupons = [...]
self.available_items = {
  "炸雞類": ["炸雞", "辣脆雞", ...],
  "漢堡類": ["雞腿堡"],
  "飲料": ["可樂", "綠茶", ...],
  "甜點": ["蛋撻", "QQ球"],
  "其他": ["薯條"]
}
  │
  ▼ (對話過程)
self.context = {
  num_people: 3,
  preferences: ["炸雞", "蛋撻"],
  filtered_coupons: [...]
}
  │
  ▼ (顯示結果)
推薦給用戶
```

---

## 5. 模組架構

```
kfc_coupon_agent/
│
├── config/
│   ├── __init__.py
│   └── config.py              # 配置管理 (環境變數、API設定)
│
├── src/
│   ├── __init__.py
│   ├── agent.py               # KFCAgent (FSM 核心邏輯)
│   ├── scraper.py             # KFC API 爬蟲 + LLM 解析
│   ├── prompts.py             # LLM Prompt 模板
│   └── utils.py               # LLM API 呼叫工具
│
├── data/
│   ├── raw.json               # 原始 API 資料
│   └── coupons.json           # 解析後的優惠券
│
├── main.py                    # CLI 入口
├── frontend.py                # Streamlit Web UI
└── run_web.sh                 # Web 啟動腳本
```

---

## 6. 關鍵技術決策

### 6.1 為何使用 FSM？
- **清晰的狀態管理**：對話流程明確，易於追蹤
- **可預測性**：每個狀態的轉換條件明確
- **易於擴展**：新增狀態不影響既有邏輯
- **除錯友好**：可以清楚知道當前在哪個狀態

### 6.2 為何使用 LLM 進行意圖提取？
- **靈活性**：能理解各種口語化表達
- **同義詞處理**：自動映射「炸雞」「脆雞」「辣雞」
- **多意圖識別**：一句話同時提取人數和偏好
- **減少硬編碼**：不需要維護大量規則

### 6.3 優惠券匹配策略
- **雙向模糊匹配**：`pref in item or item in pref`
  - 允許部分匹配（「雞塊」匹配「上校雞塊」）
  - 提高召回率
- **多維度排序**：
  1. 符合度優先（滿足更多偏好）
  2. 人數接近度次之
  3. 價格最後
- **只顯示相關結果**：過濾掉 `match_score = 0` 的優惠券

---

## 7. 錯誤處理策略

```
LLM 呼叫失敗
 │
 └─ 回傳 None → Agent 提示「遇到問題，請再說一次」

JSON 解析失敗
 │
 └─ 正則提取 → 仍失敗 → 回傳 None

KFC API 失敗
 │
 └─ 嘗試載入快取 → 快取也失敗 → 程式退出

優惠券過濾結果為空
 │
 └─ 顯示「沒有找到符合的優惠券」+ 建議重新查詢
```

---

## 8. 未來擴展方向

1. **多輪對話優化**
   - 當結果為空時，Agent 主動建議放寬條件
   - 支援「換一個」「太貴了」等反饋

2. **個性化推薦**
   - 記錄用戶歷史偏好
   - 基於協同過濾推薦

3. **預算控制**
   - 支援「100元以內」等價格限制
   - 計算 CP 值排序

4. **圖片識別**
   - 支援上傳優惠券圖片自動識別

5. **多語言支援**
   - 英文、日文等
