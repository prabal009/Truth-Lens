"""
TruthLens — Sample Dataset Generator
Creates a curated CSV of fake and real news samples for model training.
Run this once before train_model.py if you don't have Kaggle access.
"""

import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import csv
import random

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
OUT_FILE  = os.path.join(DATA_DIR, "sample_news.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Fake News Samples ──────────────────────────────────────────────────────────
FAKE_TEMPLATES = [
    "URGENT!!! {topic} has been CANCELLED immediately. Forward this to all students NOW!!!",
    "BREAKING: {topic} postponed due to {reason}. Share with everyone immediately!",
    "🚨🚨 ALERT: {topic} is suspended until further notice. Tell everyone ASAP! 🚨🚨",
    "*Forwarded as received* {topic} will not happen tomorrow. Reliable source confirmed.",
    "You won't believe this! {topic} has been {action}. The truth is shocking!",
    "EXCLUSIVE LEAKED INFO: {topic} is completely {action}. Share before it gets deleted!",
    "IMPORTANT MESSAGE: Due to {reason}, {topic} is now {action}. Share immediately!",
    "100% confirmed: {topic} {action}. Don't ignore this, forward to everyone now!",
    "Breaking news: Secret information about {topic} - they don't want you to know this!",
    "Urgent warning: {topic} is dangerous. Forward this to protect everyone you know.",
    "Message from reliable source: {topic} cancelled without prior notice. Tell everyone.",
    "MUST SHARE!!! {topic} has been unexpectedly {action}. All students must know NOW!!!",
    "Shocking revelation: {topic} is a complete fraud. Share this viral truth immediately!",
    "Last minute information: {topic} tomorrow is {action}. Stay home, forward this message.",
    "Alert from higher authorities: {topic} {action} with immediate effect. Share urgently!",
    "Hidden truth revealed: {topic} is not what they tell you. Spread awareness now!",
    "VIRAL: {topic} {action} - government trying to hide this. Share before its deleted!",
    "WARNING: If you attend {topic} tomorrow you might {reason}. Share to save people!",
    "Confirmed by insiders: {topic} is {action}. The real reason will shock you!",
    "Don't attend {topic}! It has been {action} due to {reason}. Spread the word!",
]

TOPICS    = ["exam", "class", "college", "university event", "result declaration",
             "seminar", "fest", "annual function", "sports day", "convocation",
             "viva examination", "lab practical", "project submission", "workshop"]
REASONS   = ["government order", "technical issues", "security concerns", "COVID protocol",
             "unexpected maintenance", "staff absence", "administrative decision",
             "safety hazard", "power failure", "water shortage"]
ACTIONS   = ["cancelled", "postponed", "suspended", "rescheduled", "called off",
             "banned", "delayed indefinitely", "moved online", "merged with another event"]

def make_fake(n: int):
    rows = []
    for _ in range(n):
        tpl    = random.choice(FAKE_TEMPLATES)
        topic  = random.choice(TOPICS)
        reason = random.choice(REASONS)
        action = random.choice(ACTIONS)
        text   = tpl.format(topic=topic, reason=reason, action=action)
        text  += " " + random.choice([
            "This is 100% real information.",
            "Please verify and share.",
            "Do not ignore this message.",
            "Passed on from group admin.",
            "Received from department WhatsApp group.",
        ])
        rows.append((text, 0))
    return rows

# ── Real News Samples ──────────────────────────────────────────────────────────
REAL_TEMPLATES = [
    "Dear Students, The {topic} scheduled for {date} will be held as per the original timetable in {venue}. — {authority}",
    "Notice: The {topic} has been rescheduled to {date} at {time}. Please check the official portal for details. — {authority}",
    "This is to inform all students that {topic} will take place on {date} as announced. Attendance is mandatory. — {authority}",
    "Official communication: {topic} result will be declared on {date}. Check the official website for updates. — {authority}",
    "Reminder: {topic} registration deadline is {date}. Visit the administrative office for further queries. — {authority}",
    "Students are informed that {topic} will commence from {date} as per the academic calendar. — {authority}",
    "Important: The venue for {topic} has been changed to {venue}. All other details remain the same. — {authority}",
    "Academic Notice: {topic} will be conducted online via the college portal on {date}. — {authority}",
    "{authority} announces the commencement of {topic} from {date}. All students are requested to prepare accordingly.",
    "Update: {topic} originally scheduled for {date} stands confirmed. No changes have been made. — {authority}",
    "The {authority} hereby informs students that {topic} is scheduled on {date} in {venue}. Be present on time.",
    "Notice from {authority}: {topic} registration is now open. Last date to apply is {date}.",
    "Students of {year} are reminded that {topic} is compulsory. Contact the office for any clarifications. — {authority}",
    "{authority}: The timetable for {topic} is now available on the college website. Check before {date}.",
    "Circular No. {num}: {topic} will be held as per schedule on {date}. Carry your ID cards. — {authority}",
]

OFFICIAL_TOPICS = [
    "mid-semester examination", "end-semester examination", "project viva",
    "practical examination", "sports meet", "annual cultural fest",
    "convocation ceremony", "alumni meet", "workshop on machine learning",
    "seminar on cybersecurity", "industrial visit", "library book submission",
    "fee payment", "scholarship application", "result declaration",
]
DATES      = ["15th May 2026", "20th May 2026", "25th May 2026", "1st June 2026",
              "Monday 10AM", "Tuesday 9AM", "Wednesday 2PM", "Friday 11AM"]
TIMES      = ["10:00 AM", "9:30 AM", "2:00 PM", "11:00 AM"]
VENUES     = ["Room 204", "Auditorium A", "Seminar Hall", "Lab Block 3",
              "Main Hall", "Examination Hall", "Computer Centre"]
AUTHORITIES = [
    "Prof. Sharma, HOD Computer Science",
    "Dr. Mehta, Dean Academic Affairs",
    "The Examination Controller",
    "Student Affairs Office",
    "Department of Information Technology",
    "Principal's Office",
    "The Registrar",
    "Academic Section",
]
YEARS = ["first year", "second year", "third year", "final year", "all"]
NUMS  = ["101", "202", "305", "418", "523"]

def make_real(n: int):
    rows = []
    for _ in range(n):
        tpl   = random.choice(REAL_TEMPLATES)
        text  = tpl.format(
            topic     = random.choice(OFFICIAL_TOPICS),
            date      = random.choice(DATES),
            time      = random.choice(TIMES),
            venue     = random.choice(VENUES),
            authority = random.choice(AUTHORITIES),
            year      = random.choice(YEARS),
            num       = random.choice(NUMS),
        )
        rows.append((text, 1))
    return rows

# ── Write CSV ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🛡️  TruthLens — Dataset Generator")
    print("=" * 45)

    N_PER_CLASS = 3000  # 3000 fake + 3000 real = 6000 total

    fake_rows = make_fake(N_PER_CLASS)
    real_rows = make_real(N_PER_CLASS)
    all_rows  = fake_rows + real_rows
    random.shuffle(all_rows)

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(all_rows)

    print(f"✅  Generated {len(all_rows):,} samples ({N_PER_CLASS} fake + {N_PER_CLASS} real)")
    print(f"💾  Saved to: {OUT_FILE}")
    print("\nNext step: Run  python train_model.py")
