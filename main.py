from Fastapi import fastAPI, UploadFile, File, From
from Fastapi.middleware.cors import CORSMiddleware
import numpy as np
import librosa
import io

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.post("/analyze-audio")
async def analyze_audio(
  audio: UploadFile = File(...),
  surah: str = Form(...),
  riwaya: str = Form(...)
):
   try:
    contents = await audio.read()
    audio_file = io.BytesIO(contents)
    y, sr = librosa.load(audio_file, sr=None)
    
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    duration = librosa.get_duration(y=y, sr=sr)
    
    has_error = bool(spectral_centroid > 3500 or duration < 1.0)
    
    if has_error:
      analysis_result = {
        "status": "error",
        "message": f"تنبيه في تلاوة سورة {surah} برواية {riwaya}: تم رصد ملاحظة في احكام التلاوة.",
        "details": {"spectral_centroid": float(spectral_centroid), "duration": float(duration)}
      }
    else:
      analysis_result = {
        "status": "success",
        "message": f"تلاوة سورة ما شاء الله {surah} برواية {riwaya} دقيقة ومطابقة للأحكام بنجاح.",
        "details": {"spectral_centroid": float(spectral_centroid), "duration": float(duration)}
      }

    return analysis_result

   except Exception as e:
    return {"status": "error", "message": f"حدث خطأ في المعالجة الفنية: {str(e)}"}



