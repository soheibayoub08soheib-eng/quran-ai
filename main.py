import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# تهيئة المفتاح بالطريقة الكلاسيكية المستقرة
api_key = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

@app.route('/analyze-audio', methods=['POST'])
def analyze_audio():
    audio_path = None
    try:
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

        # حفظ الملف مؤقتاً
        audio_path = "temp_audio_file.mp3"
        audio_file.save(audio_path)

        # رفع الملف بالطريقة الكلاسيكية المعتمدة
        audio_ref = genai.upload_file(audio_path)

        # استدعاء النموذج المستقر
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""أنت مقرئ وخبير محترف في علم التجويد والقراءات القرآنية برواية {riwaya}.
مهمتك هي الاستماع بعناية للملف الصوتي المرفق ومقارنته بالآيات المطلوبة
- السورة: {surah}
- من الآية: {verse_from} إلى الآية {verse_to}

تعليمات التقييم:
1. افحص الحفظ وصحة الكلمات ومخارج الحروف. إذا كان الملف الصوتي عبارة عن صوت عشوائي تماماً، أو كلام فارغ لا علاقة له بالقرآن، اجعل الحالة "error". أما إذا كانت التلاوة قرآنية صحيحة، فاجعل الحالة "success".
2. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين:
- "status": إما "success" أو "error"
- "message": التقرير المفصل بالعربية
"""

        response = model.generate_content([audio_ref, prompt])

        # حذف الملف المؤقت
        if os.path.exists(audio_path):
            os.remove(audio_path)

        import json
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result_json = json.loads(clean_text)

        return jsonify(result_json)

    except Exception as e:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            
        return jsonify({
            "status": "error",
            "message": f"الخطأ بالتفصيل: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
