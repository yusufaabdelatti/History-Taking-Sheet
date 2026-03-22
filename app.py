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
NAVY            = RGBColor(0x1B, 0x2A, 0x4A)
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

def sec(en, ar=""):
    label = f"{en} / {ar}" if ar else en
    st.markdown(f'<div class="sec-header">{label}</div>', unsafe_allow_html=True)

def lbl(en, ar):
    st.markdown(f'<div class="field-label"><b>{en}</b> / {ar}</div>', unsafe_allow_html=True)

def sv(d, key, default="—"):
    v = d.get(key, "")
    if not v: return default
    v = str(v).strip()
    return v if v else default

# ── CHOOSE TYPE ──
sheet_type = st.radio("**Sheet Type / نوع الاستمارة**",
                      ["👤 Adult / بالغ", "👶 Child / طفل"],
                      horizontal=True)
is_adult = "Adult" in sheet_type
st.divider()

# ════════════════════════════════════════════════════════
#  COLLECT ALL VALUES INTO A DICT
# ════════════════════════════════════════════════════════
d = {}   # all form values stored here

if is_adult:
    # ── PERSONAL ──
    sec("Personal Details", "البيانات الشخصية")
    c1, c2 = st.columns(2)
    with c1:
        lbl("Full Name","الاسم");              d["name"]         = st.text_input("", key="a_name",     label_visibility="collapsed")
        lbl("Age","السن");                     d["age"]          = st.text_input("", key="a_age",      label_visibility="collapsed")
        lbl("Gender","النوع");                 d["gender"]       = st.text_input("", key="a_gender",   label_visibility="collapsed")
        lbl("Occupation / Study","الوظيفة / الدراسة"); d["occupation"] = st.text_input("", key="a_occ", label_visibility="collapsed")
        lbl("Education Level","المستوى التعليمي"); d["education"] = st.text_input("", key="a_edu",    label_visibility="collapsed")
    with c2:
        lbl("Social Status","الحالة الاجتماعية"); d["social"]    = st.text_input("", key="a_social",  label_visibility="collapsed")
        lbl("Hobbies","الهوايات");             d["hobbies"]      = st.text_input("", key="a_hobbies", label_visibility="collapsed")
        lbl("Smoking","التدخين");              d["smoking"]      = st.text_input("", key="a_smoking",  label_visibility="collapsed")
        lbl("Phone","رقم الهاتف");             d["phone"]        = st.text_input("", key="a_phone",   label_visibility="collapsed")
        lbl("Referral Source","مصدر الإحالة"); d["referral"]    = st.text_input("", key="a_referral", label_visibility="collapsed")
    lbl("Date","التاريخ"); d["date"] = st.text_input("", key="a_date", placeholder=str(date.today()), label_visibility="collapsed")
    lbl("History Type","نوع التاريخ"); d["htype"] = st.text_input("", key="a_htype", label_visibility="collapsed")

    # ── FAMILY ──
    sec("Family Details", "بيانات الأسرة")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Father / الأب**")
        lbl("Father Name","اسم الأب");       d["father_name"] = st.text_input("", key="a_fn",  label_visibility="collapsed")
        lbl("Father Age","سن الأب");         d["father_age"]  = st.text_input("", key="a_fa",  label_visibility="collapsed")
        lbl("Father Occupation","وظيفة الأب"); d["father_occ"] = st.text_input("", key="a_fo", label_visibility="collapsed")
    with c2:
        st.markdown("**Mother / الأم**")
        lbl("Mother Name","اسم الأم");       d["mother_name"] = st.text_input("", key="a_mn",  label_visibility="collapsed")
        lbl("Mother Age","سن الأم");         d["mother_age"]  = st.text_input("", key="a_ma",  label_visibility="collapsed")
        lbl("Mother Occupation","وظيفة الأم"); d["mother_occ"] = st.text_input("", key="a_mo", label_visibility="collapsed")
    lbl("Consanguinity","صلة القرابة");      d["consanguinity"]    = st.text_input("", key="a_cons",    label_visibility="collapsed")
    lbl("Chronic illness in family","مرض مزمن"); d["chronic"]   = st.text_input("", key="a_chronic",  label_visibility="collapsed")

    # ── MARRIAGE ──
    sec("Marriage Details", "بيانات الزواج")
    c1, c2 = st.columns(2)
    with c1:
        lbl("Spouse Name","اسم الزوج/الزوجة");  d["spouse_name"] = st.text_input("", key="a_spn",  label_visibility="collapsed")
        lbl("Spouse Age","سن الزوج/الزوجة");    d["spouse_age"]  = st.text_input("", key="a_spa",  label_visibility="collapsed")
        lbl("Spouse Occupation","وظيفة الزوج/الزوجة"); d["spouse_occ"] = st.text_input("", key="a_spo", label_visibility="collapsed")
    with c2:
        lbl("Marriage Duration","فترة الزواج"); d["marriage_dur"]  = st.text_input("", key="a_mdur", label_visibility="collapsed")
        lbl("Engagement Period","فترة الخطوبة"); d["engagement"]   = st.text_input("", key="a_eng",  label_visibility="collapsed")
        lbl("Number of Children","عدد الأبناء"); d["num_children"] = st.text_input("", key="a_nch",  label_visibility="collapsed")
    lbl("Katb Ketab / كتب كتاب","كتب كتاب قبل الزواج")
    d["katb"] = st.radio("", ["Yes/نعم", "No/لا", "N/A"], key="a_katb", horizontal=True, label_visibility="collapsed")
    lbl("Relationship before marriage","العلاقة قبل الزواج"); d["pre_marriage"] = st.text_input("", key="a_pre", label_visibility="collapsed")

    # ── SIBLINGS ──
    sec("Brothers and Sisters", "الإخوة والأخوات")
    siblings = []
    for i in range(1, 5):
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: g  = st.text_input("", key=f"a_sg{i}", placeholder=f"Gender {i}/النوع",     label_visibility="collapsed")
        with c2: n  = st.text_input("", key=f"a_sn{i}", placeholder=f"Name {i}/الاسم",       label_visibility="collapsed")
        with c3: a  = st.text_input("", key=f"a_sa{i}", placeholder=f"Age {i}/السن",          label_visibility="collapsed")
        with c4: e  = st.text_input("", key=f"a_se{i}", placeholder=f"Education {i}/التعليم", label_visibility="collapsed")
        with c5: nt = st.text_input("", key=f"a_st{i}", placeholder=f"Notes {i}/ملاحظات",     label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a,"edu":e,"notes":nt})
    d["siblings"] = siblings

    # ── COMPLAINTS ──
    sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
    lbl("Onset — Since when?","متى بدأت الأعراض؟"); d["onset"]      = st.text_input("", key="a_onset",     label_visibility="collapsed")
    lbl("Chief Complaints (C/O)","الشكاوى الرئيسية"); d["complaints"] = st.text_area("", key="a_complaints", height=120, label_visibility="collapsed")
    lbl("History of Presenting Illness (HPI)","تاريخ المرض الحالي بالتفصيل"); d["hpi"] = st.text_area("", key="a_hpi", height=220, label_visibility="collapsed")

    # ── DRUG / PAST / FAMILY HX ──
    sec("Drug History", "تاريخ الأدوية")
    lbl("Current and past medications","الأدوية الحالية والسابقة"); d["drug_hx"] = st.text_area("", key="a_drug", height=100, label_visibility="collapsed")
    sec("Past History", "التاريخ المرضي السابق")
    lbl("Previous illnesses / hospitalizations","الأمراض السابقة / دخول المستشفى"); d["past_hx"] = st.text_area("", key="a_past", height=100, label_visibility="collapsed")
    sec("Family History", "التاريخ العائلي")
    lbl("Psychiatric or neurological illness in family","أمراض نفسية أو عصبية في الأسرة"); d["family_hx"] = st.text_area("", key="a_famhx", height=100, label_visibility="collapsed")

    # ── INVESTIGATIONS ──
    sec("Investigations", "الفحوصات")
    lbl("Lab, EEG, MRI, CT, etc.","تحاليل، رسم مخ، رنين، أشعة مقطعية..."); d["investigations"] = st.text_area("", key="a_inv", height=100, label_visibility="collapsed")
    sec("Operations and Surgeries", "العمليات والجراحات")
    lbl("Previous surgeries","العمليات الجراحية السابقة"); d["surgeries"] = st.text_area("", key="a_surg", height=80, label_visibility="collapsed")

    # ── CLINICAL ASSESSMENT ──
    sec("Clinical Assessment", "التقييم السريري")
    c1, c2 = st.columns(2)
    with c1:
        lbl("Sleep / النوم","النوم")
        d["sleep"] = st.radio("", ["Normal/طبيعي","Insomnia/أرق","Hypersomnia/نوم زيادة","Disrupted/متقطع"], key="a_sleep", horizontal=True, label_visibility="collapsed")
        lbl("Appetite / الشهية","الشهية")
        d["appetite"] = st.radio("", ["Normal/طبيعي","Decreased/قلت","Increased/زادت"], key="a_appetite", horizontal=True, label_visibility="collapsed")
        lbl("Suicidal ideation / أفكار انتحارية","أفكار انتحارية")
        d["suicidal"] = st.radio("", ["None/لا","Passive/سلبية","Active/نشطة"], key="a_suicidal", horizontal=True, label_visibility="collapsed")
    with c2:
        lbl("Substance use / تعاطي مواد","تعاطي مواد")
        d["substance"] = st.radio("", ["None/لا","Yes/نعم"], key="a_subs", horizontal=True, label_visibility="collapsed")
        lbl("Substance details if yes","تفاصيل المواد إن وجدت"); d["substance_details"] = st.text_area("", key="a_subsd", height=60, label_visibility="collapsed")
    lbl("Additional notes / ملاحظات إضافية","ملاحظات إضافية"); d["extra_notes"] = st.text_area("", key="a_extra", height=100, label_visibility="collapsed")

    patient_name = d.get("name") or "Patient"

else:
    # ════════ CHILD SHEET ════════
    sec("Personal Details & Developmental Milestones", "البيانات الشخصية ومراحل النمو")
    c1, c2 = st.columns(2)
    with c1:
        lbl("Child's Full Name","اسم الطفل");     d["name"]     = st.text_input("", key="c_name",   label_visibility="collapsed")
        lbl("Age","السن");                         d["age"]      = st.text_input("", key="c_age",    label_visibility="collapsed")
        lbl("Gender","النوع");                     d["gender"]   = st.text_input("", key="c_gender", label_visibility="collapsed")
        lbl("School Name","اسم المدرسة");          d["school"]   = st.text_input("", key="c_school", label_visibility="collapsed")
        lbl("Grade / Year","الصف الدراسي");        d["grade"]    = st.text_input("", key="c_grade",  label_visibility="collapsed")
        lbl("Who does child live with?","يعيش مع"); d["lives_with"] = st.text_input("", key="c_lives", label_visibility="collapsed")
    with c2:
        lbl("Academic Performance","المستوى الدراسي")
        d["academic"] = st.radio("", ["Excellent/ممتاز","Good/جيد","Average/متوسط","Weak/ضعيف"], key="c_academic", horizontal=True, label_visibility="collapsed")
        lbl("Phone","تليفون");                    d["phone"]       = st.text_input("", key="c_phone",  label_visibility="collapsed")
        lbl("Date","التاريخ");                    d["date"]        = st.text_input("", key="c_date",   placeholder=str(date.today()), label_visibility="collapsed")
        lbl("Daily screen time","وقت الشاشة اليومي"); d["screen_time"] = st.text_input("", key="c_screen", label_visibility="collapsed")

    st.markdown("---")
    st.markdown("**Developmental Milestones / مراحل النمو**")
    c1,c2,c3 = st.columns(3)
    with c1:
        lbl("Pregnancy details","تفاصيل الحمل");       d["pregnancy"]   = st.text_input("", key="c_preg",  label_visibility="collapsed")
        lbl("Birth type (natural/CS)","نوع الولادة");  d["birth"]       = st.text_input("", key="c_birth", label_visibility="collapsed")
        lbl("Birth complications","مضاعفات الولادة");  d["birth_comp"]  = st.text_input("", key="c_bcomp", label_visibility="collapsed")
        lbl("Incubator / Jaundice","حضانة / صفراء");   d["incubator"]   = st.text_input("", key="c_incu",  label_visibility="collapsed")
    with c2:
        lbl("Breastfeeding","الرضاعة");                d["breastfeeding"]= st.text_input("", key="c_bf",   label_visibility="collapsed")
        lbl("Weaning age","سن الفطام");                d["weaning"]     = st.text_input("", key="c_wean",  label_visibility="collapsed")
        lbl("Motor development","سن الحركة");          d["motor"]       = st.text_input("", key="c_motor", label_visibility="collapsed")
        lbl("Teething age","سن التسنين");              d["teething"]    = st.text_input("", key="c_teeth", label_visibility="collapsed")
    with c3:
        lbl("Speech onset age","سن بداية الكلام");     d["speech"]      = st.text_input("", key="c_speech",label_visibility="collapsed")
        lbl("Toilet training age","سن تدريب دورة المياه"); d["toilet"]  = st.text_input("", key="c_toilet",label_visibility="collapsed")
        lbl("Vaccination status","التطعيمات");          d["vaccinations"]= st.text_input("", key="c_vacc", label_visibility="collapsed")
        lbl("Post-vaccine complications","مضاعفات التطعيم"); d["vacc_comp"] = st.text_input("", key="c_vcomp", label_visibility="collapsed")
    lbl("Developmental notes","ملاحظات النمو"); d["dev_notes"] = st.text_area("", key="c_devnotes", height=80, label_visibility="collapsed")

    # ── FAMILY ──
    sec("Family Details", "بيانات الأسرة")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Father / الأب**")
        lbl("Father Name","اسم الأب");            d["father_name"]      = st.text_input("", key="c_fn",   label_visibility="collapsed")
        lbl("Father Age","سن الأب");              d["father_age"]       = st.text_input("", key="c_fa",   label_visibility="collapsed")
        lbl("Father Occupation","وظيفة الأب");    d["father_occ"]       = st.text_input("", key="c_fo",   label_visibility="collapsed")
        lbl("Father hereditary illness","مرض وراثي — الأب"); d["father_hereditary"] = st.text_input("", key="c_fh", label_visibility="collapsed")
    with c2:
        st.markdown("**Mother / الأم**")
        lbl("Mother Name","اسم الأم");            d["mother_name"]      = st.text_input("", key="c_mn",   label_visibility="collapsed")
        lbl("Mother Age","سن الأم");              d["mother_age"]       = st.text_input("", key="c_ma",   label_visibility="collapsed")
        lbl("Mother Occupation","وظيفة الأم");    d["mother_occ"]       = st.text_input("", key="c_mo",   label_visibility="collapsed")
        lbl("Mother hereditary illness","مرض وراثي — الأم"); d["mother_hereditary"] = st.text_input("", key="c_mh", label_visibility="collapsed")
    lbl("Consanguinity between parents","صلة القرابة بين الأب والأم"); d["consanguinity"] = st.text_input("", key="c_cons", label_visibility="collapsed")
    lbl("Parents relationship quality","علاقة الأب والأم ببعض"); d["parents_rel"] = st.text_input("", key="c_prel", label_visibility="collapsed")
    lbl("Was the child wanted/planned?","هل كان الطفل مرغوباً فيه؟")
    d["wanted"] = st.radio("", ["Yes/نعم","No/لا","Unplanned/غير مخطط"], key="c_wanted", horizontal=True, label_visibility="collapsed")
    lbl("Was child's gender desired?","هل نوع الطفل كان مرغوباً فيه؟")
    d["gender_desired"] = st.radio("", ["Yes/نعم","No/لا","Didn't matter/لا فرق"], key="c_gdesired", horizontal=True, label_visibility="collapsed")

    # ── SIBLINGS ──
    sec("Brothers and Sisters", "الإخوة والأخوات")
    siblings = []
    for i in range(1, 5):
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: g  = st.text_input("", key=f"c_sg{i}", placeholder=f"Gender {i}/النوع",      label_visibility="collapsed")
        with c2: n  = st.text_input("", key=f"c_sn{i}", placeholder=f"Name {i}/الاسم",        label_visibility="collapsed")
        with c3: a  = st.text_input("", key=f"c_sa{i}", placeholder=f"Age {i}/السن",           label_visibility="collapsed")
        with c4: e  = st.text_input("", key=f"c_se{i}", placeholder=f"Education {i}/التعليم",  label_visibility="collapsed")
        with c5: nt = st.text_input("", key=f"c_st{i}", placeholder=f"Notes {i}/ملاحظات",      label_visibility="collapsed")
        if n: siblings.append({"gender":g,"name":n,"age":a,"edu":e,"notes":nt})
    d["siblings"] = siblings
    lbl("Sibling relationship with each other","علاقة الأخوة ببعض"); d["sibling_rel"] = st.text_input("", key="c_sibrel", label_visibility="collapsed")
    lbl("Do siblings attend same school?","هل الأخوة في نفس المدرسة؟")
    d["same_school"] = st.radio("", ["Yes/نعم","No/لا","N/A"], key="c_ssch", horizontal=True, label_visibility="collapsed")

    # ── COMPLAINTS ──
    sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
    lbl("Onset — Since when?","متى بدأت الأعراض؟"); d["onset"]      = st.text_input("", key="c_onset",     label_visibility="collapsed")
    lbl("Chief Complaints (C/O)","الشكاوى الرئيسية"); d["complaints"] = st.text_area("", key="c_complaints", height=120, label_visibility="collapsed")
    lbl("History of Presenting Illness (HPI)","تاريخ المرض الحالي بالتفصيل"); d["hpi"] = st.text_area("", key="c_hpi", height=220, label_visibility="collapsed")

    # ── PAST / FAMILY HX ──
    sec("Past History", "التاريخ المرضي السابق")
    lbl("Previous illnesses / hospitalizations / fever ≥40°C / head trauma / convulsions",
        "الأمراض السابقة / دخول المستشفى / حرارة ≥40 / ارتطام رأس / تشنجات")
    d["past_hx"] = st.text_area("", key="c_past", height=120, label_visibility="collapsed")
    sec("Family History", "التاريخ العائلي")
    lbl("Psychiatric, neurological, MR or epilepsy in family","أمراض نفسية أو عصبية أو إعاقة أو صرع في الأسرة")
    d["family_hx"] = st.text_area("", key="c_famhx", height=100, label_visibility="collapsed")

    # ── INVESTIGATIONS ──
    sec("Investigations", "الفحوصات")
    lbl("CT, MRI, EEG, IQ (SB5, CARS), who ordered/reviewed","أشعة مقطعية، رنين، رسم مخ، اختبارات ذكاء")
    d["investigations"] = st.text_area("", key="c_inv", height=100, label_visibility="collapsed")
    sec("Operations and Surgeries", "العمليات والجراحات")
    lbl("Previous surgeries","العمليات الجراحية السابقة"); d["surgeries"] = st.text_area("", key="c_surg", height=60, label_visibility="collapsed")

    # ── CLINICAL ──
    sec("Clinical Assessment", "التقييم السريري")
    c1, c2 = st.columns(2)
    with c1:
        lbl("Sleep / النوم","النوم")
        d["sleep"] = st.radio("", ["Normal/طبيعي","Insomnia/أرق","Hypersomnia/نوم زيادة","Disrupted/متقطع"], key="c_sleep", horizontal=True, label_visibility="collapsed")
        lbl("Appetite / الشهية","الشهية")
        d["appetite"] = st.radio("", ["Normal/طبيعي","Decreased/قلت","Increased/زادت"], key="c_appetite", horizontal=True, label_visibility="collapsed")
    with c2:
        lbl("Punishment methods used","طرق العقاب المستخدمة"); d["punishment"]     = st.text_input("", key="c_punish",  label_visibility="collapsed")
        lbl("Reaction to stress","رد الفعل تجاه الضغوط");     d["stress_reaction"] = st.text_input("", key="c_stress",  label_visibility="collapsed")
    lbl("Current therapy sessions (speech, skills, etc.)","الجلسات الحالية (تخاطب، تنمية مهارات...)")
    d["therapy"] = st.text_area("", key="c_therapy", height=60, label_visibility="collapsed")
    lbl("Additional notes / ملاحظات إضافية","ملاحظات إضافية"); d["extra_notes"] = st.text_area("", key="c_extra", height=80, label_visibility="collapsed")

    # ── CHILD CHECKLIST ──
    sec("Child Clinical Checklist", "قائمة التدقيق السريري للأطفال")
    st.caption("Answer Yes / No for each item and add notes where relevant / أجب بنعم أو لا وأضف ملاحظات")

    checklist_items = [
        ("Consanguinity between parents","القرابة بين الأب والأم"),
        ("Was the child wanted / planned?","هل الطفل كان مرغوباً فيه؟"),
        ("Was the child's gender desired?","هل نوع الطفل كان مرغوباً فيه؟"),
        ("Motor & cognitive developmental history","تاريخ النمو الحركي والمعرفي"),
        ("Toilet training age & punishment methods","سن تدريب دورة المياه وطرق العقاب"),
        ("Siblings at same/different school? Relationship?","الأخوة في نفس المدرسة؟ علاقتهم ببعض؟"),
        ("Full prenatal / natal / postnatal history","تاريخ الحمل كامل: قبل/أثناء/بعد الولادة"),
        ("Birth type, forceps/vacuum, incubator, jaundice","نوع الولادة، جفت/شفاط، حضانة، صفراء"),
        ("Problems during pregnancy / late pregnancy age","مشاكل أثناء الحمل / حمل في سن متأخر"),
        ("Family members with psychiatric illness, MR, epilepsy","أقارب لديهم مشكلة نفسية أو إعاقة أو صرع"),
        ("Reaction to stress / punishment methods","رد الفعل تجاه الضغوط / طرق العقاب"),
        ("If seizures: document doctors and treatments","في حالة تشنجات: الأطباء والعلاجات"),
        ("High fever ≥40°C / hospitalization","ارتفاع حرارة ≥40 درجة / دخول مستشفى"),
        ("Head trauma: location, vomiting, sleep changes","ارتطام الرأس: مكانه، قيء، تغير في النوم"),
        ("Convulsions / post-vaccine complications (MMR at 18m)","تشنجات / مضاعفات تطعيم MMR عند سنة ونصف"),
        ("Cognitive distinctions: attention vs concentration","التفرقة: انتباه، تركيز، إدراك، فهم"),
        ("Current therapy sessions","جلسات تخاطب / تنمية مهارات"),
        ("Death of a sibling: details, age, reaction","وفاة أحد الأخوة: التفاصيل، عمر الطفل، رد فعله"),
        ("Investigations: who ordered / who reviewed?","الفحوصات: من طلبها ومن راجعها؟"),
    ]

    checklist_results = {}
    for idx_c, (en, ar) in enumerate(checklist_items):
        col1, col2, col3 = st.columns([3, 1, 3])
        with col1:
            st.markdown(f"**{en}**")
            st.markdown(f"*{ar}*")
        with col2:
            ans = st.radio("", ["Yes/نعم","No/لا","N/A"],
                           key=f"chk_{idx_c}", horizontal=False, label_visibility="collapsed")
        with col3:
            note = st.text_input("", key=f"chkn_{idx_c}",
                                 placeholder="Notes / ملاحظات", label_visibility="collapsed")
        checklist_results[en] = {"ar": ar, "answer": ans, "notes": note}
        st.divider()

    d["checklist"] = checklist_results
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
            f"  {i+1}. {sb['name']} | {sb['gender']} | Age: {sb['age']} | {sb['edu']} | Notes: {sb['notes']}"
            for i, sb in enumerate(siblings)
        ]) or "—"

        if is_adult:
            data_block = f"""
=== ADULT HISTORY SHEET ===
Patient: {sv(d,'name')} | Age: {sv(d,'age')} | Gender: {sv(d,'gender')}
Date: {sv(d,'date')} | History by: {history_by or '—'} | Type: {sv(d,'htype')}
Phone: {sv(d,'phone')} | Referral: {sv(d,'referral')}
Occupation: {sv(d,'occupation')} | Education: {sv(d,'education')}
Social Status: {sv(d,'social')} | Hobbies: {sv(d,'hobbies')} | Smoking: {sv(d,'smoking')}

FAMILY:
Father: {sv(d,'father_name')} | Age: {sv(d,'father_age')} | Occ: {sv(d,'father_occ')}
Mother: {sv(d,'mother_name')} | Age: {sv(d,'mother_age')} | Occ: {sv(d,'mother_occ')}
Consanguinity: {sv(d,'consanguinity')} | Chronic illness: {sv(d,'chronic')}

MARRIAGE:
Spouse: {sv(d,'spouse_name')} | Age: {sv(d,'spouse_age')} | Occ: {sv(d,'spouse_occ')}
Duration: {sv(d,'marriage_dur')} | Engagement: {sv(d,'engagement')}
Katb Ketab: {sv(d,'katb')} | Pre-marriage relation: {sv(d,'pre_marriage')}
Number of children: {sv(d,'num_children')}

SIBLINGS:
{sibling_text}

Onset: {sv(d,'onset')}
C/O: {sv(d,'complaints')}
HPI: {sv(d,'hpi')}

Drug History: {sv(d,'drug_hx')}
Past History: {sv(d,'past_hx')}
Family History: {sv(d,'family_hx')}
Investigations: {sv(d,'investigations')}
Surgeries: {sv(d,'surgeries')}

Sleep: {sv(d,'sleep')} | Appetite: {sv(d,'appetite')}
Suicidal ideation: {sv(d,'suicidal')}
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
Screen time: {sv(d,'screen_time')}

DEVELOPMENTAL MILESTONES:
Pregnancy: {sv(d,'pregnancy')} | Birth: {sv(d,'birth')} | Complications: {sv(d,'birth_comp')}
Incubator/Jaundice: {sv(d,'incubator')} | Breastfeeding: {sv(d,'breastfeeding')} | Weaning: {sv(d,'weaning')}
Motor: {sv(d,'motor')} | Teething: {sv(d,'teething')} | Speech: {sv(d,'speech')}
Toilet training: {sv(d,'toilet')} | Vaccinations: {sv(d,'vaccinations')} | Post-vaccine: {sv(d,'vacc_comp')}
Notes: {sv(d,'dev_notes')}

FAMILY:
Father: {sv(d,'father_name')} | Age: {sv(d,'father_age')} | Occ: {sv(d,'father_occ')} | Hereditary: {sv(d,'father_hereditary')}
Mother: {sv(d,'mother_name')} | Age: {sv(d,'mother_age')} | Occ: {sv(d,'mother_occ')} | Hereditary: {sv(d,'mother_hereditary')}
Consanguinity: {sv(d,'consanguinity')} | Parents relation: {sv(d,'parents_rel')}
Child wanted: {sv(d,'wanted')} | Gender desired: {sv(d,'gender_desired')}

SIBLINGS:
{sibling_text}
Sibling relation: {sv(d,'sibling_rel')} | Same school: {sv(d,'same_school')}

Onset: {sv(d,'onset')}
C/O: {sv(d,'complaints')}
HPI: {sv(d,'hpi')}

Past History: {sv(d,'past_hx')}
Family History: {sv(d,'family_hx')}
Investigations: {sv(d,'investigations')}
Surgeries: {sv(d,'surgeries')}

Sleep: {sv(d,'sleep')} | Appetite: {sv(d,'appetite')}
Punishment: {sv(d,'punishment')} | Stress reaction: {sv(d,'stress_reaction')}
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
[عربي — استخدم البيانات الفعلية من حقلي C/O و HPI]
[English — use actual C/O and HPI data]

** الخلفية الشخصية والاجتماعية / Personal & Social Background **
[عربي — استخدم بيانات الوظيفة، التعليم، الحالة الاجتماعية]
[English — use occupation, education, social status data]

** الخلفية العائلية / Family Background **
[عربي — استخدم البيانات العائلية الفعلية]
[English — use actual family data]

** التاريخ الطبي والدوائي / Medical & Drug History **
[عربي — استخدم بيانات التاريخ السابق والأدوية]
[English — use past history and drug history data]

** الملاحظات السريرية / Clinical Observations **
[عربي — استخدم بيانات النوم، الشهية، التقييم السريري]
[English — use sleep, appetite, clinical assessment data]

** الانطباع العام / Summary Impression **
[عربي — انطباع سريري مختصر بناءً على جميع البيانات]
[English — brief clinical impression based on all data]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الجزء الثاني / PART 2 — السجل التفصيلي / DETAILED RECORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

قدم جميع البيانات في جدول بثلاثة أعمدة:
| Field (English) | الحقل (عربي) | Response / الإجابة |

أبقِ الكلمات كما كُتبت تماماً. اشمل كل حقل بدون استثناء.

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

# ════════════════════════════════════════════════════════
#  SHOW REPORT
# ════════════════════════════════════════════════════════
if st.session_state.get("report_text"):
    report_text  = st.session_state["report_text"]
    p_name       = st.session_state.get("report_patient_name", "Patient")
    r_sheet_type = st.session_state.get("report_sheet_type", "")
    r_history_by = st.session_state.get("report_history_by", "—")

    st.divider()
    st.markdown("### ✅ Report Generated / تم إنشاء التقرير")
    st.text_area("", value=report_text, height=500, label_visibility="collapsed")

    filename = f"{p_name.replace(' ','_')}_HistorySheet.docx"

    def build_docx(report_text, p_name, r_sheet_type, r_history_by, logo_path, doctor):
        doc = Document()
        for section in doc.sections:
            section.top_margin = Cm(2.5); section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5); section.right_margin = Cm(2.5)
            section.different_first_page_header_footer = True
            for hdr in [section.header, section.first_page_header]:
                for p in hdr.paragraphs: p.clear()

        # Page border
        for section in doc.sections:
            sectPr = section._sectPr
            pgBorders = OxmlElement('w:pgBorders')
            pgBorders.set(qn('w:offsetFrom'), 'page')
            for side in ('top','left','bottom','right'):
                b = OxmlElement(f'w:{side}')
                b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'12')
                b.set(qn('w:space'),'24'); b.set(qn('w:color'),'1B2A4A')
                pgBorders.append(b)
            sectPr.append(pgBorders)

        # Page numbers
        for section in doc.sections:
            footer = section.footer
            para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            para.clear(); para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(); run.font.size = Pt(9); run.font.color.rgb = CLINIC_BLUE
            for tag, text in [('begin',None),(None,' PAGE '),('end',None)]:
                if tag:
                    el = OxmlElement('w:fldChar'); el.set(qn('w:fldCharType'),tag); run._r.append(el)
                else:
                    instr = OxmlElement('w:instrText'); instr.text = text; run._r.append(instr)

        # Logo + title
        p_top = doc.add_paragraph()
        p_top.paragraph_format.space_before = Pt(0); p_top.paragraph_format.space_after = Pt(6)
        if os.path.exists(logo_path):
            p_top.add_run().add_picture(logo_path, width=Inches(1.2))
        r_t = p_top.add_run("   Clinical History Report")
        r_t.font.name="Arial"; r_t.font.size=Pt(20); r_t.font.bold=True; r_t.font.color.rgb=CLINIC_BLUE
        pPr=p_top._p.get_or_add_pPr(); pBdr=OxmlElement('w:pBdr')
        bot=OxmlElement('w:bottom'); bot.set(qn('w:val'),'single')
        bot.set(qn('w:sz'),'8'); bot.set(qn('w:space'),'4'); bot.set(qn('w:color'),'1A5CB8')
        pBdr.append(bot); pPr.append(pBdr)

        doc.add_paragraph()
        p_info = doc.add_paragraph()
        for label, val in [("Patient: ", p_name),("   |   Type: ", r_sheet_type),("   |   History by: ", r_history_by)]:
            r = p_info.add_run(label); r.bold=True; r.font.size=Pt(11); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
            r2 = p_info.add_run(val); r2.font.size=Pt(11); r2.font.name="Arial"
        doc.add_paragraph()

        in_table = False; table = None
        for line in report_text.split('\n'):
            ls = line.strip()
            if not ls:
                if not in_table: doc.add_paragraph()
                continue
            if ls.startswith('|') and ls.endswith('|'):
                cells = [c.strip() for c in ls.strip('|').split('|')]
                if all(set(c) <= set('-: ') for c in cells): continue
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

            if ls.startswith('PART ') or 'PROFESSIONAL SUMMARY' in ls or 'DETAILED RECORD' in ls or 'الملخص المهني' in ls or 'السجل التفصيلي' in ls:
                p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(14)
                r=p.add_run(ls); r.bold=True; r.font.size=Pt(13); r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                continue

            if ls.startswith('• ') or ls.startswith('- '):
                p=doc.add_paragraph(style='List Bullet')
                r=p.add_run(ls.lstrip('•- ').strip()); r.font.size=Pt(11); r.font.name="Arial"
                continue

            p=doc.add_paragraph(); r=p.add_run(ls); r.font.size=Pt(11); r.font.name="Arial"

        # Doctor footer
        doc.add_paragraph(); doc.add_paragraph()
        p_sep=doc.add_paragraph(); pPr_s=p_sep._p.get_or_add_pPr(); pBdr_s=OxmlElement('w:pBdr')
        top_s=OxmlElement('w:top'); top_s.set(qn('w:val'),'single')
        top_s.set(qn('w:sz'),'6'); top_s.set(qn('w:space'),'1'); top_s.set(qn('w:color'),'1A5CB8')
        pBdr_s.append(top_s); pPr_s.append(pBdr_s)
        p_dr=doc.add_paragraph()
        r_dr=p_dr.add_run(doctor["name"]); r_dr.bold=True; r_dr.font.size=Pt(12); r_dr.font.name="Arial"; r_dr.font.color.rgb=CLINIC_BLUE
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

    col1, col2, col3 = st.columns(3)
    with col1:
        docx_buf = build_docx(report_text, p_name, r_sheet_type, r_history_by, LOGO_PATH, DOCTOR)
        st.download_button("📄 Download .docx", data=docx_buf, file_name=filename,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with col2:
        if st.button("📧 Send to Email / إرسال بالبريد"):
            try:
                docx_buf2 = build_docx(report_text, p_name, r_sheet_type, r_history_by, LOGO_PATH, DOCTOR)
                msg = MIMEMultipart()
                msg['From'] = GMAIL_USER; msg['To'] = RECIPIENT_EMAIL
                msg['Subject'] = f"History Report — {p_name}"
                msg.attach(MIMEText(f"History report for: {p_name}\nType: {r_sheet_type}\nBy: {r_history_by}", 'plain'))
                part = MIMEBase('application','octet-stream'); part.set_payload(docx_buf2.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(GMAIL_USER, GMAIL_PASS)
                    server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
                st.success(f"✅ Sent to {RECIPIENT_EMAIL}")
            except Exception as e:
                st.error(f"Email error: {str(e)}")
    with col3:
        if st.button("↺ New Patient / مريض جديد"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
