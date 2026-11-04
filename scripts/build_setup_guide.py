"""Builds docs/PhysioBand_AI_Complete_Hardware_and_Software_Setup_Guide.pdf.

    python scripts/build_setup_guide.py

All values (pins, UUIDs, commands, endpoints, examples) are taken from the project source.
"""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "PhysioBand_AI_Complete_Hardware_and_Software_Setup_Guide.pdf"
LOGO = ROOT / "frontend" / "assets" / "logo.png"

NAVY = colors.HexColor("#021C40")
NAVY2 = colors.HexColor("#063862")
TEAL = colors.HexColor("#00A396")
TEAL_BRIGHT = colors.HexColor("#00FAD8")
GREEN = colors.HexColor("#16C060")
LIGHT = colors.HexColor("#EBFCF8")
GREY = colors.HexColor("#44546B")
BORDER = colors.HexColor("#C9D5E3")
WARN_BG = colors.HexColor("#FEF3C7")
DANGER_BG = colors.HexColor("#FEE2E2")
INFO_BG = colors.HexColor("#E3F2FD")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=26, leading=32, textColor=NAVY, alignment=TA_CENTER),
    "subtitle": ParagraphStyle("subtitle", parent=ss["Normal"], fontSize=13, leading=18, textColor=GREY, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=NAVY, spaceBefore=4, spaceAfter=10),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=18, textColor=TEAL, spaceBefore=10, spaceAfter=5),
    "body": ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=10, leading=14.5, textColor=colors.HexColor("#1E293B"), spaceAfter=5),
    "bullet": ParagraphStyle("bullet", parent=ss["BodyText"], fontName="Helvetica", fontSize=10, leading=14, leftIndent=14, bulletIndent=4, spaceAfter=2),
    "cell": ParagraphStyle("cell", parent=ss["BodyText"], fontName="Helvetica", fontSize=8.6, leading=11),
    "cellb": ParagraphStyle("cellb", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=8.6, leading=11, textColor=colors.white),
    "code": ParagraphStyle("code", parent=ss["Code"], fontName="Courier", fontSize=8.2, leading=10.4, backColor=colors.HexColor("#F1F5F9"),
                           borderColor=BORDER, borderWidth=0.5, borderPadding=6, leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=8),
    "note": ParagraphStyle("note", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.5),
    "caption": ParagraphStyle("caption", parent=ss["BodyText"], fontName="Helvetica-Oblique", fontSize=8.5, textColor=GREY, alignment=TA_CENTER, spaceAfter=8),
}

story: list = []


def jdump(obj) -> str:
    """JSON with short scalar lists (sensor vectors) kept on one line."""
    import re

    text = json.dumps(obj, indent=1)
    return re.sub(r"\[\s*([^\[\]{}]*?)\s*\]", lambda m: "[" + re.sub(r"\s*\n\s*", " ", m.group(1)) + "]", text)


def h1(t):
    story.append(Paragraph(t, S["h1"]))


def h2(t):
    story.append(Paragraph(t, S["h2"]))


def p(t):
    story.append(Paragraph(t, S["body"]))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="\u2022"))
    story.append(Spacer(1, 4))


def steps(items):
    for i, it in enumerate(items, 1):
        story.append(Paragraph(it, S["bullet"], bulletText=f"{i}."))
    story.append(Spacer(1, 4))


def code(t):
    story.append(Preformatted(t.strip("\n"), S["code"]))


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), S["cellb"] if header and r == 0 else S["cell"]) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFD")]),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    t.setStyle(TableStyle(style))
    story.append(t)
    story.append(Spacer(1, 8))


def callout(text, kind="info"):
    bg = {"info": INFO_BG, "warn": WARN_BG, "danger": DANGER_BG, "tip": LIGHT}[kind]
    label = {"info": "NOTE", "warn": "IMPORTANT", "danger": "SAFETY", "tip": "TIP"}[kind]
    t = Table([[Paragraph(f"<b>{label}:</b> {text}", S["note"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(t)
    story.append(Spacer(1, 8))


def figure(drawing, caption):
    story.append(KeepTogether([drawing, Paragraph(caption, S["caption"])]))


# ---------------------------------------------------------------- diagrams
def box(d, x, y, w, h, label, fill=LIGHT, stroke=TEAL, fs=8, color=NAVY, sub=None):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=stroke, strokeWidth=1))
    d.add(String(x + w / 2, y + h / 2 + (3 if sub else -3), label, fontName="Helvetica-Bold", fontSize=fs, fillColor=color, textAnchor="middle"))
    if sub:
        d.add(String(x + w / 2, y + h / 2 - 8, sub, fontName="Helvetica", fontSize=fs - 1.5, fillColor=GREY, textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, color=NAVY, label=None):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.2))
    import math

    a = math.atan2(y2 - y1, x2 - x1)
    s = 5
    d.add(Polygon([x2, y2, x2 - s * math.cos(a - 0.4), y2 - s * math.sin(a - 0.4), x2 - s * math.cos(a + 0.4), y2 - s * math.sin(a + 0.4)],
                  fillColor=color, strokeColor=color))
    if label:
        d.add(String((x1 + x2) / 2 + 3, (y1 + y2) / 2 + 3, label, fontName="Helvetica", fontSize=6.5, fillColor=GREY))


def architecture_diagram():
    d = Drawing(480, 250)
    d.add(Rect(0, 0, 480, 250, fillColor=colors.HexColor("#F7FAFD"), strokeColor=None))
    d.add(String(70, 235, "HARDWARE", fontName="Helvetica-Bold", fontSize=9, fillColor=TEAL, textAnchor="middle"))
    d.add(String(240, 235, "MOBILE", fontName="Helvetica-Bold", fontSize=9, fillColor=TEAL, textAnchor="middle"))
    d.add(String(410, 235, "CLOUD", fontName="Helvetica-Bold", fontSize=9, fillColor=TEAL, textAnchor="middle"))
    box(d, 15, 190, 110, 32, "MPU6050 x 2", sub="upper arm 0x68 / forearm 0x69")
    box(d, 15, 145, 110, 32, "S-type load cell", sub="band tension")
    box(d, 15, 100, 110, 32, "HX711", sub="24-bit ADC")
    box(d, 15, 40, 110, 40, "ESP32 DevKit V1", fill=NAVY, color=colors.white, sub=None)
    d.add(String(70, 47, "50 Hz sampling + BLE", fontName="Helvetica", fontSize=6.5, fillColor=TEAL_BRIGHT, textAnchor="middle"))
    arrow(d, 70, 190, 70, 80, label="I2C")
    arrow(d, 70, 145, 70, 132)
    box(d, 180, 165, 120, 40, "React Native app", fill=NAVY, color=colors.white)
    box(d, 180, 105, 120, 40, "Decode + validate", sub="batch ~1 s (50 samples)")
    box(d, 180, 40, 120, 45, "Live feedback UI", sub="reps, quality, tension")
    arrow(d, 125, 60, 180, 180, color=TEAL, label="BLE notify")
    arrow(d, 240, 165, 240, 145)
    box(d, 350, 185, 120, 36, "FastAPI REST", fill=NAVY, color=colors.white)
    box(d, 350, 135, 120, 36, "Python ML engine", sub="filter, angle, features")
    box(d, 350, 90, 120, 36, "Reps + Random Forest", sub="quality classification")
    box(d, 350, 40, 120, 36, "MongoDB Atlas", sub="physioband_ai")
    arrow(d, 300, 125, 350, 200, color=TEAL, label="HTTPS")
    arrow(d, 410, 185, 410, 171)
    arrow(d, 410, 135, 410, 126)
    arrow(d, 410, 90, 410, 76)
    arrow(d, 350, 105, 300, 65, color=GREEN, label="analysis")
    return d


def wiring_diagram():
    d = Drawing(480, 260)
    d.add(Rect(180, 70, 120, 150, rx=5, ry=5, fillColor=NAVY, strokeColor=TEAL, strokeWidth=1))
    d.add(String(240, 204, "ESP32 DevKit V1", fontName="Helvetica-Bold", fontSize=8.5, fillColor=colors.white, textAnchor="middle"))
    pins = [("3V3", 185), ("GND", 170), ("GPIO21 SDA", 155), ("GPIO22 SCL", 140), ("GPIO16 <- DT", 112), ("GPIO4 -> SCK", 97), ("VIN 5V", 80)]
    for name, y in pins:
        d.add(String(240, y - 3, name, fontName="Helvetica", fontSize=7, fillColor=TEAL_BRIGHT, textAnchor="middle"))
    box(d, 10, 175, 120, 60, "MPU6050 #1  UPPER ARM", fs=7.5, sub="AD0 -> GND  = 0x68")
    box(d, 10, 95, 120, 60, "MPU6050 #2  FOREARM", fs=7.5, sub="AD0 -> 3V3  = 0x69")
    for y0 in (205, 125):
        for k, (lbl, col) in enumerate([("VCC", colors.red), ("GND", colors.black), ("SDA", colors.HexColor("#2563EB")), ("SCL", colors.HexColor("#CA8A04"))]):
            ty = {0: 185, 1: 170, 2: 155, 3: 140}[k]
            d.add(Line(130, y0 + 12 - k * 8, 180, ty, strokeColor=col, strokeWidth=0.9))
            d.add(String(133, y0 + 14 - k * 8, lbl, fontName="Helvetica", fontSize=5.5, fillColor=col))
    box(d, 350, 80, 115, 50, "HX711", sub="VCC 3V3, GND, DT, SCK")
    d.add(Line(350, 112, 300, 112, strokeColor=colors.HexColor("#7C3AED"), strokeWidth=1))
    d.add(Line(350, 97, 300, 97, strokeColor=colors.HexColor("#DB2777"), strokeWidth=1))
    d.add(Line(350, 122, 300, 185, strokeColor=colors.red, strokeWidth=0.9))
    d.add(Line(350, 88, 300, 170, strokeColor=colors.black, strokeWidth=0.9))
    box(d, 350, 170, 115, 55, "S-type load cell", sub="E+ E- A+ A- (check datasheet)")
    for i, lbl in enumerate(["E+", "E-", "A+", "A-"]):
        x = 365 + i * 26
        d.add(Line(x, 170, x, 130, strokeColor=GREY, strokeWidth=0.9))
        d.add(String(x + 2, 148, lbl, fontName="Helvetica", fontSize=6, fillColor=GREY))
    box(d, 180, 10, 120, 40, "5 V boost converter OUT", fs=7.5, sub="(battery stage only)")
    arrow(d, 240, 50, 240, 70, color=colors.red)
    return d


def power_diagram():
    d = Drawing(480, 90)
    items = [("Protected 18650", "3.0-4.2 V"), ("TP4056 + protection", "B+/B- in, OUT+/OUT-"), ("5 V boost converter", "set to 5.0 V"), ("ESP32 VIN / GND", "on-board 3.3 V reg."), ("Sensors on 3V3", "MPU6050 x2, HX711")]
    for i, (a, b) in enumerate(items):
        x = 5 + i * 96
        box(d, x, 25, 86, 44, a, fs=7.2, sub=b, fill=NAVY if i == 3 else LIGHT, color=colors.white if i == 3 else NAVY)
        if i < len(items) - 1:
            arrow(d, x + 86, 47, x + 96, 47, color=colors.red)
    d.add(String(240, 8, "First tests: power the ESP32 from USB only. Never feed battery/TP4056 OUT directly to the ESP32.", fontName="Helvetica-Oblique", fontSize=7, fillColor=colors.HexColor("#B91C1C"), textAnchor="middle"))
    return d


def placement_diagram():
    d = Drawing(480, 230)
    d.add(Circle(120, 205, 16, fillColor=colors.HexColor("#E2E8F0"), strokeColor=GREY))
    d.add(Line(120, 189, 120, 110, strokeColor=GREY, strokeWidth=10))
    d.add(Line(120, 180, 150, 120, strokeColor=GREY, strokeWidth=8))
    d.add(Line(150, 120, 190, 160, strokeColor=GREY, strokeWidth=7))
    d.add(Rect(138, 140, 18, 12, fillColor=TEAL, strokeColor=NAVY))
    d.add(Rect(162, 134, 18, 12, fillColor=TEAL, strokeColor=NAVY))
    d.add(Rect(186, 158, 14, 22, fillColor=colors.HexColor("#94A3B8"), strokeColor=NAVY))
    d.add(Line(193, 158, 193, 30, strokeColor=GREEN, strokeWidth=3))
    d.add(Rect(126, 160, 16, 10, fillColor=NAVY, strokeColor=NAVY))
    d.add(String(260, 200, "1  PCB (ESP32, HX711, power) on upper-arm strap or waist belt", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(String(260, 180, "2  Upper-arm MPU6050 (0x68): lateral side, mid upper arm", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(String(260, 160, "3  Forearm MPU6050 (0x69): lateral side, mid forearm", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(String(260, 140, "    BOTH: chip facing out, X arrow pointing to the hand", fontName="Helvetica-Bold", fontSize=8, fillColor=TEAL))
    d.add(String(260, 120, "4  S-type load cell in-line: handle - cell - band", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(String(260, 100, "5  Resistance band anchored under the foot", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(String(260, 80, "    Load path in pure tension, along the cell axis", fontName="Helvetica-Bold", fontSize=8, fillColor=TEAL))
    for n, (x, y) in enumerate([(122, 172), (132, 147), (170, 128), (205, 170), (198, 40)], 1):
        d.add(Circle(x - 14, y, 6, fillColor=NAVY, strokeColor=None))
        d.add(String(x - 14, y - 2.5, str(n), fontName="Helvetica-Bold", fontSize=7, fillColor=colors.white, textAnchor="middle"))
    return d


# ---------------------------------------------------------------- content
def cover():
    story.append(Spacer(1, 30 * mm))
    if LOGO.exists():
        story.append(Image(str(LOGO), width=70 * mm, height=70 * mm))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("PhysioBand AI", S["title"]))
    story.append(Paragraph("Intelligent Resistance Exercise Quality Monitoring System", S["subtitle"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("<b>Complete Hardware and Software Setup Guide</b>", ParagraphStyle("c", parent=S["subtitle"], fontSize=15, textColor=TEAL)))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("ESP32 firmware - React Native app - FastAPI backend - Python ML pipeline - MongoDB Atlas", S["subtitle"]))
    story.append(Spacer(1, 25 * mm))
    callout("PhysioBand AI provides exercise feedback for training purposes only. It is not a medical device, does not provide clinical "
            "diagnosis and does not guarantee injury prevention. The included AI model is a DEMO model trained on synthetic data and is not validated.", "warn")
    story.append(PageBreak())


def contents():
    h1("Contents")
    chapters = ["Project overview", "Components required", "Hardware assembly", "Circuit connections", "Development environment setup",
                "ESP32 firmware setup", "Frontend (mobile app) setup", "Backend setup", "MongoDB Atlas setup", "ML model setup",
                "Connecting everything", "Testing and troubleshooting", "Complete project execution (demonstration day)"]
    table([["Chapter", "Title"]] + [[str(i), c] for i, c in enumerate(chapters, 1)], [25, 145])
    story.append(PageBreak())


def ch1():
    h1("Chapter 1 - Project Overview")
    h2("1.1 Objective")
    p("PhysioBand AI is a wearable, AI-assisted resistance-band exercise monitor. It measures <b>upper-arm movement</b>, "
      "<b>forearm movement</b> and <b>resistance-band tension</b>, then recognises the exercise, counts repetitions automatically, "
      "detects selected incorrect movement patterns, analyses tension and consistency, and gives feedback in a mobile app with a "
      "full workout history. The first implemented exercise is the <b>Biceps Curl</b>; the software is structured so that further "
      "exercises (Shoulder Press, Chest Press, Seated Row, Triceps Extension) can be added later.")
    h2("1.2 System functionality")
    bullets(["Two MPU6050 IMUs and an S-type load cell (through an HX711) are sampled by an ESP32 at 50 Hz.",
             "The ESP32 streams binary sensor packets to the phone over Bluetooth Low Energy (BLE).",
             "The React Native app decodes, validates and batches the data and uploads it to the FastAPI backend about once per second.",
             "The backend runs the Python ML pipeline: filtering, elbow-angle estimation, repetition counting and Random Forest quality classification.",
             "Results are stored in MongoDB Atlas and returned to the app, which shows live feedback and the final workout report."])
    h2("1.3 Architecture")
    figure(architecture_diagram(), "Figure 1 - PhysioBand AI architecture and data flow (the only data path in the system)")
    h2("1.4 Responsibilities")
    table([["Layer", "Technology", "Responsibility"],
           ["Hardware / firmware", "ESP32, Arduino C++", "Sampling, timestamps, sensor validation flags, calibration, BLE"],
           ["Mobile app", "Expo, React Native, TypeScript", "BLE connection, decoding, batching, live UI, history, profile"],
           ["Backend", "FastAPI, Pydantic, Motor", "Authentication, devices, workouts, sensor storage, analytics"],
           ["ML engine", "NumPy, SciPy, scikit-learn", "Preprocessing, rep counting, features, classification"],
           ["Database", "MongoDB Atlas", "Users, devices, exercises, sessions, sensor batches, feedback"]], [35, 50, 85])
    h2("1.5 Movement-quality classes (Biceps Curl)")
    table([["Class", "Meaning"], ["Correct", "Full range of motion, controlled tempo, upper arm steady"],
           ["Incomplete", "Clearly reduced range of motion"], ["Excessively fast", "Full range but very short repetition"],
           ["Irregular", "Jerky / stop-and-go movement or swinging the upper arm"]], [40, 130])
    p("These sensors cannot detect every possible posture error; only the four classes above are claimed.")
    story.append(PageBreak())


def ch2():
    h1("Chapter 2 - Components Required")
    p("Only the approved components below are used. No additional sensors, displays, LEDs or buzzers are required. "
      "The ESP32 has Bluetooth Low Energy built in, so no separate Bluetooth module is needed.")
    table([["Component", "Qty", "Purpose / where used", "Important specifications", "Cables / accessories"],
           ["ESP32 DevKit V1", "1", "Main controller on the PCB: reads sensors, BLE", "Dual-core 240 MHz, BLE 4.2, 3.3 V logic, VIN 5 V input", "Micro-USB data cable"],
           ["MPU6050 GY-521", "2", "Upper-arm and forearm motion (accel + gyro)", "3-axis accel + gyro, I2C 0x68/0x69 via AD0, on-board regulator", "Jumper wires, arm straps"],
           ["S-type load cell", "1", "In-line between handle and band: band tension", "Capacity >= 2 x max band force (Ch. 3.4), threaded ends", "Eye bolts, carabiners rated above capacity"],
           ["HX711 amplifier", "1", "Converts load-cell bridge signal to digital", "24-bit ADC, gain 128, 10/80 SPS", "Screw terminals / jumpers"],
           ["Protected 18650, 3.7 V", "1", "Portable power", "Built-in protection circuit, >= 2000 mAh recommended", "18650 holder"],
           ["TP4056 with protection", "1", "Charges the 18650 safely", "1 A charging, B+/B- battery, OUT+/OUT- load (NOT a regulator)", "USB charging cable"],
           ["Regulated 5 V boost", "1", "Raises 3.0-4.2 V battery to stable 5 V for ESP32 VIN", "Output set/verified at 5.0 V, >= 500 mA", "-"],
           ["Resistance band", "1", "Exercise resistance", "Known resistance level; inspect for wear", "Handle"],
           ["Jumper wires", "1 set", "All electrical connections", "Male/female, keep I2C runs short", "-"],
           ["General-purpose PCB", "1", "Holds ESP32, HX711, TP4056, boost converter", "Perforated board, headers", "Solder, headers"],
           ["18650 battery holder", "1", "Mounts the cell", "Correct polarity marking", "-"],
           ["Straps & mounting", "1 set", "Fix sensors / PCB to arm, mount load cell", "Elastic hook-and-loop straps, enclosure", "Eye bolts, lock nuts, carabiners"]],
          [30, 10, 40, 50, 40])
    h2("Why every component is required")
    bullets(["<b>Two IMUs</b>: the elbow angle is computed from the difference between upper-arm and forearm orientation; one IMU alone cannot separate elbow flexion from whole-arm swinging.",
             "<b>Load cell + HX711</b>: measures the actual band tension, used for tension analysis and consistency features.",
             "<b>ESP32</b>: fixed-rate sampling, timestamps and BLE in one low-cost board.",
             "<b>18650 + TP4056 + boost</b>: wireless operation during exercise; TP4056 charges, the boost converter regulates.",
             "<b>PCB, holder, wires, straps</b>: robust, wearable assembly."])
    story.append(PageBreak())


def ch3():
    h1("Chapter 3 - Hardware Assembly")
    figure(placement_diagram(), "Figure 2 - Sensor, PCB and load-cell placement for the Biceps Curl")
    h2("3.1 Upper-arm MPU6050 (address 0x68)")
    bullets(["Lateral (outer) side of the upper arm, halfway between shoulder and elbow, on a flat muscular area.",
             "Chip side facing away from the body; the printed X arrow points down the arm towards the hand when the arm hangs straight.",
             "Strap firmly so it cannot slide or rotate."])
    h2("3.2 Forearm MPU6050 (address 0x69)")
    bullets(["Lateral side of the forearm, halfway between elbow and wrist.",
             "<b>Exactly the same orientation as the upper-arm sensor</b> (chip outward, X arrow towards the hand). The ML pipeline computes the elbow angle "
             "as the angle between the two gravity directions, which is only valid with identical orientation."])
    h2("3.3 ESP32, PCB and battery")
    bullets(["Solder the ESP32, HX711, TP4056 and boost converter onto the general-purpose PCB using headers.",
             "Mount the PCB and 18650 holder in an enclosure on the upper-arm strap (above the IMU) or on a waist belt, so cables to both IMUs and the load cell stay short.",
             "Keep the TP4056 USB socket accessible for charging and the ESP32 USB socket accessible for programming."])
    h2("3.4 S-type load cell selection and safe installation")
    steps(["<b>Measure the expected maximum tension</b>: attach the strongest band to a luggage scale and stretch it to the length reached at the top of a curl.",
           "<b>Choose a capacity of at least 2 x that value</b> (safety margin for jerks). Example: 12 kg (~118 N) measured -> 30 kg or 50 kg cell. Avoid a much larger capacity (weak, noisy signal).",
           "Every part in the load path (eye bolts, threads, carabiners, band attachment) must be rated above the cell capacity.",
           "Thread eye bolts fully into both ends (thread size from the datasheet, e.g. M6/M8/M10) and lock them with nuts.",
           "Connect: <b>handle - carabiner - load cell - carabiner - band</b>. The cell must hang freely in line with the band (pure tension, no bending or side load).",
           "Strain-relieve the load-cell cable so the band never pulls on the wires.",
           "Inspect bolts, threads and band before every session; never exceed the rated capacity."])
    callout("The load cell and its mounting hardware must safely withstand the applied tensile force. Do not assume a capacity without measuring the band.", "danger")
    story.append(PageBreak())


def ch4():
    h1("Chapter 4 - Circuit Connections")
    figure(wiring_diagram(), "Figure 3 - Signal wiring (all sensors on 3V3, shared I2C bus)")
    h2("4.1 Two MPU6050 sensors on one I2C bus")
    table([["GY-521 pin", "Upper-arm sensor", "Forearm sensor", "ESP32"],
           ["VCC", "VCC", "VCC", "3V3"], ["GND", "GND", "GND", "GND"], ["SDA", "SDA", "SDA", "GPIO 21"], ["SCL", "SCL", "SCL", "GPIO 22"],
           ["AD0", "GND -> address 0x68", "3V3 -> address 0x69", "-"], ["XDA / XCL / INT", "not connected", "not connected", "-"]], [32, 45, 45, 48])
    p("Both modules share SDA and SCL (a bus). Each I2C device must have a unique address; the AD0 pin selects 0x68 (LOW) or 0x69 (HIGH). "
      "Never leave AD0 unconnected. Keep the forearm cable short (< 50 cm) and twist SDA/SCL with GND wires. If communication errors occur, "
      "set <font face='Courier'>I2C_CLOCK_HZ</font> to <font face='Courier'>100000UL</font> in config.h.")
    h2("4.2 HX711 and S-type load cell")
    table([["Load-cell wire", "HX711", "Function"], ["Excitation +", "E+", "Bridge supply +"], ["Excitation -", "E-", "Bridge supply -"],
           ["Signal +", "A+", "Output + (channel A, gain 128)"], ["Signal -", "A-", "Output -"], ["Shield (if any)", "GND", "Optional noise shield"]], [45, 30, 95])
    table([["HX711 pin", "ESP32", "Note"], ["VCC (and VDD)", "3V3", "DT logic level = supply; 3.3 V keeps it ESP32-safe"], ["GND", "GND", ""],
           ["DT / DOUT", "GPIO 16", "PIN_HX711_DT in config.h (configurable)"], ["SCK / PD_SCK", "GPIO 4", "PIN_HX711_SCK in config.h (configurable)"]], [35, 30, 105])
    callout("Load-cell wire colours are NOT standardised. Red/black/green/white is common but not guaranteed. Use the manufacturer's datasheet. "
            "Without one: measure the resistance of all six wire pairs - the excitation pair and the signal pair read the full bridge resistance "
            "(excitation usually slightly higher, e.g. ~400 vs ~350 ohm), the other four pairs read about 3/4 of it. If force reads negative when pulling, swap A+ and A-.", "warn")
    h2("4.3 Power supply")
    figure(power_diagram(), "Figure 4 - Battery power chain (only after USB tests pass)")
    table([["From", "To"], ["18650 holder + / -", "TP4056 B+ / B-"], ["TP4056 OUT+ / OUT-", "Boost converter IN+ / IN-"],
           ["Boost OUT+ (5.0 V)", "ESP32 VIN (5V)"], ["Boost OUT-", "ESP32 GND"], ["ESP32 3V3 / GND", "Both MPU6050 and HX711"]], [70, 100])
    bullets(["<b>TP4056 is a charging module, not a voltage regulator</b>; its OUT pins carry raw battery voltage (3.0-4.2 V).",
             "Never connect the battery or TP4056 OUT directly to the ESP32 5V/VIN or 3V3 pins. Always use the boost converter.",
             "Measure the boost converter output (5.0 V) with a multimeter before connecting the ESP32.",
             "Use a protected cell and a TP4056 module with protection IC; check that the cell accepts ~1 A charge current.",
             "Do not connect USB and battery power simultaneously unless your board schematic confirms diode isolation.",
             "There is no switch in the approved list: switch off by disconnecting the boost output jumper or removing the cell."])
    h2("4.4 Safety checklist")
    table([["#", "Check before powering"], ["1", "First test on USB power only, battery circuit disconnected"], ["2", "All grounds common"],
           ["3", "Sensors powered from 3V3, never 5 V"], ["4", "Boost output measured at 5.0 V"], ["5", "Battery polarity correct, no exposed contacts"],
           ["6", "TP4056 OUT never wired directly to the ESP32"], ["7", "Load-path hardware rated above band force"], ["8", "Cables strain-relieved"]], [10, 160])
    story.append(PageBreak())


def ch5():
    h1("Chapter 5 - Development Environment Setup (Windows)")
    table([["Tool", "Download", "Notes"], ["Python 3.11 / 3.12", "python.org/downloads", "Tick 'Add python.exe to PATH'"],
           ["VS Code", "code.visualstudio.com", "Extensions: Python, ESLint, Prettier"], ["Arduino IDE 2.x", "arduino.cc/en/software", "For the ESP32 firmware"],
           ["Node.js LTS (22.x)", "nodejs.org", "Includes npm and npx"], ["Git", "git-scm.com", "Version control / GitHub"],
           ["Android Studio", "developer.android.com/studio", "Android SDK + platform tools for the development build"],
           ["MongoDB Atlas", "mongodb.com/atlas", "Free cloud database (Chapter 9)"]], [38, 52, 80])
    p("Verify the installations in <b>Windows PowerShell</b>:")
    code("""
python --version
node --version
npm --version
git --version
""")
    p("If PowerShell blocks virtual-environment activation, allow local scripts once for your user:")
    code("Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned")
    p("Get the project (clone from your GitHub repository or copy the folder):")
    code("""
cd "D:\\Student Projects"
git clone https://github.com/<your-account>/physioband-ai.git PhysioBand
cd PhysioBand
""")
    p("React Native uses Expo. No global install is needed; commands run through <font face='Courier'>npx expo ...</font>. "
      "For the Android development build, Android Studio must install an SDK and you need USB debugging enabled on the phone "
      "(Settings -> About phone -> tap Build number 7 times -> Developer options -> USB debugging).")
    story.append(PageBreak())


def ch6():
    h1("Chapter 6 - ESP32 Firmware Setup")
    steps(["Install <b>Arduino IDE 2.x</b>.",
           "<b>ESP32 board package</b>: File -> Preferences -> Additional boards manager URLs: "
           "<font face='Courier'>https://espressif.github.io/arduino-esp32/package_esp32_index.json</font>. Then Tools -> Board -> Boards Manager -> search <b>esp32</b> (Espressif) -> Install (tested 3.3.7).",
           "<b>Library</b>: Sketch -> Include Library -> Manage Libraries -> install <b>HX711</b> by Bogdan Necula. (BLE, Wire, Preferences are part of the ESP32 package.)",
           "Open <font face='Courier'>firmware/esp32_physioband/esp32_physioband.ino</font> (the .h files open as tabs).",
           "Tools -> Board -> esp32 -> <b>ESP32 Dev Module</b>.",
           "Connect the ESP32 by USB; Tools -> Port -> select the new <b>COM</b> port (install the CP210x or CH340 USB driver if none appears).",
           "Click <b>Upload</b>. If it stays at 'Connecting...', hold the BOOT button until uploading starts.",
           "Open Tools -> Serial Monitor at <b>115200 baud</b>, line ending <b>Newline</b>."])
    h2("6.1 Verify the sensors")
    code("""
=== PhysioBand AI firmware 1.0.0 ===
[I2C] Devices found: 0x68 0x69
[IMU] upper-arm at 0x68 OK
[IMU] forearm at 0x69 OK
[HX711] OK, factor=21000.00 counts/kg (DEFAULT - run 'cal <kg>'), offset=...
[BLE] Advertising as 'PhysioBand-A2F0'
""")
    table([["Command", "Purpose"], ["status", "Sensor, calibration and BLE status"], ["i2c", "Scan the I2C bus (expect 0x68 and 0x69)"],
           ["read", "One sample in physical units (g, deg/s, N)"], ["debug on / off", "Print a sample every 2 s"],
           ["tare", "Zero the load cell (band attached but slack)"], ["cal <kg>", "Calibrate with a known hanging mass"],
           ["factor <value>", "Set the HX711 factor directly"], ["gyrocal", "Gyro bias calibration (sensors still for 3 s)"],
           ["csv on / off", "CSV stream for ml/scripts/collect_data.py"]], [40, 130])
    h2("6.2 Testing MPU6050 readings")
    p("Send <font face='Courier'>read</font> with the sensors lying flat: one accelerometer axis reads about +/-1.0 g, the others near 0, gyro near 0 deg/s. "
      "Rotate a sensor: the gyro values change and the 1 g moves between axes.")
    h2("6.3 Testing HX711 and calibrating the load cell")
    steps(["<font face='Courier'>tare</font> with no load.", "Pull the band: <font face='Courier'>read</font> shows the raw value and force changing.",
           "Hang a known mass, e.g. 2.0 kg, freely from the cell and send <font face='Courier'>cal 2.0</font>. The factor is saved in flash.",
           "Check: <font face='Courier'>read</font> should show about 19.6 N (2.0 x 9.81).",
           "Place both IMUs still and send <font face='Courier'>gyrocal</font>."])
    callout("HX711_DEFAULT_CALIBRATION_FACTOR in config.h is only a placeholder. The real factor depends on your specific load cell and MUST be measured with 'cal <kg>'.", "warn")
    h2("6.4 Testing BLE")
    p("Install a generic BLE scanner app (for example nRF Connect) on the phone. A device named <b>PhysioBand-XXXX</b> with service "
      "<font face='Courier'>7b1e0001-5c3a-4d8e-9f21-6a0b3c4d5e6f</font> must appear. Then test with the PhysioBand app (Chapter 7).")
    story.append(PageBreak())


def ch7():
    h1("Chapter 7 - Frontend (Mobile App) Setup")
    callout("react-native-ble-plx is a native module. It does NOT work in the standard Expo Go app. You must build and install an Expo "
            "development build (npx expo run:android or EAS Build). Expo Go / web can only be used to preview screens; BLE then shows 'unavailable'.", "warn")
    steps(["Open the folder in a terminal: <font face='Courier'>cd frontend</font>",
           "Install dependencies: <font face='Courier'>npm install</font> (BLE, navigation, SVG charts, secure storage are already listed in package.json).",
           "Create <font face='Courier'>.env</font> from <font face='Courier'>.env.example</font> and set the backend URL (use your PC's IPv4 from <font face='Courier'>ipconfig</font>, not localhost).",
           "Connect the Android phone by USB with USB debugging enabled (check with <font face='Courier'>adb devices</font>).",
           "Build and install the development build: <font face='Courier'>npx expo run:android</font> (first build takes several minutes).",
           "Later runs: <font face='Courier'>npx expo start --dev-client</font> and open the installed PhysioBand AI app."])
    code("""
cd frontend
npm install
copy .env.example .env
notepad .env        # EXPO_PUBLIC_API_URL=http://192.168.1.20:8000/api/v1
npx expo run:android
""")
    p("Alternative without Android Studio: <font face='Courier'>npx eas-cli@latest build --profile development --platform android</font> builds in the cloud and gives an installable APK.")
    h2("7.1 Bluetooth permissions")
    p("On first scan Android asks for <b>Nearby devices</b> (Android 12+) or <b>Location</b> (Android 11 and below). Allow it. "
      "If denied: Settings -> Apps -> PhysioBand AI -> Permissions. Bluetooth must be switched on.")
    h2("7.2 Scanning and receiving sensor data")
    steps(["Power the ESP32 (USB first).", "In the app: Device tab -> <b>Scan for devices</b> -> tap <b>PhysioBand-XXXX</b> -> Connect.",
           "The Device screen shows 'Receiving data', ~50 Hz, and the status of upper-arm IMU, forearm IMU, load cell and calibration, plus a live tension trace.",
           "The device is registered automatically with the backend on each connection.",
           "Tare and gyro calibration can also be started from this screen."])
    h2("7.3 App screens")
    table([["Screen", "Content"], ["Splash", "Logo and loading animation while the session is restored"], ["Login / Register", "Email + password, validation, backend auth"],
           ["Dashboard", "Today's reps, correct / incorrect, quality ring, week chart, recent workouts, Start Workout"],
           ["Device connection", "Scan, connect / disconnect, sensor availability, tension, calibration"],
           ["Exercise selection", "Biceps Curl (active); other exercises shown as Coming soon"],
           ["Live workout", "Rep counter, per-rep feedback, counts per class, arm status, band tension, cloud/BLE status"],
           ["Workout result", "Totals, breakdown, tension, duration, per-rep chart, suggestions"],
           ["History", "Quality trend, reps per day, paginated sessions"], ["Profile & settings", "Account, password, devices, AI model info, logout"]], [40, 130])
    story.append(PageBreak())


def ch8():
    h1("Chapter 8 - Backend Setup")
    code("""
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
notepad .env
""")
    table([["Variable", "Value"], ["MONGODB_URI", "Atlas connection string (Chapter 9)"], ["MONGODB_DB_NAME", "physioband_ai"],
           ["JWT_SECRET_KEY", "long random secret (see command below)"], ["ML_MODEL_PATH", "../ml/saved_models/biceps_curl_quality.pkl"],
           ["CORS_ORIGINS", "* (development)"]], [45, 125])
    code('python -c "import secrets; print(secrets.token_urlsafe(48))"')
    p("Start the API (0.0.0.0 makes it reachable from the phone on the same Wi-Fi):")
    code("uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    bullets(["Swagger UI: <font face='Courier'>http://localhost:8000/docs</font> - try every endpoint ('Authorize' with the token from login).",
             "Health: <font face='Courier'>http://localhost:8000/health</font> - shows database connection and model status.",
             "Allow Python through the Windows Firewall on <b>private</b> networks when prompted, otherwise the phone cannot connect.",
             "Run tests: <font face='Courier'>python -m pytest -q</font> (24 tests, in-memory database)."])
    h2("8.1 Main endpoints")
    table([["Method", "Endpoint", "Purpose"], ["POST", "/api/v1/auth/register, /auth/login", "Account and JWT token"], ["GET", "/api/v1/auth/me", "Current user"],
           ["POST/GET", "/api/v1/devices/register, /devices", "ESP32 registration"], ["GET", "/api/v1/exercises", "Exercise catalogue"],
           ["POST", "/api/v1/workouts/start", "Start a session"], ["POST", "/api/v1/workouts/{id}/sensor-data", "Upload batch, live analysis"],
           ["POST", "/api/v1/workouts/{id}/analyze, /complete", "Full analysis, finish session"], ["GET", "/api/v1/workouts, /workouts/{id}", "History, detail"],
           ["POST/GET", "/api/v1/ml/predict, /ml/model-info", "Stateless prediction, model status"], ["GET", "/api/v1/dashboard/summary, /performance", "Analytics"]], [22, 70, 78])
    story.append(PageBreak())


def ch9():
    h1("Chapter 9 - MongoDB Atlas Setup")
    steps(["Create an account at <b>mongodb.com/atlas</b>.", "Create a project, e.g. <b>PhysioBand AI</b>.",
           "Create a cluster: choose the <b>free tier (M0)</b> if available and a region close to you.",
           "<b>Database Access</b> -> Add New Database User -> username + strong password, role 'Read and write to any database'.",
           "<b>Network Access</b> -> Add IP Address -> 'Add current IP address' (for demos you may add 0.0.0.0/0 temporarily; remove it afterwards).",
           "<b>Database -> Connect -> Drivers -> Python</b>: copy the connection string "
           "<font face='Courier'>mongodb+srv://&lt;user&gt;:&lt;password&gt;@&lt;cluster&gt;/?retryWrites=true&amp;w=majority</font>.",
           "Paste it into <font face='Courier'>backend/.env</font> as MONGODB_URI (URL-encode special characters in the password, e.g. @ -> %40).",
           "Start FastAPI; the log shows <i>Connected to MongoDB database 'physioband_ai'</i> and /health shows connected: true.",
           "The backend creates the six collections, their indexes and the exercise catalogue automatically on first start.",
           "After a workout, open <b>Browse Collections</b> and check the saved data (below)."])
    table([["Collection", "Contents", "Key index"], ["users", "name, email, password hash, profile", "unique email"],
           ["devices", "device_id, name, firmware, user", "unique (user_id, device_id)"], ["exercises", "catalogue, is_active flag", "_id slug"],
           ["workout_sessions", "times, reps, quality, tension, status", "(user_id, start_time)"], ["sensor_records", "one document per ~1 s batch (arrays)", "unique (session_id, batch_seq)"],
           ["workout_feedback", "one document per repetition", "unique (session_id, repetition_number)"]], [35, 75, 60])
    h2("9.1 Verifying saved workout data")
    bullets(["workout_sessions: filter <font face='Courier'>{ \"status\": \"completed\" }</font>, sort <font face='Courier'>{ \"start_time\": -1 }</font> - totals must match the app.",
             "workout_feedback: filter <font face='Courier'>{ \"session_id\": \"&lt;session id&gt;\" }</font> - one document per rep.",
             "sensor_records: same filter - sample_count values add up to the session's sample_count."])
    callout("Keep credentials secret: they live only in backend/.env, which is listed in .gitignore. Never hard-code passwords in source files, "
            "never commit .env, and rotate the database password if it was ever shared.", "danger")
    story.append(PageBreak())


def ch10():
    h1("Chapter 10 - ML Model Setup")
    code("""
cd ml
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
""")
    h2("10.1 Synthetic demonstration data vs. real collected data")
    p("<b>Synthetic data</b> (<font face='Courier'>scripts/generate_synthetic_data.py</font>) is simulated from a simple physical model. It only proves that "
      "the software pipeline works end to end. The included demo model was trained on 10 simulated participants and scores 100 % on 3 held-out "
      "simulated participants - this number is <b>meaningless for real use</b> because the synthetic classes were generated to be separable. "
      "<b>Real data</b> recorded from volunteers with the actual hardware is required for a meaningful model; report only metrics from real held-out volunteers.")
    h2("10.2 Collecting and labelling real samples")
    steps(["Mount the sensors (Chapter 3), <font face='Courier'>tare</font>, <font face='Courier'>gyrocal</font>, close the Arduino Serial Monitor.",
           "For each volunteer record one set per label (8-12 reps): correct, incomplete, too_fast, irregular.",
           "Run: <font face='Courier'>python scripts\\collect_data.py --port COM5 --participant P01 --label correct --reps 10</font>, press Enter, perform the set, Ctrl+C.",
           "Repeat for every label and volunteer (at least 3 volunteers, ideally 8 or more). Files go to data/raw/&lt;participant&gt;/.",
           "Validate: <font face='Courier'>python scripts\\validate_dataset.py data\\raw</font> (rep count per set, sensor issues)."])
    p("CSV columns: participant_id, session_id, exercise_id, label, is_synthetic, timestamp_ms, ua_ax..ua_gz, fa_ax..fa_gz, force_n.")
    h2("10.3 Features, training, evaluation")
    code("""
python scripts\\extract_features.py data\\raw --out data\\processed\\features_collected.csv
python scripts\\train_model.py --data data\\raw
python scripts\\evaluate_model.py --data data\\raw\\P09
python scripts\\predict.py data\\sample\\sample_biceps_curl_synthetic.csv
""")
    bullets(["Pipeline: validation -> resampling to 50 Hz -> calibration -> 5 Hz Butterworth low-pass -> complementary-filter gravity tracking -> elbow angle -> peak/cycle rep counting -> 31 features -> Random Forest.",
             "Split is <b>participant-wise</b> (no volunteer in both train and test).",
             "Reports: accuracy, precision, recall, F1 per class, confusion matrix PNG, feature importance PNG in ml/reports/.",
             "The model is saved to ml/saved_models/biceps_curl_quality.pkl, which FastAPI loads at start-up. Restart the backend after retraining.",
             "Check: <font face='Courier'>GET /api/v1/ml/model-info</font> shows algorithm, version, dataset_type (synthetic / collected) and validated: false."])
    story.append(PageBreak())


def ch11(examples):
    h1("Chapter 11 - Connecting Everything")
    p("<b>ESP32 -> BLE -> React Native -> FastAPI -> Python ML -> MongoDB Atlas -> mobile feedback</b>")
    h2("11.1 BLE UUID configuration")
    table([["Item", "Value"], ["Device name", "PhysioBand-XXXX"], ["Service", "7b1e0001-5c3a-4d8e-9f21-6a0b3c4d5e6f"],
           ["SENSOR_DATA (notify)", "7b1e0002-5c3a-4d8e-9f21-6a0b3c4d5e6f"], ["CONTROL (write)", "7b1e0003-... : 0x01 start, 0x02 stop, 0x03 tare, 0x04 gyro cal"],
           ["DEVICE_INFO (read)", "7b1e0004-... : JSON device id, firmware, protocol, sample rate"], ["MTU", "App requests 185; packet = 8 + 33 x N bytes (N <= 4)"]], [45, 125])
    p("The same values are defined in <font face='Courier'>firmware/esp32_physioband/config.h</font> and <font face='Courier'>frontend/src/constants/ble.ts</font>. "
      "The app scans, connects, requests the MTU, discovers services, reads DEVICE_INFO, subscribes to SENSOR_DATA notifications and writes 0x01 to CONTROL.")
    h2("11.2 Data packet format (protocol v1, little-endian)")
    table([["Offset", "Size", "Field"], ["0", "1", "protocol version = 1"], ["1", "1", "sample count N"], ["2", "2", "packet sequence"], ["4", "4", "device id"],
           ["8+33i", "4", "timestamp ms"], ["+4", "12", "upper arm ax ay az (mg), gx gy gz (0.1 deg/s) int16"], ["+16", "12", "forearm (same layout)"],
           ["+28", "4", "force int32 (0.01 N)"], ["+32", "1", "status bits: 0 UA ok, 1 FA ok, 2 load cell ok, 3 LC calibrated, 4 gyro calibrated"]], [20, 15, 135])
    p("Example decoded sample (the app turns each packet into this structure):")
    code(jdump(examples["sensor_data_request"]["samples"][0]))
    h2("11.3 API request (app -> backend, every ~1 s)")
    req = dict(examples["sensor_data_request"])
    req["samples"] = req["samples"][:1] + ["... 49 more samples ..."]
    code("POST /api/v1/workouts/<session_id>/sensor-data\nAuthorization: Bearer <token>\n" + jdump(req))
    h2("11.4 ML prediction response (backend -> app)")
    res = examples["sensor_data_response"]
    a = res["analysis"]
    rep = dict(a["new_reps"][0])
    rep.pop("features", None)
    short = {k: res[k] for k in ("session_id", "batch_seq", "accepted", "duplicate", "total_samples")}
    short["analysis"] = {k: a[k] for k in ("mode", "total_reps", "correct_reps", "incorrect_reps", "quality_score", "avg_tension_n")}
    short["analysis"]["new_reps"] = [rep]
    short["analysis"]["live"] = a["live"]
    short["analysis"]["model"] = {k: a["model"].get(k) for k in ("available", "algorithm", "dataset_type", "validated")}
    code(jdump(short))
    p("These values were produced by the real code with a synthetic stream and the demo model.")
    h2("11.5 MongoDB storage")
    bullets(["Each batch -> one sensor_records document (arrays of the 50 samples).", "Each newly completed rep -> one workout_feedback document.",
             "Session totals (reps, quality, tension) -> workout_sessions, finalised by /complete."])
    h2("11.6 Error and reconnection handling")
    table([["Situation", "Behaviour"], ["BLE drop", "App retries 5 x every 2.5 s; firmware re-advertises; banner in Live Workout"],
           ["No internet", "Batches queued and re-sent in order; app shows 'Cloud AI analysis unavailable' - no fabricated predictions"],
           ["Retried upload", "Same batch_seq ignored (idempotent)"], ["App closed mid-workout", "Session closed as interrupted when the next workout starts"],
           ["Sensor fault", "Status bit clears -> values sent as null -> pipeline interpolates short gaps"], ["Database down", "/health reports it, API returns 503"]], [40, 130])
    story.append(PageBreak())


def ch12():
    h1("Chapter 12 - Testing and Troubleshooting")
    table([["Problem", "How to verify", "Fix"],
           ["MPU6050 not detected", "'i2c' misses 0x68/0x69", "Check 3V3, GND, SDA 21, SCL 22; re-seat wires"],
           ["I2C address conflict", "Only one address found", "Upper-arm AD0 to GND, forearm AD0 to 3V3"],
           ["Incorrect orientation", "Elbow angle not ~0 deg with straight arm", "Both sensors: chip out, X arrow to hand"],
           ["HX711 shows zero", "'HX711 NOT RESPONDING'", "DT 16, SCK 4, 3V3; check E+/E-/A+/A-"],
           ["Calibration problems", "2 kg not ~19.6 N", "tare unloaded, hang mass freely, cal 2.0"],
           ["BLE not discovered", "Scanner app finds nothing", "Firmware advertising? Development build (not Expo Go)? Permission? Distance?"],
           ["BLE disconnection", "'Reconnecting' banner", "Stay close; auto-retry; avoid USB + battery together"],
           ["Permission issues", "'Permission needed'", "Allow Nearby devices / Location in Android settings"],
           ["FastAPI connection error", "'Cannot reach the server'", "Same Wi-Fi, PC IPv4 in .env, --host 0.0.0.0, firewall"],
           ["MongoDB Atlas error", "/health connected: false", "URI, password encoding, Network Access IP, cluster running"],
           ["ML model not loading", "/health model.available false", "Train model, check ML_MODEL_PATH, scikit-learn 1.6.1"],
           ["Invalid sensor packets", "Invalid packets counter / 422", "Reconnect for MTU; ua/fa need 6 values"],
           ["Incorrect rep count", "Count differs", "Curl > 25 deg, check IMU status, tune thresholds with real data"]], [38, 52, 80])
    h2("12.1 Automated tests")
    code("""
cd backend;  .\\.venv\\Scripts\\python.exe -m pytest -q        # 24 tests
cd ..\\ml;   python -m pytest -q                               # 18 tests
cd ..\\frontend; npx tsc --noEmit; npx expo-doctor
""")
    h2("12.2 End-to-end test without hardware")
    code("backend\\.venv\\Scripts\\python.exe scripts\\simulate_device.py --api http://localhost:8000/api/v1")
    p("The simulator logs in, streams a synthetic workout in 1-second batches, prints per-rep feedback and completes the session.")
    callout("Tests requiring the physical hardware cannot be completed in software: real I2C detection, orientation, HX711 calibration, BLE with a phone, "
            "battery operation and real-world accuracy. Record their results yourself during integration.", "info")
    story.append(PageBreak())


def ch13():
    h1("Chapter 13 - Complete Project Execution (Demonstration Day)")
    steps(["<b>Connect hardware</b>: sensors strapped (same orientation), load cell in-line, PCB on strap. Power by USB (or the verified battery circuit).",
           "<b>Upload ESP32 firmware</b> (if not already); Serial Monitor -> <font face='Courier'>status</font> shows both IMUs, HX711 OK, calibrated. Close the Serial Monitor.",
           "<b>Start MongoDB Atlas</b>: log in, check the cluster is running (resume if paused) and your current IP is in Network Access.",
           "<b>Start FastAPI</b>: <font face='Courier'>cd backend; .\\.venv\\Scripts\\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000</font>",
           "<b>Verify the ML model</b>: open http://localhost:8000/health -> database connected: true, model available: true.",
           "<b>Start the app</b>: <font face='Courier'>cd frontend; npx expo start --dev-client</font>, open PhysioBand AI on the phone, log in.",
           "<b>Connect the ESP32</b>: Device tab -> Scan -> PhysioBand-XXXX -> check 'Receiving data' and all sensors OK; tare the load cell.",
           "<b>Select Biceps Curl</b>: Dashboard -> Start Workout -> Biceps Curl.",
           "<b>Start a workout</b>: press Start; timer runs and status chips show 'Sensors 50 Hz' and 'Cloud AI live'.",
           "<b>Perform repetitions</b>: a few correct curls, then one incomplete, one fast and one jerky curl to demonstrate feedback.",
           "<b>View AI analysis</b>: rep counter, per-rep feedback card, counts per class, arm status and band tension update live.",
           "<b>Complete the workout</b>: press Finish workout -> result screen with totals, tension, per-rep chart and suggestions.",
           "<b>Verify in MongoDB Atlas</b>: Browse Collections -> workout_sessions (newest), workout_feedback and sensor_records for that session id; the app's History tab shows the session."])
    callout("Explain to examiners that the shipped classifier is a demo trained on synthetic data. Show the real-data workflow (collect_data -> train_model) "
            "and present only metrics obtained from real held-out volunteers.", "tip")


def main():
    examples = json.loads((ROOT / "docs" / "examples" / "api_examples.json").read_text(encoding="utf-8"))
    cover()
    contents()
    ch1(); ch2(); ch3(); ch4(); ch5(); ch6(); ch7(); ch8(); ch9(); ch10(); ch11(examples); ch12(); ch13()

    def decorate(canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, A4[1] - 10 * mm, A4[0], 10 * mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 8.5)
            canvas.drawString(15 * mm, A4[1] - 6.5 * mm, "PhysioBand AI - Hardware & Software Setup Guide")
            canvas.setFillColor(TEAL)
            canvas.rect(0, A4[1] - 10.8 * mm, A4[0], 0.8 * mm, fill=1, stroke=0)
        canvas.setFillColor(GREY)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                            title="PhysioBand AI - Complete Hardware and Software Setup Guide", author="PhysioBand AI project")
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
