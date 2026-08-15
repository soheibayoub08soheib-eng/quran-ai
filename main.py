from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# جلب مفتاح API بالطريقة الصحيحة
api_key = os.environ.get("GOOGLE_API_KEY")

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

        # حفظ الملف الصوتي مؤقتاً
        audio_path = "temp_audio_file.mp3"
        audio_file.save(audio_path)

        # استخدام الطريقة الرسمية الحديثة المتوافقة مع مفاتيح AQ
        import google.genai as genai
        
        client = genai.Client(api_key=api_key)

        # رفع الملف الصوتي عبر العميل الرسمي
        uploaded_file = client.files.upload(file=audio_path)

        prompt_text = f"""أنت مقرئ وخبير محترف في علم التجويد والقراءات القرآنية برواية {riwaya}.
مهمتك هي الاستماع بعناية للملف الصوتي المرفق ومقارنته بالآيات المطلوبة
- السورة: {surah}
- من الآية: {verse_from} إلى الآية {verse_to}

تعليمات التقييم:
1. افحص الحفظ وصحة الكلمات ومخارج الحروف. إذا كان الملف الصوتي عبارة عن صوت عشوائي تماماً، أو كلام فارغ لا علاقة له بالقرآن، اجعل الحالة "error". أما إذا كانت التلاوة قرآنية صحيحة، فاجعل الحالة "success".
2. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين:
- "status": إما "success" أو "error"
- "message": التقرير المفصل بالعربية
"""

        # استدعاء أحدث نموذج متوافق مع مفاتيح المصادقة الجديدة
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt_text]
        )

        # حذف الملف المؤقت من السيرفر لتنظيف الذاكرة
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
            "message": f"حدث خطأ أثناء معالجة التلاوة: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
