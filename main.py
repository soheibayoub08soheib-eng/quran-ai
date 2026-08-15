from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests

app = Flask(__name__)
CORS(app)

# إعداد مفتاح الـ API ورابط الاتصال المباشر
api_key = os.environ.get("GOOGLE_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={api_key}"

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

# قراءة الملف الصوتي وتحويله إلى Base64 لإرساله عبر الاتصال المباشر
        import base64
        audio_bytes = audio_file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        mime_type = audio_file.mimetype or 'audio/mp3'

        # تجهيز هيكل البيانات المرسلة باستخدام الـ prompt القديم الخاص بك
        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": f"""أنت مقرئ وخبير محترف في علم التجويد والقراءات القرآنية برواية {riwaya}.
مهمتك هي الاستماع بعناية للملف الصوتي المرفق ومقارنته بالآيات المطلوبة
- السورة: {surah}
- من الآية: {verse_from} إلى الآية {verse_to}

:تعليمات التقييم
1. "error" افحص الحفظ وصحة الكلمات ومخارج الحرف. إذا كان الملف الصوتي عبارة عن صوت عشوائي تماماً، أو كلام فارغ لا علاقة له بالقرآن، اجعل الحالة "message" واكتب في الـ "success" أما إذا كانت التلاوة قرآنية صحيحة في الجملة (حتى لو كانت هناك بعض الملاحظات أو الأخطاء التجويدية البسيط) ، فاجعل الحالة
2. "success" أو "error" نظيفة تحتوي على مفتاحين JSON أجيب حصرياً بصيغة:
- "status": إما
- "message": التقرير المفصل بالعربية
"""
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": audio_base64
                        }
                    }
                ]
            }]
        }

        headers = {'Content-Type': 'application/json'}
        
        # إرسال الطلب المباشر عبر رابط الـ URL ومعرفات الـ AQ
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": f"خطأ من سيرفر جوجل: {response.text}"
            }), 500

        result_json = response.json()
        
        # استخراج الرد وتنظيفه كما في الكود السابق تماماً
        try:
            raw_text = result_json['candidates'][0]['content']['parts'][0]['text']
            import json
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            final_json = json.loads(clean_text)
            return jsonify(final_json)
        except Exception as parsing_error:
            return jsonify({
                "status": "error",
                "message": f"حدث خطأ في تحليل الرد: {str(parsing_error)}"
            }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
            
        return jsonify({
            "status": "error",
            "message": f"حدث خطأ أثناء معالجة التلاوة بالذكاء الاصطناعي: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

