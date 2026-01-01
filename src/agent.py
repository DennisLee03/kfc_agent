# agent.py
"""
KFC 優惠券推薦 AI Agent
基於 FSM (有限狀態機) 的對話管理
"""

from enum import Enum
import json
from src.utils import call_llm
from src.prompts import EXTRACT_INFO_PROMPT
from config.config import config


class State(Enum):
    """FSM 狀態定義"""
    IDLE = "idle"
    ASKING_INFO = "asking_info"
    SHOW_MENU = "show_menu"
    FILTERING = "filtering"
    RESULTS = "results"
    DONE = "done"


class KFCAgent:
    """KFC 優惠券推薦 Agent"""
    
    def __init__(self, coupons):
        """
        初始化 Agent

        參數：
            coupons: 優惠券資料列表
        """
        self.state = State.IDLE
        self.coupons = coupons
        self.context = {
            "num_people": None,
            "preferences": [],
            "filtered_coupons": []
        }
        # 提取所有可用的品項
        self.available_items = self._extract_all_items()
    
    def reset(self):
        """重置 Agent 到初始狀態"""
        self.state = State.IDLE
        self.context = {
            "num_people": None,
            "preferences": [],
            "filtered_coupons": []
        }
    
    def get_state(self):
        """取得當前狀態（用於 debug）"""
        return self.state.value
    
    def process(self, user_input):
        """
        處理使用者輸入（FSM 主邏輯）
        
        參數：
            user_input: 使用者輸入的文字
        
        回傳：
            Agent 的回應文字
        """
        
        # ========== 狀態：IDLE ==========
        if self.state == State.IDLE:
            self.state = State.ASKING_INFO
            return self._welcome_message()
        
        # ========== 狀態：ASKING_INFO ==========
        elif self.state == State.ASKING_INFO:
            return self._handle_asking_info(user_input)
        
        # ========== 狀態：SHOW_MENU ==========
        elif self.state == State.SHOW_MENU:
            # 顯示完菜單後，回到 ASKING_INFO 狀態處理使用者輸入
            self.state = State.ASKING_INFO
            return self._handle_asking_info(user_input)
        
        # ========== 狀態：FILTERING ==========
        elif self.state == State.FILTERING:
            self.state = State.RESULTS
            return self._filter_and_show()
        
        # ========== 狀態：RESULTS ==========
        elif self.state == State.RESULTS:
            # 檢查是否要重來
            if user_input.strip() in ["重來", "重新開始", "restart", "重新查詢"]:
                self.reset()
                return self.process("")
            
            self.state = State.DONE
            return "還需要其他幫助嗎？（輸入「重來」可重新查詢）"
        
        # ========== 狀態：DONE ==========
        elif self.state == State.DONE:
            return "感謝使用！祝用餐愉快！🍗👋"
    
    def _welcome_message(self):
        """歡迎訊息 + 顯示可選品項"""
        msg = "📋 目前優惠券包含的品項：\n\n"

        category_icons = {
            '炸雞類': '🍗',
            '漢堡類': '🍔',
            '飲料': '🥤',
            '甜點': '🧁',
            '其他': '🍟'
        }

        for category, items in self.available_items.items():
            if items:  # 只顯示有品項的分類
                icon = category_icons.get(category, '📌')
                msg += f"{icon} {category}：\n"
                for item in items:
                    msg += f"   • {item}\n"
                msg += "\n"  # 分類之間空一行

        msg += """\n💡 使用方式：
1️⃣  告訴我有幾位用餐
2️⃣  告訴我想吃什麼（可以從上面品項選）
3️⃣  說「好了」開始查詢

範例：
• 「3個人」→「炸雞」→「蛋撻」→「好了」
• 「2個人，想吃炸雞和漢堡，好了」
• 「不知道吃什麼」（顯示完整品項列表）"""

        return msg
    
    def _handle_asking_info(self, user_input):
        """
        處理 ASKING_INFO 狀態
        
        可能的轉換：
        - got_info → FILTERING
        - want_menu → SHOW_MENU
        - invalid → 停留在 ASKING_INFO
        """
        
        if config.DEBUG_MODE:
            print("[DEBUG] 正在呼叫 LLM 提取資訊...")
        
        # 用 LLM 提取資訊
        extracted = self._extract_info(user_input)
        
        if not extracted:
            # LLM 呼叫失敗
            return "抱歉，我遇到了一些問題。請再說一次？"

        # 累積資訊（合併新舊資訊）
        new_num_people = extracted.get("num_people")
        new_preferences = extracted.get("preferences", [])

        # 更新 context（保留舊資訊，用新資訊覆蓋）
        if new_num_people is not None:
            self.context["num_people"] = new_num_people
        if new_preferences:
            # 合併偏好，避免重複（信任 LLM 的判斷）
            existing_prefs = self.context.get("preferences", [])
            all_prefs = existing_prefs + new_preferences
            self.context["preferences"] = list(set(all_prefs))  # 去重

        # 檢查資訊是否完整
        num_people = self.context.get("num_people")
        preferences = self.context.get("preferences", [])

        if config.DEBUG_MODE:
            print(f"[DEBUG] 累積資訊：人數={num_people}, 偏好={preferences}")

        # 檢查是否要開始查詢（使用者說「好了」「查詢」「完成」等）
        trigger_words = ["好了", "查詢", "完成", "搜尋", "搜索", "找", "開始", "go", "ok", "確定"]
        user_wants_search = any(word in user_input.lower() for word in trigger_words)

        # 如果資訊完整且使用者要查詢，就開始過濾
        if user_wants_search and num_people is not None and preferences:
            if config.DEBUG_MODE:
                print(f"[DEBUG] 事件：got_info（人數={num_people}, 偏好={preferences}）-> 轉換到 FILTERING")
            self.state = State.FILTERING
            return self.process("")

        # 事件：want_menu（只有在不是觸發查詢時才檢查）
        if extracted.get("want_menu") and not user_wants_search:
            if config.DEBUG_MODE:
                print("[DEBUG] 事件：want_menu -> 轉換到 SHOW_MENU")
            self.state = State.SHOW_MENU
            return self._show_menu()

        # 否則，顯示目前已記錄的資訊，並提示繼續輸入
        response = "✅ 已記錄：\n"
        if num_people is not None:
            response += f"👥 人數：{num_people} 人\n"
        if preferences:
            response += f"🍴 偏好：{', '.join(preferences)}\n"

        response += "\n"

        # 提示缺少的資訊
        if num_people is None:
            response += "💡 還需要：人數\n"
        if not preferences:
            response += "💡 還需要：想吃什麼\n"

        response += "\n請繼續輸入，或說「好了」開始查詢"

        return response
    
    def _extract_info(self, user_input):
        """
        用 LLM 提取資訊
        
        回傳格式：
        {
            "num_people": 3,
            "preferences": ["炸雞", "漢堡"],
            "want_menu": false
        }
        """
        
        # 建構 Prompt
        prompt = EXTRACT_INFO_PROMPT.format(user_input=user_input)
        
        # 呼叫 LLM
        response = call_llm(prompt)
        
        if not response:
            return None
        
        # 解析 JSON
        try:
            # 清理可能的 markdown 標記和額外文字
            response = response.replace("```json", "").replace("```", "").strip()

            # 嘗試提取 JSON 部分（如果有額外文字）
            import re
            json_match = re.search(r'\{[^{}]*"num_people"[^{}]*\}', response)
            if json_match:
                response = json_match.group()

            # 解析
            result = json.loads(response)

            if config.DEBUG_MODE:
                print(f"[DEBUG] LLM 提取結果: {result}")

            return result

        except json.JSONDecodeError as e:
            if config.DEBUG_MODE:
                print(f"[DEBUG] JSON 解析失敗：{response}")
                print(f"[DEBUG] 錯誤：{e}")
            return None
    
    def _extract_all_items(self):
        """從所有優惠券中提取不重複的品項（清理並分類）"""
        import re
        all_items = set()
        for coupon in self.coupons:
            items = coupon.get('items', [])
            for item in items:
                # 移除各種數量表示
                cleaned = item
                cleaned = re.sub(r'x\d+$', '', cleaned)  # 移除後綴 x1, x2 等
                cleaned = re.sub(r'\(.*?\)', '', cleaned)  # 移除括號內容
                cleaned = re.sub(r'\d+塊', '', cleaned)  # 移除數字+塊
                cleaned = re.sub(r'^\d+', '', cleaned)  # 移除其他數字前綴
                cleaned = cleaned.replace('?', '')  # 移除問號（編碼問題）
                cleaned = cleaned.strip()
                if cleaned:
                    all_items.add(cleaned)

        # 分類品項
        categorized = {
            '炸雞類': [],
            '漢堡類': [],
            '飲料': [],
            '甜點': [],
            '其他': []
        }

        for item in all_items:
            if any(kw in item for kw in ['堡']):
                categorized['漢堡類'].append(item)
            elif any(kw in item for kw in ['雞', '脆', '麻', '花雕']):
                categorized['炸雞類'].append(item)
            elif any(kw in item for kw in ['可樂', '茶', '奶茶']):
                categorized['飲料'].append(item)
            elif any(kw in item for kw in ['蛋撻', '蛋塔', 'QQ球']):
                categorized['甜點'].append(item)
            else:
                categorized['其他'].append(item)

        # 排序每個分類
        for category in categorized:
            categorized[category].sort()

        return categorized

    def _show_menu(self):
        """顯示可選品項列表（分類顯示）"""
        menu = "\n💡 你是低能兒嗎？從這裡下手！\n"
        menu += "🍗 優惠券包含的品項\n"
        menu += "=" * 60 + "\n\n"

        category_icons = {
            '炸雞類': '🍗',
            '漢堡類': '🍔',
            '飲料': '🥤',
            '甜點': '🧁',
            '其他': '🍟'
        }

        for category, items in self.available_items.items():
            if items:
                icon = category_icons.get(category, '📌')
                menu += f"{icon} {category}：\n"
                for item in items:
                    menu += f"   • {item}\n"
                menu += "\n"

        menu += "=" * 60 + "\n"
        menu += "💡 請從上面選擇想吃的品項，或直接告訴我人數和偏好\n"
        menu += "   例如：「3個人，想吃炸雞和蛋撻」\n"

        return menu
    
    def _filter_and_show(self):
        """過濾並顯示結果"""
        
        num_people = self.context["num_people"]
        preferences = self.context["preferences"]
        
        if config.DEBUG_MODE:
            print(f"[DEBUG] 開始過濾：人數={num_people}, 偏好={preferences}")
        
        # 過濾邏輯
        filtered = []
        
        for coupon in self.coupons:
            matched_items = []
            matched_preferences = []  # 記錄符合了哪些偏好

            # 檢查是否包含偏好
            for pref in preferences:
                for item in coupon["items"]:
                    # 模糊匹配（雙向包含）
                    if pref in item or item in pref:
                        matched_items.append(item)
                        matched_preferences.append(pref)

            # 計算符合度分數（符合了幾個使用者偏好）
            match_score = len(set(matched_preferences))  # 去重後符合的偏好數量

            # 檢查人數（允許±1）
            people_diff = abs(coupon["serves"] - num_people)

            # 記錄（包含沒有匹配的優惠券，但分數為 0）
            result = {
                **coupon,
                "matched_items": list(set(matched_items)),  # 去重
                "match_score": match_score,  # 新增：符合度分數
                "people_diff": people_diff,
                "people_suitable": people_diff <= 1
            }

            filtered.append(result)

        # 排序：符合度（高→低）→ 人數接近度（低→高）→ 價格（低→高）
        filtered.sort(key=lambda x: (-x["match_score"], x["people_diff"], x["price"]))

        # 只保留有匹配的優惠券（match_score > 0）
        filtered = [c for c in filtered if c["match_score"] > 0]

        if config.DEBUG_MODE:
            print(f"[DEBUG] 過濾結果：找到 {len(filtered)} 張優惠券")

        # 儲存
        self.context["filtered_coupons"] = filtered

        # 格式化輸出
        if not filtered:
            return self._format_no_results()

        return self._format_results(filtered)
    
    def _format_results(self, coupons):
        """格式化結果"""
        
        result = f"\n✅ 找到 {len(coupons)} 張符合的優惠券：\n\n"
        
        for i, coupon in enumerate(coupons, 1):
            result += "=" * 60 + "\n"
            result += f"{i}. {coupon['name']}\n"
            result += "=" * 60 + "\n"

            # 顯示優惠券代號（優先使用 code，其次使用 id）
            coupon_code = coupon.get('code') or coupon.get('id')
            if coupon_code:
                result += f"🎫 代號：{coupon_code}\n"

            result += f"📦 內容：{coupon['description']}\n"
            result += f"💰 優惠價：{coupon['price']}元\n"
            result += f"✅ 符合：{', '.join(coupon['matched_items'])}\n"

            if coupon['people_suitable']:
                result += f"👥 人數：適合 {coupon['serves']} 人 ✅\n"
            else:
                result += f"👥 人數：建議 {coupon['serves']} 人（你們 {self.context['num_people']} 人）⚠️\n"

            result += "\n"

        # 加上操作提示
        result += "=" * 60 + "\n"
        result += "💡 接下來你可以：\n"
        result += "   • 輸入「重來」「重新開始」「restart」重新查詢\n"
        result += "   • 輸入其他內容結束對話\n"
        result += "=" * 60 + "\n"

        return result
    
    def _format_no_results(self):
        """沒有結果"""
        return f"""
😢 抱歉，沒有找到完全符合的優惠券

你們的需求：
• {self.context['num_people']} 位用餐
• 想吃：{', '.join(self.context['preferences'])}

建議：
1. 輸入「菜單」查看所有優惠
2. 輸入「重來」調整需求重新查詢
"""