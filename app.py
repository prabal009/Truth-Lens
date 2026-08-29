"""
TruthLens — Flask Backend
REST API + WhatsApp Webhook + SQLite database
"""

import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import sqlite3
import joblib
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g
from flask_cors import CORS
from dotenv import load_dotenv

import heuristic
import similarity as sim_engine

load_dotenv()

# ── App Setup ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
CORS(app)

SECRET_KEY     = os.getenv("SECRET_KEY", "truthlens-dev-key")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DB_PATH        = os.path.join(BASE_DIR, "truthlens.db")
MODELS_DIR     = os.path.join(BASE_DIR, "models")
MODEL_PATH      = os.path.join(MODELS_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(MODELS_DIR, "vectorizer.pkl")

# ── Load ML Models ─────────────────────────────────────────────────────────────
_model      = None
_vectorizer = None
_meta       = {}

def load_models():
    global _model, _vectorizer, _meta
    if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
        _model      = joblib.load(MODEL_PATH)
        _vectorizer = joblib.load(VECTORIZER_PATH)
        meta_path = os.path.join(MODELS_DIR, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                _meta = json.load(f)
        print("✅  ML models loaded successfully.")
    else:
        print("⚠️   ML models not found. Run: python generate_dataset.py && python train_model.py")
        print("    The system will use heuristic analysis only until models are trained.")

load_models()

# ── Database ───────────────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE IF NOT EXISTS analyses (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                text      TEXT NOT NULL,
                ml_score  INTEGER DEFAULT NULL,
                heuristic_score INTEGER NOT NULL,
                combined_score  INTEGER NOT NULL,
                verdict   TEXT NOT NULL,
                evidence  TEXT NOT NULL,
                matches   TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS announcements (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                body       TEXT NOT NULL,
                category   TEXT NOT NULL DEFAULT 'general',
                source     TEXT NOT NULL,
                pinned     INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT NOT NULL,
                context    TEXT,
                auto_score INTEGER,
                verdict    TEXT,
                votes_fake INTEGER NOT NULL DEFAULT 0,
                votes_legit INTEGER NOT NULL DEFAULT 0,
                votes_unsure INTEGER NOT NULL DEFAULT 0,
                status     TEXT NOT NULL DEFAULT 'under_review',
                created_at TEXT NOT NULL
            );
        """)
        db.commit()
        _seed_data(db)
        db.close()

def _seed_data(db):
    """Insert demo data if tables are empty."""
    count = db.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
    if count > 0:
        return

    now = datetime.utcnow().isoformat()
    announcements = [
        ("Mid-Semester Examination Schedule Released",
         "The mid-semester examination for all semesters will commence from 25th May 2026. "
         "Students are advised to check the detailed timetable on the official portal. "
         "Examinations will be held from 10:00 AM to 12:00 PM in the respective examination halls.",
         "exams", "Prof. Sharma, HOD Computer Science", 1, None),
        ("Annual Cultural Fest — Spectrum 2026",
         "Registrations for Spectrum 2026, the annual cultural festival, are now open. "
         "Last date to register is 30th May 2026. Visit spectrum.college.edu for details. "
         "Events include music, dance, drama, and technical competitions.",
         "events", "Student Affairs Office", 0, "2026-05-30T23:59:00"),
        ("Library Extended Hours During Exams",
         "The central library will remain open until 10:00 PM from 20th May to 10th June 2026 "
         "to support students during the examination period. Wi-Fi access has been upgraded.",
         "general", "Library Administration", 0, "2026-06-10T22:00:00"),
        ("Project Submission Deadline — Final Year",
         "Final year students must submit their project reports to the department office "
         "by 22nd May 2026, 5:00 PM. Late submissions will not be accepted.",
         "exams", "Department of Computer Science", 1, "2026-05-22T17:00:00"),
    ]
    db.executemany(
        "INSERT INTO announcements (title,body,category,source,pinned,expires_at,created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        [(t, b, c, s, p, e, now) for t, b, c, s, p, e in announcements]
    )

    reports = [
        ("🚨 URGENT!!! Tomorrow's exam has been CANCELLED!!! Forward to all students immediately!!!",
         "Received in WhatsApp group", 12, "likely_fake"),
        ("*Forwarded as received* College closed for 2 weeks due to government order. Don't attend.",
         None, 18, "likely_fake"),
        ("BREAKING: All semester results declared INVALID. Call 9876543210 for details.",
         "Circulating on Telegram", 8, "almost_certainly_fake"),
    ]
    for text, ctx, score, verdict in reports:
        db.execute(
            "INSERT INTO reports (text,context,auto_score,verdict,votes_fake,votes_legit,votes_unsure,status,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (text, ctx, score, verdict, random_int(3,12), random_int(0,2), random_int(0,3), "community_flagged", now)
        )
    db.commit()

import random
def random_int(a, b): return random.randint(a, b)

# ── Helpers ────────────────────────────────────────────────────────────────────
def _clean_text(text: str) -> str:
    text = re.sub(r"http\S+|www\S+", " ", text)
    return text.strip()

def _score_to_verdict(score: int) -> str:
    if score >= 81: return "highly_credible"
    if score >= 61: return "likely_safe"
    if score >= 41: return "suspicious"
    if score >= 21: return "likely_fake"
    return "almost_certainly_fake"

def _verdict_label(verdict: str) -> str:
    return {
        "highly_credible":      "✅ Highly Credible",
        "likely_safe":          "🟡 Likely Safe",
        "suspicious":           "🟠 Suspicious",
        "likely_fake":          "🔴 Likely Fake",
        "almost_certainly_fake": "💀 Almost Certainly Fake",
    }.get(verdict, verdict)

def _run_analysis(text: str, db) -> dict:
    """Run full ML + heuristic analysis and return result dict."""
    cleaned = _clean_text(text)

    # ML Prediction
    ml_score = None
    ml_evidence = []
    if _model and _vectorizer:
        vec = _vectorizer.transform([cleaned])
        proba = _model.predict_proba(vec)[0]   # [fake_prob, real_prob]
        ml_score = int(proba[1] * 100)          # real probability × 100
        confidence = max(proba) * 100
        ml_evidence = [{
            "layer": "ML Model",
            "severity": "high" if confidence > 80 else "medium",
            "message": f"Ensemble model: {proba[1]:.0%} real / {proba[0]:.0%} fake  "
                       f"(confidence: {confidence:.0f}%)",
            "score_impact": ml_score - 50,
        }]

    # Heuristic Analysis
    h_result  = heuristic.analyze(cleaned)
    h_score   = h_result.score
    h_evidence = [e.__dict__ for e in h_result.evidence]

    # Combined Score
    if ml_score is not None:
        combined = int(ml_score * 0.70 + h_score * 0.30)
    else:
        combined = h_score

    verdict = _score_to_verdict(combined)

    # Similarity Check — load last 200 analyses
    history = [
        {"id": r["id"], "text": r["text"], "verdict": r["verdict"], "score": r["combined_score"]}
        for r in db.execute(
            "SELECT id, text, verdict, combined_score FROM analyses ORDER BY id DESC LIMIT 200"
        ).fetchall()
    ]
    matches = sim_engine.find_matches(cleaned, history)
    matches_list = [m.to_dict() for m in matches]

    all_evidence = (ml_evidence or []) + h_evidence

    return {
        "ml_score":        ml_score,
        "heuristic_score": h_score,
        "combined_score":  combined,
        "verdict":         verdict,
        "verdict_label":   _verdict_label(verdict),
        "evidence":        all_evidence,
        "similar_matches": matches_list,
    }

# ── Routes: Frontend ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ── Routes: Analysis API ───────────────────────────────────────────────────────
@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    if len(text) > 5000:
        return jsonify({"error": "Text too long (max 5000 chars)"}), 400

    db = get_db()
    result = _run_analysis(text, db)

    # Persist to DB
    db.execute(
        "INSERT INTO analyses (text,ml_score,heuristic_score,combined_score,verdict,evidence,matches,created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (text, result["ml_score"], result["heuristic_score"], result["combined_score"],
         result["verdict"], json.dumps(result["evidence"]),
         json.dumps(result["similar_matches"]), datetime.utcnow().isoformat())
    )
    db.commit()
    return jsonify(result)

@app.route("/api/history", methods=["GET"])
def history():
    db = get_db()
    rows = db.execute(
        "SELECT id, text, combined_score, verdict, created_at "
        "FROM analyses ORDER BY id DESC LIMIT 50"
    ).fetchall()
    return jsonify([dict(r) for r in rows])

# ── Routes: Announcements ──────────────────────────────────────────────────────
@app.route("/api/announcements", methods=["GET"])
def list_announcements():
    db  = get_db()
    cat = request.args.get("category", "")
    q   = request.args.get("q", "")
    sql = "SELECT * FROM announcements WHERE 1=1"
    params = []
    if cat:
        sql += " AND category=?"; params.append(cat)
    if q:
        sql += " AND (title LIKE ? OR body LIKE ?)"; params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY pinned DESC, id DESC"
    rows = db.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/announcements", methods=["POST"])
def add_announcement():
    data     = request.get_json(silent=True) or {}
    password = data.get("password", "")
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 403

    title    = (data.get("title") or "").strip()
    body     = (data.get("body")  or "").strip()
    category = data.get("category", "general")
    source   = (data.get("source") or "Admin").strip()
    pinned   = int(bool(data.get("pinned", False)))
    expires  = data.get("expires_at")

    if not title or not body:
        return jsonify({"error": "title and body are required"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO announcements (title,body,category,source,pinned,expires_at,created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (title, body, category, source, pinned, expires, datetime.utcnow().isoformat())
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "status": "created"}), 201

@app.route("/api/announcements/<int:ann_id>", methods=["DELETE"])
def delete_announcement(ann_id):
    data     = request.get_json(silent=True) or {}
    password = data.get("password", "")
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    db.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
    db.commit()
    return jsonify({"status": "deleted"})

# ── Routes: Community ──────────────────────────────────────────────────────────
@app.route("/api/community", methods=["GET"])
def list_reports():
    db   = get_db()
    sort = request.args.get("sort", "latest")
    sql  = "SELECT * FROM reports"
    if sort == "trending":
        sql += " ORDER BY (votes_fake + votes_legit + votes_unsure) DESC, id DESC"
    else:
        sql += " ORDER BY id DESC"
    sql += " LIMIT 50"
    rows = db.execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/community/report", methods=["POST"])
def submit_report():
    data    = request.get_json(silent=True) or {}
    text    = (data.get("text") or "").strip()
    context = (data.get("context") or "").strip() or None
    if not text:
        return jsonify({"error": "No text provided"}), 400

    db     = get_db()
    result = _run_analysis(text, db)

    cur = db.execute(
        "INSERT INTO reports (text,context,auto_score,verdict,votes_fake,votes_legit,votes_unsure,status,created_at) "
        "VALUES (?,?,?,?,0,0,0,?,?)",
        (text, context, result["combined_score"], result["verdict"],
         "under_review", datetime.utcnow().isoformat())
    )
    db.commit()
    return jsonify({"report_id": cur.lastrowid, "auto_score": result["combined_score"],
                    "verdict": result["verdict"]}), 201

@app.route("/api/community/vote", methods=["POST"])
def vote_report():
    data      = request.get_json(silent=True) or {}
    report_id = data.get("report_id")
    vote      = data.get("vote")   # "fake" | "legit" | "unsure"
    if not report_id or vote not in ("fake", "legit", "unsure"):
        return jsonify({"error": "Invalid vote"}), 400

    db     = get_db()
    col    = f"votes_{vote}"
    db.execute(f"UPDATE reports SET {col} = {col} + 1 WHERE id=?", (report_id,))

    # Auto-update status based on votes
    row = db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if row:
        total = row["votes_fake"] + row["votes_legit"] + row["votes_unsure"]
        if total >= 5:
            if row["votes_fake"] / total >= 0.60:
                db.execute("UPDATE reports SET status='community_flagged' WHERE id=?", (report_id,))
            elif row["votes_legit"] / total >= 0.60:
                db.execute("UPDATE reports SET status='verified' WHERE id=?", (report_id,))

    db.commit()
    updated = db.execute("SELECT votes_fake,votes_legit,votes_unsure,status FROM reports WHERE id=?",
                         (report_id,)).fetchone()
    return jsonify(dict(updated) if updated else {})

# ── Routes: Stats ──────────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def stats():
    db = get_db()
    total    = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    fake_cnt = db.execute(
        "SELECT COUNT(*) FROM analyses WHERE verdict IN ('likely_fake','almost_certainly_fake','suspicious')"
    ).fetchone()[0]
    real_cnt = db.execute(
        "SELECT COUNT(*) FROM analyses WHERE verdict IN ('highly_credible','likely_safe')"
    ).fetchone()[0]
    reports  = db.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    announcements = db.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
    recent   = db.execute(
        "SELECT combined_score, verdict, created_at FROM analyses ORDER BY id DESC LIMIT 10"
    ).fetchall()
    dist = {
        "highly_credible":      db.execute("SELECT COUNT(*) FROM analyses WHERE verdict='highly_credible'").fetchone()[0],
        "likely_safe":          db.execute("SELECT COUNT(*) FROM analyses WHERE verdict='likely_safe'").fetchone()[0],
        "suspicious":           db.execute("SELECT COUNT(*) FROM analyses WHERE verdict='suspicious'").fetchone()[0],
        "likely_fake":          db.execute("SELECT COUNT(*) FROM analyses WHERE verdict='likely_fake'").fetchone()[0],
        "almost_certainly_fake":db.execute("SELECT COUNT(*) FROM analyses WHERE verdict='almost_certainly_fake'").fetchone()[0],
    }
    model_info = _meta if _meta else {"accuracy": "N/A", "f1_score": "N/A", "note": "Model not trained yet"}
    return jsonify({
        "total_analyzed":  total,
        "fake_count":      fake_cnt,
        "real_count":      real_cnt,
        "reports_count":   reports,
        "announcements":   announcements,
        "distribution":    dist,
        "recent":          [dict(r) for r in recent],
        "model_info":      model_info,
    })

@app.route("/api/model_info", methods=["GET"])
def model_info():
    if not _model:
        return jsonify({"status": "not_trained",
                        "message": "Run generate_dataset.py then train_model.py"})
    return jsonify({"status": "ready", **_meta})

# ── WhatsApp Webhook (Twilio) ──────────────────────────────────────────────────
try:
    from twilio.twiml.messaging_response import MessagingResponse
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("ℹ️   Twilio not installed — WhatsApp webhook disabled.")

TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")

def _format_whatsapp_reply(text: str, result: dict) -> str:
    score   = result["combined_score"]
    verdict = result["verdict"]
    label   = result["verdict_label"]
    matches = result.get("similar_matches", [])

    emoji = {
        "highly_credible":       "✅",
        "likely_safe":           "🟡",
        "suspicious":            "🟠",
        "likely_fake":           "🔴",
        "almost_certainly_fake": "💀",
    }.get(verdict, "🔍")

    lines = [
        "🛡️ *TruthLens Credibility Report*",
        "━━━━━━━━━━━━━━━━━━━",
        f"📊 Score: *{score}/100*",
        f"{emoji} Verdict: *{label.split(' ', 1)[-1]}*",
        "",
        "🔍 *Key Signals:*",
    ]

    evidence = result.get("evidence", [])
    shown    = 0
    for e in evidence:
        if shown >= 4: break
        sev   = e.get("severity", "low")
        icon  = "⚠️" if sev == "high" else ("🔸" if sev == "medium" else "🔹")
        msg   = e.get("message", "")[:80]
        lines.append(f"  {icon} {msg}")
        shown += 1

    if matches:
        top = matches[0]
        lines.append("")
        lines.append(f"🔄 *{top['similarity']:.0f}% similar* to a previously flagged message")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━",
        "💡 Reply *help* for commands",
        "📋 Reply *latest* for official announcements",
    ]
    return "\n".join(lines)

def _handle_bot_command(body: str, db) -> str:
    cmd = body.strip().lower()

    if cmd == "help":
        return (
            "🛡️ *TruthLens Bot — Commands*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📨 *Forward any message* → instant credibility check\n"
            "📋 *latest* → see recent verified announcements\n"
            "📊 *stats* → your usage stats\n"
            "🚩 *report <message>* → report to community\n"
            "❓ *help* → this menu"
        )

    if cmd == "stats":
        total = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        fake  = db.execute(
            "SELECT COUNT(*) FROM analyses WHERE verdict IN ('likely_fake','almost_certainly_fake')"
        ).fetchone()[0]
        return (
            f"📊 *TruthLens Stats*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Messages analyzed: {total}\n"
            f"🔴 Likely fake: {fake}\n"
            f"✅ Verified announcements: "
            f"{db.execute('SELECT COUNT(*) FROM announcements').fetchone()[0]}\n"
            f"🚩 Community reports: "
            f"{db.execute('SELECT COUNT(*) FROM reports').fetchone()[0]}"
        )

    if cmd == "latest":
        rows = db.execute(
            "SELECT title, source, created_at FROM announcements ORDER BY pinned DESC, id DESC LIMIT 3"
        ).fetchall()
        if not rows:
            return "📋 No verified announcements yet."
        lines = ["📋 *Latest Verified Announcements*\n━━━━━━━━━━━━━━━━━━━"]
        for i, r in enumerate(rows, 1):
            date = r["created_at"][:10]
            lines.append(f"{i}. *{r['title']}*\n   — {r['source']} ({date})")
        return "\n\n".join(lines)

    if cmd.startswith("report "):
        report_text = body[7:].strip()
        if len(report_text) < 10:
            return "❌ Please include the message after 'report'.\nExample: report URGENT exam cancelled!!"
        result = _run_analysis(report_text, db)
        db.execute(
            "INSERT INTO reports (text,context,auto_score,verdict,votes_fake,votes_legit,votes_unsure,status,created_at) "
            "VALUES (?,?,?,?,0,0,0,?,?)",
            (report_text, "WhatsApp submission", result["combined_score"],
             result["verdict"], "under_review", datetime.utcnow().isoformat())
        )
        db.commit()
        return (f"🚩 *Report submitted!*\n"
                f"Auto-score: {result['combined_score']}/100\n"
                f"Verdict: {result['verdict_label']}\n"
                f"Other students can now vote on it.")

    return None   # not a command → analyze as message

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    if not TWILIO_AVAILABLE:
        return "Twilio not configured", 200

    body   = request.values.get("Body", "").strip()
    resp   = MessagingResponse()
    msg    = resp.message()

    if not body:
        msg.body("👋 Hello! Send any message to check its credibility.\nReply *help* for commands.")
        return str(resp)

    with app.app_context():
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row

        command_reply = _handle_bot_command(body, db)
        if command_reply:
            msg.body(command_reply)
        else:
            result = _run_analysis(body, db)
            db.execute(
                "INSERT INTO analyses (text,ml_score,heuristic_score,combined_score,verdict,evidence,matches,created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (body, result["ml_score"], result["heuristic_score"], result["combined_score"],
                 result["verdict"], json.dumps(result["evidence"]),
                 json.dumps(result["similar_matches"]), datetime.utcnow().isoformat())
            )
            db.commit()
            msg.body(_format_whatsapp_reply(body, result))

        db.close()

    return str(resp)

# ── Admin: verify token ────────────────────────────────────────────────────────
@app.route("/api/admin/verify", methods=["POST"])
def admin_verify():
    data = request.get_json(silent=True) or {}
    if data.get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 403

# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.getenv("FLASK_PORT", 5000))
    print(f"\n{'='*55}")
    print(f"  🛡️  TruthLens Server")
    print(f"  🌐  http://localhost:{port}")
    print(f"  📱  WhatsApp Webhook: /webhook")
    print(f"  🤖  ML Model: {'✅ Ready' if _model else '⚠️  Not trained'}")
    print(f"{'='*55}\n")
    app.run(debug=True, host="0.0.0.0", port=port)
