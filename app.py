import streamlit as st
from groq import Groq
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date

st.set_page_config(page_title="History Taking — Dr. Hany Elhennawy", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 26px; font-weight: 700; color: #1A5CB8; margin-bottom: 2px; }
    .sub-title { color: #888; font-size: 13px; margin-bottom: 20px; }
    .sec-header { font-size: 16px; font-weight: 700; color: #1A5CB8; margin-top: 20px; margin-bottom: 8px;
                  border-bottom: 2px solid #1A5CB8; padding-bottom: 4px; }
    .step-box { background: #f0f6ff; border-radius: 8px; padding: 10px 16px;
                margin-bottom: 16px; font-size: 13px; color: #1A5CB8; font-weight: 500; }
    .field-label { font-size: 13px; color: #333; margin-bottom: 2px; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ──
RECIPIENT_EMAIL = "yusuf.a.abdelatti@gmail.com"
GMAIL_USER = "yusuf.a.abdelatti@gmail.com"
GMAIL_PASS = "erjl ehlj wpyg mfgx"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")
CLINIC_BLUE = RGBColor(0x1A, 0x5C, 0xB8)
NAVY = RGBColor(0x1B, 0x2A, 0x4A)

DOCTOR = {
    "name": "Dr. Hany Elhennawy",
    "title1": "Consultant of Neuro-Psychiatry",
    "title2": "Aviation Medical Council — Faculty of Medicine, 6th October University",
    "title3": "MD of Neuroscience Research, Karolinska Institute — Sweden",
    "title4": "Member of I.S.N.R",
    "address": "16 Hesham Labib St., off Makram Ebeid St. Ext., next to Mobilia Saad Mohamed Saad",
    "phone": "+20 1000756200",
}

# ── SIDEBAR ──
with st.sidebar:
    st.header("⚙️ Settings")
    groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.caption("Get free key at [console.groq.com](https://console.groq.com)")
    st.divider()
    history_by = st.text_input("Psychologist Name / اسم الأخصائي",
                                value=st.session_state.get("history_by", ""))

st.markdown('<div class="main-title">🧠 History Taking Sheet</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Dr. Hany Elhennawy Clinic — Neuro-Psychiatry & Neurofeedback</div>',
            unsafe_allow_html=True)

# ── HELPERS ──
def sec(en, ar=""):
    label = f"{en} / {ar}" if ar else en
    st.markdown(f'<div class="sec-header">{label}</div>', unsafe_allow_html=True)

def lbl(en, ar):
    st.markdown(f'<div class="field-label"><b>{en}</b> / {ar}</div>', unsafe_allow_html=True)

def ti(en, ar, key, placeholder=""):
    lbl(en, ar)
    if key not in st.session_state:
        st.session_state[key] = ""
    return st.text_input("", key=key, placeholder=placeholder, label_visibility="collapsed")

def ta(en, ar, key, height=100):
    lbl(en, ar)
    if key not in st.session_state:
        st.session_state[key] = ""
    return st.text_area("", key=key, height=height, label_visibility="collapsed")

def rb(en, ar, opts, key):
    lbl(en, ar)
    if key not in st.session_state:
        st.session_state[key] = opts[0]
    idx = opts.index(st.session_state[key]) if st.session_state[key] in opts else 0
    return st.radio("", opts, index=idx, key=key, horizontal=True, label_visibility="collapsed")

def sv(key, default="—"):
    v = st.session_state.get(key, "")
    if v is None: return default
    v = str(v).strip()
    return v if v and v != "—" else default

def nav(prev_step, next_step=None, final=False):
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if prev_step and st.button("← Back / رجوع"):
            st.session_state.step = prev_step; st.rerun()
    with col2:
        if final:
            if st.button("✦ Generate Report / إنشاء التقرير", type="primary"):
                if not groq_key:
                    st.error("Please enter your Groq API key in the sidebar.")
                else:
                    st.session_state.generate = True; st.rerun()
        else:
            if st.button("Next / التالي →", type="primary"):
                st.session_state.step = next_step; st.rerun()

# ── CHOOSE TYPE ──
if "sheet_type" not in st.session_state:
    st.markdown("### Choose History Sheet Type / اختر نوع الاستمارة")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👤 Adult / بالغ", use_container_width=True, type="primary"):
            st.session_state.sheet_type = "adult"
            st.session_state.step = 1; st.rerun()
    with col2:
        if st.button("👶 Child / طفل", use_container_width=True):
            st.session_state.sheet_type = "child"
            st.session_state.step = 1; st.rerun()
    st.stop()

sheet_type = st.session_state.sheet_type
step = st.session_state.get("step", 1)

if sheet_type == "adult":
    steps = ["Personal Details", "Family Details", "Marriage Details", "Siblings",
             "Complaints & HPI", "Drug / Past / Family Hx", "Investigations & Surgeries", "Clinical Assessment"]
else:
    steps = ["Personal & Developmental", "Family Details", "Siblings",
             "Complaints & HPI", "Past / Family Hx", "Investigations & Surgeries", "Child Checklist"]

total = len(steps)
st.markdown(f'<div class="step-box">Step {step} of {total}: {steps[step-1]}</div>', unsafe_allow_html=True)
st.progress(step / total)

# ════════════════════════════════════════════════════════
#  ADULT SHEET
# ════════════════════════════════════════════════════════
if sheet_type == "adult":

    if step == 1:
        sec("Personal Details", "البيانات الشخصية")
        c1, c2 = st.columns(2)
        with c1:
            ti("Full Name", "الاسم", "a_name")
            ti("Age", "السن", "a_age")
            ti("Gender", "النوع", "a_gender")
            ti("Occupation / Study", "الوظيفة / الدراسة", "a_occupation")
            ti("Education Level", "المستوى التعليمي", "a_education")
        with c2:
            ti("Social Status", "الحالة الاجتماعية", "a_social_status")
            ti("Hobbies", "الهوايات", "a_hobbies")
            ti("Smoking", "التدخين", "a_smoking")
            ti("Phone Number", "رقم الهاتف", "a_phone")
            ti("Referral Source", "مصدر الإحالة", "a_referral")
        ti("Taken Date", "تاريخ الجلسة", "a_taken_date", placeholder=str(date.today()))
        ti("History Type", "نوع التاريخ", "a_history_type")
        nav(None, 2)

    elif step == 2:
        sec("Family Details", "بيانات الأسرة")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Father / الأب**")
            ti("Father's Name", "اسم الأب", "a_father_name")
            ti("Father's Age", "سن الأب", "a_father_age")
            ti("Father's Occupation", "وظيفة الأب", "a_father_occ")
        with c2:
            st.markdown("**Mother / الأم**")
            ti("Mother's Name", "اسم الأم", "a_mother_name")
            ti("Mother's Age", "سن الأم", "a_mother_age")
            ti("Mother's Occupation", "وظيفة الأم", "a_mother_occ")
        ti("Consanguinity between parents", "صلة القرابة بين الأب والأم", "a_consanguinity")
        ti("Chronic illness in family", "مرض مزمن في الأسرة", "a_chronic_illness")
        nav(1, 3)

    elif step == 3:
        sec("Marriage Details", "بيانات الزواج")
        c1, c2 = st.columns(2)
        with c1:
            ti("Spouse Name", "اسم الزوج / الزوجة", "a_spouse_name")
            ti("Spouse Age", "سن الزوج / الزوجة", "a_spouse_age")
            ti("Spouse Occupation", "وظيفة الزوج / الزوجة", "a_spouse_occ")
        with c2:
            ti("Duration of Marriage", "فترة الزواج", "a_marriage_duration")
            ti("Engagement Period", "فترة الخطوبة", "a_engagement")
            ti("Number of Children", "عدد الأبناء", "a_num_children")
        rb("Katb Ketab before marriage? / كتب كتاب قبل الزواج؟", "كتب كتاب",
           ["Yes / نعم", "No / لا", "N/A"], "a_katb_ketab")
        ti("Relationship before marriage", "العلاقة قبل الزواج", "a_pre_marriage_rel")
        nav(2, 4)

    elif step == 4:
        sec("Brothers and Sisters", "الإخوة والأخوات")
        siblings = []
        for i in range(1, 5):
            st.markdown(f"**Sibling {i} / الأخ/الأخت {i}**")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: g = st.text_input("", key=f"a_sib_g_{i}", placeholder="Gender/النوع", label_visibility="collapsed")
            with c2: n = st.text_input("", key=f"a_sib_n_{i}", placeholder="Name/الاسم", label_visibility="collapsed")
            with c3: a = st.text_input("", key=f"a_sib_a_{i}", placeholder="Age/السن", label_visibility="collapsed")
            with c4: e = st.text_input("", key=f"a_sib_e_{i}", placeholder="Education/التعليم", label_visibility="collapsed")
            with c5: nt = st.text_input("", key=f"a_sib_nt_{i}", placeholder="Notes/ملاحظات", label_visibility="collapsed")
            if n: siblings.append({"gender": g, "name": n, "age": a, "edu": e, "notes": nt})
        st.session_state["a_siblings"] = siblings
        nav(3, 5)

    elif step == 5:
        sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
        ti("Onset — Since when?", "متى بدأت الأعراض؟", "a_onset")
        ta("Chief Complaints (C/O)", "الشكاوى الرئيسية", "a_complaints", 120)
        ta("History of Presenting Illness (HPI)", "تاريخ المرض الحالي بالتفصيل", "a_hpi", 250)
        nav(4, 6)

    elif step == 6:
        sec("Drug History", "تاريخ الأدوية")
        ta("Current and past medications (name, dose, duration)", "الأدوية الحالية والسابقة", "a_drug_history", 100)
        sec("Past History", "التاريخ المرضي السابق")
        ta("Previous illnesses / hospitalizations", "الأمراض السابقة / دخول المستشفى", "a_past_history", 100)
        sec("Family History", "التاريخ العائلي")
        ta("Psychiatric or neurological illness in family", "أمراض نفسية أو عصبية في الأسرة", "a_family_history", 100)
        nav(5, 7)

    elif step == 7:
        sec("Investigations", "الفحوصات")
        ta("Lab work, EEG, MRI, CT, etc.", "تحاليل، رسم مخ، رنين، أشعة مقطعية...", "a_investigations", 100)
        sec("Operations and Surgeries", "العمليات والجراحات")
        ta("Previous surgeries", "العمليات الجراحية السابقة", "a_surgeries", 80)
        nav(6, 8)

    elif step == 8:
        sec("Clinical Assessment", "التقييم السريري")
        c1, c2 = st.columns(2)
        with c1:
            rb("Sleep / النوم", "النوم", ["Normal/طبيعي", "Insomnia/أرق", "Hypersomnia/نوم زيادة", "Disrupted/متقطع"], "a_sleep")
            rb("Appetite / الشهية", "الشهية", ["Normal/طبيعي", "Decreased/قلت", "Increased/زادت"], "a_appetite")
            rb("Suicidal ideation / أفكار انتحارية", "أفكار انتحارية", ["None/لا", "Passive/سلبية", "Active/نشطة"], "a_suicidal")
        with c2:
            rb("Substance use / تعاطي مواد", "تعاطي مواد", ["None/لا", "Yes/نعم — specify below"], "a_substance")
            ta("Substance details if yes", "تفاصيل المواد", "a_substance_details", 60)
        ta("Additional notes / ملاحظات إضافية", "ملاحظات إضافية", "a_extra_notes", 100)
        nav(7, final=True)

# ════════════════════════════════════════════════════════
#  CHILD SHEET
# ════════════════════════════════════════════════════════
else:

    if step == 1:
        sec("Personal Details & Developmental Milestones", "البيانات الشخصية ومراحل النمو")
        c1, c2 = st.columns(2)
        with c1:
            ti("Child's Full Name", "اسم الطفل", "c_name")
            ti("Age", "السن", "c_age")
            ti("Gender", "النوع", "c_gender")
            ti("School Name", "اسم المدرسة", "c_school_name")
            ti("Grade / Year", "الصف الدراسي", "c_grade")
            rb("Academic Performance / المستوى الدراسي", "المستوى",
               ["Excellent/ممتاز", "Good/جيد", "Average/متوسط", "Weak/ضعيف"], "c_academic")
        with c2:
            ti("Who does child live with?", "الطفل يعيش مع", "c_lives_with")
            ti("Phone", "تليفون", "c_phone")
            ti("Taken Date", "تاريخ الجلسة", "c_taken_date", placeholder=str(date.today()))
            ti("Daily screen time", "وقت الشاشة اليومي", "c_screen_time")

        st.markdown("---")
        st.markdown("**Developmental Milestones / مراحل النمو**")
        c1, c2, c3 = st.columns(3)
        with c1:
            ti("Pregnancy details", "تفاصيل الحمل", "c_pregnancy")
            ti("Birth type (natural/CS/forceps)", "نوع الولادة", "c_birth")
            ti("Birth complications", "مضاعفات الولادة", "c_birth_comp")
            ti("Incubator / Jaundice", "حضانة / صفراء", "c_incubator")
        with c2:
            ti("Breastfeeding", "الرضاعة", "c_breastfeeding")
            ti("Weaning age", "سن الفطام", "c_weaning")
            ti("Motor development age", "سن الحركة", "c_motor")
            ti("Teething age", "سن التسنين", "c_teething")
        with c3:
            ti("Speech onset age", "سن بداية الكلام", "c_speech")
            ti("Toilet training age", "سن تدريب دورة المياه", "c_toilet")
            ti("Vaccination status", "التطعيمات", "c_vaccinations")
            ti("Post-vaccine complications", "مضاعفات بعد التطعيم", "c_vacc_comp")
        ta("Developmental notes", "ملاحظات النمو", "c_dev_notes", 80)
        nav(None, 2)

    elif step == 2:
        sec("Family Details", "بيانات الأسرة")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Father / الأب**")
            ti("Father's Name", "اسم الأب", "c_father_name")
            ti("Father's Age", "سن الأب", "c_father_age")
            ti("Father's Occupation", "وظيفة الأب", "c_father_occ")
            ti("Father hereditary illness", "مرض وراثي — الأب", "c_father_hereditary")
        with c2:
            st.markdown("**Mother / الأم**")
            ti("Mother's Name", "اسم الأم", "c_mother_name")
            ti("Mother's Age", "سن الأم", "c_mother_age")
            ti("Mother's Occupation", "وظيفة الأم", "c_mother_occ")
            ti("Mother hereditary illness", "مرض وراثي — الأم", "c_mother_hereditary")
        ti("Consanguinity between parents", "صلة القرابة بين الأب والأم", "c_consanguinity")
        ti("Parents relationship quality", "علاقة الأب والأم ببعض", "c_parents_relation")
        rb("Was the child wanted/planned?", "هل كان الطفل مرغوباً فيه؟",
           ["Yes/نعم", "No/لا", "Unplanned/غير مخطط"], "c_wanted")
        rb("Was child's gender desired?", "هل نوع الطفل كان مرغوباً فيه؟",
           ["Yes/نعم", "No/لا", "Didn't matter/لا فرق"], "c_gender_desired")
        nav(1, 3)

    elif step == 3:
        sec("Brothers and Sisters", "الإخوة والأخوات")
        siblings = []
        for i in range(1, 5):
            st.markdown(f"**Sibling {i} / الأخ/الأخت {i}**")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: g = st.text_input("", key=f"c_sib_g_{i}", placeholder="Gender/النوع", label_visibility="collapsed")
            with c2: n = st.text_input("", key=f"c_sib_n_{i}", placeholder="Name/الاسم", label_visibility="collapsed")
            with c3: a = st.text_input("", key=f"c_sib_a_{i}", placeholder="Age/السن", label_visibility="collapsed")
            with c4: e = st.text_input("", key=f"c_sib_e_{i}", placeholder="Education/التعليم", label_visibility="collapsed")
            with c5: nt = st.text_input("", key=f"c_sib_nt_{i}", placeholder="Notes/ملاحظات", label_visibility="collapsed")
            if n: siblings.append({"gender": g, "name": n, "age": a, "edu": e, "notes": nt})
        st.session_state["c_siblings"] = siblings
        ti("Sibling relationship with each other", "علاقة الأخوة ببعض", "c_sibling_rel")
        rb("Do siblings attend same school?", "هل الأخوة في نفس المدرسة؟",
           ["Yes/نعم", "No/لا", "N/A"], "c_same_school")
        nav(2, 4)

    elif step == 4:
        sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
        ti("Onset — Since when?", "متى بدأت الأعراض؟", "c_onset")
        ta("Chief Complaints (C/O)", "الشكاوى الرئيسية", "c_complaints", 120)
        ta("History of Presenting Illness (HPI)", "تاريخ المرض الحالي بالتفصيل", "c_hpi", 250)
        nav(3, 5)

    elif step == 5:
        sec("Past History", "التاريخ المرضي السابق")
        ta("Previous illnesses / hospitalizations / fever ≥40°C / head trauma / convulsions",
           "الأمراض السابقة / دخول المستشفى / حرارة ≥40 / ارتطام رأس / تشنجات", "c_past_history", 120)
        sec("Family History", "التاريخ العائلي")
        ta("Psychiatric, neurological illness, MR or epilepsy in family",
           "أمراض نفسية أو عصبية أو إعاقة أو صرع في الأسرة", "c_family_history", 100)
        nav(4, 6)

    elif step == 6:
        sec("Investigations", "الفحوصات")
        ta("CT, MRI, EEG, IQ tests (SB5, CARS score), who ordered/reviewed",
           "أشعة مقطعية، رنين، رسم مخ، اختبارات ذكاء (SB5, CARS)، من طلبها ومن شافها", "c_investigations", 100)
        sec("Operations and Surgeries", "العمليات والجراحات")
        ta("Previous surgeries", "العمليات الجراحية السابقة", "c_surgeries", 60)
        sec("Extra Clinical / إضافي")
        c1, c2 = st.columns(2)
        with c1:
            rb("Sleep / النوم", "النوم", ["Normal/طبيعي", "Insomnia/أرق", "Hypersomnia/نوم زيادة", "Disrupted/متقطع"], "c_sleep")
            rb("Appetite / الشهية", "الشهية", ["Normal/طبيعي", "Decreased/قلت", "Increased/زادت"], "c_appetite")
        with c2:
            ti("Punishment methods used", "طرق العقاب المستخدمة", "c_punishment")
            ti("Reaction to stress", "رد الفعل تجاه الضغوط", "c_stress_reaction")
        ta("Current therapy sessions (speech, skills, etc.)",
           "الجلسات الحالية (تخاطب، تنمية مهارات...)", "c_therapy", 60)
        ta("Additional notes / ملاحظات إضافية", "ملاحظات إضافية", "c_extra_notes", 80)
        nav(5, 7)

    elif step == 7:
        sec("Child Clinical Checklist", "قائمة التدقيق السريري للأطفال")
        st.caption("Answer Yes / No for each item and add notes where relevant / أجب بنعم أو لا وأضف ملاحظات")

        checklist_items = [
            ("Consanguinity between parents", "القرابة بين الأب والأم"),
            ("Was the child wanted / planned?", "هل الطفل كان مرغوباً فيه؟"),
            ("Was the child's gender desired by parents?", "هل نوع الطفل كان مرغوباً فيه؟"),
            ("Motor & cognitive developmental history", "تاريخ النمو الحركي والمعرفي"),
            ("Toilet training age & punishment methods", "سن تدريب دورة المياه وطرق العقاب"),
            ("Siblings at same/different school? Sibling relationship?", "الأخوة في نفس المدرسة؟ علاقتهم ببعض؟"),
            ("Full prenatal / natal / postnatal history", "تاريخ الحمل كامل: قبل/أثناء/بعد الولادة"),
            ("Birth type (natural/CS), forceps/vacuum, incubator, jaundice", "نوع الولادة، جفت/شفاط، حضانة، صفراء"),
            ("Problems during pregnancy / late pregnancy age", "مشاكل أثناء الحمل / حمل في سن متأخر"),
            ("Family members with psychiatric illness, MR, or epilepsy", "أقارب لديهم مشكلة نفسية أو إعاقة أو صرع"),
            ("Reaction to stress / punishment methods (especially physical)", "رد الفعل تجاه الضغوط / طرق العقاب"),
            ("If seizures: document doctors and treatments", "في حالة تشنجات: الأطباء والعلاجات"),
            ("High fever (≥40°C) / hospitalization", "ارتفاع حرارة ≥40 درجة / دخول مستشفى"),
            ("Head trauma: location, vomiting, excess/no sleep", "ارتطام الرأس: مكانه، قيء، نوم زيادة أو عدم نوم"),
            ("Convulsions / post-vaccine complications (esp. MMR at 18m)", "تشنجات / مضاعفات بعد تطعيم MMR عند سنة ونصف"),
            ("Cognitive distinctions: attention vs concentration vs comprehension", "التفرقة: انتباه، تركيز، إدراك، فهم"),
            ("Current therapy sessions (speech, skills development)", "جلسات تخاطب / تنمية مهارات"),
            ("Death of a sibling: details, child's age at time, reaction", "وفاة أحد الأخوة: التفاصيل، عمر الطفل، رد فعله"),
            ("Investigations: who ordered / who reviewed? (CT, MRI, SB5, CARS)", "الفحوصات: من طلبها ومن راجعها؟"),
        ]

        checklist_results = {}
        for en, ar in checklist_items:
            col1, col2, col3 = st.columns([3, 1, 3])
            with col1:
                st.markdown(f"**{en}**")
                st.markdown(f"*{ar}*")
            with col2:
                chk_key = f"chk_{en[:20]}"
                chk_opts = ["Yes/نعم", "No/لا", "N/A"]
                if chk_key not in st.session_state:
                    st.session_state[chk_key] = "N/A"
                chk_idx = chk_opts.index(st.session_state[chk_key]) if st.session_state[chk_key] in chk_opts else 2
                ans = st.radio("", chk_opts, index=chk_idx,
                               key=chk_key, horizontal=False, label_visibility="collapsed")
            with col3:
                chk_note_key = f"chk_note_{en[:20]}"
                if chk_note_key not in st.session_state:
                    st.session_state[chk_note_key] = ""
                note = st.text_input("Notes", key=chk_note_key,
                                     placeholder="Notes / ملاحظات", label_visibility="collapsed")
            checklist_results[en] = {"ar": ar, "answer": ans, "notes": note}
            st.divider()

        st.session_state["c_checklist"] = checklist_results
        nav(6, final=True)

# ════════════════════════════════════════════════════════
#  GENERATE REPORT
# ════════════════════════════════════════════════════════
if st.session_state.get("generate"):
    st.session_state.generate = False
    s = st.session_state

    if sheet_type == "adult":
        siblings = s.get("a_siblings", [])
        sibling_text = "\n".join([
            f"  {i+1}. {sb['name']} | {sb['gender']} | Age: {sb['age']} | {sb['edu']} | Notes: {sb['notes']}"
            for i, sb in enumerate(siblings)
        ]) or "لا يوجد بيانات / No data"

        data_block = f"""
=== ADULT HISTORY SHEET ===
Patient Name / الاسم: {sv('a_name')}
Age / السن: {sv('a_age')}
Gender / النوع: {sv('a_gender')}
Date / التاريخ: {sv('a_taken_date')}
History by / الأخصائي: {history_by or '—'}
History Type / نوع التاريخ: {sv('a_history_type')}
Phone / الهاتف: {sv('a_phone')}
Referral Source / مصدر الإحالة: {sv('a_referral')}
Occupation / الوظيفة: {sv('a_occupation')}
Education / التعليم: {sv('a_education')}
Social Status / الحالة الاجتماعية: {sv('a_social_status')}
Hobbies / الهوايات: {sv('a_hobbies')}
Smoking / التدخين: {sv('a_smoking')}

--- FAMILY / الأسرة ---
Father / الأب: {sv('a_father_name')} | Age: {sv('a_father_age')} | Occ: {sv('a_father_occ')}
Mother / الأم: {sv('a_mother_name')} | Age: {sv('a_mother_age')} | Occ: {sv('a_mother_occ')}
Consanguinity / صلة القرابة: {sv('a_consanguinity')}
Chronic illness / مرض مزمن: {sv('a_chronic_illness')}

--- MARRIAGE / الزواج ---
Spouse / الزوج-الزوجة: {sv('a_spouse_name')} | Age: {sv('a_spouse_age')} | Occ: {sv('a_spouse_occ')}
Marriage Duration / فترة الزواج: {sv('a_marriage_duration')}
Engagement / الخطوبة: {sv('a_engagement')}
Katb Ketab / كتب كتاب: {sv('a_katb_ketab')}
Pre-marriage relation / العلاقة قبل الزواج: {sv('a_pre_marriage_rel')}
Number of children / عدد الأبناء: {sv('a_num_children')}

--- SIBLINGS / الأخوة ---
{sibling_text}

--- COMPLAINTS & HPI / الشكاوى والتاريخ ---
Onset / بداية الأعراض: {sv('a_onset')}
Chief Complaints / الشكاوى: {sv('a_complaints')}
HPI / تاريخ المرض الحالي: {sv('a_hpi')}

--- DRUG HISTORY / الأدوية ---
{sv('a_drug_history')}

--- PAST HISTORY / التاريخ السابق ---
{sv('a_past_history')}

--- FAMILY HISTORY / التاريخ العائلي ---
{sv('a_family_history')}

--- INVESTIGATIONS / الفحوصات ---
{sv('a_investigations')}

--- SURGERIES / الجراحات ---
{sv('a_surgeries')}

--- CLINICAL ASSESSMENT / التقييم السريري ---
Sleep / النوم: {sv('a_sleep')}
Appetite / الشهية: {sv('a_appetite')}
Suicidal ideation / أفكار انتحارية: {sv('a_suicidal')}
Substance use / تعاطي مواد: {sv('a_substance')} — {sv('a_substance_details')}
Additional notes / ملاحظات: {sv('a_extra_notes')}
"""
        patient_name = sv('a_name', 'Patient')

    else:
        siblings = s.get("c_siblings", [])
        sibling_text = "\n".join([
            f"  {i+1}. {sb['name']} | {sb['gender']} | Age: {sb['age']} | {sb['edu']} | Notes: {sb['notes']}"
            for i, sb in enumerate(siblings)
        ]) or "لا يوجد بيانات / No data"

        checklist = s.get("c_checklist", {})
        chk_text = "\n".join([
            f"  • {en} / {v['ar']}: {v['answer']} | Notes: {v['notes'] or '—'}"
            for en, v in checklist.items()
        ]) or "—"

        data_block = f"""
=== CHILD HISTORY SHEET ===
Child Name / الاسم: {sv('c_name')}
Age / السن: {sv('c_age')}
Gender / النوع: {sv('c_gender')}
Date / التاريخ: {sv('c_taken_date')}
History by / الأخصائي: {history_by or '—'}
Phone / الهاتف: {sv('c_phone')}
Lives with / يعيش مع: {sv('c_lives_with')}
School / المدرسة: {sv('c_school_name')} | Grade: {sv('c_grade')}
Academic performance / المستوى الدراسي: {sv('c_academic')}
Daily screen time / وقت الشاشة: {sv('c_screen_time')}

--- DEVELOPMENTAL MILESTONES / مراحل النمو ---
Pregnancy / الحمل: {sv('c_pregnancy')}
Birth type / نوع الولادة: {sv('c_birth')}
Birth complications / مضاعفات الولادة: {sv('c_birth_comp')}
Incubator/Jaundice / حضانة/صفراء: {sv('c_incubator')}
Breastfeeding / الرضاعة: {sv('c_breastfeeding')}
Weaning / الفطام: {sv('c_weaning')}
Motor development / الحركة: {sv('c_motor')}
Teething / التسنين: {sv('c_teething')}
Speech / الكلام: {sv('c_speech')}
Toilet training / دورة المياه: {sv('c_toilet')}
Vaccinations / التطعيمات: {sv('c_vaccinations')}
Post-vaccine complications / مضاعفات التطعيم: {sv('c_vacc_comp')}
Developmental notes / ملاحظات: {sv('c_dev_notes')}

--- FAMILY / الأسرة ---
Father / الأب: {sv('c_father_name')} | Age: {sv('c_father_age')} | Occ: {sv('c_father_occ')} | Hereditary: {sv('c_father_hereditary')}
Mother / الأم: {sv('c_mother_name')} | Age: {sv('c_mother_age')} | Occ: {sv('c_mother_occ')} | Hereditary: {sv('c_mother_hereditary')}
Consanguinity / القرابة: {sv('c_consanguinity')}
Parents relationship / علاقة الوالدين: {sv('c_parents_relation')}
Was child wanted? / هل كان مرغوباً فيه: {sv('c_wanted')}
Gender desired? / هل النوع كان مرغوباً: {sv('c_gender_desired')}

--- SIBLINGS / الأخوة ---
{sibling_text}
Sibling relationship / علاقة الأخوة: {sv('c_sibling_rel')}
Same school? / نفس المدرسة: {sv('c_same_school')}

--- COMPLAINTS & HPI / الشكاوى ---
Onset / البداية: {sv('c_onset')}
Chief Complaints / الشكاوى: {sv('c_complaints')}
HPI / تاريخ المرض: {sv('c_hpi')}

--- PAST HISTORY / التاريخ السابق ---
{sv('c_past_history')}

--- FAMILY HISTORY / التاريخ العائلي ---
{sv('c_family_history')}

--- INVESTIGATIONS / الفحوصات ---
{sv('c_investigations')}

--- SURGERIES / الجراحات ---
{sv('c_surgeries')}

--- CLINICAL ASSESSMENT / التقييم ---
Sleep / النوم: {sv('c_sleep')}
Appetite / الشهية: {sv('c_appetite')}
Punishment methods / طرق العقاب: {sv('c_punishment')}
Reaction to stress / رد الفعل: {sv('c_stress_reaction')}
Therapy sessions / الجلسات: {sv('c_therapy')}
Additional notes / ملاحظات: {sv('c_extra_notes')}

--- CHILD CHECKLIST / قائمة التدقيق ---
{chk_text}
"""
        patient_name = sv('c_name', 'Patient')

    prompt = f"""أنت طبيب نفسي استشاري أول. بناءً على بيانات التاريخ المرضي المفصلة أدناه، اكتب تقريراً سريرياً شاملاً باللغتين العربية والإنجليزية.

IMPORTANT RULES:
1. Use ONLY the actual data provided below — do NOT invent or assume anything
2. Every section must be written TWICE: first in Arabic, then in English
3. If a field says "—" it means no data was provided — mention it briefly as "لم يُذكر / Not reported"
4. The summary must reflect the ACTUAL patient data, not generic descriptions

التقرير يجب أن يتكون من جزأين:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الجزء الأول / PART 1 — الملخص المهني / PROFESSIONAL SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

اكتب كل قسم بالعربية أولاً ثم بالإنجليزية مباشرة بعده:

** نظرة عامة عن المريض / Patient Overview **
[Arabic paragraph about this specific patient]
[English paragraph about this specific patient]

** الشكوى الرئيسية وتاريخ المرض / Chief Complaint & HPI **
[Arabic - use exact data from HPI and complaints fields]
[English - use exact data from HPI and complaints fields]

** الخلفية الشخصية والاجتماعية / Personal & Social Background **
[Arabic - use occupation, education, social status, hobbies, smoking data]
[English - use occupation, education, social status, hobbies, smoking data]

** الخلفية العائلية / Family Background **
[Arabic - use actual family data provided]
[English - use actual family data provided]

** التاريخ الطبي والدوائي / Medical & Drug History **
[Arabic - use past history, drug history, investigations data]
[English - use past history, drug history, investigations data]

** الملاحظات السريرية / Clinical Observations **
[Arabic - use sleep, appetite, and other clinical assessment data]
[English - use sleep, appetite, and other clinical assessment data]

** الانطباع العام / Summary Impression **
[Arabic - brief clinical impression based on ALL the data]
[English - brief clinical impression based on ALL the data]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الجزء الثاني / PART 2 — السجل التفصيلي / DETAILED RECORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

قدم جميع البيانات في جدول بثلاثة أعمدة:
| Field (English) | الحقل (عربي) | Response / الإجابة |

أبقِ الكلمات كما كتبها الأخصائي تماماً. إذا كانت عربية تبقى عربية، إذا كانت إنجليزية تبقى إنجليزية.
اشمل كل حقل من البيانات أدناه بدون استثناء.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORY DATA:
{data_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
History taken by: {history_by or '—'} | Sheet type: {sheet_type.upper()}
"""

    with st.spinner("Generating report... / جاري إنشاء التقرير..."):
        try:
            client = Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000
            )
            st.session_state.report_text = response.choices[0].message.content
            st.session_state.patient_name_final = patient_name
        except Exception as e:
            st.error(f"Report generation error: {str(e)}")

# ════════════════════════════════════════════════════════
#  BUILD DOCX
# ════════════════════════════════════════════════════════
def build_docx(report_text, patient_name, sheet_type, history_by, logo_path, doctor):
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
        for side in ('top', 'left', 'bottom', 'right'):
            b = OxmlElement(f'w:{side}')
            b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '12')
            b.set(qn('w:space'), '24'); b.set(qn('w:color'), '1B2A4A')
            pgBorders.append(b)
        sectPr.append(pgBorders)

    # Page numbers in footer
    for section in doc.sections:
        footer = section.footer
        para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        para.clear(); para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run()
        run.font.size = Pt(9); run.font.color.rgb = CLINIC_BLUE
        for tag, text in [('begin', None), (None, ' PAGE '), ('end', None)]:
            if tag:
                el = OxmlElement('w:fldChar'); el.set(qn('w:fldCharType'), tag); run._r.append(el)
            else:
                instr = OxmlElement('w:instrText'); instr.text = text; run._r.append(instr)

    # Logo + title (first page only)
    p_top = doc.add_paragraph()
    p_top.paragraph_format.space_before = Pt(0); p_top.paragraph_format.space_after = Pt(6)
    if os.path.exists(logo_path):
        p_top.add_run().add_picture(logo_path, width=Inches(1.2))
    r_title = p_top.add_run("   Clinical History Report")
    r_title.font.name = "Arial"; r_title.font.size = Pt(20)
    r_title.font.bold = True; r_title.font.color.rgb = CLINIC_BLUE
    pPr = p_top._p.get_or_add_pPr(); pBdr = OxmlElement('w:pBdr')
    bot = OxmlElement('w:bottom'); bot.set(qn('w:val'), 'single')
    bot.set(qn('w:sz'), '8'); bot.set(qn('w:space'), '4'); bot.set(qn('w:color'), '1A5CB8')
    pBdr.append(bot); pPr.append(pBdr)

    # Patient info line
    doc.add_paragraph()
    p_info = doc.add_paragraph()
    for label, val in [("Patient: ", patient_name), ("   |   Type: ", sheet_type.capitalize()),
                        ("   |   History by: ", history_by or "—")]:
        r = p_info.add_run(label); r.bold = True
        r.font.size = Pt(11); r.font.name = "Arial"; r.font.color.rgb = CLINIC_BLUE
        r2 = p_info.add_run(val); r2.font.size = Pt(11); r2.font.name = "Arial"
    doc.add_paragraph()

    # Report body
    in_table = False
    table = None
    for line in report_text.split('\n'):
        ls = line.strip()
        if not ls:
            if not in_table: doc.add_paragraph()
            continue

        # Table rows
        if ls.startswith('|') and ls.endswith('|'):
            cells = [c.strip() for c in ls.strip('|').split('|')]
            if all(set(c) <= set('-: ') for c in cells): continue
            if not in_table:
                in_table = True
                table = doc.add_table(rows=0, cols=3)
                table.style = 'Table Grid'
            row = table.add_row()
            for i, ct in enumerate(cells[:3]):
                cell = row.cells[i]; cell.text = ct
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(10); run.font.name = "Arial"
            continue
        else:
            in_table = False; table = None

        if ls.startswith('━'):
            p = doc.add_paragraph()
            pPr2 = p._p.get_or_add_pPr(); pBdr2 = OxmlElement('w:pBdr')
            b2 = OxmlElement('w:bottom'); b2.set(qn('w:val'), 'single')
            b2.set(qn('w:sz'), '4'); b2.set(qn('w:space'), '1'); b2.set(qn('w:color'), '1A5CB8')
            pBdr2.append(b2); pPr2.append(pBdr2)
            continue

        if ls.startswith('**') and ls.endswith('**'):
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(10)
            r = p.add_run(ls.strip('*').strip())
            r.bold = True; r.font.size = Pt(12); r.font.name = "Arial"; r.font.color.rgb = CLINIC_BLUE
            pPr3 = p._p.get_or_add_pPr(); pBdr3 = OxmlElement('w:pBdr')
            b3 = OxmlElement('w:bottom'); b3.set(qn('w:val'), 'single')
            b3.set(qn('w:sz'), '4'); b3.set(qn('w:space'), '1'); b3.set(qn('w:color'), '1A5CB8')
            pBdr3.append(b3); pPr3.append(pBdr3)
            continue

        if ls.startswith('PART ') or 'PROFESSIONAL SUMMARY' in ls or 'DETAILED RECORD' in ls or 'الملخص المهني' in ls or 'السجل التفصيلي' in ls:
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(14)
            r = p.add_run(ls); r.bold = True; r.font.size = Pt(13)
            r.font.name = "Arial"; r.font.color.rgb = CLINIC_BLUE
            continue

        if ls.startswith('• ') or ls.startswith('- '):
            p = doc.add_paragraph(style='List Bullet')
            r = p.add_run(ls.lstrip('•- ').strip())
            r.font.size = Pt(11); r.font.name = "Arial"
            continue

        p = doc.add_paragraph()
        r = p.add_run(ls); r.font.size = Pt(11); r.font.name = "Arial"

    # Doctor footer
    doc.add_paragraph(); doc.add_paragraph()
    p_sep = doc.add_paragraph()
    pPr_s = p_sep._p.get_or_add_pPr(); pBdr_s = OxmlElement('w:pBdr')
    top_s = OxmlElement('w:top'); top_s.set(qn('w:val'), 'single')
    top_s.set(qn('w:sz'), '6'); top_s.set(qn('w:space'), '1'); top_s.set(qn('w:color'), '1A5CB8')
    pBdr_s.append(top_s); pPr_s.append(pBdr_s)

    p_dr = doc.add_paragraph()
    r_dr = p_dr.add_run(doctor["name"])
    r_dr.bold = True; r_dr.font.size = Pt(12); r_dr.font.name = "Arial"; r_dr.font.color.rgb = CLINIC_BLUE

    for t in ["title1", "title2", "title3", "title4"]:
        p_t = doc.add_paragraph()
        r_t = p_t.add_run(doctor[t]); r_t.font.size = Pt(10); r_t.font.name = "Arial"
        r_t.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
        p_t.paragraph_format.space_before = Pt(0); p_t.paragraph_format.space_after = Pt(0)

    doc.add_paragraph()
    doc.add_paragraph().add_run(f"📍  {doctor['address']}").font.size = Pt(10)
    r_ph = doc.add_paragraph().add_run(f"📞  {doctor['phone']}")
    r_ph.font.size = Pt(10); r_ph.bold = True

    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# ════════════════════════════════════════════════════════
#  DISPLAY REPORT
# ════════════════════════════════════════════════════════
if st.session_state.get("report_text"):
    report_text = st.session_state.report_text
    patient_name = st.session_state.get("patient_name_final", "Patient")

    st.divider()
    st.markdown("### ✅ Report Generated / تم إنشاء التقرير")
    st.text_area("", value=report_text, height=500, label_visibility="collapsed")

    filename = f"{patient_name.replace(' ', '_')}_HistorySheet.docx"

    col1, col2, col3 = st.columns(3)

    with col1:
        docx_buf = build_docx(report_text, patient_name, sheet_type, history_by, LOGO_PATH, DOCTOR)
        st.download_button(
            label="📄 Download .docx",
            data=docx_buf,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    with col2:
        if st.button("📧 Send to Email / إرسال بالبريد"):
            try:
                docx_buf2 = build_docx(report_text, patient_name, sheet_type, history_by, LOGO_PATH, DOCTOR)
                msg = MIMEMultipart()
                msg['From'] = GMAIL_USER
                msg['To'] = RECIPIENT_EMAIL
                msg['Subject'] = f"History Report — {patient_name}"
                msg.attach(MIMEText(
                    f"Please find attached the history report for: {patient_name}\n"
                    f"Sheet type: {sheet_type.capitalize()}\n"
                    f"History taken by: {history_by or '—'}", 'plain'))
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(docx_buf2.read())
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
