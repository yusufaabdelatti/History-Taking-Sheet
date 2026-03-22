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
CONS_AR      = [NA,"لا توجد قرابة","درجة أولى","درجة ثانية","درجة ثالثة"]
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
        d["age"]        = ti("السن","Age","a_age")
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
        d["father_occ"]   = sel("وظيفة الأب","Father Occupation", OCC_AR, "a_fo")
        d["father_alive"] = rb("حالة الأب","Father status", ALIVE_M, "a_falive")
    with c2:
        st.markdown("**الأم / Mother**")
        d["mother_name"]  = ti("اسم الأم","Mother Name","a_mn")
        d["mother_age"]   = ti("سن الأم","Mother Age","a_ma")
        d["mother_occ"]   = sel("وظيفة الأم","Mother Occupation", OCC_AR, "a_mo")
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
    c1,c2 = st.columns(2)
    with c1: d["fam_psych"]  = rb("مرض نفسي في الأسرة؟","Psychiatric in family?", نعم_لا_لاينطبق, "a_fpsych")
    with c2: d["fam_neuro"]  = rb("مرض عصبي في الأسرة؟","Neurological in family?", نعم_لا_لاينطبق, "a_fneuro")
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
        d["age"]         = ti("السن","Age","c_age")
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
        d["pregnancy"]    = sel("تفاصيل الحمل","Pregnancy", PREG_AR, "c_preg")
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
        d["father_occ"]       = sel("وظيفة الأب","Father Occupation", OCC_AR, "c_fo")
        d["father_alive"]     = rb("حالة الأب","Father status", ALIVE_M, "c_falive")
        d["father_hereditary"]= ti("مرض وراثي عند الأب (إن وجد)","Father hereditary","c_fh")
    with c2:
        st.markdown("**الأم / Mother**")
        d["mother_name"]      = ti("اسم الأم","Mother Name","c_mn")
        d["mother_age"]       = ti("سن الأم","Mother Age","c_ma")
        d["mother_occ"]       = sel("وظيفة الأم","Mother Occupation", OCC_AR, "c_mo")
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
        d["fam_neuro"]   = rb("مرض عصبي في الأسرة؟","Neurological in family?", نعم_لا_لاينطبق, "c_fneuro")
    with c2:
        d["fam_mr"]      = rb("إعاقة ذهنية في الأسرة؟","MR in family?", نعم_لا_لاينطبق, "c_fmr")
        d["fam_epilepsy"]= rb("صرع في الأسرة؟","Epilepsy in family?", نعم_لا_لاينطبق, "c_fepil")
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
        d["punishment"]     = sel("طرق العقاب المستخدمة","Punishment methods", PUNISHMENT, "c_punish")
        d["stress_reaction"]= sel("رد الفعل تجاه الضغوط","Reaction to stress", STRESS_AR, "c_stress")
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
المريض: {sv(d,'name')} | السن: {sv(d,'age')} | النوع: {sv(d,'gender')}
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

التاريخ العائلي: مرض نفسي: {sv(d,'fam_psych')} | مرض عصبي: {sv(d,'fam_neuro')}
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
الطفل: {sv(d,'name')} | السن: {sv(d,'age')} | النوع: {sv(d,'gender')}
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

التاريخ السابق: حرارة ≥40: {sv(d,'high_fever')} | ارتطام رأس: {sv(d,'head_trauma')} | تشنجات: {sv(d,'convulsions')}
مضاعفات بعد التطعيم: {sv(d,'post_vaccine')} | دخول مستشفى: {sv(d,'prev_hosp')} | جلسات سابقة: {sv(d,'prev_therapy')}
{sv(d,'past_hx')}

التاريخ العائلي: مرض نفسي: {sv(d,'fam_psych')} | عصبي: {sv(d,'fam_neuro')} | إعاقة ذهنية: {sv(d,'fam_mr')} | صرع: {sv(d,'fam_epilepsy')}
{sv(d,'family_hx')}

الفحوصات: CT: {sv(d,'had_ct')} | MRI: {sv(d,'had_mri')} | EEG: {sv(d,'had_eeg')} | SB5: {sv(d,'had_iq')} | CARS: {sv(d,'had_cars')} — الدرجة: {sv(d,'cars_score')}
{sv(d,'investigations')}

الجراحات: {sv(d,'had_surg')} — {sv(d,'surgeries')}

التقييم: النوم: {sv(d,'sleep')} | الشهية: {sv(d,'appetite')} | طرق العقاب: {sv(d,'punishment')} | رد الفعل: {sv(d,'stress_reaction')}
الجلسات الحالية: {sv(d,'therapy')}
ملاحظات إضافية: {sv(d,'extra_notes')}
"""

        prompt = f"""أنت طبيب نفسي استشاري أول متمرس. بناءً على بيانات التاريخ المرضي أدناه، اكتب تقريراً سريرياً متكاملاً باللغة العربية وفق الهيكل الآتي تماماً.

قواعد صارمة لا تحيد عنها:
١. اكتب التقرير كاملاً باللغة العربية فقط
٢. اكتب فقط ما هو مذكور في البيانات — إذا كان الحقل "لم يُذكر" فلا تكتب عنه شيئاً على الإطلاق ولا تذكره
٣. حوّل كل إجابة "نعم/لا" إلى جملة سردية كاملة مفصّلة (مثال: بدلاً من "التشنجات: نعم" اكتب "يُشار إلى وجود تشنجات في التاريخ المرضي السابق")
٤. النصوص المكتوبة في الشكاوى وHPI تُنقل حرفياً كما كُتبت دون تعديل
٥. لا تخترع أي معلومة غير موجودة في البيانات ولا تُضف أي جملة افتراضية
٦. اجعل التقرير سردياً تفصيلياً وليس قائمة أسئلة وإجابات
٧. لا تكتب أي قسم إذا كانت جميع بياناته "لم يُذكر"

نسّق البيانات التالية في تقرير منظم باستخدام الهيكل الآتي. ضع فقط البيانات المُدخلة تحت كل قسم. لا تضف أي شيء:

══════════════════════════════════════════════
البيانات الأساسية
══════════════════════════════════════════════
ضع البيانات الشخصية في جدول بعمودين (البيان | القيمة). البيانات المُدخلة فقط، لا شيء غيرها.

══════════════════════════════════════════════
{"بيانات الأسرة والزواج" if is_adult else "بيانات الأسرة"}
══════════════════════════════════════════════
ضع بيانات الأسرة كنقاط. حوّل إجابات الاختيار من متعدد إلى جمل قصيرة طبيعية. النصوص الحرة تُنسخ حرفياً.

{"" if not is_adult else ""}══════════════════════════════════════════════
{"" if is_adult else "مراحل النمو"}
{"" if is_adult else "══════════════════════════════════════════════"}
{"" if is_adult else "ضع مراحل النمو في جدول بعمودين (المرحلة | البيان). البيانات المُدخلة فقط."}

══════════════════════════════════════════════
الشكوى الرئيسية وتاريخ المرض الحالي
══════════════════════════════════════════════
انسخ نص الشكاوى وHPI حرفياً كما كُتب. أضف بيانات البداية والمسار كنقاط.

══════════════════════════════════════════════
التاريخ المرضي
══════════════════════════════════════════════
ضع كل قسم فرعي تحت عنوانه الفرعي. حوّل إجابات الاختيار من متعدد إلى جمل قصيرة. النصوص الحرة تُنسخ حرفياً.

══════════════════════════════════════════════
التقييم السريري
══════════════════════════════════════════════
ضع بيانات التقييم كنقاط. حوّل إجابات الاختيار إلى جمل قصيرة. النصوص الحرة تُنسخ حرفياً.



══════════════════════════════════════════════
بيانات التاريخ المرضي:
{data_block}
══════════════════════════════════════════════
الأخصائي: {history_by or 'لم يُذكر'} | نوع الاستمارة: {"بالغ" if is_adult else "طفل"}
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

    def build_docx(rt, pn, rs, rb_, logo_path, doctor):
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

        # ── Info box: patient separate from psychologist ──
        def info_line(label, val):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            pPr_il = p._p.get_or_add_pPr()
            jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "right"); pPr_il.append(jc)
            r1 = p.add_run(val + "  "); r1.font.size=Pt(11); r1.font.name="Arial"
            r2 = p.add_run(label); r2.bold=True; r2.font.size=Pt(11); r2.font.name="Arial"; r2.font.color.rgb=CLINIC_BLUE
            return p

        info_line("المريض:", pn)
        info_line("نوع الاستمارة:", rs)
        info_line("اسم الأخصائي:", rb_)
        doc.add_paragraph()
        in_table=False; table=None
        for line in rt.split('\n'):
            ls=line.strip()
            if not ls:
                if not in_table: doc.add_paragraph()
                continue
            if ls.startswith('|') and ls.endswith('|'):
                cells=[c.strip() for c in ls.strip('|').split('|')]
                if all(set(c)<=set('-: ') for c in cells): continue
                is_header_row = not in_table
                if not in_table:
                    in_table=True
                    table=doc.add_table(rows=0,cols=len(cells))
                    table.style='Table Grid'
                    # set column widths evenly
                    from docx.shared import Inches as _In
                    try:
                        tbl_w = 9026  # A4 content width in DXA
                        col_w = tbl_w // max(len(cells),1)
                        from docx.oxml import OxmlElement as OE2
                        tblPr = table._tbl.tblPr
                        tblW = OE2('w:tblW')
                        tblW.set(qn('w:w'), str(tbl_w))
                        tblW.set(qn('w:type'), 'dxa')
                        tblPr.append(tblW)
                    except: pass
                row=table.add_row()
                for i,ct in enumerate(cells[:len(cells)]):
                    if i >= len(row.cells): continue
                    cell=row.cells[i]
                    cell.text=""
                    para=cell.paragraphs[0]
                    # RTL cell
                    pPr_c=para._p.get_or_add_pPr()
                    jc_c=OxmlElement("w:jc"); jc_c.set(qn("w:val"),"right"); pPr_c.append(jc_c)
                    bidi_c=OxmlElement("w:bidi"); pPr_c.append(bidi_c)
                    run=para.add_run(ct)
                    run.font.size=Pt(10); run.font.name="Arial"
                    if is_header_row:
                        run.font.bold=True
                        run.font.color.rgb=RGBColor(0xFF,0xFF,0xFF)
                        # blue background for header
                        tc=cell._tc
                        tcPr=tc.get_or_add_tcPr()
                        shd=OxmlElement('w:shd')
                        shd.set(qn('w:val'),'clear')
                        shd.set(qn('w:color'),'auto')
                        shd.set(qn('w:fill'),'1A5CB8')
                        tcPr.append(shd)
                    else:
                        # alternating light blue for even rows
                        pass
                continue
            else: in_table=False; table=None
            if ls.startswith('══'):
                p=doc.add_paragraph(); pPr2=p._p.get_or_add_pPr(); pBdr2=OxmlElement('w:pBdr')
                b2=OxmlElement('w:bottom'); b2.set(qn('w:val'),'single')
                b2.set(qn('w:sz'),'6'); b2.set(qn('w:space'),'1'); b2.set(qn('w:color'),'1A5CB8')
                pBdr2.append(b2); pPr2.append(pBdr2); continue
            if 'القسم' in ls or 'ملخص سريع' in ls:
                p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(14)
                r=p.add_run(ls.strip('#* ')); r.bold=True; r.font.size=Pt(13)
                r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                pPr3=p._p.get_or_add_pPr()
                bidi3=OxmlElement("w:bidi"); pPr3.append(bidi3)
                jc3=OxmlElement("w:jc"); jc3.set(qn("w:val"),"right"); pPr3.append(jc3)
                pBdr3=OxmlElement('w:pBdr')
                b3=OxmlElement('w:bottom'); b3.set(qn('w:val'),'single')
                b3.set(qn('w:sz'),'4'); b3.set(qn('w:space'),'1'); b3.set(qn('w:color'),'1A5CB8')
                pBdr3.append(b3); pPr3.append(pBdr3); continue
            if ls.startswith('**') and ls.endswith('**'):
                p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(8)
                pPr_bld=p._p.get_or_add_pPr()
                bidi_bld=OxmlElement("w:bidi"); pPr_bld.append(bidi_bld)
                jc_bld=OxmlElement("w:jc"); jc_bld.set(qn("w:val"),"right"); pPr_bld.append(jc_bld)
                r=p.add_run(ls.strip('*')); r.bold=True; r.font.size=Pt(11); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                continue
            if ls.startswith('• ') or ls.startswith('- '):
                p=doc.add_paragraph(style='List Bullet')
                pPr_bl=p._p.get_or_add_pPr()
                bidi_bl=OxmlElement("w:bidi"); pPr_bl.append(bidi_bl)
                jc_bl=OxmlElement("w:jc"); jc_bl.set(qn("w:val"),"right"); pPr_bl.append(jc_bl)
                r=p.add_run(ls.lstrip('•- ').strip()); r.font.size=Pt(11); r.font.name="Arial"
                continue
            p=doc.add_paragraph()
            pPr_rt=p._p.get_or_add_pPr()
            bidi=OxmlElement("w:bidi"); pPr_rt.append(bidi)
            jc_rt=OxmlElement("w:jc"); jc_rt.set(qn("w:val"),"right"); pPr_rt.append(jc_rt)
            r=p.add_run(ls); r.font.size=Pt(11); r.font.name="Arial"
        doc.add_paragraph(); doc.add_paragraph()
        p_sep=doc.add_paragraph(); pPr_s=p_sep._p.get_or_add_pPr(); pBdr_s=OxmlElement('w:pBdr')
        top_s=OxmlElement('w:top'); top_s.set(qn('w:val'),'single')
        top_s.set(qn('w:sz'),'6'); top_s.set(qn('w:space'),'1'); top_s.set(qn('w:color'),'1A5CB8')
        pBdr_s.append(top_s); pPr_s.append(pBdr_s)
        p_dr=doc.add_paragraph()
        r_dr=p_dr.add_run(doctor["name"]); r_dr.bold=True; r_dr.font.size=Pt(12)
        r_dr.font.name="Arial"; r_dr.font.color.rgb=CLINIC_BLUE
        for t in ["title1","title2","title3","title4"]:
            p_t=doc.add_paragraph(); r_t2=p_t.add_run(doctor[t])
            r_t2.font.size=Pt(10); r_t2.font.name="Arial"; r_t2.font.color.rgb=RGBColor(0x44,0x44,0x44)
            p_t.paragraph_format.space_before=Pt(0); p_t.paragraph_format.space_after=Pt(0)
        doc.add_paragraph()
        doc.add_paragraph().add_run(f"📍  {doctor['address']}").font.size=Pt(10)
        r_ph=doc.add_paragraph().add_run(f"📞  {doctor['phone']}")
        r_ph.font.size=Pt(10); r_ph.bold=True
        buf=io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

    col1,col2,col3=st.columns(3)
    with col1:
        docx_buf=build_docx(rt,pn,rs,rb_,LOGO_PATH,DOCTOR)
        st.download_button("📄 تحميل Word",data=docx_buf,file_name=fn,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with col2:
        if st.button("📧 إرسال بالبريد"):
            try:
                docx_buf2=build_docx(rt,pn,rs,rb_,LOGO_PATH,DOCTOR)
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
