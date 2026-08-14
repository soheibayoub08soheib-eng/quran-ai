import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# تهيئة Gemini باستخدام المفتاح الذي أنشأته
GEMINI_API_KEY = "AQ.Ab8RN6lvMY5LkiiA9L6fGwBN6I1A9Osr04JXRkDOjk3kem8dg"
genai.configure(api_key=GEMINI_API_KEY)

@app.route('/analyze-audio', methods=['POST'])
def analyze_audio():
 try:
  # استلام البيانات المرفوعة من واجهة الموقع
  surah = request.form.get('surah', 'غير محدد')
  verse_from = request.form.get('verse_from', '1')
  verse_to = request.form.get('verse_to', '1')
  riwaya = request.form.get('riwaya', 'حفص عن عاصم')

  audio_file = request.files.get('audio')

  if not audio_file:
   return jsonify({
    "status": "error",
    "message": "الرجاء إرفاق ملف صوتي صحيح للتدقيق."
    }), 400  

   # حفظ الملف الصوتي مؤقتاً لمعالجته
   audio_path = "temp_audio_file.mp3"
   audio_file.save(audio_path)

   # رفع الملف الصوتي إلى خوادم Google المعالجة للوسائط
   print("جاري رفع وتحليل الملف الصوتي بواسطة الذكاء الاصطناعي...")
   gemini_audio_ref = genai.upload_file(audio_path)
 
   # إعداد نموذج الذكاء الاصطناعي مع التوجيهات الصارمة للتدقيق القرآني
   generation_config = {
   "temperature": 0.1,
   "top_p": 0.95,
   "top_k": 40,
   "max_output_tokens": 1024,
   }

   model = genai.GenerativeModel(
   model_name="gemini-1.5-flash",
   generation_config=generation_config
   )

   prompt = f"""
   أنت مقرئ وخبير محترف في علم التجويد والقراءات القرآنية برواية ({riwaya}).
   مهمتك هي الاستماع بعناية فائقة للملف الصوتي المرفق ومقارنته بالآيات المطلوبة:
   - السورة: {surah}
   - من الآية: {verse_from} إلى الآية: {verse_to}

   تعليمات صارمة جداً للتقييم:
   1. تحقق بدقة تامة هل الصوت المرفق يوافق الآيات المذكورة تماماً أم لا. إذا كان الملف الصوتي عبارة عن صوت عشوائي، موسيقى، كلام عادي، أو سورة أخرى غير المحددة، اعتبره فوراً (خطأ/فشل) ولا تقبله أبداً.
   2. دقق في الحفظ، صحة الكلمات، ومخارج الحروف، وأحكام التجويد الأساسية بناءً على الرواية المحددة ({riwaya}).
   3. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
   - "status": إما "success" (إذا كانت التلاوة صحيحة ومتقنة للآيات المطلوبة) أو "error" (إذا وُجدت أخطاء أو كان الصوت غير مطابق).
   - "message": تقرير مفصل بالعربية يوضح النتيجة، وفي حال وجود أخطاء قم بتوضيحها بدقة ومحبة لتوجيه الطالب.
   """

   response = model.generate_content([gemini_audio_ref, prompt])

  if os.path.exists(audio_path):
   os.remove(audio_path)

import json
 clean_text = response.text.replace("```json", "").replace("```", "").strip()
 result_json = json.loads(clean_text)

   return jsonify(result_json)

 except Exception as e:
  if 'audio_path' in locals() and os.path.exists(audio_path):
   os.remove(audio_path)

   return jsonify({
    "status": "error",
    "message": f"حدث خطأ أثناء معالجة التلاوة بالذكاء الاصطناعي: {str(e)}"
    }), 500

  if __name__ == '__main__':
   port = int(os.environ.get('PORT', 5000))
   app.run(host='0.0.0.0', port=port)


