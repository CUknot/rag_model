from google import genai
from google.genai.types import GenerateContentConfig, Content, Part
import os
from dotenv import load_dotenv
from pinecone import Pinecone
load_dotenv()

pc = Pinecone(api_key='pcsk_4gAyHb_CLkbhbpJBvFvEjEq8FBAunpg3tARThxfmjLhXUbR7TSb6PbWRZLVmZiRgDHA9Fu')
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
index = pc.Index(INDEX_NAME)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

#ดูว่าpromptจำเป็นต้องใช้ context หรือไม่
def get_context(user_input: str):
    keywords = {"หนัง":"movie", "เพลง":"music", "เกม":"game", "สัตว์":"animal"}
    for word in keywords:
            if word in user_input.lower():
                results = index.search(
                namespace=keywords[word],
                query={
                    "top_k": 10,
                    "inputs": {
                        "text": user_input
                    }
                }
                )
                return results['result']['hits'][0]['fields']['chunk_text']
    
    return None

# Agent mini 
def mimi(contents, context=None):
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

#เริ่มแชท
def chat():
    contents = []
    context = None
    while True:
        # 1.รับprompt
        user_input = input("คุณ: ")
        if user_input.lower() == "exit":
            break
        contents.append(Content(role="user", parts=[Part(text=user_input)]))

        # 2.รับ context จาก PC ถ้าจะเป็นต้องใช้
        if get_context(user_input):
            context = get_context(user_input)        
        print(f"Context: {context}")

        # 3.ส่งคำถามไปยังมีมี่
        response = mimi(contents, context)
        contents.append(Content(role="assistant", parts=[Part(text=response.text)]))
        
        # แสดงผลลัพธ์
        print(f"มีมี่: {response.text}")
        if response.text.lower() == "exit":
            break
chat()