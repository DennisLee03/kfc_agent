# config.py
"""
配置管理
統一管理所有系統配置，包含環境變數、常數等
"""

import os
from dotenv import load_dotenv

# 載入環境變數（強制覆蓋）
load_dotenv(override=True)


class Config:
    """系統配置類"""

    # ========== LLM API 配置 ==========
    @staticmethod
    def _get_env():
        """重新載入環境變數"""
        load_dotenv(override=True)
        return os

    @property
    def OLLAMA_API_URL(self):
        return os.getenv("OLLAMA_API_URL", "https://your-ollama-server.com/api")

    @property
    def OLLAMA_API_KEY(self):
        return os.getenv("OLLAMA_API_KEY", "your-api-key-here")

    @property
    def OLLAMA_MODEL(self):
        return os.getenv("OLLAMA_MODEL", "llama2")

    # LLM 請求超時設定（秒）
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

    # ========== Agent 配置 ==========
    # 是否顯示 debug 訊息
    DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

    # 人數匹配容差（允許推薦的人數差異）
    PEOPLE_TOLERANCE = int(os.getenv("PEOPLE_TOLERANCE", "1"))

    # ========== 爬蟲配置 ==========
    # KFC 優惠券頁面 URL（未來使用）
    KFC_COUPON_URL = os.getenv("KFC_COUPON_URL", "https://www.kfcclub.com.tw/")

    # 爬蟲請求超時（秒）
    SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "10"))

    # 優惠券快取檔案路徑
    COUPON_CACHE_FILE = os.getenv("COUPON_CACHE_FILE", "coupons_cache.json")

    # ========== 資料路徑 ==========
    # 優惠券圖片儲存路徑
    COUPON_IMAGES_DIR = os.getenv("COUPON_IMAGES_DIR", "coupon_images")

    @classmethod
    def validate(cls):
        """
        驗證配置是否完整

        回傳：
            tuple: (is_valid, error_messages)
        """
        errors = []

        # 檢查必要的 API 配置
        if cls.OLLAMA_API_URL == "https://your-ollama-server.com/api":
            errors.append("OLLAMA_API_URL 尚未設定（請修改 .env 檔案）")

        if cls.OLLAMA_API_KEY == "your-api-key-here":
            errors.append("OLLAMA_API_KEY 尚未設定（請修改 .env 檔案）")

        return (len(errors) == 0, errors)

    @classmethod
    def print_config(cls):
        """印出當前配置（用於 debug）"""
        print("=" * 60)
        print("系統配置")
        print("=" * 60)
        print(f"LLM API URL: {cls.OLLAMA_API_URL}")
        print(f"LLM Model: {cls.OLLAMA_MODEL}")
        print(f"LLM Timeout: {cls.LLM_TIMEOUT}秒")
        print(f"Debug Mode: {cls.DEBUG_MODE}")
        print(f"People Tolerance: ±{cls.PEOPLE_TOLERANCE}人")
        print(f"KFC URL: {cls.KFC_COUPON_URL}")
        print("=" * 60)


# 建立全域配置實例
config = Config()


if __name__ == "__main__":
    # 測試配置
    config.print_config()

    is_valid, errors = config.validate()

    if is_valid:
        print("\n✅ 配置驗證通過")
    else:
        print("\n❌ 配置驗證失敗：")
        for error in errors:
            print(f"   - {error}")
