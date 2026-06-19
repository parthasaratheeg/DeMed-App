import streamlit as st
import fitz
import tempfile
import re

from datetime import datetime

from presidio_analyzer import (
    AnalyzerEngine
)

from presidio_anonymizer import (
    AnonymizerEngine
)

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)


# --------------------------------
# PDF TEXT EXTRACTION
# --------------------------------

def extract_text(pdf):

    doc = fitz.open(pdf)

    text = ""

    for page in doc:

        text += page.get_text()

        text += "\n"

    doc.close()

    return text


# --------------------------------
# AGE → AGE GROUP
# --------------------------------

def convert_age(match):

    age = int(
        match.group(2)
    )

    start = (
        age // 10
    ) * 10

    end = (
        start + 9
    )

    return (
        f"Age Group: {start}-{end}"
    )


# --------------------------------
# DATE → MONTH YEAR
# --------------------------------

def convert_date(match):

    txt = (
        match.group(0)
        .strip()
    )

    txt = re.sub(

        r'(\d+)(st|nd|rd|th)',

        r'\1',

        txt,

        flags=re.I

    )

    formats = [

        "%d/%m/%Y",

        "%d-%m-%Y",

        "%d-%b-%Y",

        "%d-%B-%Y",

        "%d %b %Y",

        "%d %B %Y"

    ]


    for f in formats:

        try:

            d = datetime.strptime(
                txt,
                f
            )

            return d.strftime(
                "%b %Y"
            )

        except:

            pass

    return "[DATE]"


# --------------------------------
# DEIDENTIFICATION
# --------------------------------

def deidentify(text):


    rules = [

        (

            r'Name\s*:.*',

            'Name : [PATIENT]'

        ),

        (

            r'Patient.*',

            'Patient : [PATIENT]'

        ),

        (

            r'Dr\.?\s*[A-Za-z .]+',

            '[DOCTOR]'

        ),

        (

            r'Consultant Pathologist',

            '[ROLE]'

        ),

        (

            r'Kauvery Hospital.*',

            '[HOSPITAL]'

        ),

        (

            r'Trichy',

            '[CITY]'

        ),

        (

            r'Bangalore',

            '[CITY]'

        ),

        (

            r'Case ID.*',

            'Case ID : [ID]'

        ),

        (

            r'Sample ID.*',

            'Sample ID : [ID]'

        ),

        (

            r'Order ID.*',

            'Order ID : [ID]'

        ),

        (

            r'Ref By.*',

            'Ref By : [REDACTED]'

        )

    ]


    for pattern, replacement in rules:

        text = re.sub(

            pattern,

            replacement,

            text,

            flags=re.I

        )


    # AGE GROUP

    text = re.sub(

        r'(AGE|Age)\s*:\s*(\d+)\s*(years|yrs)?',

        convert_age,

        text,

        flags=re.I

    )


    # DATE

    text = re.sub(

        r'\d{1,2}(st|nd|rd|th)?[\s/-]+[A-Za-z0-9]+[\s/-]+\d{4}',

        convert_date,

        text,

        flags=re.I

    )


    analyzer = (
        AnalyzerEngine()
    )

    anonymizer = (
        AnonymizerEngine()
    )

    result = analyzer.analyze(

        text=text,

        language="en"

    )

    return anonymizer.anonymize(

        text,

        result

    ).text


# --------------------------------
# PDF EXPORT
# --------------------------------

def create_pdf(text):

    temp = tempfile.NamedTemporaryFile(

        delete=False,

        suffix=".pdf"

    )

    path = temp.name


    doc = SimpleDocTemplate(

        path

    )

    styles = (

        getSampleStyleSheet()

    )


    story = []


    story.append(

        Paragraph(

            "Deidentified Medical Report",

            styles["Title"]

        )

    )


    story.append(

        Spacer(

            1,

            20

        )

    )


    for line in text.split("\n"):

        if line.strip():

            story.append(

                Paragraph(

                    line,

                    styles["BodyText"]

                )

            )


    doc.build(

        story

    )

    return path


# --------------------------------
# STREAMLIT UI
# --------------------------------

st.set_page_config(

    page_title="Medical PDF Deidentifier",

    layout="wide"

)


st.title(

    "Medical PDF Deidentification"

)


uploaded = st.file_uploader(

    "Upload Medical PDF",

    type=["pdf"]

)


if uploaded:


    with tempfile.NamedTemporaryFile(

        delete=False,

        suffix=".pdf"

    ) as f:

        f.write(

            uploaded.read()

        )

        input_pdf = f.name


    raw = extract_text(

        input_pdf

    )


    clean = deidentify(

        raw

    )


    st.success(

        "Deidentification Completed"

    )


    st.subheader(

        "Preview"

    )


    st.text_area(

        "",

        clean,

        height=350

    )


    output = create_pdf(

        clean

    )


    with open(

        output,

        "rb"

    ) as f:

        st.download_button(

            label="Download Deidentified PDF",

            data=f.read(),

            file_name="deidentified_report.pdf",

            mime="application/pdf"

        )