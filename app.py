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

st.set_page_config(page_title="History Taking — Dr. Hany Elhennawy", page_icon="🧠", layout="wide")
st.markdown("""
<style>
    .main-title{font-size:26px;font-weight:700;color:#1A5CB8;margin-bottom:2px}
    .sub-title{color:#888;font-size:13px;margin-bottom:20px}
    .sec-header{font-size:15px;font-weight:700;color:#1A5CB8;margin-top:22px;margin-bottom:8px;
                border-bottom:2px solid #1A5CB8;padding-bottom:4px}
    .field-label{font-size:13px;color:#333;margin-bottom:2px}
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
    st.header("⚙️ Settings")
    groq_key   = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.caption("Get free key at [console.groq.com](https://console.groq.com)")
    st.divider()
    history_by = st.text_input("Psychologist Name / اسم الأخصائي")

st.markdown('<div class="main-title">🧠 History Taking Sheet</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Dr. Hany Elhennawy Clinic — Neuro-Psychiatry & Neurofeedback</div>', unsafe_allow_html=True)

# ── HELPERS ──
def sec(en, ar=""):
    st.markdown(f'<div class="sec-header">{en}{" / "+ar if ar else ""}</div>', unsafe_allow_html=True)

def lbl(en, ar):
    st.markdown(f'<div class="field-label"><b>{en}</b> / {ar}</div>', unsafe_allow_html=True)

def ti(label_en, label_ar, key, placeholder=""):
    lbl(label_en, label_ar)
    return st.text_input("", key=key, placeholder=placeholder, label_visibility="collapsed")

def ta(label_en, label_ar, key, height=100):
    lbl(label_en, label_ar)
    return st.text_area("", key=key, height=height, label_visibility="collapsed")

def rb(label_en, label_ar, opts, key):
    lbl(label_en, label_ar)
    return st.radio("", opts, key=key, horizontal=True, label_visibility="collapsed")

def sel(label_en, label_ar, opts, key):
    lbl(label_en, label_ar)
    return st.selectbox("", opts, key=key, label_visibility="collapsed")

def sv(d, key, default="—"):
    v = d.get(key, "")
    if not v: return default
    v = str(v).strip()
    return v if v and v not in ["—", "— اختر / Select —"] else default

# ── MCQ OPTIONS ──
NA           = "— اختر / Select —"
YNA          = ["Yes / نعم", "No / لا", "N/A"]
YN           = ["Yes / نعم", "No / لا"]
GENDER_OPTS  = ["Male / ذكر", "Female / أنثى"]
EDU_OPTS     = [NA,"Illiterate / أمي","Primary / ابتدائي","Preparatory / إعدادي",
                "Secondary / ثانوي","University / جامعي","Postgraduate / دراسات عليا"]
OCC_OPTS     = [NA,"Employed / موظف","Self-employed / أعمال حرة","Student / طالب",
                "Housewife / ربة منزل","Retired / متقاعد","Unemployed / عاطل","Other / أخرى"]
SOCIAL_OPTS  = [NA,"Single / أعزب","Married / متزوج","Divorced / مطلق","Widowed / أرمل","Separated / منفصل"]
SMOKING_OPTS = ["Non-smoker / لا يدخن","Smoker / مدخن","Ex-smoker / توقف","Shisha / شيشة"]
REFERRAL_OPTS= [NA,"Self / ذاتي","Family / الأسرة","Doctor / طبيب","Psychologist / أخصائي","School / مدرسة","Other / أخرى"]
ALIVE_OPTS_M = ["Alive / حي","Deceased / متوفى","Unknown / غير معروف"]
ALIVE_OPTS_F = ["Alive / حية","Deceased / متوفاة","Unknown / غير معروف"]
CONS_OPTS    = [NA,"No / لا","First degree / الدرجة الأولى","Second degree / الدرجة الثانية","Third degree / الدرجة الثالثة"]
PARENTS_REL  = [NA,"Good / جيدة","Average / متوسطة","Poor / سيئة","Separated / منفصلان","Divorced / مطلقان","One deceased / أحدهما متوفى"]
MARQ_OPTS    = [NA,"Good / جيدة","Average / متوسطة","Poor / سيئة","Separated / منفصلان"]
PRE_MAR      = [NA,"No prior relation / لا علاقة سابقة","Knew each other / تعارف فقط","Long relationship / علاقة طويلة","Arranged / مرتب"]
ONSET_MODE   = [NA,"Sudden / مفاجئ","Gradual / تدريجي"]
COURSE_OPTS  = [NA,"Continuous / مستمر","Episodic / نوبات","Improving / في تحسن","Worsening / في تدهور"]
COMPLIANCE   = [NA,"Good / جيد","Poor / سيء","Irregular / غير منتظم","Refused / رافض"]
INSIGHT_OPTS = [NA,"Full / كامل","Partial / جزئي","None / لا يوجد"]
SLEEP_OPTS   = ["Normal / طبيعي","Insomnia / أرق","Hypersomnia / نوم زيادة","Disrupted / متقطع"]
APPETITE_OPTS= ["Normal / طبيعي","Decreased / قلت","Increased / زادت"]
SUICIDAL_OPTS= ["None / لا","Passive / أفكار سلبية","Active / أفكار نشطة","Plan / خطة"]
SUBSTANCE_OPTS=[NA,"None / لا","Alcohol / كحول","Cannabis / حشيش","Pills / حبوب","Multiple / متعدد","Other / أخرى"]
SIB_GENDER   = [NA,"Male / ذكر","Female / أنثى"]
SIB_EDU      = [NA,"Kindergarten / روضة","Primary / ابتدائي","Preparatory / إعدادي",
                "Secondary / ثانوي","University / جامعي","Graduate / خريج","Not in school / لا يدرس"]
BIRTH_ORDER  = [NA,"1st / الأول","2nd / الثاني","3rd / الثالث","4th / الرابع","5th / الخامس","6th+ / السادس فأكثر","Only child / وحيد"]
BIRTH_TYPE   = [NA,"Normal / طبيعي","C-Section / قيصري","Forceps / جفت","Vacuum / شفاط"]
BIRTH_COMP   = [NA,"None / لا يوجد","Jaundice / صفراء","Incubator / حضانة","Asphyxia / اختناق","Low birth weight / وزن منخفض","Other / أخرى"]
BF_OPTS      = [NA,"Breastfed / طبيعية","Formula / صناعية","Mixed / مختلطة"]
MOTOR_OPTS   = [NA,"Normal / طبيعي","Delayed / متأخر","Early / مبكر"]
SPEECH_OPTS  = [NA,"Normal / طبيعي","Delayed / متأخر","Absent / غائب","Regressed / تراجع"]
VACC_OPTS    = [NA,"Complete / مكتمل","Incomplete / غير مكتمل","Unknown / غير معروف"]
ACADEMIC_OPTS= ["Excellent / ممتاز","Good / جيد","Average / متوسط","Weak / ضعيف","Not in school / لا يدرس"]
WANTED_OPTS  = ["Yes / نعم","No / لا","Unplanned / غير مخطط"]
GENDER_DES   = ["Yes / نعم","No / لا","Didn't matter / لا فرق"]
PUNISHMENT   = [NA,"Verbal / لفظي","Withdrawal of privileges / حرمان","Physical / جسدي","Ignoring / تجاهل","Mixed / مختلط"]
STRESS_REACT = [NA,"Calm / هادئ","Crying / بكاء","Aggression / عدوان","Withdrawal / انسحاب","Mixed / مختلط"]

# ── SHEET TYPE ──
sheet_type = st.radio("**Sheet Type / نوع الاستمارة**", ["👤 Adult / بالغ", "👶 Child / طفل"], horizontal=True)
is_adult = "Adult" in sheet_type
st.divider()
d = {}

# ════════════════════════════════════════════════════════
#  ADULT SHEET
# ════════════════════════════════════════════════════════
if is_adult:
    sec("Personal Details", "البيانات الشخصية")
    c1, c2 = st.columns(2)
    with c1:
        d["name"]       = ti("Full Name","الاسم","a_name")
        d["age"]        = ti("Age","السن","a_age")
        d["gender"]     = rb("Gender","النوع", GENDER_OPTS, "a_gender")
        d["education"]  = sel("Education","المستوى التعليمي", EDU_OPTS, "a_edu")
        d["occupation"] = sel("Occupation","الوظيفة", OCC_OPTS, "a_occ")
        d["occ_detail"] = ti("Occupation details","تفاصيل الوظيفة","a_occd")
    with c2:
        d["social"]     = sel("Social Status","الحالة الاجتماعية", SOCIAL_OPTS, "a_social")
        d["smoking"]    = sel("Smoking","التدخين", SMOKING_OPTS, "a_smoking")
        d["referral"]   = sel("Referral Source","مصدر الإحالة", REFERRAL_OPTS, "a_referral")
        d["phone"]      = ti("Phone","رقم الهاتف","a_phone")
        d["hobbies"]    = ti("Hobbies","الهوايات","a_hobbies")
        d["date"]       = ti("Date","التاريخ","a_date", placeholder=str(date.today()))
        d["htype"]      = ti("History Type","نوع التاريخ","a_htype")

    sec("Family Details", "بيانات الأسرة")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Father / الأب**")
        d["father_name"]  = ti("Father Name","اسم الأب","a_fn")
        d["father_age"]   = ti("Father Age","سن الأب","a_fa")
        d["father_occ"]   = ti("Father Occupation","وظيفة الأب","a_fo")
        d["father_alive"] = rb("Father status","حالة الأب", ALIVE_OPTS_M, "a_falive")
    with c2:
        st.markdown("**Mother / الأم**")
        d["mother_name"]  = ti("Mother Name","اسم الأم","a_mn")
        d["mother_age"]   = ti("Mother Age","سن الأم","a_ma")
        d["mother_occ"]   = ti("Mother Occupation","وظيفة الأم","a_mo")
        d["mother_alive"] = rb("Mother status","حالة الأم", ALIVE_OPTS_F, "a_malive")
    d["consanguinity"]    = sel("Consanguinity between parents","صلة القرابة بين الأب والأم", CONS_OPTS, "a_cons")
    d["parents_together"] = rb("Parents living together?","الأبوان يعيشان معاً؟", YNA, "a_ptog")
    d["chronic"]          = ti("Chronic illness in family","مرض مزمن في الأسرة","a_chronic")

    sec("Marriage Details", "بيانات الزواج")
    c1, c2 = st.columns(2)
    with c1:
        d["spouse_name"]   = ti("Spouse Name","اسم الزوج/الزوجة","a_spn")
        d["spouse_age"]    = ti("Spouse Age","سن الزوج/الزوجة","a_spa")
        d["spouse_occ"]    = ti("Spouse Occupation","وظيفة الزوج/الزوجة","a_spo")
        d["marriage_dur"]  = ti("Marriage Duration","فترة الزواج","a_mdur")
    with c2:
        d["engagement"]    = ti("Engagement Period","فترة الخطوبة","a_eng")
        d["num_children"]  = ti("Number of Children","عدد الأبناء","a_nch")
        d["katb"]          = rb("Katb Ketab / كتب كتاب","كتب كتاب قبل الزواج", ["Yes / نعم","No / لا","N/A"], "a_katb")
        d["marriage_qual"] = sel("Marriage quality","جودة الزواج", MARQ_OPTS, "a_mqual")
        d["pre_marriage"]  = sel("Relationship before marriage","العلاقة قبل الزواج", PRE_MAR, "a_pre")

    sec("Brothers and Sisters", "الإخوة والأخوات")
    siblings = []
    for i in range(1, 5):
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            lbl(f"Gender {i}","النوع"); g = st.selectbox("",SIB_GENDER,key=f"a_sg{i}",label_visibility="collapsed")
        with c2:
            n = st.text_input("",key=f"a_sn{i}",placeholder=f"Name {i} / الاسم",label_visibility="collapsed")
        with c3:
            a_s = st.text_input("",key=f"a_sa{i}",placeholder=f"Age {i} / السن",label_visibility="collapsed")
        with c4:
            lbl(f"Education {i}","التعليم"); e = st.selectbox("",SIB_EDU,key=f"a_se{i}",label_visibility="collapsed")
        with c5:
            nt = st.text_input("",key=f"a_st{i}",placeholder=f"Notes {i} / ملاحظات",label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a_s,"edu":e,"notes":nt})
    d["siblings"] = siblings

    sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
    d["onset"]      = ti("Onset — Since when?","متى بدأت الأعراض؟","a_onset")
    d["onset_mode"] = sel("Mode of onset","طريقة البداية", ONSET_MODE, "a_omode")
    d["course"]     = sel("Course of illness","مسار المرض", COURSE_OPTS, "a_course")
    d["complaints"] = ta("Chief Complaints (C/O)","الشكاوى الرئيسية","a_co",120)
    d["hpi"]        = ta("History of Presenting Illness (HPI)","تاريخ المرض الحالي بالتفصيل","a_hpi",220)

    sec("Drug History", "تاريخ الأدوية")
    d["on_meds"]    = rb("Currently on medication?","يتناول أدوية حالياً؟", YNA, "a_onmeds")
    d["compliance"] = sel("Medication compliance","الالتزام بالأدوية", COMPLIANCE, "a_comp")
    d["drug_hx"]    = ta("Medications (name, dose, duration)","الأدوية (الاسم، الجرعة، المدة)","a_drug",100)

    sec("Past History", "التاريخ المرضي السابق")
    c1,c2 = st.columns(2)
    with c1:
        d["prev_psych"] = rb("Previous psychiatric illness?","مرض نفسي سابق؟", YNA, "a_ppsych")
    with c2:
        d["prev_hosp"]  = rb("Previous hospitalization?","دخول مستشفى سابق؟", YNA, "a_phosp")
    d["past_hx"]    = ta("Past history details","تفاصيل التاريخ السابق","a_past",80)

    sec("Family History", "التاريخ العائلي")
    c1,c2 = st.columns(2)
    with c1:
        d["fam_psych"]  = rb("Psychiatric illness in family?","مرض نفسي في الأسرة؟", YNA, "a_fpsych")
    with c2:
        d["fam_neuro"]  = rb("Neurological illness in family?","مرض عصبي في الأسرة؟", YNA, "a_fneuro")
    d["family_hx"]  = ta("Family history details","تفاصيل التاريخ العائلي","a_famhx",80)

    sec("Investigations", "الفحوصات")
    d["had_inv"]       = rb("Investigations done?","تم إجراء فحوصات؟", YNA, "a_hadinv")
    d["investigations"]= ta("Details (Lab, EEG, MRI, CT, etc.)","التفاصيل (تحاليل، رسم مخ، رنين...)","a_inv",80)

    sec("Operations and Surgeries", "العمليات والجراحات")
    d["had_surg"]   = rb("Previous surgeries?","عمليات جراحية سابقة؟", YNA, "a_hsurg")
    d["surgeries"]  = ta("Surgical history details","تفاصيل العمليات الجراحية","a_surg",60)

    sec("Clinical Assessment", "التقييم السريري")
    c1, c2 = st.columns(2)
    with c1:
        d["sleep"]     = sel("Sleep pattern","نمط النوم", SLEEP_OPTS, "a_sleep")
        d["appetite"]  = sel("Appetite","الشهية", APPETITE_OPTS, "a_appetite")
        d["suicidal"]  = sel("Suicidal ideation","أفكار انتحارية", SUICIDAL_OPTS, "a_suicidal")
        d["insight"]   = sel("Insight","البصيرة / الاستبصار", INSIGHT_OPTS, "a_insight")
    with c2:
        d["substance"] = sel("Substance use","تعاطي مواد", SUBSTANCE_OPTS, "a_subs")
        d["substance_details"] = ta("Substance details","تفاصيل المواد","a_subsd",60)
    d["extra_notes"]= ta("Additional notes","ملاحظات إضافية","a_extra",80)

    patient_name = d.get("name") or "Patient"

# ════════════════════════════════════════════════════════
#  CHILD SHEET
# ════════════════════════════════════════════════════════
else:
    sec("Personal Details", "البيانات الشخصية")
    c1, c2 = st.columns(2)
    with c1:
        d["name"]        = ti("Child's Full Name","اسم الطفل","c_name")
        d["age"]         = ti("Age","السن","c_age")
        d["gender"]      = rb("Gender","النوع", GENDER_OPTS, "c_gender")
        d["school"]      = ti("School Name","اسم المدرسة","c_school")
        d["grade"]       = ti("Grade / Year","الصف الدراسي","c_grade")
        d["academic"]    = sel("Academic Performance","المستوى الدراسي", ACADEMIC_OPTS, "c_academic")
        d["birth_order"] = sel("Birth order","ترتيب الميلاد", BIRTH_ORDER, "c_border")
    with c2:
        d["lives_with"]  = ti("Who does child live with?","يعيش مع","c_lives")
        d["phone"]       = ti("Phone","تليفون","c_phone")
        d["date"]        = ti("Date","التاريخ","c_date", placeholder=str(date.today()))
        d["screen_time"] = ti("Daily screen time","وقت الشاشة اليومي","c_screen")
        d["wanted"]      = rb("Was the child wanted/planned?","هل كان مرغوباً فيه؟", WANTED_OPTS, "c_wanted")
        d["gender_des"]  = rb("Was child's gender desired?","هل النوع كان مرغوباً؟", GENDER_DES, "c_gdes")

    sec("Developmental Milestones", "مراحل النمو")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Pregnancy & Birth / الحمل والولادة**")
        d["pregnancy"]   = ti("Pregnancy details","تفاصيل الحمل","c_preg")
        d["birth_type"]  = sel("Birth type","نوع الولادة", BIRTH_TYPE, "c_btype")
        d["birth_comp"]  = sel("Birth complications","مضاعفات الولادة", BIRTH_COMP, "c_bcomp")
        d["vacc_status"] = sel("Vaccination status","التطعيمات", VACC_OPTS, "c_vacc")
        d["vacc_comp"]   = ti("Post-vaccine complications","مضاعفات بعد التطعيم","c_vcomp")
    with c2:
        st.markdown("**Feeding & Growth / التغذية والنمو**")
        d["breastfeeding"]= sel("Breastfeeding","الرضاعة", BF_OPTS, "c_bf")
        d["weaning"]      = ti("Weaning age","سن الفطام","c_wean")
        d["motor"]        = sel("Motor development","النمو الحركي", MOTOR_OPTS, "c_motor")
        d["motor_detail"] = ti("Motor details","تفاصيل الحركة","c_motord")
        d["teething"]     = ti("Teething age","سن التسنين","c_teeth")
        d["toilet"]       = ti("Toilet training age","سن تدريب دورة المياه","c_toilet")
    with c3:
        st.markdown("**Language & Cognition / اللغة والإدراك**")
        d["speech"]       = sel("Speech development","الكلام", SPEECH_OPTS, "c_speech")
        d["speech_detail"]= ti("Speech details","تفاصيل الكلام","c_speechd")
        d["attention"]    = rb("Attention / الانتباه","الانتباه",["Normal/طبيعي","Impaired/ضعيف","N/A"],"c_attn")
        d["concentration"]= rb("Concentration / التركيز","التركيز",["Normal/طبيعي","Impaired/ضعيف","N/A"],"c_conc")
        d["comprehension"]= rb("Comprehension / الفهم","الفهم",["Normal/طبيعي","Impaired/ضعيف","N/A"],"c_comp")
    d["dev_notes"]    = ta("Developmental notes","ملاحظات النمو","c_devnotes",80)

    sec("Family Details", "بيانات الأسرة")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Father / الأب**")
        d["father_name"]      = ti("Father Name","اسم الأب","c_fn")
        d["father_age"]       = ti("Father Age","سن الأب","c_fa")
        d["father_occ"]       = ti("Father Occupation","وظيفة الأب","c_fo")
        d["father_alive"]     = rb("Father status","حالة الأب", ALIVE_OPTS_M, "c_falive")
        d["father_hereditary"]= ti("Father hereditary illness","مرض وراثي — الأب","c_fh")
    with c2:
        st.markdown("**Mother / الأم**")
        d["mother_name"]      = ti("Mother Name","اسم الأم","c_mn")
        d["mother_age"]       = ti("Mother Age","سن الأم","c_ma")
        d["mother_occ"]       = ti("Mother Occupation","وظيفة الأم","c_mo")
        d["mother_alive"]     = rb("Mother status","حالة الأم", ALIVE_OPTS_F, "c_malive")
        d["mother_hereditary"]= ti("Mother hereditary illness","مرض وراثي — الأم","c_mh")
    d["consanguinity"] = sel("Consanguinity between parents","صلة القرابة بين الأب والأم", CONS_OPTS, "c_cons")
    d["parents_rel"]   = sel("Parents relationship quality","علاقة الأب والأم ببعض", PARENTS_REL, "c_prel")

    sec("Brothers and Sisters", "الإخوة والأخوات")
    siblings = []
    for i in range(1, 5):
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            lbl(f"Gender {i}","النوع"); g = st.selectbox("",SIB_GENDER,key=f"c_sg{i}",label_visibility="collapsed")
        with c2:
            n = st.text_input("",key=f"c_sn{i}",placeholder=f"Name {i} / الاسم",label_visibility="collapsed")
        with c3:
            a_s = st.text_input("",key=f"c_sa{i}",placeholder=f"Age {i} / السن",label_visibility="collapsed")
        with c4:
            lbl(f"Education {i}","التعليم"); e = st.selectbox("",SIB_EDU,key=f"c_se{i}",label_visibility="collapsed")
        with c5:
            nt = st.text_input("",key=f"c_st{i}",placeholder=f"Notes {i} / ملاحظات",label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a_s,"edu":e,"notes":nt})
    d["siblings"]    = siblings
    d["sibling_rel"] = ti("Sibling relationship with each other","علاقة الأخوة ببعض","c_sibrel")
    d["same_school"] = rb("Do siblings attend same school?","هل الأخوة في نفس المدرسة؟", ["Yes / نعم","No / لا","N/A"], "c_ssch")

    sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
    d["onset"]      = ti("Onset — Since when?","متى بدأت الأعراض؟","c_onset")
    d["onset_mode"] = sel("Mode of onset","طريقة البداية", ONSET_MODE, "c_omode")
    d["course"]     = sel("Course","مسار المرض", COURSE_OPTS, "c_course")
    d["complaints"] = ta("Chief Complaints (C/O)","الشكاوى الرئيسية","c_co",120)
    d["hpi"]        = ta("History of Presenting Illness (HPI)","تاريخ المرض الحالي","c_hpi",220)

    sec("Past History", "التاريخ المرضي السابق")
    c1, c2, c3 = st.columns(3)
    with c1:
        d["high_fever"]   = rb("High fever ≥40°C?","حرارة ≥40 درجة؟", YNA, "c_hfever")
        d["head_trauma"]  = rb("Head trauma?","ارتطام رأس؟", YNA, "c_htrauma")
    with c2:
        d["convulsions"]  = rb("Convulsions / Seizures?","تشنجات؟", YNA, "c_conv")
        d["post_vaccine"] = rb("Post-vaccine complications?","مضاعفات بعد التطعيم؟", YNA, "c_pvacc")
    with c3:
        d["prev_hosp"]    = rb("Previous hospitalization?","دخول مستشفى سابق؟", YNA, "c_phosp")
        d["prev_therapy"] = rb("Previous therapy sessions?","جلسات علاجية سابقة؟", YNA, "c_pther")
    d["past_hx"]   = ta("Past history details","تفاصيل التاريخ السابق","c_past",100)

    sec("Family History", "التاريخ العائلي")
    c1, c2 = st.columns(2)
    with c1:
        d["fam_psych"]   = rb("Psychiatric illness in family?","مرض نفسي في الأسرة؟", YNA, "c_fpsych")
        d["fam_neuro"]   = rb("Neurological illness in family?","مرض عصبي في الأسرة؟", YNA, "c_fneuro")
    with c2:
        d["fam_mr"]      = rb("Intellectual disability in family?","إعاقة ذهنية في الأسرة؟", YNA, "c_fmr")
        d["fam_epilepsy"]= rb("Epilepsy in family?","صرع في الأسرة؟", YNA, "c_fepil")
    d["family_hx"]  = ta("Family history details","تفاصيل التاريخ العائلي","c_famhx",80)

    sec("Investigations", "الفحوصات")
    c1, c2, c3 = st.columns(3)
    with c1:
        d["had_ct"]   = rb("CT scan?","أشعة مقطعية؟", YNA, "c_ct")
        d["had_mri"]  = rb("MRI?","رنين مغناطيسي؟", YNA, "c_mri")
    with c2:
        d["had_eeg"]  = rb("EEG?","رسم مخ؟", YNA, "c_eeg")
        d["had_iq"]   = rb("IQ test (SB5)?","اختبار ذكاء SB5؟", YNA, "c_iq")
    with c3:
        d["had_cars"] = rb("CARS?","CARS؟", YNA, "c_cars")
        d["cars_score"]= ti("CARS score (if done)","درجة CARS","c_carsscore")
    d["investigations"]= ta("Investigation details & results","تفاصيل الفحوصات والنتائج","c_inv",80)

    sec("Operations and Surgeries", "العمليات والجراحات")
    d["had_surg"]  = rb("Previous surgeries?","عمليات جراحية سابقة؟", YNA, "c_hsurg")
    d["surgeries"] = ta("Surgical history details","تفاصيل العمليات","c_surg",60)

    sec("Clinical Assessment", "التقييم السريري")
    c1, c2 = st.columns(2)
    with c1:
        d["sleep"]          = sel("Sleep pattern","نمط النوم", SLEEP_OPTS, "c_sleep")
        d["appetite"]       = sel("Appetite","الشهية", APPETITE_OPTS, "c_appetite")
        d["punishment"]     = sel("Punishment methods","طرق العقاب", PUNISHMENT, "c_punish")
        d["stress_reaction"]= sel("Reaction to stress","رد الفعل تجاه الضغوط", STRESS_REACT, "c_stress")
    with c2:
        d["therapy"]        = ta("Current therapy sessions","الجلسات الحالية (تخاطب، تنمية مهارات...)","c_therapy",80)
    d["extra_notes"] = ta("Additional notes","ملاحظات إضافية","c_extra",80)

    patient_name = d.get("name") or "Patient"

# ════════════════════════════════════════════════════════
#  GENERATE BUTTON
# ════════════════════════════════════════════════════════
st.divider()
if st.button("✦ Generate Report / إنشاء التقرير", type="primary", use_container_width=True):
    if not groq_key:
        st.error("Please enter your Groq API key in the sidebar.")
    else:
        siblings = d.get("siblings", [])
        sibling_text = "\n".join([
            f"  {i+1}. {sb['name']} | {sb['gender']} | Age: {sb['age']} | Education: {sb['edu']} | Notes: {sb['notes']}"
            for i, sb in enumerate(siblings)
        ]) or "None reported / لا يوجد"

        if is_adult:
            data_block = f"""
PATIENT: {sv(d,'name')} | Age: {sv(d,'age')} | Gender: {sv(d,'gender')}
Date: {sv(d,'date')} | History by: {history_by or '—'} | History type: {sv(d,'htype')}
Phone: {sv(d,'phone')} | Referral: {sv(d,'referral')}
Occupation: {sv(d,'occupation')} — {sv(d,'occ_detail')} | Education: {sv(d,'education')}
Social Status: {sv(d,'social')} | Hobbies: {sv(d,'hobbies')} | Smoking: {sv(d,'smoking')}

FAMILY:
Father: {sv(d,'father_name')} | Age: {sv(d,'father_age')} | Occ: {sv(d,'father_occ')} | Status: {sv(d,'father_alive')}
Mother: {sv(d,'mother_name')} | Age: {sv(d,'mother_age')} | Occ: {sv(d,'mother_occ')} | Status: {sv(d,'mother_alive')}
Consanguinity: {sv(d,'consanguinity')} | Parents living together: {sv(d,'parents_together')}
Chronic illness in family: {sv(d,'chronic')}

MARRIAGE:
Spouse: {sv(d,'spouse_name')} | Age: {sv(d,'spouse_age')} | Occ: {sv(d,'spouse_occ')}
Duration: {sv(d,'marriage_dur')} | Engagement: {sv(d,'engagement')} | Katb Ketab: {sv(d,'katb')}
Marriage quality: {sv(d,'marriage_qual')} | Pre-marriage relation: {sv(d,'pre_marriage')}
Number of children: {sv(d,'num_children')}

SIBLINGS:
{sibling_text}

ONSET: {sv(d,'onset')} | Mode: {sv(d,'onset_mode')} | Course: {sv(d,'course')}
CHIEF COMPLAINTS (C/O):
{sv(d,'complaints')}
HISTORY OF PRESENTING ILLNESS (HPI):
{sv(d,'hpi')}

DRUG HISTORY:
On medication: {sv(d,'on_meds')} | Compliance: {sv(d,'compliance')}
{sv(d,'drug_hx')}

PAST HISTORY:
Previous psychiatric illness: {sv(d,'prev_psych')} | Previous hospitalization: {sv(d,'prev_hosp')}
{sv(d,'past_hx')}

FAMILY HISTORY:
Psychiatric illness in family: {sv(d,'fam_psych')} | Neurological: {sv(d,'fam_neuro')}
{sv(d,'family_hx')}

INVESTIGATIONS:
Done: {sv(d,'had_inv')}
{sv(d,'investigations')}

SURGERIES:
Previous surgeries: {sv(d,'had_surg')}
{sv(d,'surgeries')}

CLINICAL ASSESSMENT:
Sleep: {sv(d,'sleep')} | Appetite: {sv(d,'appetite')}
Suicidal ideation: {sv(d,'suicidal')} | Insight: {sv(d,'insight')}
Substance use: {sv(d,'substance')} — {sv(d,'substance_details')}
Additional notes: {sv(d,'extra_notes')}
"""
        else:
            data_block = f"""
CHILD: {sv(d,'name')} | Age: {sv(d,'age')} | Gender: {sv(d,'gender')}
Date: {sv(d,'date')} | History by: {history_by or '—'}
Phone: {sv(d,'phone')} | Lives with: {sv(d,'lives_with')}
School: {sv(d,'school')} | Grade: {sv(d,'grade')} | Academic performance: {sv(d,'academic')}
Birth order: {sv(d,'birth_order')} | Daily screen time: {sv(d,'screen_time')}
Was child wanted: {sv(d,'wanted')} | Gender desired: {sv(d,'gender_des')}

DEVELOPMENTAL MILESTONES:
Pregnancy: {sv(d,'pregnancy')} | Birth type: {sv(d,'birth_type')} | Birth complications: {sv(d,'birth_comp')}
Vaccinations: {sv(d,'vacc_status')} | Post-vaccine complications: {sv(d,'vacc_comp')}
Breastfeeding: {sv(d,'breastfeeding')} | Weaning age: {sv(d,'weaning')}
Motor development: {sv(d,'motor')} — {sv(d,'motor_detail')}
Teething: {sv(d,'teething')} | Toilet training: {sv(d,'toilet')}
Speech: {sv(d,'speech')} — {sv(d,'speech_detail')}
Attention: {sv(d,'attention')} | Concentration: {sv(d,'concentration')} | Comprehension: {sv(d,'comprehension')}
Notes: {sv(d,'dev_notes')}

FAMILY:
Father: {sv(d,'father_name')} | Age: {sv(d,'father_age')} | Occ: {sv(d,'father_occ')} | Status: {sv(d,'father_alive')} | Hereditary illness: {sv(d,'father_hereditary')}
Mother: {sv(d,'mother_name')} | Age: {sv(d,'mother_age')} | Occ: {sv(d,'mother_occ')} | Status: {sv(d,'mother_alive')} | Hereditary illness: {sv(d,'mother_hereditary')}
Consanguinity: {sv(d,'consanguinity')} | Parents relationship: {sv(d,'parents_rel')}

SIBLINGS:
{sibling_text}
Sibling relationship: {sv(d,'sibling_rel')} | Same school: {sv(d,'same_school')}

ONSET: {sv(d,'onset')} | Mode: {sv(d,'onset_mode')} | Course: {sv(d,'course')}
CHIEF COMPLAINTS (C/O):
{sv(d,'complaints')}
HISTORY OF PRESENTING ILLNESS (HPI):
{sv(d,'hpi')}

PAST HISTORY:
High fever ≥40°C: {sv(d,'high_fever')} | Head trauma: {sv(d,'head_trauma')}
Convulsions: {sv(d,'convulsions')} | Post-vaccine complications: {sv(d,'post_vaccine')}
Previous hospitalization: {sv(d,'prev_hosp')} | Previous therapy: {sv(d,'prev_therapy')}
{sv(d,'past_hx')}

FAMILY HISTORY:
Psychiatric: {sv(d,'fam_psych')} | Neurological: {sv(d,'fam_neuro')} | Intellectual disability: {sv(d,'fam_mr')} | Epilepsy: {sv(d,'fam_epilepsy')}
{sv(d,'family_hx')}

INVESTIGATIONS:
CT: {sv(d,'had_ct')} | MRI: {sv(d,'had_mri')} | EEG: {sv(d,'had_eeg')} | IQ(SB5): {sv(d,'had_iq')} | CARS: {sv(d,'had_cars')} — Score: {sv(d,'cars_score')}
{sv(d,'investigations')}

SURGERIES:
Previous surgeries: {sv(d,'had_surg')}
{sv(d,'surgeries')}

CLINICAL ASSESSMENT:
Sleep: {sv(d,'sleep')} | Appetite: {sv(d,'appetite')}
Punishment methods: {sv(d,'punishment')} | Reaction to stress: {sv(d,'stress_reaction')}
Current therapy sessions: {sv(d,'therapy')}
Additional notes: {sv(d,'extra_notes')}
"""

        prompt = f"""أنت طبيب نفسي استشاري أول. بناءً على بيانات التاريخ المرضي أدناه، اكتب تقريراً سريرياً متكاملاً وفق الهيكل التالي تماماً.

قواعد صارمة:
1. استخدم البيانات المُدخلة فقط — لا تخترع أي معلومة
2. كل قسم يُكتب بالعربية أولاً ثم الإنجليزية مباشرة بعده
3. إذا كان الحقل "—" اكتب "لم يُذكر / Not reported"
4. الأقسام التي تحتوي على نصوص مكتوبة (مثل HPI والشكاوى) يجب نقلها حرفياً كما كُتبت

══════════════════════════════════════════════════
القسم الأول: ورقة التعريف / IDENTIFICATION SHEET
══════════════════════════════════════════════════
اعرض البيانات في جدول منظم بثلاثة أعمدة:
| Field | الحقل | Value |

تضمن: الاسم، السن، النوع، التاريخ، الأخصائي، نوع التاريخ، الهاتف، مصدر الإحالة، الوظيفة، التعليم، الحالة الاجتماعية، الهوايات، التدخين {"، حالة الأبوين، القرابة، الزواج، عدد الأبناء" if is_adult else "، المدرسة، الصف، المستوى الدراسي، ترتيب الميلاد، وقت الشاشة، يعيش مع"}

══════════════════════════════════════════════════
القسم الثاني: الشكوى الرئيسية وتاريخ المرض / C/O & HPI
══════════════════════════════════════════════════
اكتب هذا القسم بالعربية أولاً ثم الإنجليزية:

الشكوى الرئيسية / Chief Complaint:
[انقل نص الشكاوى حرفياً كما كُتب]

تاريخ المرض الحالي / History of Presenting Illness:
[انقل نص HPI حرفياً كما كُتب، مع ذكر بداية الأعراض وطريقة البداية ومسار المرض]

══════════════════════════════════════════════════
{"القسم الثالث: بيانات الأسرة والزواج / FAMILY & MARRIAGE" if is_adult else "القسم الثالث: بيانات الأسرة والنمو / FAMILY & DEVELOPMENT"}
══════════════════════════════════════════════════
اكتب بالعربية أولاً ثم الإنجليزية:

{"بيانات الأسرة: اعرض بيانات الأب والأم والأخوة والزواج في صورة سردية سريرية منظمة" if is_adult else "بيانات الأسرة: اعرض بيانات الأب والأم والأخوة في صورة سردية سريرية منظمة"}
{"" if is_adult else "مراحل النمو: اعرض مراحل النمو (الحمل، الولادة، الرضاعة، الحركة، الكلام، التطعيمات، التدريب) في صورة جدول واضح"}

══════════════════════════════════════════════════
القسم الرابع: التاريخ المرضي / MEDICAL HISTORY
══════════════════════════════════════════════════
اكتب بالعربية أولاً ثم الإنجليزية. اعرض كل قسم فرعي بوضوح:

{"تاريخ الأدوية / Drug History:" if is_adult else "التاريخ المرضي السابق / Past History:"}
[انقل النص حرفياً مع ذكر النتائج الرئيسية للاختيارات]

{"التاريخ السابق / Past History:" if is_adult else "التاريخ العائلي / Family History:"}
[انقل النص حرفياً]

{"التاريخ العائلي / Family History:" if is_adult else "الفحوصات / Investigations:"}
[انقل النص حرفياً]

{"الفحوصات / Investigations:" if is_adult else "العمليات / Surgeries:"}
[انقل النص حرفياً]

{"العمليات / Surgeries:" if is_adult else ""}
[انقل النص حرفياً]

══════════════════════════════════════════════════
القسم الخامس: التقييم السريري / CLINICAL ASSESSMENT
══════════════════════════════════════════════════
اكتب بالعربية أولاً ثم الإنجليزية:

اعرض النتائج السريرية (النوم، الشهية، {"الأفكار الانتحارية، البصيرة، تعاطي المواد" if is_adult else "طرق العقاب، رد الفعل، الجلسات"}) في جدول واضح، ثم اكتب فقرة تفسيرية.
{"" if is_adult else "اذكر نتائج الاختبارات (CARS, SB5, CT, MRI, EEG) بوضوح."}
ملاحظات إضافية: [انقل النص حرفياً]

══════════════════════════════════════════════════
القسم السادس: الملخص والانطباع السريري / SUMMARY & CLINICAL IMPRESSION
══════════════════════════════════════════════════
اكتب بالعربية أولاً ثم الإنجليزية:

ملخص سريري / Clinical Summary:
[فقرة سردية متكاملة تلخص أبرز ما في التاريخ المرضي — مبنية على البيانات الفعلية فقط]

الانطباع السريري / Clinical Impression:
[انطباع سريري موضوعي بناءً على جميع المعطيات — لا تضع تشخيصاً نهائياً، بل أبرز النقاط الرئيسية التي تستحق الانتباه]

══════════════════════════════════════════════════
HISTORY DATA:
{data_block}
══════════════════════════════════════════════════
History by: {history_by or '—'} | Sheet: {"Adult / بالغ" if is_adult else "Child / طفل"}
"""

        with st.spinner("Generating report... / جاري إنشاء التقرير..."):
            try:
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3000
                )
                st.session_state["report_text"]       = response.choices[0].message.content
                st.session_state["report_pname"]      = patient_name
                st.session_state["report_sheet"]      = "Adult" if is_adult else "Child"
                st.session_state["report_by"]         = history_by or "—"
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ════════════════════════════════════════════════════════
#  SHOW REPORT
# ════════════════════════════════════════════════════════
if st.session_state.get("report_text"):
    rt   = st.session_state["report_text"]
    pn   = st.session_state.get("report_pname","Patient")
    rs   = st.session_state.get("report_sheet","")
    rb_  = st.session_state.get("report_by","—")
    fn   = f"{pn.replace(' ','_')}_HistorySheet.docx"

    st.divider()
    st.markdown("### ✅ Report Generated / تم إنشاء التقرير")
    st.text_area("", value=rt, height=600, label_visibility="collapsed")

    def build_docx(rt, pn, rs, rb_, logo_path, doctor):
        doc = Document()
        for section in doc.sections:
            section.top_margin=Cm(2.5); section.bottom_margin=Cm(2.5)
            section.left_margin=Cm(2.5); section.right_margin=Cm(2.5)
            section.different_first_page_header_footer=True
            for hdr in [section.header, section.first_page_header]:
                for p in hdr.paragraphs: p.clear()
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
        r_t=p_top.add_run("   Clinical History Report")
        r_t.font.name="Arial"; r_t.font.size=Pt(20); r_t.font.bold=True; r_t.font.color.rgb=CLINIC_BLUE
        pPr=p_top._p.get_or_add_pPr(); pBdr=OxmlElement('w:pBdr')
        bot=OxmlElement('w:bottom'); bot.set(qn('w:val'),'single')
        bot.set(qn('w:sz'),'8'); bot.set(qn('w:space'),'4'); bot.set(qn('w:color'),'1A5CB8')
        pBdr.append(bot); pPr.append(pBdr)
        doc.add_paragraph()
        p_i=doc.add_paragraph()
        for label,val in [("Patient: ",pn),("   |   Type: ",rs),("   |   History by: ",rb_)]:
            r=p_i.add_run(label); r.bold=True; r.font.size=Pt(11); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
            r2=p_i.add_run(val); r2.font.size=Pt(11); r2.font.name="Arial"
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
                if not in_table:
                    in_table=True; table=doc.add_table(rows=0,cols=3); table.style='Table Grid'
                row=table.add_row()
                for i,ct in enumerate(cells[:3]):
                    cell=row.cells[i]; cell.text=ct
                    for para in cell.paragraphs:
                        for run in para.runs: run.font.size=Pt(10); run.font.name="Arial"
                continue
            else: in_table=False; table=None
            if ls.startswith('══') or ls.startswith('━'):
                p=doc.add_paragraph(); pPr2=p._p.get_or_add_pPr(); pBdr2=OxmlElement('w:pBdr')
                b2=OxmlElement('w:bottom'); b2.set(qn('w:val'),'single')
                b2.set(qn('w:sz'),'6'); b2.set(qn('w:space'),'1'); b2.set(qn('w:color'),'1A5CB8')
                pBdr2.append(b2); pPr2.append(pBdr2); continue
            if ('القسم' in ls or 'SECTION' in ls or ('/' in ls and len(ls)<80 and ls.isupper())):
                p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(14)
                r=p.add_run(ls); r.bold=True; r.font.size=Pt(13); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                pPr3=p._p.get_or_add_pPr(); pBdr3=OxmlElement('w:pBdr')
                b3=OxmlElement('w:bottom'); b3.set(qn('w:val'),'single')
                b3.set(qn('w:sz'),'4'); b3.set(qn('w:space'),'1'); b3.set(qn('w:color'),'1A5CB8')
                pBdr3.append(b3); pPr3.append(pBdr3); continue
            if ls.endswith(':') and len(ls)<80 and not ls.startswith('|'):
                p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(8)
                r=p.add_run(ls); r.bold=True; r.font.size=Pt(11); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                continue
            if ls.startswith('• ') or ls.startswith('- '):
                p=doc.add_paragraph(style='List Bullet')
                r=p.add_run(ls.lstrip('•- ').strip()); r.font.size=Pt(11); r.font.name="Arial"
                continue
            p=doc.add_paragraph(); r=p.add_run(ls); r.font.size=Pt(11); r.font.name="Arial"
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
        st.download_button("📄 Download .docx",data=docx_buf,file_name=fn,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with col2:
        if st.button("📧 Send to Email / إرسال بالبريد"):
            try:
                docx_buf2=build_docx(rt,pn,rs,rb_,LOGO_PATH,DOCTOR)
                msg=MIMEMultipart(); msg['From']=GMAIL_USER; msg['To']=RECIPIENT_EMAIL
                msg['Subject']=f"History Report — {pn}"
                msg.attach(MIMEText(f"History report for: {pn}\nType: {rs}\nBy: {rb_}",'plain'))
                part=MIMEBase('application','octet-stream'); part.set_payload(docx_buf2.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',f'attachment; filename="{fn}"')
                msg.attach(part)
                with smtplib.SMTP_SSL('smtp.gmail.com',465) as server:
                    server.login(GMAIL_USER,GMAIL_PASS)
                    server.sendmail(GMAIL_USER,RECIPIENT_EMAIL,msg.as_string())
                st.success(f"✅ Sent to {RECIPIENT_EMAIL}")
            except Exception as e:
                st.error(f"Email error: {str(e)}")
    with col3:
        if st.button("↺ New Patient / مريض جديد"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
