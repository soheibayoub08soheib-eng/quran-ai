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

        # الخطوة الثانية: تحليل النص والتلاوة بمنهجية مقرئ محترف وصارم
        prompt = f"""أنت شيخ مقرئ مجاز، خبير ومدقق محترف في علم التجويد والقراءات برواية {riwaya}. تصرف تماماً مثل المقرئ الحقيقي الذي يدقق تلاوة الطالب بدقة متناهية.

البيانات المرسلة:
- السورة المطلوبة: {surah}
- من الآية: {verse_from} إلى الآية: {verse_to}
- مستوى التصحيح المطلوب: "{level}"
- النص المستخرج من تلاوة الطالب صوتاً: "{transcription}"

تعليمات التقييم الصارمة والمحترفة:
1. **مطابقة السورة والآيات أولاً:** تحقق بدقة تامة هل النص المستخرج ينتمي يقيناً إلى سورة {surah} والآيات المحددة؟ إذا قرأ سورة أخرى (مثل خلط الفلق بالناس)، اعتبرها خطأ فادحاً فوراً واجعل الحالة "error" مع توضيح أنه قرأ سورة أو آية خاطئة.
2. **منهجية التصحيح الاحترافي:** إذا كان هناك خطأ، حدد موضع الخطأ بدقة (الكلمة أو الآية) واشرح سبب الخلل بناءً على مستوى التصحيح المحدد.
3. **التعامل مع عيوب التسجيل (Whisper):** تجاهل الأخطاء الإملائية البحتة لبرنامج النسخ الصوتي إذا تأكدت أن نطق الطالب الصوتي صحيح وسليم للآية.
4. **حالة الخطأ (error):** ضع الحالة "error" في الحالات التالية:
   - إذا حدث تحريف في الآيات أو تغيير يغير المعنى.
   - إذا كان الصوت عبارة عن ضوضاء، صمت، أو كلام عادي لا علاقة له بالقرآن.
   - إذا قرأ سورة مختلفة تماماً عن سورة {surah} المحددة.
5. **حالة النجاح (success):** ضع الحالة "success" فقط إذا كانت التلاوة مطابقة للآيات حسب المستوى المختار، مع ذكر أي تنبيهات أو توجيهات تجويدية مفيدة إن وجدت.
6. **التقرير (message):** كن دقيقاً، مهذباً، ومختصراً كالمقرئ الحقيقي، ووضح مكان الخطأ بدقة إن وجد.
7. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
- "status": إما "success" أو "error"
- "message": التقرير المفصل والموجه بدقة بالعربية.
"""

        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,  # درجة حرارة صفر لضمان الالتزام التام ومنع أي هلوسة
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
            
        # إرجاع رسالة نظيفة للمستخدم العادي
        return jsonify({
            "status": "error",
            "message": "عذراً، حدث خطأ أثناء معالجة التسجيل الصوتي. يرجى إعادة المحاولة."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
