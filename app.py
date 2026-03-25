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
    history_by = st.text_input("اسم الأخصائي / Psychologist Name")

# Using the Groq API key from Streamlit secrets
groq_key = st.secrets["GROQ_API_KEY"]

st.markdown('<div class="main-title">🧠 استمارة أخذ التاريخ المرضي</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">عيادة د. هاني الحناوي — طب وجراحة الأعصاب والنفس</div>', unsafe_allow_html=True)

# ── مساعدات (Helpers) ──
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
    # Changed from selectbox to horizontal radio (dots) for a simpler UI!
    return st.radio("", opts, key=key, horizontal=True, label_visibility="collapsed")

def ms(ar, en, opts, key):
    lbl(ar, en)
    return st.multiselect("", opts, key=key, label_visibility="collapsed")

def sv(d, key, default="لم يُذكر"):
    v = d.get(key, "")
    if not v: return default
    if isinstance(v, list): return "، ".join(v) if v else default
    v = str(v).strip()
    return v if v and v not in ["—", "— اختر —", "لم يُذكر"] else default

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
    d["on_meds"]    = rb("هل يتناول أدوية حالياً؟","On medication?", نعم_لا_لاينطبق, "a_onmeds")
    d["compliance"] = sel("الالتزام بالأدوية","Compliance", COMPLIANCE, "a_comp")
    d["drug_hx"]    = ta("تفاصيل الأدوية (الاسم، الجرعة، المدة)","Medications", "a_drug", 100)

    sec("التاريخ المرضي السابق", "Past History")
    c1,c2 = st.columns(2)
    with c1: d["prev_psych"] = rb("مرض نفسي سابق؟","Previous psychiatric?", نعم_لا_لاينطبق, "a_ppsych")
    with c2: d["prev_hosp"]  = rb("دخول مستشفى سابق؟","Previous hospitalization?", نعم_لا_لاينطبق, "a_phosp")
    d["past_hx"] = ta("تفاصيل التاريخ السابق","Details","a_past",80)

    sec("التاريخ العائلي", "Family History")
    c1, c2 = st.columns(2)
    with c1:
        d["fam_psych"]  = rb("مرض نفسي في الأسرة؟","Psychiatric in family?", نعم_لا_لاينطبق, "a_fpsych")
        if st.session_state.get("a_fpsych") == "نعم":
            d["fam_psych_details"] = ti("ما هو المرض النفسي؟ (من في الأسرة)","Specify psychiatric illness","a_fpsych_det")
        else:
            d["fam_psych_details"] = ""
    with c2:
        d["fam_neuro"]  = rb("مرض عصبي في الأسرة؟","Neurological in family?", نعم_لا_لاينطبق, "a_fneuro")
        if st.session_state.get("a_fneuro") == "نعم":
            d["fam_neuro_details"] = ti("ما هو المرض العصبي؟ (من في الأسرة)","Specify neurological illness","a_fneuro_det")
        else:
            d["fam_neuro_details"] = ""
    d["family_hx"] = ta("تفاصيل التاريخ العائلي","Details","a_famhx",80)

    sec("الفحوصات", "Investigations")
    d["had_inv"]       = rb("هل أُجريت فحوصات؟","Investigations done?", نعم_لا_لاينطبق, "a_hadinv")
    d["investigations"]= ta("تفاصيل الفحوصات ونتائجها","Details","a_inv",80)

    sec("العمليات والجراحات", "Operations and Surgeries")
    d["had_surg"]  = rb("عمليات جراحية سابقة؟","Previous surgeries?", نعم_لا_لاينطبق, "a_hsurg")
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
    c1, c2, c3 = st.columns(3)
    with c1:
        d["high_fever"]   = rb("حرارة ≥40 درجة؟","High fever?", نعم_لا_لاينطبق, "c_hfever")
        d["head_trauma"]  = rb("ارتطام رأس؟","Head trauma?", نعم_لا_لاينطبق, "c_htrauma")
        if st.session_state.get("c_htrauma") == "نعم":
            d["head_trauma_location"] = ti("مكان الارتطام في الرأس","Location on head","c_htrauma_loc")
            d["head_trauma_details"]  = ti("كيف حدث الارتطام؟","How did it happen?","c_htrauma_det")
        else:
            d["head_trauma_location"] = ""
            d["head_trauma_details"]  = ""
    with c2:
        d["convulsions"]  = rb("تشنجات؟","Convulsions?", نعم_لا_لاينطبق, "c_conv")
        d["post_vaccine"] = rb("مضاعفات بعد التطعيم؟","Post-vaccine comp.?", نعم_لا_لاينطبق, "c_pvacc")
    with c3:
        d["prev_hosp"]    = rb("دخول مستشفى سابق؟","Previous hospitalization?", نعم_لا_لاينطبق, "c_phosp")
        d["prev_therapy"] = rb("جلسات علاجية سابقة؟","Previous therapy?", نعم_لا_لاينطبق, "c_pther")
    d["past_hx"] = ta("تفاصيل التاريخ السابق","Details","c_past",100)

    sec("التاريخ العائلي", "Family History")
    c1, c2 = st.columns(2)
    with c1:
        d["fam_psych"]   = rb("مرض نفسي في الأسرة؟","Psychiatric in family?", نعم_لا_لاينطبق, "c_fpsych")
        if st.session_state.get("c_fpsych") == "نعم":
            d["fam_psych_details"] = ti("ما هو المرض النفسي؟ (من في الأسرة)","Specify psychiatric illness","c_fpsych_det")
        else:
            d["fam_psych_details"] = ""
        d["fam_neuro"]   = rb("مرض عصبي في الأسرة؟","Neurological in family?", نعم_لا_لاينطبق, "c_fneuro")
        if st.session_state.get("c_fneuro") == "نعم":
            d["fam_neuro_details"] = ti("ما هو المرض العصبي؟ (من في الأسرة)","Specify neurological illness","c_fneuro_det")
        else:
            d["fam_neuro_details"] = ""
    with c2:
        d["fam_mr"]      = rb("إعاقة ذهنية في الأسرة؟","MR in family?", نعم_لا_لاينطبق, "c_fmr")
        if st.session_state.get("c_fmr") == "نعم":
            d["fam_mr_details"] = ti("من في الأسرة؟ وما درجة الإعاقة؟","Specify MR details","c_fmr_det")
        else:
            d["fam_mr_details"] = ""
        d["fam_epilepsy"]= rb("صرع في الأسرة؟","Epilepsy in family?", نعم_لا_لاينطبق, "c_fepil")
        if st.session_state.get("c_fepil") == "نعم":
            d["fam_epilepsy_details"] = ti("من في الأسرة؟ وهل يتعالج؟","Specify epilepsy details","c_fepil_det")
        else:
            d["fam_epilepsy_details"] = ""
    d["family_hx"] = ta("تفاصيل التاريخ العائلي","Details","c_famhx",80)

    sec("الفحوصات", "Investigations")
    c1, c2, c3 = st.columns(3)
    with c1:
        d["had_ct"]   = rb("أشعة مقطعية؟","CT?", نعم_لا_لاينطبق, "c_ct")
        d["had_mri"]  = rb("رنين مغناطيسي؟","MRI?", نعم_لا_لاينطبق, "c_mri")
    with c2:
        d["had_eeg"]  = rb("رسم مخ (EEG)؟","EEG?", نعم_لا_لاينطبق, "c_eeg")
        d["had_iq"]   = rb("اختبار ذكاء SB5؟","IQ test?", نعم_لا_لاينطبق, "c_iq")
    with c3:
        d["had_cars"] = rb("مقياس CARS؟","CARS?", نعم_لا_لاينطبق, "c_cars")
        d["cars_score"]= ti("درجة CARS (إن أُجري)","CARS score","c_carsscore")
    d["investigations"]= ta("تفاصيل الفحوصات ونتائجها","Details","c_inv",80)

    sec("العمليات والجراحات", "Operations and Surgeries")
    d["had_surg"]  = rb("عمليات جراحية سابقة؟","Previous surgeries?", نعم_لا_لاينطبق, "c_hsurg")
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
#  زر توليد التقرير ونداء الـ API
# ════════════════════════════════════════════════════════
st.divider()

if st.button("✦ توليد التقرير / Generate Report", type="primary", use_container_width=True):
    with st.spinner("⏳ جاري تحليل التاريخ المرضي وإعداد التقرير السريري... / Generating clinical report..."):
        
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

        # 1. Build the Verbatim Block securely in Python (No AI hallucination here!)
        verbatim_block = "\n\n---\n### 📝 الاستجابات الأصلية (Original Arabic Responses)\n\n"
        
        def add_verbatim(title, text):
            if text and text not in ["—", "— اختر —", "لم يُذكر"]:
                return f"**{title}:**\n> {text}\n\n"
            return ""

        verbatim_block += add_verbatim("الشكوى الرئيسية (C/O)", sv(d, 'complaints'))
        verbatim_block += add_verbatim("تاريخ المرض الحالي (HPI)", sv(d, 'hpi'))
        if not is_adult:
            verbatim_block += add_verbatim("تفاصيل الحمل والولادة", sv(d, 'pregnancy'))
            verbatim_block += add_verbatim("ملاحظات النمو", sv(d, 'dev_notes'))
        verbatim_block += add_verbatim("تفاصيل الفحوصات", sv(d, 'investigations'))
        verbatim_block += add_verbatim("ملاحظات إضافية", sv(d, 'extra_notes'))

        # 2. System Prompt for Premium Clinical Formatting
        system_prompt = """
        You are an expert Chief Medical Officer. Your job is to convert the provided patient data into a premium, highly structured clinical psychiatric/neurological report in English.

        Follow this strict format:
        1. Use clean Markdown headings (e.g., ### Patient Demographics).
        2. Use bullet points for lists.
        3. Bold critical keys (e.g., **Age:** 34).
        4. Highlight "Red Flags" (like suicidal thoughts, poor insight, severe substance use, or severe family history) in a dedicated **⚠️ Clinical Alerts** section at the top.
        5. If a field says "لم يُذكر" or is empty, exclude it entirely to keep the report clean.
        6. Keep the tone strictly professional, objective, and easy for a doctor to scan in 10 seconds.
        7. DO NOT include the original Arabic text. (It will be appended manually outside of your response).
        """

        # 3. Call the Groq API
        try:
            client = Groq(api_key=groq_key)
            completion = client.chat.completions.create(
                model="llama3-70b-8192", # You can change this to your preferred Groq model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data_block}
                ],
                temperature=0.2,
                max_tokens=2500,
                top_p=1,
                stream=False,
            )
            
            english_report = completion.choices[0].message.content
            
            # 4. Combine the AI English report with the Python-generated Arabic verbatim block
            final_report = english_report + verbatim_block
            
            # Display it on screen
            st.success("✅ تم إعداد التقرير بنجاح! / Report Generated Successfully!")
            with st.expander("📄 عرض التقرير النهائي / View Final Report", expanded=True):
                st.markdown(final_report)
                
            # --- Document Creation ---
            doc = Document()
            doc.add_heading(f'Clinical Assessment Report - {patient_name}', 0)
            doc.add_paragraph(final_report) # Basic text insert. You can refine formatting here if needed.
            
            # Save doc to a bytes buffer so user can download it
            bio = io.BytesIO()
            doc.save(bio)
            
            st.download_button(
                label="📥 تحميل كملف وورد / Download Word Document",
                data=bio.getvalue(),
                file_name=f"Clinical_Report_{patient_name.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )

        except Exception as e:
            st.error(f"حدث خطأ أثناء توليد التقرير: {e}")
