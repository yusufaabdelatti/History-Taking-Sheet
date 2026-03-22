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
    .sec-header{font-size:16px;font-weight:700;color:#1A5CB8;margin-top:24px;margin-bottom:8px;
                border-bottom:2px solid #1A5CB8;padding-bottom:4px}
    .field-label{font-size:13px;color:#333;margin-bottom:2px}
</style>
""", unsafe_allow_html=True)

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

def ti(en, ar, key, placeholder=""):
    lbl(en, ar)
    return st.text_input("", key=key, placeholder=placeholder, label_visibility="collapsed")

def ta(en, ar, key, height=100):
    lbl(en, ar)
    return st.text_area("", key=key, height=height, label_visibility="collapsed")

def rb(en, ar, opts, key):
    lbl(en, ar)
    return st.radio("", opts, key=key, horizontal=True, label_visibility="collapsed")

def sel(en, ar, opts, key):
    lbl(en, ar)
    return st.selectbox("", opts, key=key, label_visibility="collapsed")

def sv(d, key, default="—"):
    v = d.get(key, "")
    if not v: return default
    v = str(v).strip()
    return v if v and v not in ["—", "اختر / Select"] else default

# ── CHOOSE TYPE ──
sheet_type = st.radio("**Sheet Type / نوع الاستمارة**",
                      ["👤 Adult / بالغ", "👶 Child / طفل"],
                      horizontal=True)
is_adult = "Adult" in sheet_type
st.divider()

d = {}  # all values

NA_OPT    = "— اختر / Select —"
YES_NO_NA = ["Yes / نعم", "No / لا", "N/A"]
YES_NO    = ["Yes / نعم", "No / لا"]
GENDER_OPTS = ["Male / ذكر", "Female / أنثى"]
SOCIAL_OPTS = ["Single / أعزب", "Married / متزوج", "Divorced / مطلق", "Widowed / أرمل"]
SMOKING_OPTS= ["Non-smoker / لا يدخن", "Smoker / مدخن", "Ex-smoker / توقف عن التدخين", "Shisha / شيشة"]
EDU_OPTS    = ["Illiterate / أمي", "Primary / ابتدائي", "Preparatory / إعدادي",
               "Secondary / ثانوي", "University / جامعي", "Postgraduate / دراسات عليا"]
SOCIAL_STATUS_OPTS = ["Single / أعزب", "Married / متزوج", "Divorced / مطلق",
                      "Widowed / أرمل", "Separated / منفصل"]
REFERRAL_OPTS = [NA_OPT, "Self / ذاتي", "Family / الأسرة", "Doctor / طبيب",
                 "Psychologist / أخصائي نفسي", "School / المدرسة", "Other / أخرى"]
OCCUPATION_STATUS = [NA_OPT, "Employed / موظف", "Self-employed / أعمال حرة",
                     "Student / طالب", "Housewife / ربة منزل",
                     "Retired / متقاعد", "Unemployed / عاطل", "Other / أخرى"]
BIRTH_ORDER_OPTS = [NA_OPT,"1st / الأول","2nd / الثاني","3rd / الثالث",
                    "4th / الرابع","5th / الخامس","6th+ / السادس فأكثر","Only child / وحيد"]
KATB_OPTS  = ["Yes / نعم", "No / لا", "N/A"]
MARRIAGE_QUALITY = [NA_OPT,"Good / جيدة","Average / متوسطة","Poor / سيئة","Separated / منفصلان"]
PRE_MARRIAGE = [NA_OPT,"No prior relation / لا توجد علاقة سابقة",
                "Knew each other / تعارف فقط","Long relationship / علاقة طويلة",
                "Arranged / مرتب","Other / أخرى"]
ONSET_MODE = [NA_OPT,"Sudden / مفاجئ","Gradual / تدريجي"]
COURSE_OPTS= [NA_OPT,"Continuous / مستمر","Episodic / نوبات","Improving / في تحسن","Worsening / في تدهور"]
COMPLIANCE = [NA_OPT,"Good / جيد","Poor / سيء","Irregular / غير منتظم","Refused / رافض"]
INSIGHT_OPTS=[NA_OPT,"Full / كامل","Partial / جزئي","None / لا يوجد"]
SLEEP_OPTS = ["Normal / طبيعي","Insomnia / أرق","Hypersomnia / نوم زيادة","Disrupted / متقطع"]
APPETITE_OPTS=["Normal / طبيعي","Decreased / قلت","Increased / زادت"]
SUICIDAL_OPTS=["None / لا","Passive ideation / أفكار سلبية","Active ideation / أفكار نشطة","Plan / خطة"]
SUBSTANCE_OPTS=["None / لا","Alcohol / كحول","Cannabis / حشيش","Pills / حبوب",
                "Other / أخرى","Multiple / متعدد"]
BIRTH_TYPE = [NA_OPT,"Normal / طبيعي","C-Section / قيصري","Forceps / جفت","Vacuum / شفاط"]
BIRTH_COMP = [NA_OPT,"None / لا يوجد","Jaundice / صفراء","Incubator / حضانة",
              "Asphyxia / اختناق","Low birth weight / وزن منخفض","Other / أخرى"]
BF_OPTS    = [NA_OPT,"Breastfed / رضاعة طبيعية","Formula / صناعية","Mixed / مختلطة"]
MOTOR_OPTS = [NA_OPT,"Normal / طبيعي","Delayed / متأخر","Early / مبكر"]
SPEECH_OPTS= [NA_OPT,"Normal / طبيعي","Delayed / متأخر","Absent / غائب","Regressed / تراجع"]
VACC_OPTS  = [NA_OPT,"Complete / مكتمل","Incomplete / غير مكتمل","Unknown / غير معروف"]
ACADEMIC_OPTS=["Excellent / ممتاز","Good / جيد","Average / متوسط","Weak / ضعيف","Not in school / لا يدرس"]
WANTED_OPTS= ["Yes / نعم","No / لا","Unplanned / غير مخطط"]
GENDER_DES = ["Yes / نعم","No / لا","Didn't matter / لا فرق"]
SAME_SCH   = ["Yes / نعم","No / لا","N/A"]
PARENTS_REL= [NA_OPT,"Good / جيدة","Average / متوسطة","Poor / سيئة",
              "Separated / منفصلان","Divorced / مطلقان","One deceased / أحدهما متوفى"]
CONS_OPTS  = [NA_OPT,"No / لا","First degree / الدرجة الأولى",
              "Second degree / الدرجة الثانية","Third degree / الدرجة الثالثة"]
SIB_GENDER = [NA_OPT,"Male / ذكر","Female / أنثى"]
SIB_EDU    = [NA_OPT,"Kindergarten / روضة","Primary / ابتدائي","Preparatory / إعدادي",
              "Secondary / ثانوي","University / جامعي","Graduate / خريج","Not in school / لا يدرس"]
PUNISHMENT = [NA_OPT,"Verbal / لفظي","Withdrawal of privileges / حرمان","Physical / جسدي","Ignoring / تجاهل","Mixed / مختلط"]
STRESS_REACT=[NA_OPT,"Calm / هادئ","Crying / بكاء","Aggression / عدوان","Withdrawal / انسحاب","Mixed / مختلط"]

# ══════════════════════════════════════════════════════════
#  ADULT SHEET
# ══════════════════════════════════════════════════════════
if is_adult:

    sec("Personal Details", "البيانات الشخصية")
    c1, c2 = st.columns(2)
    with c1:
        ti("Full Name","الاسم","a_name")
        d["name"] = st.session_state.get("a_name","")
        ti("Age","السن","a_age")
        d["age"] = st.session_state.get("a_age","")
        d["gender"]    = rb("Gender","النوع", GENDER_OPTS, "a_gender")
        d["education"] = sel("Education Level","المستوى التعليمي", EDU_OPTS, "a_edu")
        d["occupation"]= sel("Occupation","الوظيفة", OCCUPATION_STATUS, "a_occ")
        ti("Occupation details","تفاصيل الوظيفة","a_occ_detail")
        d["occ_detail"]= st.session_state.get("a_occ_detail","")
    with c2:
        d["social"]    = sel("Social Status","الحالة الاجتماعية", SOCIAL_STATUS_OPTS, "a_social")
        d["smoking"]   = sel("Smoking","التدخين", SMOKING_OPTS, "a_smoking")
        d["referral"]  = sel("Referral Source","مصدر الإحالة", REFERRAL_OPTS, "a_referral")
        ti("Phone","رقم الهاتف","a_phone")
        d["phone"] = st.session_state.get("a_phone","")
        ti("Hobbies","الهوايات","a_hobbies")
        d["hobbies"] = st.session_state.get("a_hobbies","")
        ti("Date","التاريخ","a_date", placeholder=str(date.today()))
        d["date"] = st.session_state.get("a_date","") or str(date.today())
        ti("History Type","نوع التاريخ","a_htype")
        d["htype"] = st.session_state.get("a_htype","")

    sec("Family Details", "بيانات الأسرة")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Father / الأب**")
        ti("Father Name","اسم الأب","a_fn"); d["father_name"]=st.session_state.get("a_fn","")
        ti("Father Age","سن الأب","a_fa");   d["father_age"] =st.session_state.get("a_fa","")
        ti("Father Occupation","وظيفة الأب","a_fo"); d["father_occ"]=st.session_state.get("a_fo","")
        d["father_alive"]=rb("Father status","حالة الأب",["Alive / حي","Deceased / متوفى","Unknown / غير معروف"],"a_falive")
    with c2:
        st.markdown("**Mother / الأم**")
        ti("Mother Name","اسم الأم","a_mn"); d["mother_name"]=st.session_state.get("a_mn","")
        ti("Mother Age","سن الأم","a_ma");   d["mother_age"] =st.session_state.get("a_ma","")
        ti("Mother Occupation","وظيفة الأم","a_mo"); d["mother_occ"]=st.session_state.get("a_mo","")
        d["mother_alive"]=rb("Mother status","حالة الأم",["Alive / حية","Deceased / متوفاة","Unknown / غير معروف"],"a_malive")
    d["consanguinity"]  = sel("Consanguinity","صلة القرابة", CONS_OPTS, "a_cons")
    d["parents_together"]= rb("Parents living together?","الأبوان يعيشان معاً؟", YES_NO_NA, "a_ptog")
    ti("Chronic illness in family","مرض مزمن في الأسرة","a_chronic")
    d["chronic"] = st.session_state.get("a_chronic","")

    sec("Marriage Details", "بيانات الزواج")
    c1, c2 = st.columns(2)
    with c1:
        ti("Spouse Name","اسم الزوج/الزوجة","a_spn"); d["spouse_name"]=st.session_state.get("a_spn","")
        ti("Spouse Age","سن الزوج/الزوجة","a_spa");   d["spouse_age"] =st.session_state.get("a_spa","")
        ti("Spouse Occupation","وظيفة الزوج/الزوجة","a_spo"); d["spouse_occ"]=st.session_state.get("a_spo","")
        ti("Marriage Duration","فترة الزواج","a_mdur"); d["marriage_dur"]=st.session_state.get("a_mdur","")
    with c2:
        ti("Engagement Period","فترة الخطوبة","a_eng"); d["engagement"]=st.session_state.get("a_eng","")
        ti("Number of Children","عدد الأبناء","a_nch"); d["num_children"]=st.session_state.get("a_nch","")
        d["katb"]          = rb("Katb Ketab / كتب كتاب","كتب كتاب", KATB_OPTS, "a_katb")
        d["marriage_qual"] = sel("Marriage quality","جودة الزواج", MARRIAGE_QUALITY, "a_mqual")
        d["pre_marriage"]  = sel("Relationship before marriage","العلاقة قبل الزواج", PRE_MARRIAGE, "a_pre")

    sec("Brothers and Sisters", "الإخوة والأخوات")
    siblings = []
    for i in range(1, 5):
        st.markdown(f"**Sibling {i} / الأخ/الأخت {i}**")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            lbl(f"Gender {i}","النوع")
            g = st.selectbox("",SIB_GENDER,key=f"a_sg{i}",label_visibility="collapsed")
        with c2:
            n = st.text_input("",key=f"a_sn{i}",placeholder=f"Name {i}/الاسم",label_visibility="collapsed")
        with c3:
            a = st.text_input("",key=f"a_sa{i}",placeholder=f"Age {i}/السن",label_visibility="collapsed")
        with c4:
            lbl(f"Education {i}","التعليم")
            e = st.selectbox("",SIB_EDU,key=f"a_se{i}",label_visibility="collapsed")
        with c5:
            nt= st.text_input("",key=f"a_st{i}",placeholder=f"Notes {i}/ملاحظات",label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a,"edu":e,"notes":nt})
    d["siblings"] = siblings

    sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
    ti("Onset — Since when?","متى بدأت الأعراض؟","a_onset"); d["onset"]=st.session_state.get("a_onset","")
    d["onset_mode"] = sel("Mode of onset","طريقة البداية", ONSET_MODE, "a_omode")
    d["course"]     = sel("Course of illness","مسار المرض", COURSE_OPTS, "a_course")
    ta("Chief Complaints (C/O)","الشكاوى الرئيسية","a_complaints",120); d["complaints"]=st.session_state.get("a_complaints","")
    ta("History of Presenting Illness (HPI)","تاريخ المرض الحالي بالتفصيل","a_hpi",220);  d["hpi"]=st.session_state.get("a_hpi","")

    sec("Drug History", "تاريخ الأدوية")
    d["on_meds"]   = rb("Currently on medication?","يتناول أدوية حالياً؟", YES_NO_NA, "a_onmeds")
    d["compliance"]= sel("Compliance","الالتزام بالأدوية", COMPLIANCE, "a_comp")
    ta("Medications (name, dose, duration)","الأدوية (الاسم، الجرعة، المدة)","a_drug",100); d["drug_hx"]=st.session_state.get("a_drug","")

    sec("Past History", "التاريخ المرضي السابق")
    d["prev_psych"] = rb("Previous psychiatric illness?","مرض نفسي سابق؟", YES_NO_NA, "a_ppsych")
    d["prev_hosp"]  = rb("Previous hospitalization?","دخول مستشفى سابق؟", YES_NO_NA, "a_phosp")
    ta("Details","التفاصيل","a_past",80); d["past_hx"]=st.session_state.get("a_past","")

    sec("Family History", "التاريخ العائلي")
    d["fam_psych"] = rb("Psychiatric illness in family?","مرض نفسي في الأسرة؟", YES_NO_NA, "a_fpsych")
    d["fam_neuro"] = rb("Neurological illness in family?","مرض عصبي في الأسرة؟", YES_NO_NA, "a_fneuro")
    ta("Details","التفاصيل","a_famhx",80); d["family_hx"]=st.session_state.get("a_famhx","")

    sec("Investigations", "الفحوصات")
    d["had_inv"] = rb("Investigations done?","تم إجراء فحوصات؟", YES_NO_NA, "a_hadinv")
    ta("Details (Lab, EEG, MRI, CT, etc.)","التفاصيل (تحاليل، رسم مخ، رنين...)","a_inv",80); d["investigations"]=st.session_state.get("a_inv","")

    sec("Operations and Surgeries", "العمليات والجراحات")
    d["had_surg"] = rb("Previous surgeries?","عمليات جراحية سابقة؟", YES_NO_NA, "a_hsurg")
    ta("Details","التفاصيل","a_surg",60); d["surgeries"]=st.session_state.get("a_surg","")

    sec("Clinical Assessment", "التقييم السريري")
    c1, c2 = st.columns(2)
    with c1:
        d["sleep"]    = sel("Sleep","النوم", SLEEP_OPTS, "a_sleep")
        d["appetite"] = sel("Appetite","الشهية", APPETITE_OPTS, "a_appetite")
        d["suicidal"] = sel("Suicidal ideation","أفكار انتحارية", SUICIDAL_OPTS, "a_suicidal")
        d["insight"]  = sel("Insight","البصيرة", INSIGHT_OPTS, "a_insight")
    with c2:
        d["substance"]= sel("Substance use","تعاطي مواد", SUBSTANCE_OPTS, "a_subs")
        ta("Substance details if applicable","تفاصيل المواد","a_subsd",60); d["substance_details"]=st.session_state.get("a_subsd","")
    ta("Additional notes / ملاحظات إضافية","ملاحظات إضافية","a_extra",80); d["extra_notes"]=st.session_state.get("a_extra","")

    patient_name = st.session_state.get("a_name","") or "Patient"

# ══════════════════════════════════════════════════════════
#  CHILD SHEET
# ══════════════════════════════════════════════════════════
else:
    sec("Personal Details", "البيانات الشخصية")
    c1, c2 = st.columns(2)
    with c1:
        ti("Child's Full Name","اسم الطفل","c_name"); d["name"]=st.session_state.get("c_name","")
        ti("Age","السن","c_age"); d["age"]=st.session_state.get("c_age","")
        d["gender"]   = rb("Gender","النوع", GENDER_OPTS, "c_gender")
        ti("School Name","اسم المدرسة","c_school"); d["school"]=st.session_state.get("c_school","")
        ti("Grade / Year","الصف الدراسي","c_grade"); d["grade"]=st.session_state.get("c_grade","")
        d["academic"] = sel("Academic Performance","المستوى الدراسي", ACADEMIC_OPTS, "c_academic")
    with c2:
        ti("Who does child live with?","يعيش مع","c_lives"); d["lives_with"]=st.session_state.get("c_lives","")
        ti("Phone","تليفون","c_phone"); d["phone"]=st.session_state.get("c_phone","")
        ti("Date","التاريخ","c_date",placeholder=str(date.today())); d["date"]=st.session_state.get("c_date","") or str(date.today())
        ti("Daily screen time","وقت الشاشة اليومي","c_screen"); d["screen_time"]=st.session_state.get("c_screen","")
        d["birth_order"]=sel("Birth order","ترتيب الميلاد", BIRTH_ORDER_OPTS, "c_border")

    sec("Developmental Milestones", "مراحل النمو")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Pregnancy & Birth / الحمل والولادة**")
        ti("Pregnancy details","تفاصيل الحمل","c_preg"); d["pregnancy"]=st.session_state.get("c_preg","")
        d["birth_type"] = sel("Birth type","نوع الولادة", BIRTH_TYPE, "c_btype")
        d["birth_comp"] = sel("Birth complications","مضاعفات الولادة", BIRTH_COMP, "c_bcomp")
        d["vacc_status"]= sel("Vaccination status","التطعيمات", VACC_OPTS, "c_vacc")
        ti("Post-vaccine complications","مضاعفات بعد التطعيم","c_vcomp"); d["vacc_comp"]=st.session_state.get("c_vcomp","")
    with c2:
        st.markdown("**Feeding / التغذية**")
        d["breastfeeding"] = sel("Breastfeeding","الرضاعة", BF_OPTS, "c_bf")
        ti("Weaning age","سن الفطام","c_wean"); d["weaning"]=st.session_state.get("c_wean","")
        st.markdown("**Motor / الحركة**")
        d["motor"] = sel("Motor development","النمو الحركي", MOTOR_OPTS, "c_motor")
        ti("Motor milestones details","تفاصيل الحركة","c_motord"); d["motor_detail"]=st.session_state.get("c_motord","")
    with c3:
        st.markdown("**Language & Other / اللغة وغيره**")
        d["speech"]  = sel("Speech development","الكلام", SPEECH_OPTS, "c_speech")
        ti("Speech details","تفاصيل الكلام","c_speechd"); d["speech_detail"]=st.session_state.get("c_speechd","")
        ti("Teething age","سن التسنين","c_teeth"); d["teething"]=st.session_state.get("c_teeth","")
        ti("Toilet training age","سن تدريب دورة المياه","c_toilet"); d["toilet"]=st.session_state.get("c_toilet","")
    ta("Developmental notes","ملاحظات النمو","c_devnotes",80); d["dev_notes"]=st.session_state.get("c_devnotes","")

    sec("Family Details", "بيانات الأسرة")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Father / الأب**")
        ti("Father Name","اسم الأب","c_fn"); d["father_name"]=st.session_state.get("c_fn","")
        ti("Father Age","سن الأب","c_fa");   d["father_age"] =st.session_state.get("c_fa","")
        ti("Father Occupation","وظيفة الأب","c_fo"); d["father_occ"]=st.session_state.get("c_fo","")
        d["father_alive"]=rb("Father status","حالة الأب",["Alive / حي","Deceased / متوفى","Unknown / غير معروف"],"c_falive")
        ti("Father hereditary illness","مرض وراثي — الأب","c_fh"); d["father_hereditary"]=st.session_state.get("c_fh","")
    with c2:
        st.markdown("**Mother / الأم**")
        ti("Mother Name","اسم الأم","c_mn"); d["mother_name"]=st.session_state.get("c_mn","")
        ti("Mother Age","سن الأم","c_ma");   d["mother_age"] =st.session_state.get("c_ma","")
        ti("Mother Occupation","وظيفة الأم","c_mo"); d["mother_occ"]=st.session_state.get("c_mo","")
        d["mother_alive"]=rb("Mother status","حالة الأم",["Alive / حية","Deceased / متوفاة","Unknown / غير معروف"],"c_malive")
        ti("Mother hereditary illness","مرض وراثي — الأم","c_mh"); d["mother_hereditary"]=st.session_state.get("c_mh","")
    d["consanguinity"]  = sel("Consanguinity between parents","صلة القرابة بين الأب والأم", CONS_OPTS, "c_cons")
    d["parents_rel"]    = sel("Parents relationship quality","علاقة الأب والأم ببعض", PARENTS_REL, "c_prel")
    d["wanted"]         = rb("Was the child wanted/planned?","هل كان مرغوباً فيه؟", WANTED_OPTS, "c_wanted")
    d["gender_desired"] = rb("Was child's gender desired?","هل نوع الطفل كان مرغوباً فيه؟", GENDER_DES, "c_gdes")

    sec("Brothers and Sisters", "الإخوة والأخوات")
    siblings = []
    for i in range(1, 5):
        st.markdown(f"**Sibling {i} / الأخ/الأخت {i}**")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            lbl(f"Gender {i}","النوع")
            g = st.selectbox("",SIB_GENDER,key=f"c_sg{i}",label_visibility="collapsed")
        with c2:
            n = st.text_input("",key=f"c_sn{i}",placeholder=f"Name {i}/الاسم",label_visibility="collapsed")
        with c3:
            a = st.text_input("",key=f"c_sa{i}",placeholder=f"Age {i}/السن",label_visibility="collapsed")
        with c4:
            lbl(f"Education {i}","التعليم")
            e = st.selectbox("",SIB_EDU,key=f"c_se{i}",label_visibility="collapsed")
        with c5:
            nt= st.text_input("",key=f"c_st{i}",placeholder=f"Notes {i}/ملاحظات",label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a,"edu":e,"notes":nt})
    d["siblings"] = siblings
    ti("Sibling relationship with each other","علاقة الأخوة ببعض","c_sibrel"); d["sibling_rel"]=st.session_state.get("c_sibrel","")
    d["same_school"] = rb("Do siblings attend same school?","هل الأخوة في نفس المدرسة؟", SAME_SCH, "c_ssch")

    sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
    ti("Onset — Since when?","متى بدأت الأعراض؟","c_onset"); d["onset"]=st.session_state.get("c_onset","")
    d["onset_mode"] = sel("Mode of onset","طريقة البداية", ONSET_MODE, "c_omode")
    d["course"]     = sel("Course","مسار المرض", COURSE_OPTS, "c_course")
    ta("Chief Complaints (C/O)","الشكاوى الرئيسية","c_complaints",120); d["complaints"]=st.session_state.get("c_complaints","")
    ta("History of Presenting Illness (HPI)","تاريخ المرض الحالي","c_hpi",220); d["hpi"]=st.session_state.get("c_hpi","")

    sec("Past History", "التاريخ المرضي السابق")
    c1, c2 = st.columns(2)
    with c1:
        d["high_fever"]  = rb("High fever ≥40°C?","حرارة ≥40 درجة؟", YES_NO_NA, "c_hfever")
        d["head_trauma"] = rb("Head trauma?","ارتطام رأس؟", YES_NO_NA, "c_htrauma")
        d["convulsions"] = rb("Convulsions?","تشنجات؟", YES_NO_NA, "c_conv")
    with c2:
        d["post_vaccine"]= rb("Post-vaccine complications?","مضاعفات بعد التطعيم؟", YES_NO_NA, "c_pvacc")
        d["prev_hosp"]   = rb("Previous hospitalization?","دخول مستشفى سابق؟", YES_NO_NA, "c_phosp")
        d["prev_therapy"]= rb("Previous therapy sessions?","جلسات علاجية سابقة؟", YES_NO_NA, "c_pther")
    ta("Past history details","تفاصيل التاريخ السابق","c_past",100); d["past_hx"]=st.session_state.get("c_past","")

    sec("Family History", "التاريخ العائلي")
    c1, c2 = st.columns(2)
    with c1:
        d["fam_psych"] = rb("Psychiatric illness in family?","مرض نفسي في الأسرة؟", YES_NO_NA, "c_fpsych")
        d["fam_neuro"] = rb("Neurological illness in family?","مرض عصبي في الأسرة؟", YES_NO_NA, "c_fneuro")
    with c2:
        d["fam_mr"]    = rb("Intellectual disability in family?","إعاقة ذهنية في الأسرة؟", YES_NO_NA, "c_fmr")
        d["fam_epilepsy"]=rb("Epilepsy in family?","صرع في الأسرة؟", YES_NO_NA, "c_fepil")
    ta("Family history details","تفاصيل التاريخ العائلي","c_famhx",80); d["family_hx"]=st.session_state.get("c_famhx","")

    sec("Investigations", "الفحوصات")
    c1, c2 = st.columns(2)
    with c1:
        d["had_ct"]  = rb("CT scan done?","أشعة مقطعية؟", YES_NO_NA, "c_ct")
        d["had_mri"] = rb("MRI done?","رنين مغناطيسي؟", YES_NO_NA, "c_mri")
        d["had_eeg"] = rb("EEG done?","رسم مخ؟", YES_NO_NA, "c_eeg")
    with c2:
        d["had_iq"]  = rb("IQ test (SB5)?","اختبار ذكاء SB5؟", YES_NO_NA, "c_iq")
        d["had_cars"]= rb("CARS done?","CARS؟", YES_NO_NA, "c_cars")
        ti("CARS score","درجة CARS","c_carsscore"); d["cars_score"]=st.session_state.get("c_carsscore","")
    ta("Investigation details & results","تفاصيل الفحوصات والنتائج","c_inv",80); d["investigations"]=st.session_state.get("c_inv","")

    sec("Operations and Surgeries", "العمليات والجراحات")
    d["had_surg"] = rb("Previous surgeries?","عمليات جراحية سابقة؟", YES_NO_NA, "c_hsurg")
    ta("Details","التفاصيل","c_surg",60); d["surgeries"]=st.session_state.get("c_surg","")

    sec("Clinical Assessment", "التقييم السريري")
    c1, c2 = st.columns(2)
    with c1:
        d["sleep"]    = sel("Sleep","النوم", SLEEP_OPTS, "c_sleep")
        d["appetite"] = sel("Appetite","الشهية", APPETITE_OPTS, "c_appetite")
        d["punishment"]    = sel("Punishment methods","طرق العقاب", PUNISHMENT, "c_punish")
        d["stress_reaction"]= sel("Reaction to stress","رد الفعل تجاه الضغوط", STRESS_REACT, "c_stress")
    with c2:
        ta("Current therapy sessions","الجلسات الحالية (تخاطب، تنمية مهارات...)","c_therapy",60); d["therapy"]=st.session_state.get("c_therapy","")
    ta("Additional notes / ملاحظات إضافية","ملاحظات إضافية","c_extra",80); d["extra_notes"]=st.session_state.get("c_extra","")

    sec("Child Clinical Checklist", "قائمة التدقيق السريري للأطفال")
    st.caption("Answer Yes / No for each item / أجب بنعم أو لا لكل بند")
    checklist_items = [
        ("Consanguinity between parents","القرابة بين الأب والأم"),
        ("Was the child wanted / planned?","هل الطفل كان مرغوباً فيه؟"),
        ("Was the child's gender desired?","هل نوع الطفل كان مرغوباً فيه؟"),
        ("Motor & cognitive developmental history","تاريخ النمو الحركي والمعرفي"),
        ("Toilet training age & punishment methods","سن تدريب دورة المياه وطرق العقاب"),
        ("Siblings at same/different school?","الأخوة في نفس المدرسة؟"),
        ("Full prenatal / natal / postnatal history","تاريخ الحمل كامل: قبل/أثناء/بعد الولادة"),
        ("Birth type, forceps/vacuum, incubator, jaundice","نوع الولادة، جفت/شفاط، حضانة، صفراء"),
        ("Problems during pregnancy / late pregnancy age","مشاكل أثناء الحمل / حمل في سن متأخر"),
        ("Family: psychiatric illness, MR, epilepsy","أقارب: مشكلة نفسية، إعاقة، صرع"),
        ("Reaction to stress / punishment methods","رد الفعل تجاه الضغوط / طرق العقاب"),
        ("If seizures: doctors and treatments documented","تشنجات: توثيق الأطباء والعلاجات"),
        ("High fever ≥40°C / hospitalization","ارتفاع حرارة ≥40 / دخول مستشفى"),
        ("Head trauma: location, vomiting, sleep changes","ارتطام الرأس: مكانه، قيء، تغير نوم"),
        ("Convulsions / post-vaccine complications (MMR)","تشنجات / مضاعفات تطعيم MMR"),
        ("Cognitive distinctions: attention vs concentration","التفرقة: انتباه، تركيز، إدراك، فهم"),
        ("Current therapy sessions","جلسات تخاطب / تنمية مهارات"),
        ("Death of a sibling: details, age, reaction","وفاة أحد الأخوة: التفاصيل، العمر، رد الفعل"),
        ("Investigations: who ordered / who reviewed?","الفحوصات: من طلبها ومن راجعها؟"),
    ]
    checklist_results = {}
    for idx_c, (en, ar) in enumerate(checklist_items):
        col1, col2, col3 = st.columns([3,1,3])
        with col1:
            st.markdown(f"**{en}**")
            st.markdown(f"*{ar}*")
        with col2:
            ans = st.radio("", YES_NO_NA, key=f"chk_{idx_c}", horizontal=False, label_visibility="collapsed")
        with col3:
            note = st.text_input("", key=f"chkn_{idx_c}", placeholder="Notes / ملاحظات", label_visibility="collapsed")
        checklist_results[en] = {"ar": ar, "answer": ans, "notes": note}
        st.divider()
    d["checklist"] = checklist_results
    patient_name = st.session_state.get("c_name","") or "Patient"

# ══════════════════════════════════════════════════════════
#  GENERATE BUTTON
# ══════════════════════════════════════════════════════════
st.divider()
if st.button("✦ Generate Report / إنشاء التقرير", type="primary", use_container_width=True):
    if not groq_key:
        st.error("Please enter your Groq API key in the sidebar.")
    else:
        siblings = d.get("siblings", [])
        sibling_text = "\n".join([
            f"  {i+1}. {sb['name']} | {sb['gender']} | Age: {sb['age']} | {sb['edu']} | Notes: {sb['notes']}"
            for i, sb in enumerate(siblings)
        ]) or "—"

        if is_adult:
            data_block = f"""
=== ADULT HISTORY SHEET ===
Patient: {sv(d,'name')} | Age: {sv(d,'age')} | Gender: {sv(d,'gender')}
Date: {sv(d,'date')} | History by: {history_by or '—'} | Type: {sv(d,'htype')}
Phone: {sv(d,'phone')} | Referral: {sv(d,'referral')}
Occupation: {sv(d,'occupation')} — {sv(d,'occ_detail')}
Education: {sv(d,'education')} | Social Status: {sv(d,'social')}
Hobbies: {sv(d,'hobbies')} | Smoking: {sv(d,'smoking')}

FAMILY:
Father: {sv(d,'father_name')} | Age: {sv(d,'father_age')} | Occ: {sv(d,'father_occ')} | Status: {sv(d,'father_alive')}
Mother: {sv(d,'mother_name')} | Age: {sv(d,'mother_age')} | Occ: {sv(d,'mother_occ')} | Status: {sv(d,'mother_alive')}
Consanguinity: {sv(d,'consanguinity')} | Parents together: {sv(d,'parents_together')}
Chronic illness: {sv(d,'chronic')}

MARRIAGE:
Spouse: {sv(d,'spouse_name')} | Age: {sv(d,'spouse_age')} | Occ: {sv(d,'spouse_occ')}
Duration: {sv(d,'marriage_dur')} | Engagement: {sv(d,'engagement')}
Katb Ketab: {sv(d,'katb')} | Marriage quality: {sv(d,'marriage_qual')}
Pre-marriage relation: {sv(d,'pre_marriage')} | Children: {sv(d,'num_children')}

SIBLINGS:
{sibling_text}

Onset: {sv(d,'onset')} | Mode: {sv(d,'onset_mode')} | Course: {sv(d,'course')}
C/O: {sv(d,'complaints')}
HPI: {sv(d,'hpi')}

On medication: {sv(d,'on_meds')} | Compliance: {sv(d,'compliance')}
Drug History: {sv(d,'drug_hx')}

Previous psychiatric illness: {sv(d,'prev_psych')} | Previous hospitalization: {sv(d,'prev_hosp')}
Past History: {sv(d,'past_hx')}

Psychiatric illness in family: {sv(d,'fam_psych')} | Neurological: {sv(d,'fam_neuro')}
Family History: {sv(d,'family_hx')}

Investigations done: {sv(d,'had_inv')}
Investigations: {sv(d,'investigations')}
Surgeries: {sv(d,'had_surg')} — {sv(d,'surgeries')}

Sleep: {sv(d,'sleep')} | Appetite: {sv(d,'appetite')}
Suicidal ideation: {sv(d,'suicidal')} | Insight: {sv(d,'insight')}
Substance use: {sv(d,'substance')} — {sv(d,'substance_details')}
Extra notes: {sv(d,'extra_notes')}
"""
        else:
            chk = d.get("checklist", {})
            chk_text = "\n".join([
                f"  • {en} / {v['ar']}: {v['answer']} | Notes: {v['notes'] or '—'}"
                for en, v in chk.items()
            ]) or "—"
            data_block = f"""
=== CHILD HISTORY SHEET ===
Child: {sv(d,'name')} | Age: {sv(d,'age')} | Gender: {sv(d,'gender')}
Date: {sv(d,'date')} | History by: {history_by or '—'}
Phone: {sv(d,'phone')} | Lives with: {sv(d,'lives_with')}
School: {sv(d,'school')} | Grade: {sv(d,'grade')} | Academic: {sv(d,'academic')}
Birth order: {sv(d,'birth_order')} | Screen time: {sv(d,'screen_time')}

DEVELOPMENTAL MILESTONES:
Pregnancy: {sv(d,'pregnancy')} | Birth type: {sv(d,'birth_type')} | Birth complications: {sv(d,'birth_comp')}
Vaccinations: {sv(d,'vacc_status')} | Post-vaccine complications: {sv(d,'vacc_comp')}
Breastfeeding: {sv(d,'breastfeeding')} | Weaning: {sv(d,'weaning')}
Motor development: {sv(d,'motor')} — {sv(d,'motor_detail')}
Speech: {sv(d,'speech')} — {sv(d,'speech_detail')}
Teething: {sv(d,'teething')} | Toilet training: {sv(d,'toilet')}
Notes: {sv(d,'dev_notes')}

FAMILY:
Father: {sv(d,'father_name')} | Age: {sv(d,'father_age')} | Occ: {sv(d,'father_occ')} | Status: {sv(d,'father_alive')} | Hereditary: {sv(d,'father_hereditary')}
Mother: {sv(d,'mother_name')} | Age: {sv(d,'mother_age')} | Occ: {sv(d,'mother_occ')} | Status: {sv(d,'mother_alive')} | Hereditary: {sv(d,'mother_hereditary')}
Consanguinity: {sv(d,'consanguinity')} | Parents relation: {sv(d,'parents_rel')}
Child wanted: {sv(d,'wanted')} | Gender desired: {sv(d,'gender_desired')}

SIBLINGS:
{sibling_text}
Sibling relation: {sv(d,'sibling_rel')} | Same school: {sv(d,'same_school')}

Onset: {sv(d,'onset')} | Mode: {sv(d,'onset_mode')} | Course: {sv(d,'course')}
C/O: {sv(d,'complaints')}
HPI: {sv(d,'hpi')}

High fever: {sv(d,'high_fever')} | Head trauma: {sv(d,'head_trauma')} | Convulsions: {sv(d,'convulsions')}
Post-vaccine complications: {sv(d,'post_vaccine')} | Hospitalization: {sv(d,'prev_hosp')} | Previous therapy: {sv(d,'prev_therapy')}
Past History: {sv(d,'past_hx')}

Psychiatric in family: {sv(d,'fam_psych')} | Neurological: {sv(d,'fam_neuro')} | MR: {sv(d,'fam_mr')} | Epilepsy: {sv(d,'fam_epilepsy')}
Family History: {sv(d,'family_hx')}

CT: {sv(d,'had_ct')} | MRI: {sv(d,'had_mri')} | EEG: {sv(d,'had_eeg')} | IQ(SB5): {sv(d,'had_iq')} | CARS: {sv(d,'had_cars')} score: {sv(d,'cars_score')}
Investigations: {sv(d,'investigations')}
Surgeries: {sv(d,'had_surg')} — {sv(d,'surgeries')}

Sleep: {sv(d,'sleep')} | Appetite: {sv(d,'appetite')}
Punishment methods: {sv(d,'punishment')} | Stress reaction: {sv(d,'stress_reaction')}
Therapy sessions: {sv(d,'therapy')}
Extra notes: {sv(d,'extra_notes')}

CHILD CHECKLIST:
{chk_text}
"""

        prompt = f"""أنت طبيب نفسي استشاري أول. بناءً على بيانات التاريخ المرضي المفصلة أدناه، اكتب تقريراً سريرياً شاملاً.

STRICT RULES:
1. Use ONLY the actual data provided — never invent or assume anything
2. Every section must be written in Arabic FIRST, then English immediately after
3. If a field shows "—" write "لم يُذكر / Not reported"
4. The summary must reflect THIS specific patient's actual data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الجزء الأول / PART 1 — الملخص المهني / PROFESSIONAL SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

اكتب كل قسم بالعربية أولاً ثم الإنجليزية:

** نظرة عامة عن المريض / Patient Overview **
[فقرة عربية عن هذا المريض تحديداً]
[English paragraph about this specific patient]

** الشكوى الرئيسية وتاريخ المرض / Chief Complaint & HPI **
[عربي — استخدم البيانات الفعلية]
[English — use actual data]

** الخلفية الشخصية والاجتماعية / Personal & Social Background **
[عربي]
[English]

** الخلفية العائلية / Family Background **
[عربي]
[English]

** التاريخ الطبي والدوائي / Medical & Drug History **
[عربي]
[English]

** الملاحظات السريرية / Clinical Observations **
[عربي]
[English]

** الانطباع العام / Summary Impression **
[عربي]
[English]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الجزء الثاني / PART 2 — السجل التفصيلي / DETAILED RECORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

قدم جميع البيانات في جدول بثلاثة أعمدة:
| Field (English) | الحقل (عربي) | Response / الإجابة |

اشمل كل حقل بدون استثناء. أبقِ الكلمات كما كُتبت تماماً.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORY DATA:
{data_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
History by: {history_by or '—'} | Type: {"Adult/بالغ" if is_adult else "Child/طفل"}
"""

        with st.spinner("Generating report... / جاري إنشاء التقرير..."):
            try:
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3000
                )
                st.session_state["report_text"]         = response.choices[0].message.content
                st.session_state["report_patient_name"] = patient_name
                st.session_state["report_sheet_type"]   = "Adult" if is_adult else "Child"
                st.session_state["report_history_by"]   = history_by or "—"
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ══════════════════════════════════════════════════════════
#  SHOW REPORT + DOWNLOAD + EMAIL
# ══════════════════════════════════════════════════════════
if st.session_state.get("report_text"):
    report_text  = st.session_state["report_text"]
    p_name       = st.session_state.get("report_patient_name","Patient")
    r_sheet_type = st.session_state.get("report_sheet_type","")
    r_history_by = st.session_state.get("report_history_by","—")
    filename     = f"{p_name.replace(' ','_')}_HistorySheet.docx"

    st.divider()
    st.markdown("### ✅ Report Generated / تم إنشاء التقرير")
    st.text_area("", value=report_text, height=500, label_visibility="collapsed")

    def build_docx(report_text, p_name, r_sheet_type, r_history_by, logo_path, doctor):
        doc = Document()
        for section in doc.sections:
            section.top_margin=Cm(2.5); section.bottom_margin=Cm(2.5)
            section.left_margin=Cm(2.5); section.right_margin=Cm(2.5)
            section.different_first_page_header_footer=True
            for hdr in [section.header, section.first_page_header]:
                for p in hdr.paragraphs: p.clear()
        for section in doc.sections:
            sectPr=section._sectPr; pgBorders=OxmlElement('w:pgBorders')
            pgBorders.set(qn('w:offsetFrom'),'page')
            for side in ('top','left','bottom','right'):
                b=OxmlElement(f'w:{side}'); b.set(qn('w:val'),'single')
                b.set(qn('w:sz'),'12'); b.set(qn('w:space'),'24'); b.set(qn('w:color'),'1B2A4A')
                pgBorders.append(b)
            sectPr.append(pgBorders)
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
        p_info=doc.add_paragraph()
        for label,val in [("Patient: ",p_name),("   |   Type: ",r_sheet_type),("   |   History by: ",r_history_by)]:
            r=p_info.add_run(label); r.bold=True; r.font.size=Pt(11); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
            r2=p_info.add_run(val); r2.font.size=Pt(11); r2.font.name="Arial"
        doc.add_paragraph()
        in_table=False; table=None
        for line in report_text.split('\n'):
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
            if ls.startswith('━'):
                p=doc.add_paragraph(); pPr2=p._p.get_or_add_pPr(); pBdr2=OxmlElement('w:pBdr')
                b2=OxmlElement('w:bottom'); b2.set(qn('w:val'),'single')
                b2.set(qn('w:sz'),'4'); b2.set(qn('w:space'),'1'); b2.set(qn('w:color'),'1A5CB8')
                pBdr2.append(b2); pPr2.append(pBdr2); continue
            if ls.startswith('**') and ls.endswith('**'):
                p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(10)
                r=p.add_run(ls.strip('*').strip()); r.bold=True; r.font.size=Pt(12)
                r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                pPr3=p._p.get_or_add_pPr(); pBdr3=OxmlElement('w:pBdr')
                b3=OxmlElement('w:bottom'); b3.set(qn('w:val'),'single')
                b3.set(qn('w:sz'),'4'); b3.set(qn('w:space'),'1'); b3.set(qn('w:color'),'1A5CB8')
                pBdr3.append(b3); pPr3.append(pBdr3); continue
            if ls.startswith('PART ') or 'PROFESSIONAL SUMMARY' in ls or 'DETAILED RECORD' in ls or 'الملخص' in ls or 'السجل' in ls:
                p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(14)
                r=p.add_run(ls); r.bold=True; r.font.size=Pt(13); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
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
        docx_buf=build_docx(report_text,p_name,r_sheet_type,r_history_by,LOGO_PATH,DOCTOR)
        st.download_button("📄 Download .docx",data=docx_buf,file_name=filename,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with col2:
        if st.button("📧 Send to Email / إرسال بالبريد"):
            try:
                docx_buf2=build_docx(report_text,p_name,r_sheet_type,r_history_by,LOGO_PATH,DOCTOR)
                msg=MIMEMultipart(); msg['From']=GMAIL_USER; msg['To']=RECIPIENT_EMAIL
                msg['Subject']=f"History Report — {p_name}"
                msg.attach(MIMEText(f"History report for: {p_name}\nType: {r_sheet_type}\nBy: {r_history_by}",'plain'))
                part=MIMEBase('application','octet-stream'); part.set_payload(docx_buf2.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',f'attachment; filename="{filename}"')
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
