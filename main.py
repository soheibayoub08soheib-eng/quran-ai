import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import json
import traceback

app = Flask(__name__)
# التصحيح: تفعيل CORS ليشمل المسار الصحيح بالكامل أو كل التطبيق
CORS(app, resources={r"/api/*": {"origins": "*"}})

# تهيئة عميل Groq باستخدام المفتاح من البيئة
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route('/api/correct-recitation', methods=['POST'])
def analyze_audio():
    audio_path = None
    try:
        surah = request.form.get('surah', 'غير محدد')
        # تصحيح أسماء الحقول لتتوافق تماماً مع ما ترسله واجهة الموقع
        verse_from = request.form.get('ayah_from', '1')
        verse_to = request.form.get('ayah_to', '1')
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

        # الخطوة الثانية: تحليل النص والتلاوة والأحكام عبر نموذج Llama 3
        prompt = f"""أنت مقرئ وخبير محترف في علم التجويد والقراءات برواية {riwaya}.
الآيات المحددة من المستخدم: السورة {surah}، من الآية {verse_from} إلى {verse_to}.
النص المستخرج من التلاوة: "{transcription}"

تعليمات التقييم:
1. **حالة الخطأ (error):** ضع الحالة "error" حصرياً في حالتين:
   - إذا كان الصوت عبارة عن ضوضاء، صمت، أو كلام عادي لا علاقة له بالقرآن.
   - إذا كان الشخص يقرأ سورة أخرى تماماً أو آيات بعيدة كلياً عن ما حدده.
2. **حالة النجاح (success):** ضع الحالة "success" إذا كانت التلاوة تخص نفس الآيات أو قريبة جداً منها، حتى لو كان فيها بعض الأخطاء في الحفظ أو أحكام التجويد.
3. **التقرير (message):** اشرح في الرسالة بالتفصيل أين كان الصواب وأين وقع الخطأ أو التبديل في الكلمات بلطف وتوجيه تعليمي.
4. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
- "status": إما "success" أو "error"
- "message": التقرير المفصل بالعربية.
"""

        completion = groq_client.chat.completions.create(
            model="⁠llama-3.1-8b-instant⁠⁠",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        # تنظيف الملف المؤقت
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

        result_json = json.loads(completion.choices[0].message.content)

        return jsonify(result_json)

    except Exception as e:
        # تنظيف الملف المؤقت في حال حدوث خطأ
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            
        # طباعة تفاصيل الخطأ كاملة في Render Logs
        print("CRITICAL ERROR TRACEBACK:")
        traceback.print_exc()
            
        return jsonify({
            "status": "error",
            "message": f"الخطأ الحقيقي هو: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
