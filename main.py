import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# تهيئة Gemini باستخدام المفتاح الذي أنشأته
import os
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

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

        # حفظ الملف الصوتي مؤقتاً لمعالجته
        audio_path = "temp_audio_file.mp3"
        audio_file.save(audio_path)

        # المعالجة للوسائط Google رفع الملف الصوتي إلى خوادم
        print("جاري رفع وتحليل الملف الصوتي بواسطة الذكاء الاصطناعي...")
        gemini_audio_ref = genai.upload_file(audio_path)

        # إعداد نموذج الذكاء الاصطناعي بمرونة أكبر وتوجيهات بناءة
        generation_config = {
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config
        )

        prompt = f"""
        أنت مقرئ وخبير محترف في علم التجويد والقراءات القرآنية برواية {riwaya}.
        مهمتك هي الاستماع بعناية للملف الصوتي المرفق ومقارنته بالآيات المطلوبة:
        - السورة: {surah}
        - من الآية: {verse_from} إلى الآية: {verse_to}
    
        تعليمات التقييم:
        1. افحص الحفظ وصحة الكلمات ومخارج الحروف. إذا كان الملف الصوتي عبارة عن صوت عشوائي تماماً، موسيقى، أو كلام فارغ لا علاقة له بالقرآن، اجعل الحالة "error".
        2. أما إذا كانت التلاوة قرآنية صحيحة في الجملة (حتى لو كانت هناك بعض الملاحظات أو الأخطاء التجويدية البسيطة)، فاجعل الحالة "success"، واكتب في الـ "message" تقريراً مفصلاً ولطيفاً يوضح للطالب أخطاءه ويوجهه بحكمة ومحبة لتصحيحها.
        3. أجب حصرياً بصيغة JSON نظيفة تحتوي على مفتاحين:
           - "status": إما "success" أو "error"
           - "message": التقرير المفصل بالعربية.
        """

        response = model.generate_content([gemini_audio_ref, prompt])

        if os.path.exists(audio_path):
            os.remove(audio_path)

        import json
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result_json = json.loads(clean_text)

        return jsonify(result_json)

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

