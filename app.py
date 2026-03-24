import streamlit as st
from groq import Groq
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io, os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date

st.set_page_config(page_title="أخذ التاريخ المرضي — د. هاني الحناوي", page_icon="🧠", layout="wide")
st.markdown("""
<style>
    .main-title{font-size:26px;font-weight:700;color:#1A5CB8;margin-bottom:2px}
    .sub-title{color:#888;font-size:13px;margin-bottom:20px}
    .sec-header{font-size:15px;font-weight:700;color:#1A5CB8;margin-top:22px;margin-bottom:8px;
                border-bottom:2px solid #1A5CB8;padding-bottom:4px}
    .field-label{font-size:13px;color:#222;margin-bottom:2px;font-weight:500}
</style>""", unsafe_allow_html=True)

RECIPIENT_EMAIL = "yusuf.a.abdelatti@gmail.com"
GMAIL_USER      = "yusuf.a.abdelatti@gmail.com"
GMAIL_PASS      = "erjl ehlj wpyg mfgx"
LOGO_PATH       = os.path.join(os.path.dirname(__file__), "logo.png")
CLINIC_BLUE     = RGBColor(0x1A, 0x5C, 0xB8)
DOCTOR = {
    "name":   "Dr. Hany Elhennawy",
    "title1": "Consultant of Neuro-Psychiatry",
    "title2": "Aviation Medical Council — Faculty of Medicine, 6th October University",
    "title3": "MD of Neuroscience Research, Karolinska Institute — Sweden",
    "title4": "Member of I.S.N.R",
    "address":"16 Hesham Labib St., off Makram Ebeid St. Ext., next to Mobilia Saad Mohamed Saad",
    "phone":  "+20 1000756200",
}

with st.sidebar:
    st.header("⚙️ الإعدادات")
    groq_key   = st.text_input("مفتاح Groq API", type="password", placeholder="gsk_...")
    st.caption("احصل على مفتاح مجاني من [console.groq.com](https://console.groq.com)")
    st.divider()
    history_by = st.text_input("اسم الأخصائي / Psychologist Name")

st.markdown('<div class="main-title">🧠 استمارة أخذ التاريخ المرضي</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">عيادة د. هاني الحناوي — طب وجراحة الأعصاب والنفس</div>', unsafe_allow_html=True)

# ── مساعدات ──
def sec(ar, en=""):
    st.markdown(f'<div class="sec-header">{ar}{" / "+en if en else ""}</div>', unsafe_allow_html=True)

def lbl(ar, en=""):
    txt = f"<b>{ar}</b>" + (f" / {en}" if en else "")
    st.markdown(f'<div class="field-label">{txt}</div>', unsafe_allow_html=True)

def ti(ar, en, key, placeholder=""):
    lbl(ar, en)
    return st.text_input("", key=key, placeholder=placeholder, label_visibility="collapsed")

def ta(ar, en, key, height=100):
    lbl(ar, en)
    return st.text_area("", key=key, height=height, label_visibility="collapsed")

def rb(ar, en, opts, key):
    lbl(ar, en)
    return st.radio("", opts, key=key, horizontal=True, label_visibility="collapsed")

def sel(ar, en, opts, key):
    lbl(ar, en)
    return st.selectbox("", opts, key=key, label_visibility="collapsed")

def ms(ar, en, opts, key):
    lbl(ar, en)
    return st.multiselect("", opts, key=key, label_visibility="collapsed")

def sv(d, key, default="لم يُذكر"):
    v = d.get(key, "")
    if not v: return default
    if isinstance(v, list): return "، ".join(v) if v else default
    v = str(v).strip()
    return v if v and v not in ["—", "— اختر —", "لم يُذكر"] else default

def yn_table(questions, d):
    """Render a clean Yes/No/N-A table for a list of (label_ar, label_en, key) tuples."""
    st.markdown("""
    <style>
    .yn-table { width:100%; border-collapse:collapse; margin-bottom:10px; }
    .yn-table td { padding:7px 10px; font-size:13px; border-bottom:1px solid #e0e6f0; }
    .yn-table tr:last-child td { border-bottom:none; }
    .yn-table tr:hover td { background:#f5f8ff; }
    .yn-label { color:#222; font-weight:500; width:65%; }
    </style>""", unsafe_allow_html=True)
    for (ar, en, key, opts) in questions:
        col_q, col_a = st.columns([3, 2])
        with col_q:
            st.markdown(f'<div style="padding:6px 0;font-size:13px;font-weight:500;color:#222">{ar}<br><span style="color:#888;font-size:11px">{en}</span></div>', unsafe_allow_html=True)
        with col_a:
            d[key] = st.radio("", opts, key=f"yn_{key}", horizontal=True, label_visibility="collapsed")
        st.markdown('<hr style="margin:0;border:none;border-top:1px solid #eef0f5">', unsafe_allow_html=True)
    return d

# ── قوائم الاختيارات ──
NA           = "— اختر —"
نعم_لا_لاينطبق = ["نعم", "لا", "لا ينطبق"]
نعم_لا      = ["نعم", "لا"]
GENDER_AR    = ["ذكر", "أنثى"]
EDU_AR       = [NA,"أمي","ابتدائي","إعدادي","ثانوي","جامعي","دراسات عليا"]
OCC_AR       = [NA,"موظف حكومي","موظف قطاع خاص","أعمال حرة","طالب","ربة منزل","متقاعد","عاطل عن العمل","أخرى"]
SOCIAL_AR    = [NA,"أعزب","متزوج","مطلق","أرمل","منفصل"]
SMOKING_AR   = ["لا يدخن","مدخن","توقف عن التدخين","شيشة","تدخين وشيشة"]
REFERRAL_AR  = [NA,"ذاتي","الأسرة","طبيب","أخصائي نفسي","مدرسة","أخرى"]
HTYPE_AR     = [NA,"أولي / Initial","متابعة / Follow-up","طارئ / Emergency","استشاري / Consultation"]
ALIVE_M      = ["على قيد الحياة","متوفى","غير معروف"]
ALIVE_F      = ["على قيد الحياة","متوفاة","غير معروف"]
CONS_AR      = [NA,"لا توجد قرابة","درجة أولى (مثال: أبناء العمومة والخؤولة)","درجة ثانية (مثال: أقارب من الدرجة الثانية)","درجة ثالثة (مثال: أقارب بعيدون)"]
PARENTS_REL  = [NA,"جيدة","متوسطة","سيئة","منفصلان","مطلقان","أحدهما متوفى"]
MARQ_AR      = [NA,"جيدة","متوسطة","سيئة","منفصلان"]
PRE_MAR      = [NA,"لا توجد علاقة سابقة","تعارف فقط","علاقة طويلة","زواج مرتب","أخرى"]
NUM_CHILD    = [NA,"لا يوجد أبناء","1","2","3","4","5","6 فأكثر"]
MARRIAGE_DUR = [NA,"أقل من سنة","1-3 سنوات","3-5 سنوات","5-10 سنوات","أكثر من 10 سنوات"]
ENGAGEMENT   = [NA,"لم تكن هناك خطوبة","أقل من 3 أشهر","3-6 أشهر","6-12 شهراً","أكثر من سنة"]
ONSET_MODE   = [NA,"مفاجئ","تدريجي"]
COURSE_AR    = [NA,"مستمر","نوبات متكررة","في تحسن","في تدهور","متذبذب"]
COMPLIANCE   = [NA,"ملتزم","غير منتظم","غير ملتزم","رافض"]
INSIGHT_AR   = [NA,"كاملة","جزئية","غائبة"]
SLEEP_AR     = ["طبيعي","أرق","نوم زيادة","متقطع"]
APPETITE_AR  = ["طبيعية","قلت","زادت"]
SUICIDAL_AR  = ["لا توجد","أفكار سلبية فقط","أفكار نشطة","خطة واضحة"]
SUBSTANCE_AR = [NA,"لا يوجد","كحول","حشيش","حبوب مهدئة","متعدد","أخرى"]
HOBBIES_AR   = ["قراءة","رياضة","موسيقى","رسم","طبخ","ألعاب إلكترونية","تواصل اجتماعي","لا توجد","أخرى"]
CHRONIC_AR   = [NA,"لا يوجد","سكري","ضغط","أمراض قلب","أمراض كلى","أمراض مناعية","سرطان","أخرى"]
SIB_GENDER   = [NA,"ذكر","أنثى"]
SIB_EDU      = [NA,"روضة","ابتدائي","إعدادي","ثانوي","جامعي","خريج","لا يدرس"]
SIB_REL      = [NA,"جيدة","متوسطة","تنافسية","صراع مستمر","إهمال متبادل"]
BIRTH_ORDER  = [NA,"الأول","الثاني","الثالث","الرابع","الخامس","السادس فأكثر","وحيد"]
BIRTH_TYPE   = [NA,"طبيعي","قيصري","بالجفت","بالشفاط"]
BIRTH_COMP   = [NA,"لا يوجد","صفراء","حضانة","اختناق","وزن منخفض","أخرى"]
BF_AR        = [NA,"رضاعة طبيعية","رضاعة صناعية","مختلطة"]
WEANING_AR   = [NA,"قبل 6 أشهر","6-12 شهراً","12-18 شهراً","18-24 شهراً","بعد سنتين"]
MOTOR_AR     = [NA,"طبيعي","متأخر","مبكر"]
SPEECH_AR    = [NA,"طبيعي","متأخر","غائب","تراجع بعد اكتمال"]
TEETH_AR     = [NA,"طبيعي (6-8 أشهر)","مبكر (قبل 6 أشهر)","متأخر (بعد 12 شهراً)"]
TOILET_AR    = [NA,"طبيعي (18-30 شهراً)","مبكر","متأخر (بعد 3 سنوات)"]
VACC_AR      = [NA,"مكتمل","غير مكتمل","غير معروف"]
ACADEMIC_AR  = ["ممتاز","جيد","متوسط","ضعيف","لا يدرس"]
WANTED_AR    = ["نعم، مرغوب فيه","لا، لم يكن مرغوباً فيه","حمل غير مخطط"]
GENDER_DES   = ["نعم، كان النوع مرغوباً","لا، كان يُفضَّل نوع آخر","لا فرق"]
LIVES_WITH   = [NA,"مع الوالدين","مع الأم فقط","مع الأب فقط","مع الجدين","مع أحد الأقارب","أخرى"]
SCREEN_AR    = [NA,"أقل من ساعة","1-2 ساعة","2-4 ساعات","4-6 ساعات","أكثر من 6 ساعات"]
PREG_AR      = [NA,"حمل طبيعي بدون مشاكل","حمل مع ضغط","حمل مع سكري","حمل مع نزيف","حمل في سن متأخرة (>35)","حمل مع مشكلة أخرى"]
PUNISHMENT   = [NA,"لفظي فقط","حرمان من الامتيازات","جسدي","تجاهل","مختلط"]
STRESS_AR    = [NA,"هادئ","بكاء","عدوان","انسحاب واستقواء","مختلط"]
SAME_SCH     = ["نعم","لا","لا ينطبق"]

# ════════════════════════════════════════════════════════
# نوع الاستمارة
# ════════════════════════════════════════════════════════
sheet_type = st.radio("**نوع الاستمارة / Sheet Type**", ["👤 بالغ / Adult", "👶 طفل / Child"], horizontal=True)
is_adult = "بالغ" in sheet_type
st.divider()
d = {}

# ════════════════════════════════════════════════════════
#  استمارة البالغ
# ════════════════════════════════════════════════════════
if is_adult:
    sec("البيانات الشخصية", "Personal Details")
    c1, c2 = st.columns(2)
    with c1:
        d["name"]       = ti("الاسم الكامل","Full Name","a_name")
        d["birthdate"]  = ti("تاريخ الميلاد","Birth Date","a_birthdate", placeholder="DD/MM/YYYY")
        # Auto-calculate age
        import re as _re
        from datetime import date as _date
        _bd = st.session_state.get("a_birthdate","")
        _age_str = ""
        if _bd:
            try:
                _parts = _re.split(r'[/\-\.]', _bd.strip())
                if len(_parts)==3:
                    _d,_m,_y = int(_parts[0]),int(_parts[1]),int(_parts[2])
                    _today = _date.today()
                    _years = _today.year - _y - ((_today.month,_today.day) < (_m,_d))
                    _months = (_today.month - _m) % 12
                    _age_str = f"{_years} years, {_months} months"
            except: pass
        d["age"] = _age_str
        if _age_str:
            st.caption(f"Calculated Age: **{_age_str}**")
        d["gender"]     = rb("النوع","Gender", GENDER_AR, "a_gender")
        d["education"]  = sel("المستوى التعليمي","Education", EDU_AR, "a_edu")
        d["occupation"] = sel("الوظيفة","Occupation", OCC_AR, "a_occ")
        d["occ_detail"] = ti("تفاصيل الوظيفة (إن لزم)","Occupation details","a_occd")
        d["hobbies"]    = ms("الهوايات","Hobbies", HOBBIES_AR, "a_hobbies")
    with c2:
        d["social"]     = sel("الحالة الاجتماعية","Social Status", SOCIAL_AR, "a_social")
        d["smoking"]    = sel("التدخين","Smoking", SMOKING_AR, "a_smoking")
        d["referral"]   = sel("مصدر الإحالة","Referral Source", REFERRAL_AR, "a_referral")
        d["htype"]      = sel("نوع التاريخ","History Type", HTYPE_AR, "a_htype")
        d["phone"]      = ti("رقم الهاتف","Phone","a_phone")
        d["date"]       = ti("تاريخ الجلسة","Date","a_date", placeholder=str(date.today()))

    sec("بيانات الأسرة", "Family Details")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**الأب / Father**")
        d["father_name"]  = ti("اسم الأب","Father Name","a_fn")
        d["father_age"]   = ti("سن الأب","Father Age","a_fa")
        d["father_occ"]   = ti("وظيفة الأب","Father Occupation","a_fo")
        d["father_alive"] = rb("حالة الأب","Father status", ALIVE_M, "a_falive")
    with c2:
        st.markdown("**الأم / Mother**")
        d["mother_name"]  = ti("اسم الأم","Mother Name","a_mn")
        d["mother_age"]   = ti("سن الأم","Mother Age","a_ma")
        d["mother_occ"]   = ti("وظيفة الأم","Mother Occupation","a_mo")
        d["mother_alive"] = rb("حالة الأم","Mother status", ALIVE_F, "a_malive")
    d["consanguinity"]    = sel("القرابة بين الأب والأم","Consanguinity", CONS_AR, "a_cons")
    d["parents_together"] = rb("هل الأبوان يعيشان معاً؟","Parents living together?", نعم_لا_لاينطبق, "a_ptog")
    d["chronic"]          = sel("مرض مزمن في الأسرة","Chronic illness in family", CHRONIC_AR, "a_chronic")

    sec("بيانات الزواج", "Marriage Details")
    c1, c2 = st.columns(2)
    with c1:
        d["spouse_name"]   = ti("اسم الزوج / الزوجة","Spouse Name","a_spn")
        d["spouse_age"]    = ti("سن الزوج / الزوجة","Spouse Age","a_spa")
        d["spouse_occ"]    = sel("وظيفة الزوج / الزوجة","Spouse Occupation", OCC_AR, "a_spo")
        d["marriage_dur"]  = sel("مدة الزواج","Marriage Duration", MARRIAGE_DUR, "a_mdur")
    with c2:
        d["engagement"]    = sel("فترة الخطوبة","Engagement Period", ENGAGEMENT, "a_eng")
        d["num_children"]  = sel("عدد الأبناء","Number of Children", NUM_CHILD, "a_nch")
        d["katb"]          = rb("كتب كتاب قبل الزواج؟","Katb Ketab?", ["نعم","لا","لا ينطبق"], "a_katb")
        d["marriage_qual"] = sel("جودة العلاقة الزوجية","Marriage quality", MARQ_AR, "a_mqual")
        d["pre_marriage"]  = sel("العلاقة قبل الزواج","Relationship before marriage", PRE_MAR, "a_pre")

    sec("الإخوة والأخوات", "Brothers and Sisters")
    siblings = []
    for i in range(1, 5):
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            lbl(f"النوع {i}",""); g = st.selectbox("",SIB_GENDER,key=f"a_sg{i}",label_visibility="collapsed")
        with c2:
            n = st.text_input("",key=f"a_sn{i}",placeholder=f"الاسم {i}",label_visibility="collapsed")
        with c3:
            a_s = st.text_input("",key=f"a_sa{i}",placeholder=f"السن {i}",label_visibility="collapsed")
        with c4:
            lbl(f"التعليم {i}",""); e = st.selectbox("",SIB_EDU,key=f"a_se{i}",label_visibility="collapsed")
        with c5:
            nt = st.text_input("",key=f"a_st{i}",placeholder=f"ملاحظات {i}",label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a_s,"edu":e,"notes":nt})
    d["siblings"] = siblings

    sec("الشكاوى وتاريخ المرض الحالي", "Complaints & HPI")
    d["onset"]      = ti("متى بدأت الأعراض؟","Onset","a_onset")
    d["onset_mode"] = sel("طريقة البداية","Mode of onset", ONSET_MODE, "a_omode")
    d["course"]     = sel("مسار المرض","Course", COURSE_AR, "a_course")
    d["complaints"] = ta("الشكاوى الرئيسية (C/O)","Chief Complaints",  "a_co",  120)
    d["hpi"]        = ta("تاريخ المرض الحالي بالتفصيل (HPI)","HPI", "a_hpi", 220)

    sec("تاريخ الأدوية", "Drug History")
    yn_table([
        ("هل يتناول أدوية حالياً؟","Currently on medication?","on_meds", نعم_لا_لاينطبق),
    ], d)
    d["compliance"] = sel("الالتزام بالأدوية","Compliance", COMPLIANCE, "a_comp")
    d["drug_hx"]    = ta("تفاصيل الأدوية (الاسم، الجرعة، المدة)","Medications", "a_drug", 100)

    sec("التاريخ المرضي السابق", "Past History")
    yn_table([
        ("مرض نفسي سابق؟","Previous psychiatric illness?","prev_psych", نعم_لا_لاينطبق),
        ("دخول مستشفى سابق؟","Previous hospitalization?","prev_hosp", نعم_لا_لاينطبق),
    ], d)
    d["past_hx"] = ta("تفاصيل التاريخ السابق","Details","a_past",80)

    sec("التاريخ العائلي", "Family History")
    yn_table([
        ("مرض نفسي في الأسرة؟","Psychiatric illness in family?","fam_psych", نعم_لا_لاينطبق),
        ("مرض عصبي في الأسرة؟","Neurological illness in family?","fam_neuro", نعم_لا_لاينطبق),
    ], d)
    if d.get("fam_psych") == "نعم":
        d["fam_psych_details"] = ti("ما هو المرض النفسي؟ (من في الأسرة)","Specify psychiatric illness","a_fpsych_det")
    else:
        d["fam_psych_details"] = ""
    if d.get("fam_neuro") == "نعم":
        d["fam_neuro_details"] = ti("ما هو المرض العصبي؟ (من في الأسرة)","Specify neurological illness","a_fneuro_det")
    else:
        d["fam_neuro_details"] = ""
    d["family_hx"] = ta("تفاصيل التاريخ العائلي","Details","a_famhx",80)

    sec("الفحوصات", "Investigations")
    yn_table([
        ("هل أُجريت فحوصات؟","Investigations done?","had_inv", نعم_لا_لاينطبق),
    ], d)
    d["investigations"] = ta("تفاصيل الفحوصات ونتائجها","Details","a_inv",80)

    sec("العمليات والجراحات", "Operations and Surgeries")
    yn_table([
        ("عمليات جراحية سابقة؟","Previous surgeries?","had_surg", نعم_لا_لاينطبق),
    ], d)
    d["surgeries"] = ta("تفاصيل العمليات","Details","a_surg",60)

    sec("التقييم السريري", "Clinical Assessment")
    c1, c2 = st.columns(2)
    with c1:
        d["sleep"]     = sel("نمط النوم","Sleep", SLEEP_AR, "a_sleep")
        d["appetite"]  = sel("الشهية","Appetite", APPETITE_AR, "a_appetite")
        d["suicidal"]  = sel("أفكار انتحارية","Suicidal ideation", SUICIDAL_AR, "a_suicidal")
        d["insight"]   = sel("البصيرة / الاستبصار","Insight", INSIGHT_AR, "a_insight")
    with c2:
        d["substance"] = sel("تعاطي مواد","Substance use", SUBSTANCE_AR, "a_subs")
        d["substance_details"] = ta("تفاصيل المواد","Details","a_subsd",60)
    d["extra_notes"]= ta("ملاحظات إضافية","Additional notes","a_extra",80)
    patient_name = d.get("name") or "المريض"

# ════════════════════════════════════════════════════════
#  استمارة الطفل
# ════════════════════════════════════════════════════════
else:
    sec("البيانات الشخصية", "Personal Details")
    c1, c2 = st.columns(2)
    with c1:
        d["name"]        = ti("اسم الطفل كاملاً","Child's Full Name","c_name")
        d["birthdate"]  = ti("تاريخ الميلاد","Birth Date","c_birthdate", placeholder="DD/MM/YYYY")
        # Auto-calculate age
        import re as _re2
        from datetime import date as _date2
        _bd2 = st.session_state.get("c_birthdate","")
        _age_str2 = ""
        if _bd2:
            try:
                _parts2 = _re2.split(r'[/\-\.]', _bd2.strip())
                if len(_parts2)==3:
                    _d2,_m2,_y2 = int(_parts2[0]),int(_parts2[1]),int(_parts2[2])
                    _today2 = _date2.today()
                    _years2 = _today2.year - _y2 - ((_today2.month,_today2.day) < (_m2,_d2))
                    _months2 = (_today2.month - _m2) % 12
                    _age_str2 = f"{_years2} years, {_months2} months"
            except: pass
        d["age"] = _age_str2
        if _age_str2:
            st.caption(f"Calculated Age: **{_age_str2}**")
        d["gender"]      = rb("النوع","Gender", GENDER_AR, "c_gender")
        d["school"]      = ti("اسم المدرسة","School Name","c_school")
        d["grade"]       = ti("الصف الدراسي","Grade","c_grade")
        d["academic"]    = sel("المستوى الدراسي","Academic Performance", ACADEMIC_AR, "c_academic")
        d["birth_order"] = sel("ترتيب الميلاد","Birth order", BIRTH_ORDER, "c_border")
    with c2:
        d["lives_with"]  = sel("يعيش مع","Lives with", LIVES_WITH, "c_lives")
        d["phone"]       = ti("تليفون","Phone","c_phone")
        d["date"]        = ti("تاريخ الجلسة","Date","c_date", placeholder=str(date.today()))
        d["screen_time"] = sel("وقت الشاشة اليومي","Daily screen time", SCREEN_AR, "c_screen")
        d["wanted"]      = rb("هل كان الطفل مرغوباً فيه؟","Was child wanted?", WANTED_AR, "c_wanted")
        d["gender_des"]  = rb("هل كان النوع مرغوباً فيه؟","Was gender desired?", GENDER_DES, "c_gdes")

    sec("مراحل النمو", "Developmental Milestones")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**الحمل والولادة**")
        d["pregnancy"]    = ta("تفاصيل الحمل","Pregnancy details","c_preg", 80)
        d["birth_type"]   = sel("نوع الولادة","Birth type", BIRTH_TYPE, "c_btype")
        d["birth_comp"]   = sel("مضاعفات الولادة","Birth complications", BIRTH_COMP, "c_bcomp")
        d["vacc_status"]  = sel("التطعيمات","Vaccinations", VACC_AR, "c_vacc")
        d["vacc_comp"]    = ti("مضاعفات بعد التطعيم (إن وجدت)","Post-vaccine comp.","c_vcomp")
    with c2:
        st.markdown("**التغذية والنمو الحركي**")
        d["breastfeeding"]= sel("الرضاعة","Breastfeeding", BF_AR, "c_bf")
        d["weaning"]      = sel("سن الفطام","Weaning age", WEANING_AR, "c_wean")
        d["motor"]        = sel("النمو الحركي","Motor development", MOTOR_AR, "c_motor")
        d["motor_detail"] = ti("تفاصيل الحركة (مشي، جلوس...)","Motor details","c_motord")
        d["teething"]     = sel("التسنين","Teething", TEETH_AR, "c_teeth")
        d["toilet"]       = sel("تدريب دورة المياه","Toilet training", TOILET_AR, "c_toilet")
    with c3:
        st.markdown("**اللغة والإدراك**")
        d["speech"]       = sel("الكلام","Speech", SPEECH_AR, "c_speech")
        d["speech_detail"]= ti("تفاصيل الكلام","Speech details","c_speechd")
        d["attention"]    = rb("الانتباه","Attention",["طبيعي","ضعيف","لا ينطبق"],"c_attn")
        d["concentration"]= rb("التركيز","Concentration",["طبيعي","ضعيف","لا ينطبق"],"c_conc")
        d["comprehension"]= rb("الفهم والإدراك","Comprehension",["طبيعي","ضعيف","لا ينطبق"],"c_comp")
    d["dev_notes"] = ta("ملاحظات النمو","Developmental notes","c_devnotes",80)

    sec("بيانات الأسرة", "Family Details")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**الأب / Father**")
        d["father_name"]      = ti("اسم الأب","Father Name","c_fn")
        d["father_age"]       = ti("سن الأب","Father Age","c_fa")
        d["father_occ"]       = ti("وظيفة الأب","Father Occupation","c_fo")
        d["father_alive"]     = rb("حالة الأب","Father status", ALIVE_M, "c_falive")
        d["father_hereditary"]= ti("مرض وراثي عند الأب (إن وجد)","Father hereditary","c_fh")
    with c2:
        st.markdown("**الأم / Mother**")
        d["mother_name"]      = ti("اسم الأم","Mother Name","c_mn")
        d["mother_age"]       = ti("سن الأم","Mother Age","c_ma")
        d["mother_occ"]       = ti("وظيفة الأم","Mother Occupation","c_mo")
        d["mother_alive"]     = rb("حالة الأم","Mother status", ALIVE_F, "c_malive")
        d["mother_hereditary"]= ti("مرض وراثي عند الأم (إن وجد)","Mother hereditary","c_mh")
    d["consanguinity"] = sel("القرابة بين الأب والأم","Consanguinity", CONS_AR, "c_cons")
    d["parents_rel"]   = sel("طبيعة العلاقة بين الأب والأم","Parents relationship", PARENTS_REL, "c_prel")

    sec("الإخوة والأخوات", "Brothers and Sisters")
    siblings = []
    for i in range(1, 5):
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            lbl(f"النوع {i}",""); g = st.selectbox("",SIB_GENDER,key=f"c_sg{i}",label_visibility="collapsed")
        with c2:
            n = st.text_input("",key=f"c_sn{i}",placeholder=f"الاسم {i}",label_visibility="collapsed")
        with c3:
            a_s = st.text_input("",key=f"c_sa{i}",placeholder=f"السن {i}",label_visibility="collapsed")
        with c4:
            lbl(f"التعليم {i}",""); e = st.selectbox("",SIB_EDU,key=f"c_se{i}",label_visibility="collapsed")
        with c5:
            nt = st.text_input("",key=f"c_st{i}",placeholder=f"ملاحظات {i}",label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a_s,"edu":e,"notes":nt})
    d["siblings"]    = siblings
    d["sibling_rel"] = sel("علاقة الأخوة ببعض","Sibling relationship", SIB_REL, "c_sibrel")
    d["same_school"] = rb("هل الأخوة في نفس المدرسة؟","Same school?", SAME_SCH, "c_ssch")

    sec("الشكاوى وتاريخ المرض الحالي", "Complaints & HPI")
    d["onset"]      = ti("متى بدأت الأعراض؟","Onset","c_onset")
    d["onset_mode"] = sel("طريقة البداية","Mode of onset", ONSET_MODE, "c_omode")
    d["course"]     = sel("مسار المرض","Course", COURSE_AR, "c_course")
    d["complaints"] = ta("الشكاوى الرئيسية (C/O)","Chief Complaints","c_co",120)
    d["hpi"]        = ta("تاريخ المرض الحالي بالتفصيل (HPI)","HPI","c_hpi",220)

    sec("التاريخ المرضي السابق", "Past History")
    yn_table([
        ("حرارة ≥40 درجة؟","High fever ≥40°C?","high_fever", نعم_لا_لاينطبق),
        ("ارتطام رأس؟","Head trauma?","head_trauma", نعم_لا_لاينطبق),
        ("تشنجات؟","Convulsions?","convulsions", نعم_لا_لاينطبق),
        ("مضاعفات بعد التطعيم؟","Post-vaccine complications?","post_vaccine", نعم_لا_لاينطبق),
        ("دخول مستشفى سابق؟","Previous hospitalization?","prev_hosp", نعم_لا_لاينطبق),
        ("جلسات علاجية سابقة؟","Previous therapy sessions?","prev_therapy", نعم_لا_لاينطبق),
    ], d)
    if d.get("head_trauma") == "نعم":
        c1, c2 = st.columns(2)
        with c1:
            d["head_trauma_location"] = ti("مكان الارتطام في الرأس","Location on head","c_htrauma_loc")
        with c2:
            d["head_trauma_details"]  = ti("كيف حدث الارتطام؟","How did it happen?","c_htrauma_det")
    else:
        d["head_trauma_location"] = ""
        d["head_trauma_details"]  = ""
    d["past_hx"] = ta("تفاصيل التاريخ السابق","Details","c_past",100)

    sec("التاريخ العائلي", "Family History")
    yn_table([
        ("مرض نفسي في الأسرة؟","Psychiatric illness in family?","fam_psych", نعم_لا_لاينطبق),
        ("مرض عصبي في الأسرة؟","Neurological illness in family?","fam_neuro", نعم_لا_لاينطبق),
        ("إعاقة ذهنية في الأسرة؟","Intellectual disability in family?","fam_mr", نعم_لا_لاينطبق),
        ("صرع في الأسرة؟","Epilepsy in family?","fam_epilepsy", نعم_لا_لاينطبق),
    ], d)
    if d.get("fam_psych") == "نعم":
        d["fam_psych_details"] = ti("ما هو المرض النفسي؟ (من في الأسرة)","Specify psychiatric illness","c_fpsych_det")
    else:
        d["fam_psych_details"] = ""
    if d.get("fam_neuro") == "نعم":
        d["fam_neuro_details"] = ti("ما هو المرض العصبي؟ (من في الأسرة)","Specify neurological illness","c_fneuro_det")
    else:
        d["fam_neuro_details"] = ""
    if d.get("fam_mr") == "نعم":
        d["fam_mr_details"] = ti("من في الأسرة؟ وما درجة الإعاقة؟","Specify MR details","c_fmr_det")
    else:
        d["fam_mr_details"] = ""
    if d.get("fam_epilepsy") == "نعم":
        d["fam_epilepsy_details"] = ti("من في الأسرة؟ وهل يتعالج؟","Specify epilepsy details","c_fepil_det")
    else:
        d["fam_epilepsy_details"] = ""
    d["family_hx"] = ta("تفاصيل التاريخ العائلي","Details","c_famhx",80)

    sec("الفحوصات", "Investigations")
    yn_table([
        ("أشعة مقطعية؟","CT scan?","had_ct", نعم_لا_لاينطبق),
        ("رنين مغناطيسي؟","MRI?","had_mri", نعم_لا_لاينطبق),
        ("رسم مخ (EEG)؟","EEG?","had_eeg", نعم_لا_لاينطبق),
        ("اختبار ذكاء SB5؟","IQ test (SB5)?","had_iq", نعم_لا_لاينطبق),
        ("مقياس CARS؟","CARS scale?","had_cars", نعم_لا_لاينطبق),
    ], d)
    if d.get("had_cars") == "نعم":
        d["cars_score"] = ti("درجة CARS","CARS score","c_carsscore")
    else:
        d["cars_score"] = ""
    d["investigations"] = ta("تفاصيل الفحوصات ونتائجها","Details","c_inv",80)

    sec("العمليات والجراحات", "Operations and Surgeries")
    yn_table([
        ("عمليات جراحية سابقة؟","Previous surgeries?","had_surg", نعم_لا_لاينطبق),
    ], d)
    d["surgeries"] = ta("تفاصيل العمليات","Details","c_surg",60)

    sec("التقييم السريري", "Clinical Assessment")
    c1, c2 = st.columns(2)
    with c1:
        d["sleep"]          = sel("نمط النوم","Sleep", SLEEP_AR, "c_sleep")
        d["appetite"]       = sel("الشهية","Appetite", APPETITE_AR, "c_appetite")
        d["punishment"]     = ms("طرق العقاب المستخدمة","Punishment methods", ["لفظي","حرمان من الامتيازات","جسدي","تجاهل","عقاب بالحرمان الاجتماعي","أخرى"], "c_punish")
        d["stress_reaction"]= ms("رد الفعل تجاه الضغوط","Reaction to stress", ["هادئ","بكاء","عدوان","انسحاب","نوبات غضب","تبوّل لاإرادي","أخرى"], "c_stress")
    with c2:
        d["therapy"] = ta("الجلسات العلاجية الحالية","Current therapy sessions","c_therapy",80)
    d["extra_notes"] = ta("ملاحظات إضافية","Additional notes","c_extra",80)
    patient_name = d.get("name") or "الطفل"

# ════════════════════════════════════════════════════════
#  زر توليد التقرير
# ════════════════════════════════════════════════════════
st.divider()
if st.button("✦ توليد التقرير / Generate Report", type="primary", use_container_width=True):
    if not groq_key:
        st.error("الرجاء إدخال مفتاح Groq API في الشريط الجانبي.")
    else:
        siblings = d.get("siblings", [])
        sib_text = "\n".join([
            f"  {i+1}. {sb['name']} | {sb['gender']} | السن: {sb['age']} | التعليم: {sb['edu']} | ملاحظات: {sb['notes'] or 'لا يوجد'}"
            for i, sb in enumerate(siblings)
        ]) or "لا يوجد إخوة مُدخَلون"

        if is_adult:
            data_block = f"""
المريض: {sv(d,'name')} | تاريخ الميلاد: {sv(d,'birthdate')} | السن: {sv(d,'age')} | النوع: {sv(d,'gender')}
التاريخ: {sv(d,'date')} | الأخصائي: {history_by or 'لم يُذكر'} | نوع التاريخ: {sv(d,'htype')}
الهاتف: {sv(d,'phone')} | مصدر الإحالة: {sv(d,'referral')}
الوظيفة: {sv(d,'occupation')} — {sv(d,'occ_detail')} | التعليم: {sv(d,'education')}
الحالة الاجتماعية: {sv(d,'social')} | التدخين: {sv(d,'smoking')}
الهوايات: {sv(d,'hobbies')}

بيانات الأسرة:
الأب: {sv(d,'father_name')} | السن: {sv(d,'father_age')} | الوظيفة: {sv(d,'father_occ')} | الحالة: {sv(d,'father_alive')}
الأم: {sv(d,'mother_name')} | السن: {sv(d,'mother_age')} | الوظيفة: {sv(d,'mother_occ')} | الحالة: {sv(d,'mother_alive')}
القرابة بين الأبوين: {sv(d,'consanguinity')} | يعيشان معاً: {sv(d,'parents_together')}
مرض مزمن في الأسرة: {sv(d,'chronic')}

بيانات الزواج:
الزوج/الزوجة: {sv(d,'spouse_name')} | السن: {sv(d,'spouse_age')} | الوظيفة: {sv(d,'spouse_occ')}
مدة الزواج: {sv(d,'marriage_dur')} | فترة الخطوبة: {sv(d,'engagement')}
كتب كتاب: {sv(d,'katb')} | جودة الزواج: {sv(d,'marriage_qual')} | العلاقة قبل الزواج: {sv(d,'pre_marriage')}
عدد الأبناء: {sv(d,'num_children')}

الإخوة:
{sib_text}

بداية الأعراض: {sv(d,'onset')} | طريقة البداية: {sv(d,'onset_mode')} | المسار: {sv(d,'course')}
الشكاوى الرئيسية:
{sv(d,'complaints')}
تاريخ المرض الحالي:
{sv(d,'hpi')}

الأدوية: يتناول أدوية حالياً: {sv(d,'on_meds')} | الالتزام: {sv(d,'compliance')}
تفاصيل الأدوية:
{sv(d,'drug_hx')}

التاريخ السابق: مرض نفسي سابق: {sv(d,'prev_psych')} | دخول مستشفى: {sv(d,'prev_hosp')}
{sv(d,'past_hx')}

التاريخ العائلي: مرض نفسي: {sv(d,'fam_psych')}{(' — ' + sv(d,'fam_psych_details')) if d.get('fam_psych_details') else ''} | مرض عصبي: {sv(d,'fam_neuro')}{(' — ' + sv(d,'fam_neuro_details')) if d.get('fam_neuro_details') else ''}
{sv(d,'family_hx')}

الفحوصات: أُجريت فحوصات: {sv(d,'had_inv')}
{sv(d,'investigations')}

الجراحات: عمليات سابقة: {sv(d,'had_surg')}
{sv(d,'surgeries')}

التقييم السريري:
النوم: {sv(d,'sleep')} | الشهية: {sv(d,'appetite')} | الأفكار الانتحارية: {sv(d,'suicidal')} | البصيرة: {sv(d,'insight')}
تعاطي المواد: {sv(d,'substance')} — {sv(d,'substance_details')}
ملاحظات إضافية: {sv(d,'extra_notes')}
"""
        else:
            data_block = f"""
الطفل: {sv(d,'name')} | تاريخ الميلاد: {sv(d,'birthdate')} | السن: {sv(d,'age')} | النوع: {sv(d,'gender')}
التاريخ: {sv(d,'date')} | الأخصائي: {history_by or 'لم يُذكر'}
الهاتف: {sv(d,'phone')} | يعيش مع: {sv(d,'lives_with')}
المدرسة: {sv(d,'school')} | الصف: {sv(d,'grade')} | المستوى الدراسي: {sv(d,'academic')}
ترتيب الميلاد: {sv(d,'birth_order')} | وقت الشاشة اليومي: {sv(d,'screen_time')}
هل كان مرغوباً فيه: {sv(d,'wanted')} | النوع المرغوب: {sv(d,'gender_des')}

مراحل النمو:
الحمل: {sv(d,'pregnancy')} | نوع الولادة: {sv(d,'birth_type')} | مضاعفات الولادة: {sv(d,'birth_comp')}
التطعيمات: {sv(d,'vacc_status')} | مضاعفات التطعيم: {sv(d,'vacc_comp')}
الرضاعة: {sv(d,'breastfeeding')} | الفطام: {sv(d,'weaning')}
النمو الحركي: {sv(d,'motor')} — {sv(d,'motor_detail')}
التسنين: {sv(d,'teething')} | تدريب دورة المياه: {sv(d,'toilet')}
الكلام: {sv(d,'speech')} — {sv(d,'speech_detail')}
الانتباه: {sv(d,'attention')} | التركيز: {sv(d,'concentration')} | الفهم والإدراك: {sv(d,'comprehension')}
ملاحظات النمو: {sv(d,'dev_notes')}

الأسرة:
الأب: {sv(d,'father_name')} | السن: {sv(d,'father_age')} | الوظيفة: {sv(d,'father_occ')} | الحالة: {sv(d,'father_alive')} | مرض وراثي: {sv(d,'father_hereditary')}
الأم: {sv(d,'mother_name')} | السن: {sv(d,'mother_age')} | الوظيفة: {sv(d,'mother_occ')} | الحالة: {sv(d,'mother_alive')} | مرض وراثي: {sv(d,'mother_hereditary')}
القرابة: {sv(d,'consanguinity')} | طبيعة العلاقة الزوجية: {sv(d,'parents_rel')}

الإخوة:
{sib_text}
علاقة الأخوة ببعض: {sv(d,'sibling_rel')} | في نفس المدرسة: {sv(d,'same_school')}

بداية الأعراض: {sv(d,'onset')} | طريقة البداية: {sv(d,'onset_mode')} | المسار: {sv(d,'course')}
الشكاوى الرئيسية:
{sv(d,'complaints')}
تاريخ المرض الحالي:
{sv(d,'hpi')}

التاريخ السابق: حرارة ≥40: {sv(d,'high_fever')} | ارتطام رأس: {sv(d,'head_trauma')}{(' — المكان: ' + sv(d,'head_trauma_location') + ' — كيف: ' + sv(d,'head_trauma_details')) if sv(d,'head_trauma_location') != 'لم يُذكر' or sv(d,'head_trauma_details') != 'لم يُذكر' else ''} | تشنجات: {sv(d,'convulsions')}
مضاعفات بعد التطعيم: {sv(d,'post_vaccine')} | دخول مستشفى: {sv(d,'prev_hosp')} | جلسات سابقة: {sv(d,'prev_therapy')}
{sv(d,'past_hx')}

التاريخ العائلي: مرض نفسي: {sv(d,'fam_psych')}{(' — ' + sv(d,'fam_psych_details')) if d.get('fam_psych_details') else ''} | عصبي: {sv(d,'fam_neuro')}{(' — ' + sv(d,'fam_neuro_details')) if d.get('fam_neuro_details') else ''} | إعاقة ذهنية: {sv(d,'fam_mr')}{(' — ' + sv(d,'fam_mr_details')) if d.get('fam_mr_details') else ''} | صرع: {sv(d,'fam_epilepsy')}{(' — ' + sv(d,'fam_epilepsy_details')) if d.get('fam_epilepsy_details') else ''}
{sv(d,'family_hx')}

الفحوصات: CT: {sv(d,'had_ct')} | MRI: {sv(d,'had_mri')} | EEG: {sv(d,'had_eeg')} | SB5: {sv(d,'had_iq')} | CARS: {sv(d,'had_cars')} — الدرجة: {sv(d,'cars_score')}
{sv(d,'investigations')}

الجراحات: {sv(d,'had_surg')} — {sv(d,'surgeries')}

التقييم: النوم: {sv(d,'sleep')} | الشهية: {sv(d,'appetite')} | طرق العقاب: {sv(d,'punishment')} | رد الفعل: {sv(d,'stress_reaction')}
الجلسات الحالية: {sv(d,'therapy')}
ملاحظات إضافية: {sv(d,'extra_notes')}
"""

        # Build verbatim Arabic section
        verbatim_block = ""
        verbatim_fields = [
            ("الشكوى الرئيسية", sv(d,'complaints')),
            ("تاريخ المرض الحالي", sv(d,'hpi')),
            ("تفاصيل الحمل", sv(d,'pregnancy') if not is_adult else ""),
            ("تاريخ الأدوية - تفاصيل", sv(d,'drug_hx') if is_adult else ""),
            ("التاريخ المرضي السابق - تفاصيل", sv(d,'past_hx')),
            ("التاريخ العائلي - تفاصيل", sv(d,'family_hx')),
            ("الفحوصات - تفاصيل", sv(d,'investigations')),
            ("الجلسات العلاجية الحالية", sv(d,'therapy') if not is_adult else ""),
            ("ملاحظات إضافية", sv(d,'extra_notes')),
        ]
        for heading, text in verbatim_fields:
            if text and text != "لم يُذكر":
                verbatim_block += f"\n{heading}:\n{text}\n"
        if not verbatim_block:
            verbatim_block = "(No long text responses provided)"

        prompt = f"""You are a clinical report formatter. Generate a clean, professional clinical report in ENGLISH based on the structured data below.

STRICT RULES:

LANGUAGE HANDLING:
1. The main report body must be fully in English — no Arabic text anywhere in sections 1 through 6.
2. SHORT answers (MCQ, yes/no, single-word): convert to clear natural English sentences.
   - Correct: "The child is breastfed." / "Sleep is interrupted." / "There is a delay in speech."
   - Incorrect: "Breastfeeding: طبيعية" / "النوم: متقطع"
3. LONG text responses (paragraphs, detailed descriptions written in Arabic):
   - DO NOT translate them.
   - DO NOT include them anywhere in the main report sections.
   - Place them ONLY in the final section "Original Arabic Responses" exactly as written.
4. DO NOT mix Arabic and English in the same sentence or the same section.
5. Arabic is ONLY allowed in section 7 "Original Arabic Responses".

CONTENT RULES:
6. DO NOT add interpretations, diagnoses, clinical judgments, or assumptions.
7. DO NOT add any information not explicitly provided in the data.
8. If a field is "لم يُذكر" (not reported) — skip it completely, do not mention it.
9. If all fields in a section are not reported — skip the entire section.
10. "No" / "لا" answers — do not mention them at all.
11. FORBIDDEN: No diagnosis, no clinical judgment, no recommendations, no assumptions, no summarization of Arabic text.

FORMATTING RULES FOR OUTPUT:
12. Do NOT use any markdown symbols for bold (no **, no __, no ##, no #).
    Use ONLY plain text. Bold rendering will be handled by the document builder.
13. For section titles: write them in ALL CAPS on their own line, preceded by the section number.
    Example: "1. PATIENT INFORMATION" — no symbols before or after.
14. For sub-table titles: write them in Title Case on their own line, followed by a colon.
    Example: "Personal Details:" or "Father Information:"
15. For table rows: use pipe format exactly like this:
    Field | Value
    Do NOT bold inside the pipe row. The builder will bold the field.
16. For line-by-line sections: write one statement per line, no bullet symbols.
17. The Specialist Name must appear ONLY in the header section at the top, nowhere else.
18. No hashtags, no asterisks, no markdown of any kind anywhere in the output.

Structure the report using these sections. Include ONLY data that was provided.

REPORT HEADER (top of report, before all sections):
Write these fields as pipe-separated rows — labels in English only:
Patient Name | [value]
Form Type | [value]
Specialist Name | [value]
Date | [value]
Phone Number | [value]
Add a clear visual separator line after this header.
The Specialist Name must NOT appear anywhere else in the report.

CLINICAL SUMMARY (immediately after the header, before section 1):
Write a brief, professional English summary (3-5 sentences maximum).
Rules:
- Written in English only.
- Summarize the most important case information (who, main complaint, key background).
- DO NOT add diagnosis, assumptions, or information not in the input.
- DO NOT repeat the exact same wording as the structured sections below.
- Keep it concise and clinically relevant.
Write it as a paragraph under the title: CLINICAL SUMMARY
Format this title EXACTLY the same as all other numbered section titles (e.g. "CLINICAL SUMMARY" on its own line, all caps, no symbols).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. PATIENT INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Split into exactly THREE separate sub-tables, each with its own title and 2–5 rows:

Sub-table 1 title: Personal Details
Fields: Name, Birth Date, Age (auto-calculated), Gender, {"Social Status, Education, Occupation" if is_adult else "Birth Order, Lives With, School, Grade, Academic Performance"}

Sub-table 2 title: {"Lifestyle & Background" if is_adult else "Daily Routine & Screen Time"}
Fields: {"Smoking, Hobbies, Referral Source, History Type" if is_adult else "Screen Time, Referral Source, History Type"}

Each sub-table format — Field | Value (do not bold inside the row, builder handles it).
Skip any fields not reported.
Do NOT create a "Contact and Administrative" sub-table — these fields are in the header only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. PRESENTING CONCERNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This section has TWO parts only:

PART A — Onset Details:
Present onset, mode of onset, and course as a table (Field | Value rows, 2-3 rows max).
Sub-table title: Onset Details:

PART B — Symptoms:
Write ONLY the sub-table title: Symptoms:
Then write each symptom on its own line below the title — do NOT put them in a table.
Do NOT include Chief Complaint or HPI text here — those go in section 7.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{"3. FAMILY AND MARRIAGE BACKGROUND" if is_adult else "3. FAMILY BACKGROUND"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MUST be in structured table format — NOT narrative sentences.
- Split into multiple smaller sub-tables (2–5 rows each).
- Sub-categories: Father | Mother | Parents Relationship | {"Marriage Details | " if is_adult else ""}Siblings.
- Format: | **Field** | Value |
- Bold Field. Normal Value. No paragraphs.
- Free text fields go to section 7.

{"" if is_adult else """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. DEVELOPMENTAL HISTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Present as a clean two-column table.
- Split into sub-tables: Pregnancy & Birth | Feeding & Growth | Language & Cognition.
- Do NOT add any header row to developmental history tables.
- Tables start directly with data rows (no Field|Value, no Milestone|Finding header).
- Include only provided milestones. Skip not reported ones."""}

{"4. MEDICAL HISTORY" if is_adult else "5. MEDICAL HISTORY"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This section MUST contain FOUR mandatory sub-sections, each as a separate sub-table with its own title.
Write each finding as a separate line — do NOT combine into paragraphs.
Convert Yes/No answers to natural English sentences, one per line.
Long text details go to section 7 (Original Arabic Responses).

Sub-section 1 — Sub-table title: Past History:
Include: previous psychiatric illness, previous hospitalization, and any other past history data.
{"Also include: high fever, head trauma, convulsions, post-vaccine complications, previous therapy." if not is_adult else ""}
One finding per line under the sub-table.

Sub-section 2 — Sub-table title: Family History:
Include: psychiatric illness in family, neurological illness in family{"and intellectual disability and epilepsy in family." if not is_adult else "."}
One finding per line under the sub-table.

Sub-section 3 — Sub-table title: Investigations:
Include: {"CT, MRI, EEG, IQ test (SB5), CARS score." if not is_adult else "any investigations done."}
One finding per line under the sub-table.

Sub-section 4 — Sub-table title: Operations and Surgeries:
Include: previous surgeries data.
One finding per line under the sub-table.
Skip this sub-section entirely if no surgeries were reported.

{"Sub-section 5 — Sub-table title: Drug History:" if is_adult else ""}
{"Include: whether on medication, compliance, medication details." if is_adult else ""}
{"One finding per line under the sub-table." if is_adult else ""}

{"5. BEHAVIORAL AND CLINICAL OBSERVATIONS" if is_adult else "6. BEHAVIORAL AND CLINICAL OBSERVATIONS"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write each observation on a SEPARATE LINE — do NOT combine into paragraphs.
- One statement per line.
- Convert each MCQ answer to a natural English sentence.
- Each line = one clear piece of information.
Example format:
Sleep is interrupted.
Appetite is decreased.
Punishment methods used include verbal and withdrawal of privileges.

6. ADDITIONAL INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Include siblings data and any other structured fields not covered above.
One item per line.

7. ORIGINAL ARABIC RESPONSES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Copy each item below EXACTLY as written — zero modification, zero translation.
Present each one under its heading with a clear separator:
{verbatim_block}

══════════════════════════════════════════════
DATA:
{data_block}
══════════════════════════════════════════════
History by: {history_by or 'Not reported'} | Sheet: {"Adult" if is_adult else "Child"}
"""

        with st.spinner("جاري إنشاء التقرير..."):
            try:
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3500
                )
                st.session_state["report_text"] = response.choices[0].message.content
                st.session_state["report_pname"]= patient_name
                st.session_state["report_sheet"]= "بالغ" if is_adult else "طفل"
                st.session_state["report_by"]   = history_by or "—"
            except Exception as e:
                st.error(f"خطأ: {str(e)}")

# ════════════════════════════════════════════════════════
#  عرض التقرير
# ════════════════════════════════════════════════════════
if st.session_state.get("report_text"):
    rt  = st.session_state["report_text"]
    pn  = st.session_state.get("report_pname","المريض")
    rs  = st.session_state.get("report_sheet","")
    rb_ = st.session_state.get("report_by","—")
    fn  = f"{pn.replace(' ','_')}_HistorySheet.docx"

    st.divider()
    st.markdown("### ✅ تم إنشاء التقرير")
    st.text_area("", value=rt, height=600, label_visibility="collapsed")

    def build_docx(rt, pn, rs, rb_, logo_path):
        doc = Document()
        for section in doc.sections:
            section.top_margin=Cm(2.5); section.bottom_margin=Cm(2.5)
            section.left_margin=Cm(2.5); section.right_margin=Cm(2.5)
            section.different_first_page_header_footer=True
            for hdr in [section.header, section.first_page_header]:
                for p in hdr.paragraphs: p.clear()
        # Set document default RTL
        try:
            settings = doc.settings.element
            rsid = OxmlElement('w:themeFontLang')
            rsid.set(qn('w:bidi'), 'ar-EG')
            settings.append(rsid)
        except: pass

        for section in doc.sections:
            sectPr=section._sectPr; pgB=OxmlElement('w:pgBorders')
            pgB.set(qn('w:offsetFrom'),'page')
            for side in ('top','left','bottom','right'):
                b=OxmlElement(f'w:{side}'); b.set(qn('w:val'),'single')
                b.set(qn('w:sz'),'12'); b.set(qn('w:space'),'24'); b.set(qn('w:color'),'1B2A4A')
                pgB.append(b)
            sectPr.append(pgB)
        for section in doc.sections:
            footer=section.footer
            para=footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            para.clear(); para.alignment=WD_ALIGN_PARAGRAPH.CENTER
            run=para.add_run(); run.font.size=Pt(9); run.font.color.rgb=CLINIC_BLUE
            for tag,text in [('begin',None),(None,' PAGE '),('end',None)]:
                if tag:
                    el=OxmlElement('w:fldChar'); el.set(qn('w:fldCharType'),tag); run._r.append(el)
                else:
                    instr=OxmlElement('w:instrText'); instr.text=text; run._r.append(instr)
        p_top=doc.add_paragraph()
        p_top.paragraph_format.space_before=Pt(0); p_top.paragraph_format.space_after=Pt(6)
        if os.path.exists(logo_path):
            p_top.add_run().add_picture(logo_path,width=Inches(1.2))
        r_t=p_top.add_run("   التقرير السريري للتاريخ المرضي")
        r_t.font.name="Arial"; r_t.font.size=Pt(18); r_t.font.bold=True; r_t.font.color.rgb=CLINIC_BLUE
        pPr=p_top._p.get_or_add_pPr(); pBdr=OxmlElement('w:pBdr')
        bot=OxmlElement('w:bottom'); bot.set(qn('w:val'),'single')
        bot.set(qn('w:sz'),'8'); bot.set(qn('w:space'),'4'); bot.set(qn('w:color'),'1A5CB8')
        pBdr.append(bot); pPr.append(pBdr)
        doc.add_paragraph()
        def add_rtl_para(text, bold=False, size=11, color=None, space_before=0, space_after=4, underline=False):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(space_before)
            p.paragraph_format.space_after  = Pt(space_after)
            pPr = p._p.get_or_add_pPr()
            bidi = OxmlElement("w:bidi"); pPr.append(bidi)
            jc   = OxmlElement("w:jc");   jc.set(qn("w:val"),"right"); pPr.append(jc)
            r = p.add_run(text)
            r.font.size = Pt(size); r.font.name = "Arial"; r.bold = bold
            if color: r.font.color.rgb = color
            if underline: r.font.underline = True
            return p

        def add_section_title(text):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after  = Pt(4)
            p.paragraph_format.keep_with_next = True  # stay with first content below
            r = p.add_run(text.strip('# '))
            r.font.size = Pt(13); r.font.name = "Arial"
            r.font.bold = True; r.font.color.rgb = CLINIC_BLUE
            pPr = p._p.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            bot  = OxmlElement('w:bottom')
            bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'6')
            bot.set(qn('w:space'),'2');    bot.set(qn('w:color'),'1A5CB8')
            pBdr.append(bot); pPr.append(pBdr)

        def add_subtable_title(text):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after  = Pt(3)
            p.paragraph_format.keep_with_next = True  # stay with table below
            r = p.add_run(text.rstrip(':'))
            r.font.size = Pt(11); r.font.name = "Arial"
            r.font.bold = True; r.font.color.rgb = RGBColor(0x1B,0x2A,0x4A)

        def add_table_row(table, field, value, is_header_row=False):
            row = table.add_row()
            # Prevent row from splitting across pages
            trPr = row._tr.get_or_add_trPr()
            cantSplit = OxmlElement('w:cantSplit')
            cantSplit.set(qn('w:val'), '1')
            trPr.append(cantSplit)
            # Field cell
            fc = row.cells[0]; fc.text = ""
            fp = fc.paragraphs[0]
            fr = fp.add_run(field); fr.font.size=Pt(10); fr.font.name="Arial"; fr.font.bold=True
            tc1 = fc._tc; tcPr1 = tc1.get_or_add_tcPr()
            shd1 = OxmlElement('w:shd')
            shd1.set(qn('w:val'),'clear'); shd1.set(qn('w:color'),'auto')
            # Header row: deep blue bg + white text; Data row: light blue bg
            if is_header_row:
                shd1.set(qn('w:fill'),'1A5CB8')
                fr.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
            else:
                shd1.set(qn('w:fill'),'E8F0FE')
            tcPr1.append(shd1)
            margins1 = OxmlElement('w:tcMar')
            for side in ['top','bottom','left','right']:
                m = OxmlElement(f'w:{side}'); m.set(qn('w:w'),'80'); m.set(qn('w:type'),'dxa')
                margins1.append(m)
            tcPr1.append(margins1)
            # Value cell — supports multi-line values (\n separated)
            vc = row.cells[1]; vc.text = ""
            tc2 = vc._tc; tcPr2 = tc2.get_or_add_tcPr()
            if is_header_row:
                shd2 = OxmlElement('w:shd')
                shd2.set(qn('w:val'),'clear'); shd2.set(qn('w:color'),'auto')
                shd2.set(qn('w:fill'),'2E6FD4')
                tcPr2.append(shd2)
            margins2 = OxmlElement('w:tcMar')
            for side in ['top','bottom','left','right']:
                m = OxmlElement(f'w:{side}'); m.set(qn('w:w'),'80'); m.set(qn('w:type'),'dxa')
                margins2.append(m)
            tcPr2.append(margins2)
            # Split on newlines to support multi-line cell content (e.g. symptoms list)
            value_lines = value.split('\n') if '\n' in value else [value]
            for idx_vl, vline in enumerate(value_lines):
                if idx_vl == 0:
                    vp = vc.paragraphs[0]
                else:
                    vp = vc.add_paragraph()
                vr = vp.add_run(vline.strip())
                vr.font.size=Pt(10); vr.font.name="Arial"; vr.font.bold=False
                if is_header_row:
                    vr.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
                    vr.font.bold = True

        def make_table():
            t = doc.add_table(rows=0, cols=2)
            t.style = 'Table Grid'
            try:
                tblPr = t._tbl.tblPr
                tblW  = OxmlElement('w:tblW')
                tblW.set(qn('w:w'),'9026'); tblW.set(qn('w:type'),'dxa')
                tblPr.append(tblW)
                cols_el = OxmlElement('w:tblGrid')
                for w in [3000, 6026]:
                    gc = OxmlElement('w:gridCol'); gc.set(qn('w:w'), str(w))
                    cols_el.append(gc)
                t._tbl.insert(0, cols_el)
                # Keep table together on one page if it fits
                tblLook = OxmlElement('w:tblLook')
                tblLook.set(qn('w:val'), '04A0')
                tblPr.append(tblLook)
            except: pass
            return t

        # ── Parse and render the report ──
        in_table = False
        current_table = None
        in_dev_history = False
        in_symptoms_box = False
        lines = rt.split('\n')
        i = 0
        while i < len(lines):
            ls = lines[i].strip()
            i += 1
            if not ls:
                if in_table: in_table = False; current_table = None
                in_symptoms_box = False
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
                continue

            # Section title: starts with digit + dot + space + CAPS (e.g. "1. PATIENT INFORMATION")
            import re
            if (re.match(r'^\d+\.\s+[A-Z\s]+$', ls) or
                re.match(r'^\d+\.\s+[A-Z][A-Z\s&]+$', ls) or
                ls in ('CLINICAL SUMMARY', 'REPORT HEADER')):
                in_table = False; current_table = None
                in_dev_history = 'DEVELOPMENTAL' in ls.upper()
                in_symptoms_box = False
                add_section_title(ls)
                continue

            # Sub-table title: Title Case line ending with colon, no pipe
            if ls.endswith(':') and '|' not in ls and len(ls) < 60 and ls[0].isupper():
                in_table = False; current_table = None
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
                add_subtable_title(ls)
                # Symptoms section: no table — just collect lines as styled text box
                if ls.lower().startswith('symptom'):
                    in_symptoms_box = True
                    in_table = False; current_table = None
                else:
                    in_symptoms_box = False
                    current_table = make_table()
                    if not in_dev_history:
                        add_table_row(current_table, "Field", "Value", is_header_row=True)
                    in_table = True
                continue

            # Table row: contains pipe separator
            if '|' in ls:
                parts = [p.strip() for p in ls.split('|') if p.strip()]
                # Skip markdown separator rows
                if all(set(p) <= set('-: ') for p in parts): continue

                # Always skip Field|Value and Milestone|Finding header rows —
                # headers are added programmatically, not from AI output
                skip_keywords = [
                    ("field","value"), ("milestone","finding"),
                    ("item","detail"), ("category","information")
                ]
                if len(parts) >= 2 and (parts[0].strip('* ').lower(), parts[1].strip('* ').lower()) in skip_keywords:
                    continue  # skip — never render these from AI output

                is_new_table = not in_table or current_table is None
                if is_new_table:
                    in_table = True
                    current_table = make_table()
                    # Add header row only for non-developmental tables
                    if not in_dev_history:
                        add_table_row(current_table, "Field", "Value", is_header_row=True)

                # Handle multi-line symptoms in one cell
                if len(parts) >= 2:
                    field = parts[0].strip('* ')
                    value = ' | '.join(parts[1:])  # rejoin if value contained pipes
                    add_table_row(current_table, field, value)
                elif len(parts) == 1:
                    add_table_row(current_table, parts[0].strip('* '), '')
                continue

            # Separator lines
            if ls.startswith('━') or ls.startswith('══') or ls.startswith('---'):
                in_table = False; current_table = None
                p = doc.add_paragraph(); p.paragraph_format.space_before=Pt(4)
                pPr2=p._p.get_or_add_pPr(); pBdr2=OxmlElement('w:pBdr')
                b2=OxmlElement('w:bottom'); b2.set(qn('w:val'),'single')
                b2.set(qn('w:sz'),'4'); b2.set(qn('w:space'),'1'); b2.set(qn('w:color'),'CCCCCC')
                pBdr2.append(b2); pPr2.append(pBdr2)
                continue

            # Arabic verbatim heading (ends with colon, contains Arabic)
            if ls.endswith(':') and any('\u0600' <= c <= '\u06ff' for c in ls):
                in_table = False; current_table = None
                add_rtl_para(ls.rstrip(':'), bold=True, size=11,
                             color=RGBColor(0x1B,0x2A,0x4A), space_before=10)
                continue

            # Normal line — check if symptoms box, Arabic (RTL) or English (LTR)
            if in_symptoms_box:
                # Render each symptom as an indented line inside a light box feel
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after  = Pt(3)
                p.paragraph_format.left_indent  = Inches(0.2)
                r = p.add_run(f"• {ls.lstrip('•- ').strip()}")
                r.font.size=Pt(11); r.font.name="Arial"
                continue
            in_table = False; current_table = None
            is_arabic = any('\u0600' <= c <= '\u06ff' for c in ls)
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after  = Pt(4)
            if is_arabic:
                pPr = p._p.get_or_add_pPr()
                bidi = OxmlElement("w:bidi"); pPr.append(bidi)
                jc   = OxmlElement("w:jc"); jc.set(qn("w:val"),"right"); pPr.append(jc)
            r = p.add_run(ls); r.font.size=Pt(11); r.font.name="Arial"
        # Footer removed per request
        buf=io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

    col1,col2,col3=st.columns(3)
    with col1:
        docx_buf=build_docx(rt,pn,rs,rb_,LOGO_PATH)
        st.download_button("📄 تحميل Word",data=docx_buf,file_name=fn,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with col2:
        if st.button("📧 إرسال بالبريد"):
            try:
                docx_buf2=build_docx(rt,pn,rs,rb_,LOGO_PATH)
                msg=MIMEMultipart(); msg['From']=GMAIL_USER; msg['To']=RECIPIENT_EMAIL
                msg['Subject']=f"تقرير التاريخ المرضي — {pn}"
                msg.attach(MIMEText(f"التقرير المرفق خاص بـ: {pn}\nالنوع: {rs}\nالأخصائي: {rb_}",'plain'))
                part=MIMEBase('application','octet-stream'); part.set_payload(docx_buf2.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',f'attachment; filename="{fn}"')
                msg.attach(part)
                with smtplib.SMTP_SSL('smtp.gmail.com',465) as server:
                    server.login(GMAIL_USER,GMAIL_PASS)
                    server.sendmail(GMAIL_USER,RECIPIENT_EMAIL,msg.as_string())
                st.success(f"✅ تم الإرسال إلى {RECIPIENT_EMAIL}")
            except Exception as e:
                st.error(f"خطأ في الإرسال: {str(e)}")
    with col3:
        if st.button("↺ مريض جديد"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
