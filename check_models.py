import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Lỗi: Chưa có GEMINI_API_KEY trong file .env")
else:
    genai.configure(api_key=api_key)
    print(f"--- Đang kiểm tra Model cho key: {api_key[:10]}... ---")
    try:
        models = genai.list_models()
        print("✅ Các model khả dụng cho bạn:")
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
    except Exception as e:
        print(f"❌ Lỗi khi liệt kê model: {e}")
