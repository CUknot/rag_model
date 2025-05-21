import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Content, Part
from pinecone import Pinecone

load_dotenv()

# --- Initialize Model ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# --- Chat Functions ---
def get_response_from_llm(contents, context=None):
    system_instruction = f'คุณคือ "มีมี่" ผู้ช่วย AI สาวน้อยอัจฉริยะ พูดจาสุภาพ ขี้เล่น สดใส และใช้ภาษาไทยตลอดการสนทนา ต้องลงท้ายประโยคทุกครั้งด้วยคำว่า "ค่ะ" พูดให้ดูเป็นกันเอง น่ารัก และเข้าใจง่าย อย่าใช้ภาษาทางการมากเกินไป แต่ต้องไม่หยาบคาย ห้ามพูดภาษาอังกฤษ เว้นแต่จำเป็นต้องแปลหรืออธิบายคำศัพท์'
    if context:
        system_instruction += f" และใช้ข้อมูลนี้ {context} ในการตอบคำถาม ห้ามใช้ข้อมูลที่ไม่เกี่ยวข้องกับคำถาม"

    response = client.models.generate_content(
        config=GenerateContentConfig(
            system_instruction=system_instruction
        ),
        model="gemini-2.0-flash",
        contents=contents
    )
    return response
    