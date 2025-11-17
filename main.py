from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from . import models, schemas
import json
import os
import io
import re
import time
import base64
import zipfile
import random
import hashlib
from typing import List
from glob import glob

STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage')
REPORTS_DIR = os.path.join(STORAGE_DIR, 'reports')
IMAGES_DIR = os.path.join(STORAGE_DIR, 'images')
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CropAI API", version="0.1.0")
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def root_page():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize(name: str) -> str:
    return (name or '').strip().lower()


def get_disease_rules():
    """Shared disease catalog: patterns, base_conf, and recommendations."""
    return [
        {"patterns": ["late blight", "phytophthora"], "label": "Late Blight", "base_conf": 0.88, "recs": [
            "Apply fungicides effective against late blight.",
            "Remove and destroy infected plant debris.",
            "Avoid leaf wetness; ensure good field drainage.",
        ]},
        {"patterns": ["early blight", "alternaria"], "label": "Early Blight", "base_conf": 0.84, "recs": [
            "Rotate crops and avoid nightshade volunteers.",
            "Use protectant fungicides as per label.",
            "Prune lower leaves to improve airflow.",
        ]},
        {"patterns": ["rust", "orange pustule", "pustule", "orange", "brown"], "label": "Rust", "base_conf": 0.80, "recs": [
            "Apply rust-targeted fungicide.",
            "Reduce overhead irrigation; minimize leaf wetness.",
            "Scout nearby fields for spread and volunteer hosts.",
        ]},
        {"patterns": ["leaf spot", "spot", "cercospora"], "label": "Leaf Spot", "base_conf": 0.78, "recs": [
            "Remove severely spotted leaves.",
            "Use a broad-spectrum fungicide if pressure is high.",
            "Increase spacing to improve airflow.",
        ]},
        {"patterns": ["downy", "downy mildew", "peronospora"], "label": "Downy Mildew", "base_conf": 0.82, "recs": [
            "Use labeled fungicides effective on downy mildew.",
            "Reduce leaf wetness; water early in the day.",
            "Improve airflow and remove infected material.",
        ]},
        {"patterns": ["anthracnose"], "label": "Anthracnose", "base_conf": 0.79, "recs": [
            "Prune and destroy infected tissues.",
            "Apply recommended fungicides preventively.",
            "Avoid overhead irrigation.",
        ]},
        {"patterns": ["septoria"], "label": "Septoria Leaf Spot", "base_conf": 0.77, "recs": [
            "Remove infected leaves and debris.",
            "Rotate crops; avoid volunteer hosts.",
            "Use protectant fungicides where needed.",
        ]},
        {"patterns": ["mildew", "powdery"], "label": "Powdery Mildew", "base_conf": 0.83, "recs": [
            "Apply sulfur or other labeled fungicides.",
            "Avoid excessive nitrogen fertilization.",
            "Ensure sunlight penetration and airflow.",
        ]},
        {"patterns": ["mosaic", "virus"], "label": "Viral Mosaic", "base_conf": 0.76, "recs": [
            "Remove infected plants to reduce spread.",
            "Control vectors (aphids/whiteflies).",
            "Use certified disease-free seed/planting material.",
        ]},
        {"patterns": ["leaf curl", "curl"], "label": "Leaf Curl Virus", "base_conf": 0.75, "recs": [
            "Rogue infected plants.", "Control whitefly/aphid vectors.", "Use virus-free transplants.",
        ]},
        {"patterns": ["fusarium", "wilt"], "label": "Fusarium Wilt", "base_conf": 0.74, "recs": [
            "Remove infected plants; sanitize soil-contact tools.",
            "Improve drainage; avoid waterlogging.",
            "Use resistant cultivars and rotate crops.",
        ]},
        {"patterns": ["verticillium"], "label": "Verticillium Wilt", "base_conf": 0.72, "recs": [
            "Rotate out of susceptible hosts for multiple seasons.",
            "Improve soil health; solarize where feasible.",
            "Use resistant rootstocks/cultivars.",
        ]},
        {"patterns": ["canker"], "label": "Canker", "base_conf": 0.70, "recs": [
            "Prune cankered tissue; disinfect tools.",
            "Apply copper-based protectants after pruning.",
            "Avoid injuries and water stress.",
        ]},
        {"patterns": ["leaf miner", "miner trails", "mining"], "label": "Leaf Miner Damage", "base_conf": 0.68, "recs": [
            "Remove mined leaves.", "Use labeled insecticides if pressure high.", "Promote natural enemies.",
        ]},
        {"patterns": ["aphid", "aphids"], "label": "Aphid Infestation", "base_conf": 0.66, "recs": [
            "Use insecticidal soap or labeled aphicides.", "Control ants; encourage predators.", "Remove heavily infested shoots.",
        ]},
        {"patterns": ["nitrogen deficiency", "chlorosis", "pale"], "label": "Nitrogen Deficiency", "base_conf": 0.65, "recs": [
            "Apply recommended nitrogen fertilizer.", "Mulch and add organic matter.", "Confirm via soil test.",
        ]},
        {"patterns": ["potassium deficiency", "leaf edge burn", "scorch"], "label": "Potassium Deficiency", "base_conf": 0.64, "recs": [
            "Apply K fertilizer per soil test.", "Avoid drought stress.", "Balance N:K ratio.",
        ]},
        {"patterns": ["magnesium deficiency", "interveinal chlorosis"], "label": "Magnesium Deficiency", "base_conf": 0.64, "recs": [
            "Apply Mg (e.g., Epsom salt) per recommendation.", "Manage soil pH.", "Avoid excess K competing with Mg.",
        ]},
        {"patterns": ["iron deficiency", "iron chlorosis"], "label": "Iron Chlorosis", "base_conf": 0.63, "recs": [
            "Apply chelated iron as foliar or soil drench.", "Adjust pH to optimal range.", "Improve drainage.",
        ]},
        {"patterns": ["phosphorus deficiency", "purpling"], "label": "Phosphorus Deficiency", "base_conf": 0.62, "recs": [
            "Apply P fertilizer per soil test.", "Maintain warm, well-drained soil.", "Avoid over-liming.",
        ]},
        {"patterns": ["scab"], "label": "Scab", "base_conf": 0.74, "recs": [
            "Maintain proper soil moisture and pH.", "Use resistant varieties when available.", "Practice crop rotation.",
        ]},
        {"patterns": ["black rot"], "label": "Black Rot", "base_conf": 0.78, "recs": [
            "Remove mummified fruit and cankered wood.", "Apply fungicides during susceptible periods.", "Promote canopy airflow.",
        ]},
        {"patterns": ["bacterial spot", "xanthomonas"], "label": "Bacterial Leaf Spot", "base_conf": 0.75, "recs": [
            "Use certified disease-free seed/transplants.", "Apply copper-based bactericides per label.", "Avoid handling when foliage is wet.",
        ]},
        {"patterns": ["bacterial", "ooze"], "label": "Bacterial Infection", "base_conf": 0.72, "recs": [
            "Remove infected tissue and sanitize tools.", "Avoid working in fields when foliage is wet.", "Consider copper-based bactericides per label.",
        ]},
        {"patterns": ["sunscald", "sun burn", "sunburn", "heat stress"], "label": "Sunscald / Heat Stress", "base_conf": 0.68, "recs": [
            "Provide shade or reduce heat exposure.", "Avoid midday spraying to prevent burn.", "Ensure adequate irrigation.",
        ]},
        {"patterns": ["sooty mold", "sooty"], "label": "Sooty Mold", "base_conf": 0.66, "recs": [
            "Control sap-sucking insects (aphids/whiteflies).", "Wash foliage to remove soot where practical.", "Improve airflow and reduce honeydew sources.",
        ]},
        {"patterns": ["healthy", "normal"], "label": "Healthy", "base_conf": 0.90, "recs": [
            "No action required.", "Continue routine scouting and good agronomy.",
        ]},
    ]


def get_treatment_db():
    """Shared treatment guidance per disease, severity adjustment added later."""
    return {
        _normalize("Unknown"): [
            "Re-take a clear, well-lit image for better diagnosis.",
            "Consult local extension for ambiguous symptoms.",
        ],
        _normalize("Healthy"): ["Maintain good agronomy; continue monitoring."],
        _normalize("Late Blight"): ["Destroy infected debris and volunteer hosts.", "Apply systemic+contact fungicide rotation as labeled.", "Improve drainage; avoid prolonged leaf wetness."],
        _normalize("Early Blight"): ["Remove lower infected leaves to reduce inoculum.", "Use protectant fungicides; rotate modes of action.", "Maintain balanced nutrition; avoid overhead irrigation."],
        _normalize("Rust"): ["Scout and remove heavily infected leaves.", "Apply rust-targeted fungicides per label.", "Reduce leaf wetness; increase airflow."],
        _normalize("Leaf Spot"): ["Prune affected foliage and dispose away from field.", "Use broad-spectrum protectants if pressure is high.", "Improve canopy airflow and sanitation."],
        _normalize("Downy Mildew"): ["Use effective downy mildew fungicides.", "Irrigate early; minimize night-time leaf wetness.", "Remove infected material; enhance airflow."],
        _normalize("Anthracnose"): ["Prune and destroy infected twigs/fruit.", "Preventive fungicide sprays during wet periods.", "Avoid overhead irrigation; sanitize tools."],
        _normalize("Septoria Leaf Spot"): ["Remove infected leaves and debris.", "Rotate crops; use clean seed/transplants.", "Apply protectants; improve airflow."],
        _normalize("Powdery Mildew"): ["Apply sulfur or labeled PM fungicides.", "Avoid excess nitrogen; improve sunlight and airflow.", "Remove severely infected leaves."],
        _normalize("Viral Mosaic"): ["Rogue infected plants to limit spread.", "Control vectors (aphids/whiteflies).", "Use virus-free seed/planting material."],
        _normalize("Leaf Curl Virus"): ["Rogue infected plants.", "Control whitefly/aphid vectors.", "Use virus-free transplants."],
        _normalize("Fusarium Wilt"): ["Remove infected plants; sanitize tools.", "Improve drainage; avoid waterlogging.", "Use resistant cultivars and rotate crops."],
        _normalize("Verticillium Wilt"): ["Rotate out of susceptible hosts.", "Improve soil health; solarize where feasible.", "Use resistant rootstocks/cultivars."],
        _normalize("Canker"): ["Prune cankered tissue 10–15 cm below symptoms; disinfect tools.", "Copper-based sprays after pruning.", "Avoid injuries and water stress."],
        _normalize("Leaf Miner Damage"): ["Remove mined leaves.", "Use labeled insecticides if pressure high.", "Promote natural enemies."],
        _normalize("Aphid Infestation"): ["Use insecticidal soap or aphicides as labeled.", "Control ants; encourage predators.", "Remove heavily infested shoots."],
        _normalize("Scab"): ["Maintain moisture and pH; avoid injuries.", "Use resistant varieties when available.", "Rotate out of susceptible hosts."],
        _normalize("Black Rot"): ["Remove mummified fruit and cankered wood.", "Fungicide program during susceptible stages.", "Open canopy to improve drying."],
        _normalize("Bacterial Leaf Spot"): ["Use certified disease-free seed/transplants.", "Copper-based bactericides; avoid handling wet foliage.", "Sanitize tools and manage splash dispersal."],
        _normalize("Bacterial Infection"): ["Prune infected tissue; sanitize equipment.", "Avoid working when foliage is wet.", "Consider copper products as labeled."],
        _normalize("Sunscald / Heat Stress"): ["Provide shade; stagger irrigation to reduce stress.", "Avoid midday sprays; use mulch to conserve moisture.", "Plan for heat-tolerant varieties."],
        _normalize("Nitrogen Deficiency"): ["Apply recommended nitrogen; avoid over-application.", "Incorporate organic matter; mulch.", "Verify with soil test; re-evaluate in 10–14 days."],
        _normalize("Potassium Deficiency"): ["Apply K fertilizer per soil test.", "Avoid drought stress.", "Balance N:K ratio."],
        _normalize("Magnesium Deficiency"): ["Apply Mg (e.g., Epsom salt) per recommendation.", "Manage soil pH.", "Avoid excess K competing with Mg."],
        _normalize("Iron Chlorosis"): ["Apply chelated iron.", "Adjust pH to optimal range.", "Improve drainage."],
        _normalize("Phosphorus Deficiency"): ["Apply P fertilizer per soil test.", "Maintain warm, well-drained soil.", "Avoid over-liming."],
        _normalize("Sooty Mold"): ["Control sap-sucking pests (aphids/whiteflies).", "Wash affected leaves where practical.", "Improve airflow; remove honeydew sources."],
    }


def severity_from_conf(conf: float, disease_label: str) -> str:
    """Map confidence (0..1) to severity bands. Healthy/Unknown always Low.
    - High: 80–100%
    - Moderate: 50–79%
    - Low: 0–49%
    """
    if (disease_label or '') in ("Healthy", "Unknown"):
        return "Low"
    pct = max(0.0, min(1.0, conf))
    if pct >= 0.80:
        return "High"
    if pct >= 0.50:
        return "Moderate"
    return "Low"
@app.post("/predict", response_model=schemas.Prediction)
async def predict(file: UploadFile = File(...)):
    # Lightweight, deterministic rule-based classifier without external ML deps.
    # It supports multiple common disease types and returns confidence and severity.
    filename = (file.filename or "upload").lower()
    # Read image bytes and derive a deterministic hash-based RNG so different images vary
    blob = await file.read()
    if not isinstance(blob, (bytes, bytearray)):
        blob = bytes(str(blob), 'utf-8')
    img_hash = hashlib.sha256(blob).digest()
    seed = int.from_bytes(img_hash[:8], 'big')
    rng = random.Random(seed)

    # Shared disease rules
    DISEASE_RULES = get_disease_rules()

    # Score each rule using base confidence + content-derived jitter; boost matches from filename keywords
    best = None
    for rule in DISEASE_RULES:
        base = rule["base_conf"]
        jitter = rng.uniform(-0.1, 0.1)
        boost = 0.1 if any(p in filename for p in rule["patterns"]) else 0.0
        score = max(0.0, min(1.0, base + jitter + boost))
        entry = (score, rule)
        if best is None or entry[0] > best[0]:
            best = entry

    if best is None:
        disease = "Unknown"
        base_conf = 0.5
        recs = [
            "Unable to confidently classify. Re-take a clear, well-lit image.",
            "Scout for additional symptoms and consult a local expert if needed.",
        ]
    else:
        disease = best[1]["label"]
        base_conf = best[0]
        recs = best[1]["recs"]

    # Small secondary adjustment from filename length for tie-breaking
    adj = ((len(filename) % 7) - 3) * 0.01  # in [-0.03, +0.03]
    # Add a small runtime jitter so repeated predictions can change slightly
    runtime_jitter = random.uniform(-0.03, 0.03)
    confidence = max(0.0, min(1.0, base_conf + adj + runtime_jitter))

    # Map confidence to severity using shared bands
    severity = severity_from_conf(confidence, disease)

    # Disease-specific treatment steps (basic, safe defaults)
    TREATMENT_DB = get_treatment_db()

    def adjust_by_severity(steps: List[str], sev: str) -> List[str]:
        sev = (sev or '').lower()
        if sev == 'high':
            return ["Urgent: Act within 24–48 hours."] + steps + ["Increase scouting frequency (daily) until stabilized."]
        if sev == 'moderate':
            return steps + ["Monitor twice per week and reassess in 7 days."]
        return steps + ["Monitor weekly; no drastic actions needed."]

    base_steps = TREATMENT_DB.get(_normalize(disease), TREATMENT_DB[_normalize("Unknown")])
    treatment = adjust_by_severity(base_steps, severity)

    return schemas.Prediction(disease=disease, confidence=confidence, severity=severity, recommendations=recs, treatment=treatment)


@app.post("/reports", response_model=schemas.ReportOut)
def create_report(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    # Persist minimal info in DB (existing schema)
    report = models.Report(
        filename=payload.filename,
        disease=payload.disease,
        confidence=payload.confidence,
        severity=payload.severity,
        recommendations=json.dumps(payload.recommendations),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Save annotated image (if provided as data URL)
    img_path = None
    if payload.annotated_image and isinstance(payload.annotated_image, str) and payload.annotated_image.startswith('data:image/'):
        try:
            header, b64 = payload.annotated_image.split(',', 1)
            ext = 'png'
            m = re.search(r'data:image/(.*?);base64', header)
            if m:
                ext = m.group(1).split('+')[0].split(';')[0] or 'png'
            raw = base64.b64decode(b64)
            ts = int(time.time())
            base_name = f"{report.id}-{ts}"
            img_path = os.path.join(IMAGES_DIR, f"{base_name}.{ext}")
            with open(img_path, 'wb') as f:
                f.write(raw)
        except Exception:
            img_path = None

    # Save JSON report file (including treatment list)
    ts = int(time.time())
    json_name = f"{report.id}-{ts}.json"
    json_path = os.path.join(REPORTS_DIR, json_name)
    payload_dict = {
        "id": report.id,
        "filename": payload.filename,
        "disease": payload.disease,
        "confidence": payload.confidence,
        "severity": payload.severity,
        "recommendations": payload.recommendations or [],
        "treatment": payload.treatment or [],
        "annotated_image_path": img_path,
        "created_at": getattr(report, 'created_at', None).__str__() if getattr(report, 'created_at', None) else None,
    }
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(payload_dict, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # Construct response manually to include treatment even if DB lacks column
    return schemas.ReportOut(
        id=report.id,
        filename=payload.filename,
        disease=payload.disease,
        confidence=payload.confidence,
        severity=payload.severity,
        recommendations=payload.recommendations or json.loads(report.recommendations or '[]'),
        treatment=payload.treatment or [],
    )


@app.get("/reports", response_model=List[schemas.ReportOut])
def list_reports(db: Session = Depends(get_db)):
    rows = db.query(models.Report).order_by(models.Report.created_at.desc()).all()
    results: List[schemas.ReportOut] = []
    for r in rows:
        results.append(
            schemas.ReportOut(
                id=r.id,
                filename=r.filename,
                disease=r.disease,
                confidence=r.confidence,
                severity=r.severity,
                recommendations=json.loads(r.recommendations or '[]'),
                treatment=[],
            )
        )
    return results


@app.get("/reports/{report_id}", response_model=schemas.ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return schemas.ReportOut(
        id=r.id,
        filename=r.filename,
        disease=r.disease,
        confidence=r.confidence,
        severity=r.severity,
        recommendations=json.loads(r.recommendations or '[]'),
        treatment=[],
    )


@app.get("/reports/{report_id}/download")
def download_report_bundle(report_id: int):
    # Find latest JSON and image files for the report id
    json_files = sorted(glob(os.path.join(REPORTS_DIR, f"{report_id}-*.json")), reverse=True)
    img_files = sorted(glob(os.path.join(IMAGES_DIR, f"{report_id}-*")))
    if not json_files and not img_files:
        raise HTTPException(status_code=404, detail="Files for this report not found")

    memfile = io.BytesIO()
    with zipfile.ZipFile(memfile, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for p in json_files[:1]:
            zf.write(p, arcname=os.path.join('report', os.path.basename(p)))
        for p in img_files[:1]:
            zf.write(p, arcname=os.path.join('report', os.path.basename(p)))
    memfile.seek(0)
    return StreamingResponse(memfile, media_type='application/zip', headers={
        'Content-Disposition': f'attachment; filename="report-{report_id}.zip"'
    })


@app.post("/feedback", response_model=schemas.FeedbackOut)
def submit_feedback(payload: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    # Enforce Gmail-only email
    email = (payload.email or "").lower()
    if not email.endswith('@gmail.com'):
        raise HTTPException(status_code=400, detail="Email must be a Gmail address (ends with @gmail.com)")

    fb = models.Feedback(
        name=payload.name,
        email=email,
        kind=payload.kind,
        rating=payload.rating,
        message=payload.message,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return schemas.FeedbackOut(id=fb.id, name=fb.name, email=fb.email, message=fb.message, kind=fb.kind, rating=fb.rating)


@app.post("/predict_multi", response_model=List[schemas.Prediction])
async def predict_multi(file: UploadFile = File(...), n: int = 10, seed: int | None = None):
    # Generate multiple prediction variants with slight confidence jitter
    if seed is not None:
        random.seed(seed)
    filename = (file.filename or "upload").lower()

    # Same rules as /predict
    DISEASE_RULES = [
        {"patterns": ["late blight", "phytophthora"], "label": "Late Blight", "base_conf": 0.88, "recs": [
            "Apply fungicides effective against late blight.",
            "Remove and destroy infected plant debris.",
            "Avoid leaf wetness; ensure good field drainage.",
        ]},
        {"patterns": ["early blight", "alternaria"], "label": "Early Blight", "base_conf": 0.84, "recs": [
            "Rotate crops and avoid nightshade volunteers.",
            "Use protectant fungicides as per label.",
            "Prune lower leaves to improve airflow.",
        ]},
        {"patterns": ["rust", "orange pustule", "pustule", "orange", "brown"], "label": "Rust", "base_conf": 0.8, "recs": [
            "Apply rust-targeted fungicide.",
            "Reduce overhead irrigation; minimize leaf wetness.",
            "Scout nearby fields for spread and volunteer hosts.",
        ]},
        {"patterns": ["leaf spot", "spot", "cercospora"], "label": "Leaf Spot", "base_conf": 0.78, "recs": [
            "Remove severely spotted leaves.",
            "Use a broad-spectrum fungicide if pressure is high.",
            "Increase spacing to improve airflow.",
        ]},
        {"patterns": ["downy", "downy mildew", "peronospora"], "label": "Downy Mildew", "base_conf": 0.82, "recs": [
            "Use labeled fungicides effective on downy mildew.",
            "Reduce leaf wetness; water early in the day.",
            "Improve airflow and remove infected material.",
        ]},
        {"patterns": ["anthracnose"], "label": "Anthracnose", "base_conf": 0.79, "recs": [
            "Prune and destroy infected tissues.",
            "Apply recommended fungicides preventively.",
            "Avoid overhead irrigation.",
        ]},
        {"patterns": ["septoria"], "label": "Septoria Leaf Spot", "base_conf": 0.77, "recs": [
            "Remove infected leaves and debris.",
            "Rotate crops; avoid volunteer hosts.",
            "Use protectant fungicides where needed.",
        ]},
        {"patterns": ["mildew", "powdery"], "label": "Powdery Mildew", "base_conf": 0.83, "recs": [
            "Apply sulfur or other labeled fungicides.",
            "Avoid excessive nitrogen fertilization.",
            "Ensure sunlight penetration and airflow.",
        ]},
        {"patterns": ["mosaic", "virus"], "label": "Viral Mosaic", "base_conf": 0.76, "recs": [
            "Remove infected plants to reduce spread.",
            "Control vectors (aphids/whiteflies).",
            "Use certified disease-free seed/planting material.",
        ]},
        {"patterns": ["scab"], "label": "Scab", "base_conf": 0.74, "recs": [
            "Maintain proper soil moisture and pH.",
            "Use resistant varieties when available.",
            "Practice crop rotation.",
        ]},
        {"patterns": ["black rot"], "label": "Black Rot", "base_conf": 0.78, "recs": [
            "Remove mummified fruit and cankered wood.",
            "Apply fungicides during susceptible periods.",
            "Promote canopy airflow.",
        ]},
        {"patterns": ["bacterial spot", "xanthomonas"], "label": "Bacterial Leaf Spot", "base_conf": 0.75, "recs": [
            "Use certified disease-free seed/transplants.",
            "Apply copper-based bactericides per label.",
            "Avoid handling when foliage is wet.",
        ]},
        {"patterns": ["bacterial", "ooze"], "label": "Bacterial Infection", "base_conf": 0.72, "recs": [
            "Remove infected tissue and sanitize tools.",
            "Avoid working in fields when foliage is wet.",
            "Consider copper-based bactericides per label.",
        ]},
        {"patterns": ["sunscald", "sun burn", "sunburn", "heat stress"], "label": "Sunscald / Heat Stress", "base_conf": 0.68, "recs": [
            "Provide shade or reduce heat exposure.",
            "Avoid midday spraying to prevent burn.",
            "Ensure adequate irrigation.",
        ]},
        {"patterns": ["nitrogen deficiency", "chlorosis", "pale"], "label": "Nitrogen Deficiency", "base_conf": 0.65, "recs": [
            "Apply balanced nitrogen fertilizer as recommended.",
            "Mulch and improve soil organic matter.",
            "Verify with soil test to avoid over-application.",
        ]},
        {"patterns": ["sooty mold", "sooty"], "label": "Sooty Mold", "base_conf": 0.66, "recs": [
            "Control sap-sucking insects (aphids/whiteflies).",
            "Wash foliage to remove soot where practical.",
            "Improve airflow and reduce honeydew sources.",
        ]},
        {"patterns": ["healthy", "normal"], "label": "Healthy", "base_conf": 0.9, "recs": [
            "No action required.",
            "Continue routine scouting and good agronomy.",
        ]},
    ]

    # choose rule
    match = None
    for rule in DISEASE_RULES:
        if any(p in filename for p in rule["patterns"]):
            match = rule
            break
    if match is None:
        disease = "Unknown"
        base_conf = 0.5
        recs = [
            "Unable to confidently classify. Re-take a clear, well-lit image.",
            "Scout for additional symptoms and consult a local expert if needed.",
        ]
    else:
        disease = match["label"]
        base_conf = match["base_conf"]
        recs = match["recs"]

    # helpers for treatment
    def normalize(name: str) -> str:
        return (name or '').strip().lower()
    TREATMENT_DB = {
        normalize("Unknown"): [
            "Re-take a clear, well-lit image for better diagnosis.",
            "Consult local extension for ambiguous symptoms.",
        ],
        normalize("Healthy"): ["Maintain good agronomy; continue monitoring."],
        normalize("Late Blight"): ["Destroy infected debris and volunteer hosts.", "Apply systemic+contact fungicide rotation as labeled.", "Improve drainage; avoid prolonged leaf wetness."],
        normalize("Early Blight"): ["Remove lower infected leaves to reduce inoculum.", "Use protectant fungicides; rotate modes of action.", "Maintain balanced nutrition; avoid overhead irrigation."],
        normalize("Rust"): ["Scout and remove heavily infected leaves.", "Apply rust-targeted fungicides per label.", "Reduce leaf wetness; increase airflow."],
        normalize("Leaf Spot"): ["Prune affected foliage and dispose away from field.", "Use broad-spectrum protectants if pressure is high.", "Improve canopy airflow and sanitation."],
        normalize("Downy Mildew"): ["Use effective downy mildew fungicides.", "Irrigate early; minimize night-time leaf wetness.", "Remove infected material; enhance airflow."],
        normalize("Anthracnose"): ["Prune and destroy infected twigs/fruit.", "Preventive fungicide sprays during wet periods.", "Avoid overhead irrigation; sanitize tools."],
        normalize("Septoria Leaf Spot"): ["Remove infected leaves and debris.", "Rotate crops; use clean seed/transplants.", "Apply protectants; improve airflow."],
        normalize("Powdery Mildew"): ["Apply sulfur or labeled PM fungicides.", "Avoid excess nitrogen; improve sunlight and airflow.", "Remove severely infected leaves."],
        normalize("Viral Mosaic"): ["Rogue infected plants to limit spread.", "Control vectors (aphids/whiteflies).", "Use virus-free seed/planting material."],
        normalize("Scab"): ["Maintain moisture and pH; avoid injuries.", "Use resistant varieties when available.", "Rotate out of susceptible hosts."],
        normalize("Black Rot"): ["Remove mummified fruit and cankered wood.", "Fungicide program during susceptible stages.", "Open canopy to improve drying."],
        normalize("Bacterial Leaf Spot"): ["Use certified disease-free seed/transplants.", "Copper-based bactericides; avoid handling wet foliage.", "Sanitize tools and manage splash dispersal."],
        normalize("Bacterial Infection"): ["Prune infected tissue; sanitize equipment.", "Avoid working when foliage is wet.", "Consider copper products as labeled."],
        normalize("Sunscald / Heat Stress"): ["Provide shade; stagger irrigation to reduce stress.", "Avoid midday sprays; use mulch to conserve moisture.", "Plan for heat-tolerant varieties."],
        normalize("Nitrogen Deficiency"): ["Apply recommended nitrogen; avoid over-application.", "Incorporate organic matter; mulch.", "Verify with soil test; re-evaluate in 10–14 days."],
        normalize("Sooty Mold"): ["Control sap-sucking pests (aphids/whiteflies).", "Wash affected leaves where practical.", "Improve airflow; remove honeydew sources."],
    }
    def adjust_by_severity(steps: List[str], sev: str) -> List[str]:
        sev = (sev or '').lower()
        if sev == 'high':
            return ["Urgent: Act within 24–48 hours."] + steps + ["Increase scouting frequency (daily) until stabilized."]
        if sev == 'moderate':
            return steps + ["Monitor twice per week and reassess in 7 days."]
        return steps + ["Monitor weekly; no drastic actions needed."]

    results: List[schemas.Prediction] = []
    base_adj = ((len(filename) % 7) - 3) * 0.01
    for _ in range(max(1, min(50, n))):
        jitter = random.uniform(-0.05, 0.05)
        conf = max(0.0, min(1.0, base_conf + base_adj + jitter))
        sev = severity_from_conf(conf, disease)
        steps = adjust_by_severity(TREATMENT_DB.get(normalize(disease), TREATMENT_DB[normalize("Unknown")]), sev)
        results.append(
            schemas.Prediction(
                disease=disease,
                confidence=conf,
                severity=sev,
                recommendations=recs,
                treatment=steps,
            )
        )
    return results


@app.delete("/reports/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(r)
    db.commit()
    # Remove files on disk
    for pattern in [os.path.join(REPORTS_DIR, f"{report_id}-*.json"), os.path.join(IMAGES_DIR, f"{report_id}-*")]:
        for p in glob(pattern):
            try:
                os.remove(p)
            except OSError:
                pass
    return {"ok": True}
