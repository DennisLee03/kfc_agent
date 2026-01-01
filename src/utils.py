# utils.py
"""
工具函數：LLM 呼叫、輔助功能
"""

import requests
import logging
from config.config import config

# 設定日誌
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def call_llm(prompt, model=None, temperature=0.7, max_tokens=500):
    """
    呼叫 Ollama API

    參數：
        prompt: 要傳給 LLM 的提示詞
        model: 使用的模型（預設用配置檔的）
        temperature: 溫度參數（0.0-1.0，越高越隨機）
        max_tokens: 最大回應長度

    回傳：
        LLM 的回應文字，失敗則回傳 None
    """
    if model is None:
        model = config.OLLAMA_MODEL

    logger.debug(f"正在呼叫 LLM (model={model})...")

    headers = {
        "Authorization": f"Bearer {config.OLLAMA_API_KEY}",
        "Content-Type": "application/json"
    }

    # 嘗試 /generate endpoint（老師的 API 格式）
    data_generate = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }

    try:
        # 先嘗試 /generate endpoint
        response = requests.post(
            f"{config.OLLAMA_API_URL}/generate",
            headers=headers,
            json=data_generate,
            timeout=config.LLM_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            # Ollama /generate 的回應格式
            content = result.get("response", "")
            logger.debug(f"LLM 回應成功（/generate，長度={len(content)}）")
            return content

        # 如果 /generate 失敗，嘗試 /chat endpoint
        logger.warning(f"/generate 失敗 ({response.status_code})，嘗試 /chat")

        data_chat = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        response = requests.post(
            f"{config.OLLAMA_API_URL}/chat",
            headers=headers,
            json=data_chat,
            timeout=config.LLM_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            # Ollama /chat 的回應格式
            content = result.get("message", {}).get("content", "")
            logger.debug(f"LLM 回應成功（/chat，長度={len(content)}）")
            return content
        else:
            error_msg = f"API 錯誤 {response.status_code}: {response.text}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            return None

    except requests.exceptions.Timeout:
        error_msg = f"請求超時（{config.LLM_TIMEOUT}秒）"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None

    except requests.exceptions.ConnectionError as e:
        error_msg = f"連接失敗：{e}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None

    except Exception as e:
        error_msg = f"呼叫失敗: {e}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None


def test_connection():
    """
    測試 Ollama 連接是否正常

    回傳：
        bool: 連接成功則回傳 True
    """
    logger.info("測試 Ollama 連接...")
    print(f"   API URL: {config.OLLAMA_API_URL}")
    print(f"   模型: {config.OLLAMA_MODEL}")

    # 簡單的測試 prompt
    test_prompt = "請只回答「OK」，不要其他文字。"

    response = call_llm(test_prompt, temperature=0.1, max_tokens=10)

    if response:
        print(f"✅ 連接成功！")
        print(f"   LLM 回應: {response.strip()}")
        logger.info("LLM 連接測試通過")
        return True
    else:
        print(f"❌ 連接失敗")
        print(f"   請檢查 .env 檔案的設定")
        logger.error("LLM 連接測試失敗")
        return False


if __name__ == "__main__":
    # 直接執行此檔案時測試連接
    from config import config
    config.print_config()
    print()
    test_connection()