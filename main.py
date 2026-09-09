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
        level = request.form.get('level', 'ابتدائي') # استقبال مستوى التصحيح (ابتدائي / متقدم)
        
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

        # الخطوة الثانية: تحليل النص والتلاوة بناءً على المستوى والصرامة المطلوبة
        prompt = f"""أنت مقرئ وخبير محترف في علم التجويد والقراءات برواية {riwaya}.
البيانات المطلوبة: سورة {surah}، من الآية {verse_from} إلى {verse_to}.
مستوى التصحيح المطلوب: {level} (إذا كان 'ابتدائي'، فركز على صحة الكلمات والحروف الأساسية ولا تكن صارماً في أحكام التجويد الدقيقة. أما إذا كان 'متقدم'، فدقق في كل أحكام التجويد والتشكيل بدقة تامة).
النص المستخرج من تلاوة الصوت فعلياً: "{transcription}"

تعليمات التقييم الدقيقة:
1. **التحريف والكلمات:** القرآن لا يُقْبَل فيه تحريف الكلمات أو تبديلها (مثل الخطأ في المعنى أو تبديل الألفاظ) بغض النظر عن المستوى.
2. **التعامل مع أخطاء التحويل الصوتي (Whisper):** نموذج التحويل قد يخطئ أحياناً في كتابة بعض الهمزات أو الحروف رسمياً (إملائياً) رغم صحة النطق. ركّز على نطق الكلمات ولا تحاسب على مجرد اختلاف رسم إملائي بحت ناتج عن محرك الكتابة.
3. **حالة الخطأ (error):** ضع الحالة "error" في الحالات التالية:
   - إذا حدث تحريف في الآيات أو تغيير يغير المعنى.
   - إذا كان الصوت عبارة عن ضوضاء، صمت، أو كلام عادي لا علاقة له بالقرآن.
   - إذا كان الطالب يقرأ سورة مختلفة تماماً عن سورة {surah} المحددة.
4. **حالة النجاح (success):** ضع الحالة "success" فقط إذا كانت التلاوة مطابقة للآيات حسب المستوى المحدد، مع ذكر أي تنبيهات أو أخطاء إن وجدت.
5. **التقرير (message):** كن مختصراً جداً ومباشراً بدون مقدمات أو ثرثرة، ووضح للطالب مكان الخطأ بدقة إن وجد.
6. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
- "status": إما "success" أو "error"
- "message": التقرير المختصر بالعربية.
"""

        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b", # الاحتفاظ بالنموذج المطلوب مع بقية الإعدادات المستقرة
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, # مرونة طفيفة لتجنب التعقيد الحرفي المفرط مع الحفاظ على الدقة
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
