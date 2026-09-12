import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import json
import traceback

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route('/api/correct-recitation', methods=['POST'])
def analyze_audio():
    audio_path = None
    try:
        print("--- NEW REQUEST RECEIVED ---")
        print("FORM DATA:", request.form)
        print("FILES DATA:", request.files)
        
        surah = request.form.get('surah', 'غير محدد')
        verse_from = request.form.get('ayah_from', '1')
        verse_to = request.form.get('ayah_to', '1')
        riwaya = request.form.get('riwaya', 'حفص عن عاصم')
        level = request.form.get('level', 'متوسط (الاحكام العامة والوقف)')
        
        # البحث عن الملف بأي اسم مفتاح محتمل
        audio_file = request.files.get('audio') or request.files.get('file') or request.files.get('recording')
        
        if not audio_file:
            print("ERROR: No audio file found in request.files")
            return jsonify({
                "status": "error",
                "message": "الرجاء التأكد من اختيار ملف صوتي صحيح."
            }), 400

        # استخراج الامتداد بطريقة آمنة جداً تمنع انهيار سفاري إذا كان اسم الملف فارغاً
        original_filename = audio_file.filename if audio_file.filename else "recording.mp3"
        if '.' in original_filename:
            ext = original_filename.rsplit('.', 1)[1].lower()
            if ext not in ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'webm', 'mp4']:
                ext = 'mp3'
        else:
            ext = 'mp3'
            
        audio_path = f"temp_audio_file.{ext}"
        audio_file.save(audio_path)

        # تحويل الصوت عبر Whisper
        with open(audio_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3",
                language="ar",
                response_format="text"
            )

        prompt = f"""أنت شيخ مقرئ مجاز، خبير ومدقق محترف في علم التجويد والقراءات برواية {riwaya}. تمتلك أذناً موسيقية دقيقة وخبرة طويلة في اكتشاف الأخطاء الحقيقية والتمييز بينها وبين عيوب التسجيل.

البيانات المرسلة للتدقيق:
- السورة المطلوبة: {surah}
- من الآية: {verse_from} إلى الآية: {verse_to}
- مستوى التصحيح المطلوب: "{level}"
- النص المستخرج من تلاوة الطالب صوتاً: "{transcription}"

التعليمات الصارمة للاستماع والتقييم الاحترافي:
1. **التعامل الذكي مع التشويش والتسجيل:** إذا كان هناك تشويش طفيف في الخلفية أو تقطيع بسيط في الصوت، لا تتجاهل التلاوة ولا تعتبرها خطأ؛ بل ركز على الكلمات الواضحة وحلل صحتها بدقة متجاوزاً عيوب الميكروفون أو البيئة المحيطة.
2. **التفريق بين زلة اللسان والخطأ الجوهري:** تفرّق بذكاء شديد بين الخطأ الإملائي البسيط الناتج عن تقنيات تحويل الصوت (Whisper) وبين الخطأ الحقيقي في الآيات (كإبدال كلمة بأخرى، تبديل المعنى، أو اللحن الجلي). لا تحاسب الطالب على قيود نظام التفريغ الصوتي.
3. **الدقة في الأحكام بحسب المستوى ({level}):** 
   - إن كان المستوى مبتدئاً: ركز فقط على الأخطاء الجلية التي تفسد المعنى.
   - إن كان المستوى متقدماً/دقيقاً: دقق في الأحكام التجويدية والمخارج بدقة مع تقديم توجيه راقي ومحفز.
4. **العدالة التامة:** إذا كانت القراءة صحيحة ومطابقة، امنح النتيجة "success" فوراً مع تشجيع لطيف. وإذا وُجد خطأ بيّن في الآيات أو تحريف، امنح "error" فوراً وحدد موضع الخلل بوضوح.
5. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين فقط:
- "status": إما "success" أو "error"
- "message": التقرير الاحترافي، الموجز، والمشجع بالعربية.
"""

        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

        result_json = json.loads(completion.choices[0].message.content)
        return jsonify(result_json)

    except Exception as e:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            
        print("CRITICAL ERROR TRACEBACK:")
        traceback.print_exc()
            
        return jsonify({
            "status": "error",
            "message": f"عذراً، حدث خطأ أثناء المعالجة التقنية: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
