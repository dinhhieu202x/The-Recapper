import os
import google.generativeai as genai
from utils.constants import MAX_AI_CHARS, CHUNK_SIZE

# Khởi tạo Gemini client
_api_key = os.getenv("GEMINI_API_KEY", "")
if _api_key:
    genai.configure(api_key=_api_key)

SYSTEM_PROMPT = """Bạn là trợ lý tóm tắt nội dung chat. Nhiệm vụ của bạn là tóm tắt đoạn hội thoại dưới đây một cách ngắn gọn, rõ ràng.

Hãy tuân theo các quy tắc sau:
1. Viết bằng tiếng Việt
2. Dùng bullet points (•) để liệt kê các ý chính
3. Nêu bật các chủ đề được thảo luận nhiều nhất
4. Liệt kê các quyết định hoặc action items (nếu có) dưới mục riêng
5. Đề cập tên người tham gia khi có thể
6. Không bịa đặt thông tin không có trong đoạn hội thoại
7. Giữ tóm tắt trong khoảng 150-300 từ"""

CHUNK_SUMMARY_PROMPT = """Đây là một phần của cuộc hội thoại. Hãy tóm tắt ngắn gọn nội dung phần này bằng tiếng Việt:"""

MERGE_PROMPT = """Dưới đây là các bản tóm tắt từng phần của một cuộc hội thoại. Hãy tổng hợp thành một bản tóm tắt hoàn chỉnh, mạch lạc bằng tiếng Việt, dùng bullet points và nêu rõ các chủ đề chính, quyết định và action items nếu có:"""


async def summarize(conversation_text: str) -> str:
    """
    Gửi nội dung chat tới Gemini để tóm tắt.
    Nếu nội dung quá dài → chia chunk → tóm tắt từng chunk → merge.
    """
    if not _api_key:
        return "⚠️ Chưa cấu hình GEMINI_API_KEY. Vui lòng thêm vào file .env"

    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        system_instruction=SYSTEM_PROMPT,
    )

    # Nội dung ngắn → tóm tắt trực tiếp
    if len(conversation_text) <= MAX_AI_CHARS:
        return await _summarize_single(model, conversation_text)

    # Nội dung dài → Map-Reduce
    return await _summarize_mapreduce(model, conversation_text)


async def _summarize_single(model, text: str) -> str:
    """Tóm tắt 1 đoạn text trực tiếp."""
    try:
        prompt = f"Hãy tóm tắt cuộc hội thoại sau:\n\n{text}"
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Lỗi khi gọi AI: {str(e)}"


async def _summarize_mapreduce(model, text: str) -> str:
    """
    Map-Reduce: Chia text thành chunks → tóm tắt từng chunk → merge tất cả.
    """
    # Bước 1: Chia thành chunks theo dòng (tránh cắt giữa câu)
    chunks: list[str] = []
    current_chunk_lines: list[str] = []
    current_len = 0

    for line in text.split("\n"):
        if current_len + len(line) > CHUNK_SIZE and current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))
            current_chunk_lines = [line]
            current_len = len(line)
        else:
            current_chunk_lines.append(line)
            current_len += len(line)

    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines))

    # Bước 2: Tóm tắt từng chunk
    partial_summaries: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        try:
            prompt = f"{CHUNK_SUMMARY_PROMPT}\n\n{chunk}"
            response = await model.generate_content_async(prompt)
            partial_summaries.append(f"Phần {i}:\n{response.text.strip()}")
        except Exception as e:
            partial_summaries.append(f"Phần {i}: [Lỗi tóm tắt: {e}]")

    # Bước 3: Merge các phần
    merged_text = "\n\n".join(partial_summaries)
    try:
        prompt = f"{MERGE_PROMPT}\n\n{merged_text}"
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Lỗi khi merge tóm tắt: {str(e)}"
