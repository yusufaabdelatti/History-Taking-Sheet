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
.sec-header{font-size:16px;font-weight:700;color:#1A5CB8;margin-top:18px;margin-bottom:6px;
            border-bottom:2px solid #1A5CB8;padding-bottom:4px}
.step-box{background:#f0f6ff;border-radius:8px;padding:10px 16px;margin-bottom:16px;
          font-size:13px;color:#1A5CB8;font-weight:500}
.qlabel{font-size:13.5px;font-weight:500;margin-bottom:4px}
.qlabel-ar{font-size:13px;color:#555;direction:rtl;text-align:right;margin-bottom:6px}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ──
RECIPIENT_EMAIL = "yusuf.a.abdelatti@gmail.com"
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
    gmail_user = st.text_input("Gmail Address (sender)", placeholder="yourname@gmail.com")
    gmail_pass = st.text_input("Gmail App Password", type="password", placeholder="xxxx xxxx xxxx xxxx")
    st.caption("Use Gmail App Password — [how to get one](https://support.google.com/accounts/answer/185833)")
    st.divider()
    history_by = st.text_input("Psychologist Name / اسم الأخصائي", value=st.session_state.get("history_by", ""))

st.markdown('<div class="main-title">🧠 History Taking Sheet</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Dr. Hany Elhennawy Clinic — Neuro-Psychiatry & Neurofeedback</div>', unsafe_allow_html=True)

# ── HELPERS ──
def sec(en, ar=""):
    st.markdown(f'<div class="sec-header">{en}{" / " + ar if ar else ""}</div>', unsafe_allow_html=True)

def qlabel(en, ar):
    st.markdown(f'<div class="qlabel">{en}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="qlabel-ar">{ar}</div>', unsafe_allow_html=True)

def mc(en, ar, options, key, multi=False, note_key=None):
    """Multiple choice with optional notes box"""
    qlabel(en, ar)
    if multi:
        val = st.multiselect("", options, default=st.session_state.get(key, []),
                             key=key, label_visibility="collapsed")
    else:
        prev = st.session_state.get(key, options[0])
        if prev not in options:
            prev = options[0]
        val = st.radio("", options, index=options.index(prev),
                       key=key, horizontal=True, label_visibility="collapsed")
    if note_key:
        note = st.text_input("📝 Additional notes / ملاحظات", key=note_key,
                             label_visibility="collapsed",
                             placeholder="Additional notes / ملاحظات إضافية...")
    return val

def ti(en, ar, key, placeholder=""):
    qlabel(en, ar)
    return st.text_input("", key=key, placeholder=placeholder, label_visibility="collapsed")

def ta(en, ar, key, height=100):
    qlabel(en, ar)
    return st.text_area("", key=key, height=height, label_visibility="collapsed")

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

def sv(key, default="—"):
    v = st.session_state.get(key, "")
    if isinstance(v, list):
        return ", ".join(v) if v else default
    return str(v).strip() if v and str(v).strip() else default

# ── SHEET TYPE SELECTION ──
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
    steps = ["Personal Details", "Family Details", "Marriage Details",
             "Siblings", "Complaints & HPI", "Drug / Past / Family Hx",
             "Investigations & Surgeries", "Clinical Assessment"]
else:
    steps = ["Personal Details", "Family Details", "Siblings",
             "Complaints & HPI", "Past / Family History",
             "Investigations & Surgeries", "Child Checklist"]

total = len(steps)
st.markdown(f'<div class="step-box">Step {step} of {total}: {steps[step-1]}</div>', unsafe_allow_html=True)
st.progress(step / total)

# ════════════════════════════════════════════════════════════════
#  ADULT SHEET
# ════════════════════════════════════════════════════════════════
if sheet_type == "adult":

    # ── STEP 1: PERSONAL DETAILS ──
    if step == 1:
        sec("Personal Details", "البيانات الشخصية")
        ti("Taken Date / تاريخ الجلسة", "تاريخ الجلسة", "taken_date", str(date.today()))
        ti("History Type / نوع التاريخ", "نوع التاريخ", "history_type", "Initial / أولي")
        st.divider()
        ti("Full Name / الاسم", "الاسم الكامل", "name")
        ti("Age / السن", "السن", "age")
        mc("Gender / النوع", "النوع", ["Male / ذكر", "Female / أنثى"], "gender", note_key="gender_note")
        mc("Social Status / الحالة الاجتماعية", "الحالة الاجتماعية",
           ["Single / أعزب", "Married / متزوج", "Divorced / مطلق", "Widowed / أرمل"], "social_status", note_key="social_note")
        mc("Education Level / المستوى التعليمي", "المستوى التعليمي",
           ["Illiterate / أمي", "Primary / ابتدائي", "Preparatory / إعدادي",
            "Secondary / ثانوي", "University / جامعي", "Postgraduate / دراسات عليا"], "education", note_key="edu_note")
        ti("Occupation / Study — الوظيفة / الدراسة", "الوظيفة / الدراسة", "occupation")
        ti("Hobbies / الهوايات", "الهوايات", "hobbies")
        mc("Smoking / التدخين", "التدخين",
           ["Non-smoker / لا يدخن", "Smoker / يدخن", "Ex-smoker / سابقاً"], "smoking", note_key="smoking_note")
        ti("Phone Number / رقم الهاتف", "رقم الهاتف", "phone")
        mc("Referral Source / مصدر الإحالة", "مصدر الإحالة",
           ["Self / ذاتي", "Family / الأسرة", "Physician / طبيب", "Psychologist / أخصائي",
            "School / المدرسة", "Other / أخرى"], "referral", note_key="referral_note")
        nav(None, 2)

    # ── STEP 2: FAMILY DETAILS ──
    elif step == 2:
        sec("Family Details", "بيانات الأسرة")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Father / الأب**")
            ti("Father's Name", "اسم الأب", "father_name")
            ti("Father's Age", "سن الأب", "father_age")
            ti("Father's Occupation", "وظيفة الأب", "father_occ")
            mc("Father alive?", "الأب على قيد الحياة؟",
               ["Alive / حي", "Deceased / متوفي"], "father_alive", note_key="father_alive_note")
        with c2:
            st.markdown("**Mother / الأم**")
            ti("Mother's Name", "اسم الأم", "mother_name")
            ti("Mother's Age", "سن الأم", "mother_age")
            ti("Mother's Occupation", "وظيفة الأم", "mother_occ")
            mc("Mother alive?", "الأم على قيد الحياة؟",
               ["Alive / حية", "Deceased / متوفية"], "mother_alive", note_key="mother_alive_note")
        mc("Consanguinity / صلة القرابة", "هل هناك قرابة بين الأب والأم؟",
           ["No / لا", "First cousins / أبناء عم/خال", "Second cousins / قرابة بعيدة", "Other / أخرى"],
           "consanguinity", note_key="consanguinity_note")
        mc("Chronic illness in family / مرض مزمن في الأسرة", "مرض مزمن في الأسرة",
           ["None / لا يوجد", "Diabetes / سكري", "Hypertension / ضغط",
            "Heart disease / قلب", "Cancer / سرطان", "Other / أخرى"],
           "chronic_illness", multi=True, note_key="chronic_note")
        mc("Parents living together? / الوالدان يعيشان معاً؟", "هل الوالدان يعيشان معاً؟",
           ["Yes / نعم", "Separated / منفصلان", "Divorced / مطلقان", "One deceased / أحدهما متوفي"],
           "parents_together", note_key="parents_together_note")
        nav(1, 3)

    # ── STEP 3: MARRIAGE DETAILS ──
    elif step == 3:
        sec("Marriage Details", "بيانات الزواج")
        ti("Spouse Name / اسم الزوج/الزوجة", "اسم الزوج / الزوجة", "spouse_name")
        ti("Spouse Age / السن", "سن الزوج / الزوجة", "spouse_age")
        mc("Spouse Occupation / الوظيفة", "وظيفة الزوج / الزوجة",
           ["Employed / يعمل", "Unemployed / لا يعمل", "Retired / متقاعد", "Student / طالب"], "spouse_occ", note_key="spouse_occ_note")
        mc("Duration of marriage / فترة الزواج", "فترة الزواج",
           ["< 1 year", "1–5 years", "6–10 years", "11–20 years", "> 20 years"], "marriage_duration", note_key="marriage_dur_note")
        mc("Engagement period / فترة الخطوبة", "فترة الخطوبة",
           ["No engagement / بدون خطوبة", "< 6 months", "6–12 months", "> 1 year"], "engagement", note_key="engagement_note")
        mc("Katb Ketab before marriage / كتب كتاب", "كتب كتاب قبل الزواج",
           ["Yes / نعم", "No / لا", "N/A"], "katb_ketab")
        mc("Relationship quality / جودة العلاقة الزوجية", "طبيعة العلاقة الزوجية",
           ["Stable / مستقرة", "Conflicted / متوترة", "Separated / منفصلان", "N/A"], "marriage_quality", note_key="marriage_quality_note")
        mc("Relationship before marriage / العلاقة قبل الزواج", "العلاقة قبل الزواج",
           ["No prior relationship / لا توجد", "Short acquaintance / تعارف قصير",
            "Long relationship / علاقة طويلة", "Arranged / زواج مرتب"], "pre_marriage_rel", note_key="pre_marriage_note")
        mc("Number of children / عدد الأبناء", "عدد الأبناء",
           ["None / لا يوجد", "1", "2", "3", "4", "5+"], "num_children", note_key="children_note")
        nav(2, 4)

    # ── STEP 4: SIBLINGS ──
    elif step == 4:
        sec("Brothers and Sisters", "الإخوة والأخوات")
        siblings = []
        for i in range(1, 5):
            st.markdown(f"**Sibling {i} / الأخ/الأخت {i}**")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                g = st.selectbox("Gender/النوع", ["—", "Male/ذكر", "Female/أنثى"],
                                 key=f"sib_gender_{i}", label_visibility="collapsed")
            with c2:
                n = st.text_input("Name/الاسم", key=f"sib_name_{i}",
                                  label_visibility="collapsed", placeholder="Name/الاسم")
            with c3:
                a = st.text_input("Age/السن", key=f"sib_age_{i}",
                                  label_visibility="collapsed", placeholder="Age/السن")
            with c4:
                ed = st.selectbox("Education/التعليم",
                                  ["—", "Student/طالب", "Primary/ابتدائي", "Secondary/ثانوي",
                                   "University/جامعي", "Working/يعمل", "N/A"],
                                  key=f"sib_edu_{i}", label_visibility="collapsed")
            with c5:
                notes = st.text_input("Notes/ملاحظات", key=f"sib_notes_{i}",
                                      label_visibility="collapsed", placeholder="Notes/ملاحظات")
            siblings.append({"gender": g, "name": n, "age": a, "edu": ed, "notes": notes})
        st.session_state["siblings"] = siblings
        nav(3, 5)

    # ── STEP 5: COMPLAINTS & HPI ──
    elif step == 5:
        sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
        mc("Complaint onset / بداية الشكاوى", "متى بدأت الأعراض؟",
           ["< 1 month / أقل من شهر", "1–3 months / 1-3 أشهر", "3–6 months / 3-6 أشهر",
            "6–12 months / 6-12 شهر", "1–2 years / 1-2 سنة", "2–5 years / 2-5 سنوات",
            "> 5 years / أكثر من 5 سنوات"], "onset", note_key="onset_note")
        mc("Mode of onset / طريقة البداية", "طريقة البداية",
           ["Sudden / مفاجئ", "Gradual / تدريجي"], "onset_mode", note_key="onset_mode_note")
        mc("Course / مسار المرض", "مسار المرض",
           ["Continuous / مستمر", "Episodic / نوبات", "Improving / يتحسن",
            "Worsening / يتدهور", "Fluctuating / متذبذب"], "course", note_key="course_note")
        mc("Precipitating factor / عامل مُسبِّب", "هل كان هناك حدث مُسبِّب؟",
           ["No clear trigger / لا يوجد", "Stress / ضغوط", "Loss / خسارة أو فقدان",
            "Trauma / صدمة", "Medical illness / مرض عضوي", "Other / أخرى"],
           "precipitant", note_key="precipitant_note")
        ta("Chief Complaints (C/O) — describe in detail", "الشكاوى الرئيسية بالتفصيل", "complaints", 130)
        ta("History of Presenting Illness (HPI)", "تاريخ المرض الحالي", "hpi", 250)
        nav(4, 6)

    # ── STEP 6: DRUG / PAST / FAMILY HX ──
    elif step == 6:
        sec("Drug History", "تاريخ الأدوية")
        mc("Currently on medication? / يتناول أدوية حالياً؟", "يتناول أدوية حالياً؟",
           ["No / لا", "Yes / نعم"], "on_medication", note_key="on_medication_note")
        ta("Medication details (name, dose, duration)", "تفاصيل الأدوية (الاسم، الجرعة، المدة)", "drug_history", 100)
        mc("Compliance / الالتزام بالدواء", "مدى الالتزام بالدواء",
           ["N/A", "Good / جيد", "Poor / ضعيف", "Irregular / غير منتظم"], "compliance", note_key="compliance_note")

        sec("Past History", "التاريخ المرضي السابق")
        mc("Previous psychiatric illness? / مرض نفسي سابق؟", "هل كان هناك مرض نفسي سابق؟",
           ["No / لا", "Yes / نعم"], "prev_psych", note_key="prev_psych_note")
        mc("Previous hospitalization? / دخول مستشفى سابق؟", "هل كان هناك دخول مستشفى؟",
           ["No / لا", "Yes / نعم"], "prev_hosp", note_key="prev_hosp_note")
        mc("Chronic medical illness? / مرض عضوي مزمن؟", "مرض عضوي مزمن؟",
           ["None / لا يوجد", "Diabetes / سكري", "Hypertension / ضغط",
            "Epilepsy / صرع", "Thyroid / غدة درقية", "Other / أخرى"],
           "chronic_medical", multi=True, note_key="chronic_medical_note")
        ta("Past history details", "تفاصيل التاريخ السابق", "past_history", 80)

        sec("Family History", "التاريخ العائلي")
        mc("Psychiatric illness in family? / مرض نفسي في الأسرة؟", "مرض نفسي في الأسرة؟",
           ["No / لا", "Yes / نعم"], "family_psych", note_key="family_psych_note")
        mc("Neurological illness in family? / مرض عصبي في الأسرة؟", "مرض عصبي في الأسرة؟",
           ["No / لا", "Yes — Epilepsy / صرع", "Yes — Other / أخرى"], "family_neuro", note_key="family_neuro_note")
        ta("Family history details", "تفاصيل التاريخ العائلي", "family_history", 80)
        nav(5, 7)

    # ── STEP 7: INVESTIGATIONS & SURGERIES ──
    elif step == 7:
        sec("Investigations", "الفحوصات")
        mc("Investigations done / فحوصات أُجريت", "الفحوصات التي أُجريت",
           ["None / لا يوجد", "Blood tests / تحاليل دم", "EEG / رسم مخ",
            "CT scan / أشعة مقطعية", "MRI / رنين مغناطيسي",
            "Psychological testing / اختبارات نفسية", "Other / أخرى"],
           "investigations", multi=True, note_key="investigations_note")
        ta("Investigation results / نتائج الفحوصات", "نتائج الفحوصات", "investigation_results", 80)

        sec("Operations and Surgeries", "العمليات والجراحات")
        mc("Previous surgeries? / عمليات جراحية سابقة؟", "عمليات جراحية سابقة؟",
           ["No / لا", "Yes / نعم"], "had_surgery", note_key="surgery_note")
        ta("Surgery details / تفاصيل العمليات", "تفاصيل العمليات", "surgeries", 70)
        nav(6, 8)

    # ── STEP 8: CLINICAL ASSESSMENT ──
    elif step == 8:
        sec("Clinical Assessment", "التقييم السريري")
        mc("Sleep pattern / نمط النوم", "نمط النوم",
           ["Normal / طبيعي", "Insomnia / أرق", "Hypersomnia / نوم زيادة",
            "Disrupted / متقطع", "Delayed sleep / تأخر النوم"], "sleep", note_key="sleep_note")
        mc("Appetite / الشهية", "الشهية",
           ["Normal / طبيعي", "Decreased / قلت", "Increased / زادت",
            "Variable / متغيرة"], "appetite", note_key="appetite_note")
        mc("Mood / المزاج", "المزاج العام",
           ["Stable / مستقر", "Depressed / اكتئابي", "Elevated / مرتفع",
            "Anxious / قلق", "Irritable / متهيج", "Variable / متقلب"], "mood", note_key="mood_note")
        mc("Energy level / مستوى الطاقة", "مستوى الطاقة",
           ["Normal / طبيعي", "Low / منخفض", "High / مرتفع"], "energy", note_key="energy_note")
        mc("Concentration / التركيز", "مستوى التركيز",
           ["Good / جيد", "Mildly impaired / ضعيف قليلاً",
            "Moderately impaired / ضعيف بشكل معتدل", "Severely impaired / ضعيف جداً"], "concentration", note_key="concentration_note")
        mc("Suicidal ideation / أفكار انتحارية", "أفكار انتحارية",
           ["None / لا", "Passive ideation / أفكار سلبية",
            "Active ideation / أفكار نشطة", "Previous attempt / محاولة سابقة"], "suicidal", note_key="suicidal_note")
        mc("Substance use / تعاطي مواد", "تعاطي مواد",
           ["None / لا", "Alcohol / كحول", "Cannabis / حشيش",
            "Stimulants / منبهات", "Other / أخرى"], "substance", multi=True, note_key="substance_note")
        mc("Insight / البصيرة المرضية", "مدى إدراك المريض لحالته",
           ["Good / جيدة", "Partial / جزئية", "Poor / ضعيفة"], "insight", note_key="insight_note")
        ta("Additional notes / ملاحظات إضافية", "ملاحظات إضافية", "extra_notes", 100)
        nav(7, final=True)


# ════════════════════════════════════════════════════════════════
#  CHILD SHEET
# ════════════════════════════════════════════════════════════════
else:

    # ── STEP 1: PERSONAL DETAILS ──
    if step == 1:
        sec("Personal Details", "البيانات الشخصية")
        ti("Taken Date / تاريخ الجلسة", "تاريخ الجلسة", "taken_date", str(date.today()))
        ti("Child's Full Name / اسم الطفل", "اسم الطفل الكامل", "name")
        ti("Age / السن", "السن", "age")
        mc("Gender / النوع", "النوع", ["Male / ذكر", "Female / أنثى"], "gender")
        mc("Who does child live with? / الطفل يعيش مع", "الطفل يعيش مع",
           ["Both parents / الوالدان", "Mother only / الأم فقط", "Father only / الأب فقط",
            "Grandparents / الأجداد", "Other / أخرى"], "lives_with", note_key="lives_with_note")
        ti("Phone / الهاتف", "رقم الهاتف", "phone")
        mc("Referral source / مصدر الإحالة", "مصدر الإحالة",
           ["Family / الأسرة", "Physician / طبيب", "School / المدرسة",
            "Psychologist / أخصائي", "Self / ذاتي", "Other / أخرى"],
           "referral", note_key="referral_note")

        sec("School & Academic", "المدرسة والمستوى الدراسي")
        ti("School Name / اسم المدرسة", "اسم المدرسة", "school_name")
        mc("Grade / الصف", "الصف الدراسي",
           ["Preschool / ما قبل المدرسة", "Grade 1 / أول ابتدائي", "Grade 2 / ثاني",
            "Grade 3 / ثالث", "Grade 4 / رابع", "Grade 5 / خامس", "Grade 6 / سادس",
            "Preparatory / إعدادي", "Secondary / ثانوي", "Other / أخرى"], "grade", note_key="grade_note")
        mc("Academic performance / المستوى الدراسي", "المستوى الدراسي",
           ["Excellent / ممتاز", "Good / جيد", "Average / متوسط",
            "Below average / أقل من المتوسط", "Weak / ضعيف", "Not enrolled / غير ملتحق"],
           "academic", note_key="academic_note")
        mc("Screen time daily / وقت الشاشة اليومي", "وقت الشاشة اليومي",
           ["< 1 hour", "1–2 hours", "2–4 hours", "4–6 hours", "> 6 hours"], "screen_time", note_key="screen_note")

        sec("Developmental Milestones", "مراحل النمو")
        mc("Pregnancy / الحمل", "الحمل",
           ["Normal / طبيعي", "Complicated / مع مضاعفات", "Unknown / غير معروف"], "pregnancy", note_key="pregnancy_note")
        mc("Birth type / نوع الولادة", "نوع الولادة",
           ["Normal vaginal / طبيعي", "C-section / قيصري"], "birth_type", note_key="birth_type_note")
        mc("Birth complications / مضاعفات الولادة", "مضاعفات الولادة",
           ["None / لا يوجد", "Forceps / جفت", "Vacuum / شفاط",
            "NICU admission / حضانة", "Jaundice / صفراء", "Other / أخرى"],
           "birth_comp", multi=True, note_key="birth_comp_note")
        mc("Breastfeeding / الرضاعة", "الرضاعة",
           ["Breastfed / طبيعية", "Formula / صناعية", "Mixed / مختلطة"], "breastfeeding", note_key="bf_note")
        ti("Weaning age / سن الفطام", "سن الفطام", "weaning")
        mc("Motor development / النمو الحركي", "النمو الحركي",
           ["Normal / طبيعي", "Delayed / متأخر", "Unknown / غير معروف"], "motor_dev", note_key="motor_note")
        mc("Speech development / نمو الكلام", "نمو الكلام",
           ["Normal / طبيعي", "Delayed / متأخر", "Absent / غائب", "Regressed / تراجع"],
           "speech", note_key="speech_note")
        ti("Teething age / سن التسنين", "سن التسنين", "teething")
        ti("Toilet training age / سن تدريب دورة المياه", "سن تدريب دورة المياه", "toilet_training")
        mc("Vaccinations / التطعيمات", "التطعيمات",
           ["Complete / مكتملة", "Incomplete / غير مكتملة", "Unknown / غير معروف"],
           "vaccinations", note_key="vacc_note")
        ta("Developmental notes / ملاحظات النمو", "ملاحظات إضافية عن النمو", "dev_notes", 80)
        nav(None, 2)

    # ── STEP 2: FAMILY DETAILS ──
    elif step == 2:
        sec("Family Details", "بيانات الأسرة")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Father / الأب**")
            ti("Father's Name", "اسم الأب", "father_name")
            ti("Father's Age", "سن الأب", "father_age")
            ti("Father's Occupation", "وظيفة الأب", "father_occ")
            mc("Father alive?", "الأب على قيد الحياة؟",
               ["Alive / حي", "Deceased / متوفي"], "father_alive", note_key="father_alive_note")
            ti("Father hereditary illness", "مرض وراثي — الأب", "father_hereditary")
        with c2:
            st.markdown("**Mother / الأم**")
            ti("Mother's Name", "اسم الأم", "mother_name")
            ti("Mother's Age", "سن الأم", "mother_age")
            ti("Mother's Occupation", "وظيفة الأم", "mother_occ")
            mc("Mother alive?", "الأم على قيد الحياة؟",
               ["Alive / حية", "Deceased / متوفية"], "mother_alive", note_key="mother_alive_note")
            ti("Mother hereditary illness", "مرض وراثي — الأم", "mother_hereditary")
        mc("Consanguinity / القرابة", "هل هناك قرابة بين الأب والأم؟",
           ["No / لا", "First cousins / أبناء عم/خال",
            "Second cousins / قرابة بعيدة", "Other / أخرى"],
           "consanguinity", note_key="consanguinity_note")
        mc("Parents relationship / العلاقة الزوجية", "العلاقة بين الوالدين",
           ["Stable / مستقرة", "Conflicted / متوترة",
            "Separated / منفصلان", "Divorced / مطلقان",
            "One deceased / أحدهما متوفي"], "parents_relation", note_key="parents_relation_note")
        mc("Siblings at same school? / الأخوة في نفس المدرسة؟", "الأخوة في نفس المدرسة؟",
           ["Yes / نعم", "No / لا", "N/A / لا ينطبق"], "same_school", note_key="same_school_note")
        mc("Sibling relationship / علاقة الأخوة ببعض", "طبيعة العلاقة بين الأخوة",
           ["Good / جيدة", "Conflicted / متوترة", "Isolated / منعزل عنهم", "N/A"],
           "sibling_rel", note_key="sibling_rel_note")
        nav(1, 3)

    # ── STEP 3: SIBLINGS ──
    elif step == 3:
        sec("Brothers and Sisters", "الإخوة والأخوات")
        siblings = []
        for i in range(1, 5):
            st.markdown(f"**Sibling {i} / الأخ/الأخت {i}**")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                g = st.selectbox("Gender/النوع", ["—", "Male/ذكر", "Female/أنثى"],
                                 key=f"sib_gender_{i}", label_visibility="collapsed")
            with c2:
                n = st.text_input("Name/الاسم", key=f"sib_name_{i}",
                                  label_visibility="collapsed", placeholder="Name/الاسم")
            with c3:
                a = st.text_input("Age/السن", key=f"sib_age_{i}",
                                  label_visibility="collapsed", placeholder="Age/السن")
            with c4:
                ed = st.selectbox("Education/التعليم",
                                  ["—", "Preschool/روضة", "Primary/ابتدائي",
                                   "Preparatory/إعدادي", "Secondary/ثانوي",
                                   "University/جامعي", "Working/يعمل", "N/A"],
                                  key=f"sib_edu_{i}", label_visibility="collapsed")
            with c5:
                notes = st.text_input("Notes/ملاحظات", key=f"sib_notes_{i}",
                                      label_visibility="collapsed", placeholder="Notes/ملاحظات")
            siblings.append({"gender": g, "name": n, "age": a, "edu": ed, "notes": notes})
        st.session_state["siblings"] = siblings
        nav(2, 4)

    # ── STEP 4: COMPLAINTS & HPI ──
    elif step == 4:
        sec("Complaints & History of Presenting Illness", "الشكاوى وتاريخ المرض الحالي")
        mc("Complaint onset / بداية الشكاوى", "متى بدأت الأعراض؟",
           ["< 1 month", "1–3 months", "3–6 months",
            "6–12 months", "1–2 years", "2–5 years", "> 5 years"],
           "onset", note_key="onset_note")
        mc("Mode of onset / طريقة البداية", "طريقة البداية",
           ["Sudden / مفاجئ", "Gradual / تدريجي"], "onset_mode", note_key="onset_mode_note")
        mc("Course / مسار الحالة", "مسار الحالة",
           ["Continuous / مستمر", "Episodic / نوبات",
            "Improving / يتحسن", "Worsening / يتدهور"], "course", note_key="course_note")
        mc("Was the child wanted / هل الطفل كان مرغوباً فيه؟", "هل الطفل كان مرغوباً فيه؟",
           ["Yes / نعم", "No / لا", "Unplanned but accepted / غير مخطط لكن مقبول"],
           "wanted_child", note_key="wanted_note")
        mc("Was the gender desired? / هل النوع كان مرغوباً فيه؟", "هل جنس الطفل كان مرغوباً فيه؟",
           ["Yes by both / نعم من الوالدين", "Only father / الأب فقط",
            "Only mother / الأم فقط", "Neither / لا"],
           "gender_desired", note_key="gender_desired_note")
        ta("Chief Complaints (C/O)", "الشكاوى الرئيسية", "complaints", 130)
        ta("History of Presenting Illness (HPI)", "تاريخ المرض الحالي", "hpi", 250)
        nav(3, 5)

    # ── STEP 5: PAST / FAMILY HISTORY ──
    elif step == 5:
        sec("Past History", "التاريخ المرضي السابق")
        mc("Previous psychiatric/neurological illness?", "مرض نفسي أو عصبي سابق؟",
           ["No / لا", "Yes / نعم"], "prev_psych", note_key="prev_psych_note")
        mc("Previous hospitalization?", "دخول مستشفى سابق؟",
           ["No / لا", "Yes / نعم"], "prev_hosp", note_key="prev_hosp_note")
        mc("High fever ≥40°C / حرارة شديدة ≥40°", "ارتفاع الحرارة لـ 40 درجة أو أكثر؟",
           ["No / لا", "Yes / نعم"], "high_fever", note_key="high_fever_note")
        mc("Head trauma / ارتطام الرأس", "هل حدث ارتطام في الرأس؟",
           ["No / لا", "Yes / نعم"], "head_trauma", note_key="head_trauma_note")
        mc("Convulsions / تشنجات", "هل كان هناك تشنجات؟",
           ["No / لا", "Yes — febrile / نعم — حرارية",
            "Yes — epileptic / نعم — صرعية", "Yes — unknown type / نعم — نوع غير محدد"],
           "convulsions", note_key="convulsions_note")
        mc("Post-vaccine complications / مضاعفات بعد التطعيم", "مضاعفات بعد التطعيم؟",
           ["No / لا", "Yes — after MMR / نعم — بعد MMR",
            "Yes — other / نعم — أخرى"], "post_vaccine", note_key="post_vaccine_note")
        mc("Current therapy sessions / جلسات علاجية حالية", "هل الطفل يحضر جلسات؟",
           ["No / لا", "Speech therapy / تخاطب", "Occupational therapy / تنمية مهارات",
            "Behavioral therapy / سلوكي", "Multiple / متعددة"],
           "therapy_sessions", multi=True, note_key="therapy_note")
        ta("Past history details / تفاصيل التاريخ السابق", "تفاصيل", "past_history", 80)

        sec("Family History", "التاريخ العائلي")
        mc("Psychiatric illness in family?", "مرض نفسي في الأسرة؟",
           ["No / لا", "Yes / نعم"], "family_psych", note_key="family_psych_note")
        mc("Neurological illness in family?", "مرض عصبي في الأسرة؟",
           ["No / لا", "Epilepsy / صرع", "Intellectual disability / إعاقة ذهنية",
            "Other / أخرى"], "family_neuro", note_key="family_neuro_note")
        ta("Family history details", "تفاصيل التاريخ العائلي", "family_history", 80)
        nav(4, 6)

    # ── STEP 6: INVESTIGATIONS & SURGERIES ──
    elif step == 6:
        sec("Investigations", "الفحوصات")
        mc("Investigations done / الفحوصات المُجراة", "الفحوصات التي أُجريت",
           ["None / لا يوجد", "Blood tests / تحاليل دم",
            "EEG / رسم مخ", "CT scan / أشعة مقطعية",
            "MRI / رنين مغناطيسي", "IQ test SB5 / اختبار ذكاء",
            "CARS / كارز", "Other / أخرى"],
           "investigations", multi=True, note_key="investigations_note")
        mc("CARS score range / نتيجة CARS", "نتيجة CARS (إن وجدت)",
           ["N/A", "< 30 (Non-autistic)", "30–36.5 (Mild-Moderate)",
            "37–60 (Severe)"], "cars_score", note_key="cars_note")
        ta("Investigation results / نتائج الفحوصات", "نتائج الفحوصات", "investigation_results", 80)

        sec("Operations and Surgeries", "العمليات والجراحات")
        mc("Previous surgeries?", "عمليات جراحية سابقة؟",
           ["No / لا", "Yes / نعم"], "had_surgery", note_key="surgery_note")
        ta("Surgery details", "تفاصيل العمليات", "surgeries", 60)

        sec("Clinical Assessment / التقييم السريري")
        mc("Sleep pattern / نمط النوم", "نمط النوم",
           ["Normal / طبيعي", "Insomnia / أرق", "Hypersomnia / نوم زيادة",
            "Disrupted / متقطع", "Nightmares / كوابيس"], "sleep", note_key="sleep_note")
        mc("Appetite / الشهية", "الشهية",
           ["Normal / طبيعي", "Decreased / قلت",
            "Increased / زادت", "Selective / انتقائية"], "appetite", note_key="appetite_note")
        mc("Attention & Concentration / الانتباه والتركيز", "الانتباه والتركيز",
           ["Good / جيد", "Mildly impaired / ضعيف قليلاً",
            "Moderately impaired / ضعيف بشكل معتدل",
            "Severely impaired / ضعيف جداً"], "attention", note_key="attention_note")
        mc("Punishment methods used / طرق العقاب المستخدمة", "طرق العقاب",
           ["Verbal / لفظي", "Time-out / عزل مؤقت",
            "Privilege removal / حرمان من امتيازات",
            "Physical / جسدي", "Multiple / متعددة"],
           "punishment", multi=True, note_key="punishment_note")
        ta("Additional notes / ملاحظات إضافية", "ملاحظات إضافية", "extra_notes", 80)
        nav(5, 7)

    # ── STEP 7: CHILD CHECKLIST ──
    elif step == 7:
        sec("Child Clinical Checklist", "قائمة التدقيق السريري للأطفال")
        st.caption("Answer Yes / No / N/A for each item and add notes where relevant.")

        checklist_items = [
            ("Consanguinity between parents", "القرابة بين الأب والأم"),
            ("Was the child wanted / planned?", "هل الطفل كان مرغوباً فيه؟"),
            ("Was the child's gender (M/F) desired by parents?", "هل جنس الطفل كان مرغوباً فيه؟"),
            ("Motor & cognitive developmental history", "تاريخ النمو الحركي والمعرفي"),
            ("Toilet training age & punishment methods", "سن تدريب دورة المياه وطرق العقاب"),
            ("Siblings at same/different school? Sibling relationship?", "الأخوة في نفس المدرسة؟ علاقتهم ببعض؟"),
            ("Full prenatal / natal / postnatal history", "تاريخ الحمل كامل: قبل/أثناء/بعد الولادة"),
            ("Birth type (natural/CS), forceps/vacuum, incubator, jaundice", "نوع الولادة، جفت/شفاط، حضانة، صفراء"),
            ("Problems during pregnancy / late pregnancy age", "مشاكل أثناء الحمل / سن متأخر للحمل"),
            ("Family members with psychiatric illness, MR, epilepsy", "أقارب لديهم مشكلة نفسية أو إعاقة أو صرع"),
            ("Reaction to stress / punishment methods (especially physical)", "رد الفعل تجاه الضغوط / طرق العقاب"),
            ("If seizures: document doctors and treatments", "في حالة تشنجات: الأطباء والعلاجات"),
            ("High fever (≥40°C) / hospitalization for fever", "ارتفاع حرارة ≥40 درجة / دخول مستشفى حميات"),
            ("Head trauma: location, vomiting, excess/no sleep", "ارتطام الرأس: مكانه، قيء، نوم زيادة أو عدم نوم"),
            ("Convulsions / post-vaccine complications (esp. MMR at 18m)", "تشنجات / مضاعفات بعد التطعيم (MMR عند سنة ونصف)"),
            ("Cognitive ability: attention vs concentration vs comprehension", "التفرقة بين الانتباه والتركيز والإدراك والفهم"),
            ("Current therapy sessions (speech, skills development)", "جلسات تخاطب / تنمية مهارات"),
            ("Death of a sibling: details, age at time, child's reaction", "وفاة أحد الأخوة: التفاصيل، عمر الطفل، رد فعله"),
            ("Investigations: who ordered / who reviewed? (CT, MRI, SB5, CARS)", "الفحوصات: من طلبها؟ من شافها؟"),
        ]

        checklist_results = {}
        for en, ar in checklist_items:
            st.markdown(f"**{en}**")
            st.markdown(f'<p style="color:#555;direction:rtl;text-align:right;font-size:13px">{ar}</p>', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 3])
            with c1:
                ans = st.radio("", ["Yes/نعم", "No/لا", "N/A"],
                               key=f"chk_{en}", horizontal=True, label_visibility="collapsed")
            with c2:
                note = st.text_input("📝 Notes", key=f"chk_note_{en}",
                                     label_visibility="collapsed",
                                     placeholder="Notes / ملاحظات...")
            checklist_results[en] = {"ar": ar, "answer": ans, "notes": note}
            st.divider()

        st.session_state["checklist"] = checklist_results
        nav(6, final=True)


# ════════════════════════════════════════════════════════════════
#  GENERATE REPORT
# ════════════════════════════════════════════════════════════════
if st.session_state.get("generate"):
    st.session_state.generate = False
    s = st.session_state

    siblings = s.get("siblings", [])
    sibling_text = "\n".join([
        f"  {i+1}. {sib['name']} | {sib['gender']} | Age: {sib['age']} | {sib['edu']} | Notes: {sib['notes']}"
        for i, sib in enumerate(siblings) if sib.get("name")
    ]) or "—"

    if sheet_type == "adult":
        data_block = f"""
PATIENT: {sv('name')} | Age: {sv('age')} | Gender: {sv('gender')}
Date: {sv('taken_date')} | History by: {history_by or '—'} | History type: {sv('history_type')}
Phone: {sv('phone')} | Referral: {sv('referral')} ({sv('referral_note')})
Occupation: {sv('occupation')} | Education: {sv('education')} ({sv('edu_note')})
Social status: {sv('social_status')} ({sv('social_note')}) | Hobbies: {sv('hobbies')}
Smoking: {sv('smoking')} ({sv('smoking_note')})

FAMILY:
Father: {sv('father_name')}, Age {sv('father_age')}, Occ: {sv('father_occ')}, Status: {sv('father_alive')}
Mother: {sv('mother_name')}, Age {sv('mother_age')}, Occ: {sv('mother_occ')}, Status: {sv('mother_alive')}
Consanguinity: {sv('consanguinity')} ({sv('consanguinity_note')})
Chronic illness: {sv('chronic_illness')} ({sv('chronic_note')})
Parents living together: {sv('parents_together')} ({sv('parents_together_note')})

MARRIAGE:
Spouse: {sv('spouse_name')}, Age {sv('spouse_age')}, Occ: {sv('spouse_occ')} ({sv('spouse_occ_note')})
Duration: {sv('marriage_duration')} ({sv('marriage_dur_note')}) | Engagement: {sv('engagement')} ({sv('engagement_note')})
Katb Ketab: {sv('katb_ketab')} | Quality: {sv('marriage_quality')} ({sv('marriage_quality_note')})
Pre-marriage relation: {sv('pre_marriage_rel')} ({sv('pre_marriage_note')})
Number of children: {sv('num_children')} ({sv('children_note')})

SIBLINGS:
{sibling_text}

COMPLAINTS ONSET: {sv('onset')} ({sv('onset_note')})
Mode of onset: {sv('onset_mode')} ({sv('onset_mode_note')})
Course: {sv('course')} ({sv('course_note')})
Precipitant: {sv('precipitant')} ({sv('precipitant_note')})
C/O: {sv('complaints')}
HPI: {sv('hpi')}

DRUG HISTORY: On medication: {sv('on_medication')} ({sv('on_medication_note')})
Details: {sv('drug_history')} | Compliance: {sv('compliance')} ({sv('compliance_note')})

PAST HISTORY: Prev psychiatric: {sv('prev_psych')} ({sv('prev_psych_note')})
Prev hospitalization: {sv('prev_hosp')} ({sv('prev_hosp_note')})
Chronic medical: {sv('chronic_medical')} ({sv('chronic_medical_note')})
Details: {sv('past_history')}

FAMILY HISTORY: Psychiatric: {sv('family_psych')} ({sv('family_psych_note')})
Neurological: {sv('family_neuro')} ({sv('family_neuro_note')})
Details: {sv('family_history')}

INVESTIGATIONS: {sv('investigations')} ({sv('investigations_note')})
Results: {sv('investigation_results')}
Surgeries: {sv('had_surgery')} ({sv('surgery_note')}) — {sv('surgeries')}

CLINICAL ASSESSMENT:
Sleep: {sv('sleep')} ({sv('sleep_note')}) | Appetite: {sv('appetite')} ({sv('appetite_note')})
Mood: {sv('mood')} ({sv('mood_note')}) | Energy: {sv('energy')} ({sv('energy_note')})
Concentration: {sv('concentration')} ({sv('concentration_note')})
Suicidal ideation: {sv('suicidal')} ({sv('suicidal_note')})
Substance use: {sv('substance')} ({sv('substance_note')})
Insight: {sv('insight')} ({sv('insight_note')})
Extra notes: {sv('extra_notes')}
"""
    else:
        checklist = s.get("checklist", {})
        chk_text = "\n".join([
            f"  - {en} ({v['ar']}): {v['answer']} | Notes: {v['notes'] or '—'}"
            for en, v in checklist.items()
        ])
        data_block = f"""
PATIENT: {sv('name')} | Age: {sv('age')} | Gender: {sv('gender')}
Date: {sv('taken_date')} | History by: {history_by or '—'}
Phone: {sv('phone')} | Lives with: {sv('lives_with')} ({sv('lives_with_note')})
Referral: {sv('referral')} ({sv('referral_note')})
School: {sv('school_name')} | Grade: {sv('grade')} ({sv('grade_note')})
Academic performance: {sv('academic')} ({sv('academic_note')})
Screen time: {sv('screen_time')} ({sv('screen_note')})

DEVELOPMENTAL MILESTONES:
Pregnancy: {sv('pregnancy')} ({sv('pregnancy_note')})
Birth type: {sv('birth_type')} ({sv('birth_type_note')})
Birth complications: {sv('birth_comp')} ({sv('birth_comp_note')})
Breastfeeding: {sv('breastfeeding')} ({sv('bf_note')}) | Weaning: {sv('weaning')}
Motor development: {sv('motor_dev')} ({sv('motor_note')})
Speech: {sv('speech')} ({sv('speech_note')}) | Teething: {sv('teething')}
Toilet training: {sv('toilet_training')}
Vaccinations: {sv('vaccinations')} ({sv('vacc_note')})
Developmental notes: {sv('dev_notes')}

FAMILY:
Father: {sv('father_name')}, Age {sv('father_age')}, Occ: {sv('father_occ')}, Status: {sv('father_alive')}, Hereditary: {sv('father_hereditary')}
Mother: {sv('mother_name')}, Age {sv('mother_age')}, Occ: {sv('mother_occ')}, Status: {sv('mother_alive')}, Hereditary: {sv('mother_hereditary')}
Consanguinity: {sv('consanguinity')} ({sv('consanguinity_note')})
Parents relation: {sv('parents_relation')} ({sv('parents_relation_note')})
Same school: {sv('same_school')} ({sv('same_school_note')})
Sibling relationship: {sv('sibling_rel')} ({sv('sibling_rel_note')})

SIBLINGS:
{sibling_text}

WANTED CHILD: {sv('wanted_child')} ({sv('wanted_note')})
GENDER DESIRED: {sv('gender_desired')} ({sv('gender_desired_note')})
COMPLAINTS ONSET: {sv('onset')} ({sv('onset_note')}) | Mode: {sv('onset_mode')} | Course: {sv('course')}
C/O: {sv('complaints')}
HPI: {sv('hpi')}

PAST HISTORY: Prev illness: {sv('prev_psych')} ({sv('prev_psych_note')})
Hospitalization: {sv('prev_hosp')} ({sv('prev_hosp_note')})
High fever: {sv('high_fever')} ({sv('high_fever_note')})
Head trauma: {sv('head_trauma')} ({sv('head_trauma_note')})
Convulsions: {sv('convulsions')} ({sv('convulsions_note')})
Post-vaccine: {sv('post_vaccine')} ({sv('post_vaccine_note')})
Therapy sessions: {sv('therapy_sessions')} ({sv('therapy_note')})
Details: {sv('past_history')}

FAMILY HISTORY: Psychiatric: {sv('family_psych')} ({sv('family_psych_note')})
Neurological: {sv('family_neuro')} ({sv('family_neuro_note')})
Details: {sv('family_history')}

INVESTIGATIONS: {sv('investigations')} ({sv('investigations_note')})
CARS score: {sv('cars_score')} ({sv('cars_note')})
Results: {sv('investigation_results')}
Surgeries: {sv('had_surgery')} ({sv('surgery_note')}) — {sv('surgeries')}

CLINICAL ASSESSMENT:
Sleep: {sv('sleep')} ({sv('sleep_note')}) | Appetite: {sv('appetite')} ({sv('appetite_note')})
Attention/Concentration: {sv('attention')} ({sv('attention_note')})
Punishment methods: {sv('punishment')} ({sv('punishment_note')})
Extra notes: {sv('extra_notes')}

CHILD CHECKLIST:
{chk_text}
"""

    patient_name = sv('name', 'Patient')
    prompt = f"""You are a senior consultant psychiatrist. Based on the structured history data below, generate a comprehensive bilingual (Arabic and English) psychiatric history report.

The report must have TWO clearly separated parts:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — PROFESSIONAL SUMMARY / الملخص المهني
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write a professional clinical summary in BOTH Arabic and English.
Structure it with these bilingual sections:
- Patient Overview / نظرة عامة عن المريض
- Chief Complaint & Presenting Illness / الشكوى الرئيسية وتاريخ المرض الحالي
- Personal & Social Background / الخلفية الشخصية والاجتماعية
- Family Background / الخلفية العائلية
- Medical & Drug History / التاريخ الطبي والدوائي
- Clinical Observations / الملاحظات السريرية
- Summary Impression / الانطباع العام

Be professional, concise, and clinically accurate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — DETAILED RECORD / السجل التفصيلي
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Present ALL data as a clean structured table with three columns:
| Field (English) | Field (Arabic) | Response |

Keep exact wording. Arabic stays Arabic, English stays English.
Include every field including checklist if present.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORY DATA:
{data_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
History by: {history_by or '—'} | Sheet type: {sheet_type.upper()}"""

    with st.spinner("Generating report... / جاري إنشاء التقرير..."):
        try:
            client = Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048
            )
            st.session_state.report_text = response.choices[0].message.content
            st.session_state.patient_name_final = patient_name
        except Exception as e:
            st.error(f"Report generation error: {str(e)}")


# ════════════════════════════════════════════════════════════════
#  BUILD DOCX & DISPLAY
# ════════════════════════════════════════════════════════════════
if st.session_state.get("report_text"):
    report_text = st.session_state.report_text
    patient_name = st.session_state.get("patient_name_final", "Patient")

    st.divider()
    st.markdown("### ✅ Report Generated / تم إنشاء التقرير")
    st.text_area("", value=report_text, height=500, label_visibility="collapsed")

    def build_docx(report_text, patient_name, sheet_type, history_by, logo_path, doctor):
        doc = Document()
        for section in doc.sections:
            section.top_margin = Cm(2.5); section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5); section.right_margin = Cm(2.5)
            section.different_first_page_header_footer = True
            for hdr in [section.header, section.first_page_header]:
                for p in hdr.paragraphs: p.clear()

        def add_border(doc, color="1B2A4A", size=12):
            for section in doc.sections:
                sectPr = section._sectPr
                pgBorders = OxmlElement('w:pgBorders')
                pgBorders.set(qn('w:offsetFrom'), 'page')
                for side in ('top','left','bottom','right'):
                    b = OxmlElement(f'w:{side}')
                    b.set(qn('w:val'),'single'); b.set(qn('w:sz'),str(size))
                    b.set(qn('w:space'),'24'); b.set(qn('w:color'),color)
                    pgBorders.append(b)
                sectPr.append(pgBorders)
        add_border(doc)

        def add_page_numbers(doc):
            for section in doc.sections:
                footer = section.footer
                para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
                para.clear(); para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.add_run()
                run.font.size = Pt(9); run.font.color.rgb = CLINIC_BLUE
                for tag, text in [('begin',None),(None,' PAGE '),('end',None)]:
                    if tag:
                        el = OxmlElement('w:fldChar'); el.set(qn('w:fldCharType'),tag); run._r.append(el)
                    else:
                        instr = OxmlElement('w:instrText'); instr.text = text; run._r.append(instr)
        add_page_numbers(doc)

        # Logo + Title
        p_top = doc.add_paragraph()
        p_top.paragraph_format.space_before = Pt(0); p_top.paragraph_format.space_after = Pt(6)
        if os.path.exists(logo_path):
            p_top.add_run().add_picture(logo_path, width=Inches(1.2))
        r_title = p_top.add_run("   Clinical History Report")
        r_title.font.name="Arial"; r_title.font.size=Pt(20)
        r_title.font.bold=True; r_title.font.color.rgb=CLINIC_BLUE
        pPr = p_top._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bot = OxmlElement('w:bottom')
        bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'8')
        bot.set(qn('w:space'),'4'); bot.set(qn('w:color'),'1A5CB8')
        pBdr.append(bot); pPr.append(pBdr)

        doc.add_paragraph()
        p_info = doc.add_paragraph()
        for label, val in [("Patient: ", patient_name),
                            ("   |   Sheet: ", sheet_type.capitalize()),
                            ("   |   History by: ", history_by or "—")]:
            r = p_info.add_run(label); r.bold=True; r.font.size=Pt(11)
            r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
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
                    in_table = True
                    table = doc.add_table(rows=0, cols=3)
                    table.style = 'Table Grid'; table.autofit = True
                row = table.add_row()
                for i, ct in enumerate(cells[:3]):
                    cell = row.cells[i]; cell.text = ct
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.font.size=Pt(10); run.font.name="Arial"
                continue
            else:
                in_table = False; table = None

            if ls.startswith('━'):
                p = doc.add_paragraph()
                pPr2 = p._p.get_or_add_pPr(); pBdr2 = OxmlElement('w:pBdr')
                b2 = OxmlElement('w:bottom')
                b2.set(qn('w:val'),'single'); b2.set(qn('w:sz'),'4')
                b2.set(qn('w:space'),'1'); b2.set(qn('w:color'),'1A5CB8')
                pBdr2.append(b2); pPr2.append(pBdr2)
                continue
            if ls.startswith('PART '):
                p = doc.add_paragraph()
                r = p.add_run(ls); r.bold=True; r.font.size=Pt(13)
                r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                continue
            if ('/' in ls and len(ls) < 80 and not ls.startswith('-')) or (ls.isupper() and len(ls) < 60):
                p = doc.add_paragraph(); p.paragraph_format.space_before=Pt(8)
                r = p.add_run(ls); r.bold=True; r.font.size=Pt(11)
                r.font.name="Arial"; r.font.color.rgb=CLINIC_BLUE
                pPr3 = p._p.get_or_add_pPr(); pBdr3 = OxmlElement('w:pBdr')
                b3 = OxmlElement('w:bottom')
                b3.set(qn('w:val'),'single'); b3.set(qn('w:sz'),'4')
                b3.set(qn('w:space'),'1'); b3.set(qn('w:color'),'1A5CB8')
                pBdr3.append(b3); pPr3.append(pBdr3)
                continue
            if ls.startswith('- ') or ls.startswith('• '):
                p = doc.add_paragraph(style='List Bullet')
                r = p.add_run(ls.lstrip('-•').strip())
                r.font.size=Pt(11); r.font.name="Arial"
                continue
            p = doc.add_paragraph()
            r = p.add_run(ls); r.font.size=Pt(11); r.font.name="Arial"

        # Doctor footer
        doc.add_paragraph(); doc.add_paragraph()
        p_sep = doc.add_paragraph()
        pPr_s = p_sep._p.get_or_add_pPr(); pBdr_s = OxmlElement('w:pBdr')
        top = OxmlElement('w:top')
        top.set(qn('w:val'),'single'); top.set(qn('w:sz'),'6')
        top.set(qn('w:space'),'1'); top.set(qn('w:color'),'1A5CB8')
        pBdr_s.append(top); pPr_s.append(pBdr_s)

        p_dr = doc.add_paragraph()
        r_dr = p_dr.add_run(doctor["name"])
        r_dr.bold=True; r_dr.font.size=Pt(12)
        r_dr.font.name="Arial"; r_dr.font.color.rgb=CLINIC_BLUE
        for t in ["title1","title2","title3","title4"]:
            p_t = doc.add_paragraph()
            r_t = p_t.add_run(doctor[t])
            r_t.font.size=Pt(10); r_t.font.name="Arial"
            r_t.font.color.rgb=RGBColor(0x44,0x44,0x44)
            p_t.paragraph_format.space_before=Pt(0)
            p_t.paragraph_format.space_after=Pt(0)
        doc.add_paragraph()
        p_addr = doc.add_paragraph()
        p_addr.add_run(f"📍  {doctor['address']}").font.size=Pt(10)
        p_ph = doc.add_paragraph()
        r_ph = p_ph.add_run(f"📞  {doctor['phone']}")
        r_ph.font.size=Pt(10); r_ph.bold=True

        buf = io.BytesIO(); doc.save(buf); buf.seek(0)
        return buf

    docx_buf = build_docx(report_text, patient_name, sheet_type, history_by, LOGO_PATH, DOCTOR)
    filename = f"{patient_name.replace(' ','_')}_HistorySheet.docx"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📄 Download .docx", data=docx_buf, file_name=filename,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with col2:
        if st.button("📧 Send to Email"):
            if not gmail_user or not gmail_pass:
                st.error("Enter Gmail credentials in the sidebar first.")
            else:
                try:
                    docx_buf2 = build_docx(report_text, patient_name, sheet_type, history_by, LOGO_PATH, DOCTOR)
                    msg = MIMEMultipart()
                    msg['From'] = gmail_user; msg['To'] = RECIPIENT_EMAIL
                    msg['Subject'] = f"History Report — {patient_name}"
                    msg.attach(MIMEText(
                        f"Please find attached the history report for {patient_name}.\n\nHistory by: {history_by or '—'}\nSheet type: {sheet_type.capitalize()}",
                        'plain'))
                    part = MIMEBase('application','octet-stream')
                    part.set_payload(docx_buf2.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                        server.login(gmail_user, gmail_pass)
                        server.sendmail(gmail_user, RECIPIENT_EMAIL, msg.as_string())
                    st.success(f"✅ Report sent to {RECIPIENT_EMAIL}")
                except Exception as e:
                    st.error(f"Email error: {str(e)}")
    with col3:
        if st.button("↺ New Patient / مريض جديد"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
