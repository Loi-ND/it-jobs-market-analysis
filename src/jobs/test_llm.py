from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv("../../.env")

MODEL_API_KEY = os.environ.get("MODEL_API_KEY")

client = genai.Client(
    api_key=MODEL_API_KEY
)
prompt = """
Hãy sumarise cái job trong đường dẫn này bằng cách truy cập vào trang web và sumarise nội dung bài tuyển dụng
https://www.topcv.vn/viec-lam/senior-it-specialist-good-english-communication/2297361.html?ta_source=JobSearchList_LinkDetail&u_sr_id=p8uYSOnzsLkugihIB2UUjFggU5sJPKSamyTqIN2d_1789117071
"""

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=prompt
)

print(response.text)