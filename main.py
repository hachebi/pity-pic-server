import base64
import os
import io
from PIL import Image # 🚨 새로 추가된 이미지 처리 라이브러리
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

# 비밀 금고에서 키 꺼내오기
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

# 🚨 [신규] 거대한 사진을 AI가 소화하기 좋게 줄여주는 함수
def resize_and_encode_image(image_bytes):
    # 1. 이미지 열기
    img = Image.open(io.BytesIO(image_bytes))
    
    # 2. RGB 모드로 변환 (혹시 모를 오류 방지)
    if img.mode != "RGB":
        img = img.convert("RGB")
        
    # 3. 최대 해상도를 1024x1024로 안전하게 줄이기 (비율은 자동 유지됨)
    img.thumbnail((1024, 1024))
    
    # 4. 다시 바이트로 변환 후 Base64로 압축
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return f"data:image/jpeg;base64,{encoded_string}"

@app.post("/generate_hachan/")
async def generate_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        
        # 🚨 여기서 원본 대신 리사이징된 이미지를 만듭니다!
        base64_image = resize_and_encode_image(image_bytes)
        
        api_url = "https://api.replicate.com/v1/predictions"
        headers = {
            "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait"
        }
        
        payload = {
            "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            "input": {
                "image": base64_image,
                "prompt": "MS paint style, badly drawn, ugly doodle, pixelated, sloppy lines, white background, masterpiece of terribly drawn art",
                "prompt_strength": 0.8
            }
        }
        
        response = requests.post(api_url, headers=headers, json=payload)
        
        # API 통신 자체가 실패했을 때
        if response.status_code not in [200, 201]:
            return JSONResponse(status_code=500, content={"status": "error", "message": "API Error", "detail": response.json()})
        
        # 🚨 [신규] 통신은 성공했지만 AI 모델 내부에서 그림 그리다 실패했을 때의 안전망
        result_json = response.json()
        if result_json.get("status") == "failed":
            return JSONResponse(
                status_code=500, 
                content={"status": "error", "message": "AI 모델이 그림을 그리다 실패했습니다.", "detail": result_json.get("error")}
            )
            
        # 모든 관문을 통과하면 성공 반환!
        return JSONResponse(content={"status": "success", "data": result_json})

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})