import streamlit as st
from groq import Groq
from docx import Document
from docx.shared import Pt, RGBColor
import io, os
from datetime import date

# --- Config & Styling ---
st.set_page_config(page_title="أخذ التاريخ المرضي — د. هاني الحناوي", page_icon="🧠", layout="wide")
st.markdown("""
<style>
    .main-title{font-size:28px;font-weight:700;color:#1A5CB8;text-align:center;margin-bottom:10px}
    .sec-header{font-size:18px;font-weight:700;color:#1A5CB8;margin-top:25px;margin-bottom:10px;
                border-bottom:3px solid #1A5CB8;padding-bottom:5px;background-color:#f0f2f6;padding-left:10px}
    .field-label{font-size:14px;color:#333;font-weight:600;margin-top:10px}
    stRadio > div{flex-direction:row !important;}
</style>""", unsafe_allow_html=True)

# --- Secrets & Constants ---
RECIPIENT_EMAIL = "yusuf.a.abdelatti@gmail.com"
groq_key = st.secrets["GROQ_API_KEY"]

# --- Helpers ---
def sec(ar, en=""):
    st.markdown(f'<div class="sec-header">{ar} / {en}</div>', unsafe_allow_html=True)

def lbl(ar, en=""):
    st.markdown(f'<div class="field-label">{ar} / {en}</div>', unsafe_allow_html=True)

def ti(ar, en, key, placeholder=""):
    lbl(ar, en); return st.text_input("", key=key, placeholder=placeholder, label_visibility="collapsed")

def ta(ar, en, key, height=120):
    lbl(ar, en); return st.text_area("", key=key, height=height, label_visibility="collapsed")

def sel(ar, en, opts, key):
    lbl(ar, en); return st.radio("", opts, key=key, horizontal=True, label_visibility="collapsed")

def sv(d, key, default="Not Mentioned"):
    v = d.get(key, "")
    if not v or v == "— اختر —": return default
    return str(v).strip()

# --- UI Lists ---
NA = "— اختر —"
GENDER_AR = ["ذكر", "أنثى"]
EDU_AR = [NA,"أمي","ابتدائي","إعدادي","ثانوي","جامعي","ماجستير/دكتوراه"]
SOCIAL_AR = [NA,"أعزب","متزوج","مطلق","أرمل"]
HTYPE_AR = [NA,"أولي / Initial","متابعة / Follow-up","استشاري"]
CONS_AR = [NA,"لا توجد","درجة أولى","درجة ثانية","أقارب بعيدون"]
ONSET_MODE = [NA,"مفاجئ / Sudden","تدريجي / Gradual"]
COURSE_AR = [NA,"مستمر","نوبات","تحسن","تدهور","متذبذب"]
BIRTH_ORDER = [NA,"الأول","الثاني","الثالث","الرابع+"]
ACADEMIC_AR = ["ممتاز","جيد","متوسط","ضعيف"]
SCREEN_AR = [NA,"أقل من ساعة","1-3 ساعات","3-6 ساعات","أكثر من 6 ساعات"]

# --- Main Interface ---
st.markdown('<div class="main-title">🧠 استمارة التاريخ المرضي الكاملة — عيادة د. هاني الحناوي</div>', unsafe_allow_html=True)

sheet_type = st.radio("**نوع الحالة / Case Type**", ["👤 بالغ / Adult", "👶 طفل / Child"], horizontal=True)
is_adult = "بالغ" in sheet_type
d = {}

with st.sidebar:
    st.header("⚙️ Clinical Info")
    history_by = st.text_input("Psychologist Name", "Dr. Yusuf")
    session_date = st.date_input("Session Date", date.today())

# ----------------- ADULT FORM -----------------
if is_adult:
    sec("البيانات الشخصية", "Demographics")
    c1, c2 = st.columns(2)
    with c1:
        d["name"] = ti("الاسم الكامل", "Full Name", "a_n")
        d["age"] = ti("السن", "Age", "a_a")
        d["gender"] = sel("النوع", "Gender", GENDER_AR, "a_g")
        d["edu"] = sel("التعليم", "Education", EDU_AR, "a_e")
    with c2:
        d["social"] = sel("الحالة الاجتماعية", "Social Status", SOCIAL_AR, "a_s")
        d["job"] = ti("الوظيفة", "Occupation", "a_j")
        d["phone"] = ti("رقم الهاتف", "Phone", "a_p")
        d["htype"] = sel("نوع التاريخ", "History Type", HTYPE_AR, "a_ht")

    sec("بيانات الأسرة والزواج", "Family & Marital History")
    c1, c2 = st.columns(2)
    with c1:
        d["f_status"] = sel("حالة الأب", "Father", ["حي", "متوفى"], "a_fs")
        d["m_status"] = sel("حالة الأم", "Mother", ["حية", "متوفاة"], "a_ms")
        d["cons"] = sel("قرابة الأبوين", "Consanguinity", CONS_AR, "a_cn")
    with c2:
        d["m_dur"] = ti("مدة الزواج", "Marriage Duration", "a_md")
        d["children"] = ti("عدد الأبناء", "Children Count", "a_cc")
        d["m_qual"] = sel("جودة العلاقة", "Marital Quality", ["جيدة", "متوسطة", "سيئة"], "a_mq")

    sec("الشكوى وتاريخ المرض الحالي", "C/O & HPI")
    d["complaints"] = ta("الشكوى الرئيسية (C/O)", "Chief Complaint", "a_co")
    d["hpi"] = ta("تاريخ المرض الحالي بالتفصيل (HPI)", "History of Present Illness", "a_hpi", height=250)

# ----------------- CHILD FORM -----------------
else:
    sec("بيانات الطفل والأسرة", "Child & Family Demographics")
    c1, c2 = st.columns(2)
    with c1:
        d["name"] = ti("اسم الطفل", "Child Name", "c_n")
        d["age"] = ti("السن", "Age", "c_a")
        d["school"] = ti("المدرسة/الحضانة", "School", "c_sch")
        d["order"] = sel("ترتيب الميلاد", "Birth Order", BIRTH_ORDER, "c_bo")
    with c2:
        d["academic"] = sel("المستوى الدراسي", "Academic Level", ACADEMIC_AR, "c_ac")
        d["screen"] = sel("وقت الشاشة", "Screen Time", SCREEN_AR, "c_st")
        d["cons"] = sel("قرابة الأبوين", "Consanguinity", CONS_AR, "c_cn")
        d["lives_with"] = ti("يعيش مع", "Lives With", "c_lw")

    sec("التاريخ التطوري", "Developmental Milestones")
    c1, c2 = st.columns(2)
    with c1:
        d["preg"] = ta("ملاحظات الحمل والولادة", "Pregnancy & Birth", "c_pb", height=80)
        d["motor"] = sel("النمو الحركي", "Motor Development", ["طبيعي", "متأخر"], "c_mo")
    with c2:
        d["speech"] = sel("الكلام", "Speech", ["طبيعي", "متأخر", "غائب"], "c_sp")
        d["toilet"] = sel("التحكم في الإخراج", "Toilet Training", ["طبيعي", "متأخر"], "c_to")

    sec("الشكوى والتاريخ الحالي", "C/O & HPI")
    d["complaints"] = ta("الشكوى الرئيسية (C/O)", "Chief Complaint", "c_co")
    d["hpi"] = ta("تاريخ المرض الحالي بالتفصيل (HPI)", "HPI", "c_hpi", height=250)

# ----------------- SHARED SECTIONS -----------------
sec("التاريخ الطبي والعائلي", "Medical & Family History")
c1, c2 = st.columns(2)
with c1:
    d["past_hx"] = ta("تاريخ مرضي سابق (عمليات/أمراض)", "Past Medical History", "g_pmh", height=100)
    d["drug_hx"] = ta("تاريخ الأدوية", "Drug History", "g_dh", height=100)
with c2:
    d["fam_hx"] = ta("تاريخ عائلي (نفسي/عصبي)", "Family History", "g_fh", height=100)
    d["inv"] = ta("الفحوصات (رسم مخ/رنين/اختبار ذكاء)", "Investigations", "g_inv", height=100)

sec("التقييم السريري العام", "Clinical Assessment")
c1, c2 = st.columns(2)
with c1:
    d["sleep"] = sel("النوم", "Sleep", ["طبيعي", "أرق", "نوم زائد"], "g_sl")
    d["appetite"] = sel("الشهية", "Appetite", ["طبيعية", "نقص", "زيادة"], "g_ap")
with c2:
    d["extra"] = ta("ملاحظات إضافية / توصيات", "Extra Notes / Recommendations", "g_ex")

# ----------------- REPORT GENERATION -----------------
st.divider()
if st.button("✦ Generate Premium Clinical Report", type="primary", use_container_width=True):
    if not d["name"] or not d["complaints"]:
        st.error("الرجاء إدخال اسم المريض والشكوى على الأقل!")
    else:
        with st.spinner("⏳ Processing with AI..."):
            # Prepare Data for AI
            summary_data = f"""
            Patient: {d['name']}, Age: {d['age']}, Type: {sheet_type}
            Chief Complaint: {d['complaints']}
            HPI: {d['hpi']}
            Past History: {d.get('past_hx')}
            Family History: {d.get('fam_hx')}
            Drug History: {d.get('drug_hx')}
            Investigations: {d.get('inv')}
            Sleep/Appetite: {d.get('sleep')}/{d.get('appetite')}
            Extra: {d.get('extra')}
            """

            system_instr = """
            You are a Senior Consultant Neurologist and Psychiatrist. 
            Convert the following raw data into a HIGH-END, professional English medical report.
            - Use formal medical terminology (e.g., 'Insidious onset', 'Stable course').
            - Organize with clear headers, bold sub-headers, and bullet points.
            - Create a section for 'Red Flags' or 'Clinical Alerts' if necessary.
            - Provide a 'Clinical Impression' or 'Summary' section.
            - DO NOT translate the Arabic verbatim; the system will append that separately.
            """

            try:
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_instr},
                        {"role": "user", "content": summary_data}
                    ],
                    temperature=0.3
                )
                
                ai_report = completion.choices[0].message.content

                # Build Verbatim Block (Pure Arabic)
                verbatim_block = f"\n\n---\n### 📝 الاستجابات الأصلية (Original Arabic Text)\n"
                verbatim_block += f"**الشكوى الرئيسية:** {d['complaints']}\n\n"
                verbatim_block += f"**تاريخ المرض الحالي:** {d['hpi']}\n\n"
                if d.get('inv'): verbatim_block += f"**الفحوصات والنتائج:** {d['inv']}\n\n"
                if d.get('extra'): verbatim_block += f"**ملاحظات إضافية:** {d['extra']}\n"

                final_report = ai_report + verbatim_block

                st.success("✅ Report Generated!")
                st.markdown(final_report)

                # Word Document Export
                doc = Document()
                doc.add_heading(f'Clinical History Report: {d["name"]}', 0)
                doc.add_paragraph(f"Date: {session_date} | Prepared by: {history_by}")
                doc.add_paragraph(final_report)
                
                bio = io.BytesIO()
                doc.save(bio)
                
                st.download_button(
                    label="📥 Download Word (.docx)",
                    data=bio.getvalue(),
                    file_name=f"Report_{d['name']}_{session_date}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Error calling Groq API: {e}")
