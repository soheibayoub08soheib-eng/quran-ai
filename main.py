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
        level = request.form.get('level', 'متوسط (الاحكام العامة والوقف)')
        
        audio_file = request.files.get('audio') or request.files.get('file') or request.files.get('recording')
        
        if not audio_file:
            return jsonify({
                "status": "error",
                "message": "الرجاء إرفاق ملف صوتي صحيح للتدقيق."
            }), 400

        # حفظ الملف مؤقتاً
        audio_path = f"temp_audio_file.{audio_file.filename.rsplit('.', 1)[1].lower() if audio_file.filename and '.' in audio_file.filename else 'mp3'}"
        audio_file.save(audio_path)

        # الخطوة الأولى: تحويل الصوت إلى نص بدقة عالية جداً عبر Whisper من Groq
        with open(audio_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3",
                language="ar",
                response_format="text"
            )

        # الخطوة الثانية: تحليل ذكي ومركز جداً يضمن الاستماع الدقيق والعدالة التامة
        prompt = f"""أنت شيخ مقرئ مجاز، خبير ومدقق محترف في علم التجويد والقراءات برواية {riwaya}.

البيانات المرسلة للتدقيق:
- السورة المطلوبة: {surah}
- من الآية: {verse_from} إلى الآية: {verse_to}
- مستوى التصحيح المطلوب: "{level}"
- النص المستخرج من تلاوة الطالب صوتاً: "{transcription}"

التعليمات الصارمة للاستماع والتقييم الدقيق:
1. **دقة الاستماع والمقارنة:** ركز جيداً في النص المستخرج وقارنه بالآيات المطلوبة لسورة {surah}. لا تفترض وجود خطأ لمجرد وجود اختلاف إملائي بسيط ناتج عن برنامج النسخ الصوتي (Whisper).
2. **منع التحريف تماماً:** إذا قام الطالب بتبديل كلمة بأخرى أو حرف المعنى أو أخطأ خطأً بيناً في الآيات، اعتبر النتيجة "error" فوراً بدون أي تساهل.
3. **العدالة مع القارئ المتقن:** إذا كانت قراءة الطالب سليمة وصحيحة للآيات والمطلوب أداءً، اعتبر النتيجة "success" فوراً ولا تختلق أخطاء وهمية.
4. **حالة الخطأ (error):** ضعها في حال: التحريف في الآيات، قراءة سورة أخرى، أو وجود ضوضاء وصمت تام.
5. **حالة النجاح (success):** ضعها في حال كانت التلاوة مطابقة وصحيحة، مع كتابة ملاحظة أو تشجيع لطيف وموجز.
6. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
- "status": إما "success" أو "error"
- "message": التقرير المختصر والموجز بالعربية.
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
            
        print("CRITICAL ERROR TRACEBACK:")
        traceback.print_exc()
            
        return jsonify({
            "status": "error",
            "message": "عذراً، حدث خطأ أثناء معالجة التسجيل الصوتي. يرجى إعادة المحاولة."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
