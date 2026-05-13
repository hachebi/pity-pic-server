import base64
import os
import io
import asyncio # 🚨 [추가] 기다림의 미학을 위한 도구
from PIL import Image
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

# 비밀 금고에서 키 꺼내오기
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

def resize_and_encode_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    # 최대 1024 해상도로 압축
    img.thumbnail((1024, 1024))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded_string}"

@app.post("/generate_hachan/")
async def generate_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        base64_image = resize_and_encode_image(image_bytes)
        
        api_url = "https://api.replicate.com/v1/predictions"
        headers = {
            "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            "input": {
                "image": base64_image,
                "prompt": "MS paint style, badly drawn, ugly doodle, pixelated, sloppy lines, white background",
                "prompt_strength": 0.8
            }
        }
        
        # 1. AI한테 그림 그려달라고 요청 쏘기
        response = requests.post(api_url, headers=headers, json=payload)
        
        # 🚨 [수정] 200(성공), 201(생성됨) 뿐만 아니라 202(처리중) 상태코드도 정상으로 받기
        if response.status_code not in [200, 201, 202]:
            return JSONResponse(status_code=500, content={"status": "error", "message": "API Error", "detail": response.json()})
        
        result_json = response.json()
        
        # 2. 결과물 확인용 URL 가져오기
        get_url = result_json["urls"]["get"]
        
        # 🚨 [핵심] AI가 그림을 다 그릴 때까지(succeeded) 2초마다 계속 새로고침하며 기다리기!
        while result_json.get("status") in ["starting", "processing"]:
            await asyncio.sleep(2) # 2초 대기
            poll_response = requests.get(get_url, headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"})
            result_json = poll_response.json()
            
        # 3. 기다렸는데 결국 실패했다면?
        if result_json.get("status") == "failed":
            return JSONResponse(
                status_code=500, 
                content={"status": "error", "message": "AI 모델이 그림을 그리다 실패했습니다.", "detail": result_json.get("error")}
            )
            
        # 4. 그림이 완성(succeeded)되었다면 안드로이드로 전송!
        return JSONResponse(content={"status": "success", "data": result_json})

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
