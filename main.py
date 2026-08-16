import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
# بدلاً من CORS(app) فقط، استخدم هذا:
CORS(app, resources={r"/analyze-audio": {"origins": "*"}})

# تهيئة عميل Groq باستخدام المفتاح الجديد
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route('/api/correct-recitation', methods=['POST'])
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

        # الخطوة الأولى: تحويل الصوت إلى نص بدقة عالية جداً عبر Whisper من Groq
        with open(audio_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3",
                language="ar",
                response_format="text"
            )

        # الخطوة الثانية: تحليل النص والتلاوة والأحكام عبر نموذج الذكاء الاصطناعي الخارق Llama 3
        prompt = f"""أنت مقرئ وخبير محترف في علم التجويد والقراءات القرآنية برواية {riwaya}.
المستخدم قام بتلاوة الآيات التالية:
- السورة: {surah}
- من الآية: {verse_from} إلى الآية {verse_to}

النص المستخرج من تلاوته هو: "{transcription}"

تعليمات التقييم:
1. قارن النص المستخرج بالآيات المطلوبة وافحص صحة الكلمات والأحكام. إذا كانت التلاوة فارغة أو لا علاقة لها بالقرآن، اجعل الحالة "error". أما إذا كانت صحيحة أو تقريبية صحيحة، فاجعل الحالة "success".
2. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
- "status": إما "success" أو "error"
- "message": التقرير المفصل بالعربية للأخطاء وملاحظات التجويد إن وجدت.
"""

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        # تنظيف الملف المؤقت
        if os.path.exists(audio_path):
            os.remove(audio_path)

        import json
        result_json = json.loads(completion.choices[0].message.content)

        return jsonify(result_json)

    except Exception as e:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            
        return jsonify({
            "status": "error",
            "message": f"الخطأ الحقيقي هو: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
