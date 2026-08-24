import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import json
import traceback

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# تهيئة عميل Groq باستخدام المفتاح من البيئة
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route('/api/correct-recitation', methods=['POST'])
def analyze_audio():
    audio_path = None
    try:
        surah = request.form.get('surah', 'غير محدد')
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

        # الخطوة الثانية: تحليل النص والتلاوة مع التأكد من مطابقة السورة والآيات بدقة
        prompt = f"""أنت مقرئ وخبير محترف في علم التجويد والقراءات برواية {riwaya}.
البيانات المطلوبة من المستخدم: سورة {surah}، من الآية {verse_from} إلى {verse_to}.
النص المستخرج من تلاوة الصوت فعلياً: "{transcription}"

تعليمات صارمة للتقييم:
1. **تطابق السورة والآيات:** تحقق بدقة هل النص المستخرج من الصوت يوافق فعلاً سورة {surah} والآيات المحددة؟ إذا كان الطالب يقرأ سورة أخرى تماماً (مثل قراءة الفاتحة وهو محدد البقرة)، فيجب اعتبار النتيجة خطأ فوراً ولا تقبلها.
2. **عدم الهلوسة:** لا تقم باختلاق كلمات أو تصحيحات وهمية.
3. **حالة الخطأ (error):** ضع الحالة "error" في الحالات التالية:
   - إذا كان الصوت عبارة عن ضوضاء، صمت، أو كلام عادي لا علاقة له بالقرآن.
   - إذا كان الطالب يقرأ سورة مختلفة تماماً عن سورة {surah} المحددة.
4. **حالة النجاح (success):** ضع الحالة "success" فقط إذا كانت التلاوة مطابقة أو قريبة جداً لنفس السورة والآيات المحددة، مع ذكر الأخطاء التجويدية أو لفظ الكلمات إن وجدت.
5. **التقرير (message):** كن مختصراً جداً ومباشراً بدون مقدمات أو ثرثرة، ووضح للطالب مكان الخطأ بدقة إن وجد.
6. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
- "status": إما "success" أو "error"
- "message": التقرير المختصر بالعربية.
"""

        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
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
            
        # طباعة التفاصيل التقنية في لوحة تحكم السيرفر للمطور فقط
        print("CRITICAL ERROR TRACEBACK:")
        traceback.print_exc()
            
        # إرجاع رسالة نظيفة للمستخدم العادي خالية تماماً من تفاصيل السيرفر أو ريندر
        return jsonify({
            "status": "error",
            "message": "عذراً، حدث خطأ أثناء معالجة التسجيل الصوتي. يرجى إعادة المحاولة."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
