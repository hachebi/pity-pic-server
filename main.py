import base64
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

# 🔑 5달러가 충전된 막강한 진짜 키를 넣어주세요!
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

def encode_image_to_base64(image_bytes):
    encoded_string = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded_string}"

@app.post("/generate_hachan/")
async def generate_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        base64_image = encode_image_to_base64(image_bytes)
        
        # 글로벌 표준 엔드포인트
        api_url = "https://api.replicate.com/v1/predictions"
        
        headers = {
            "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait" # AI가 그림 다 그릴 때까지 기다리기 (약 10~20초)
        }
        
        # SDXL 모델 해시값 + 킹받는 하찮음 프롬프트 세팅
        payload = {
            "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            "input": {
                "image": base64_image,
                "prompt": "MS paint style, badly drawn, ugly doodle, pixelated, sloppy lines, white background, masterpiece of terribly drawn art",
                "prompt_strength": 0.8
            }
        }
        
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code not in [200, 201]:
            return JSONResponse(
                status_code=500, 
                content={
                    "status": "error", 
                    "message": "Replicate API 에러", 
                    "detail": response.json()
                }
            )
            
        return JSONResponse(content={"status": "success", "data": response.json()})

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})