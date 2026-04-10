# """
# Translation API Gateway
# Unified endpoint for all translation services

# This gateway provides:
# - Single endpoint for all translation directions
# - Automatic routing based on source/target languages
# - Request aggregation and response formatting
# - Full logging of detailed responses
# - Simplified response for frontend
# - UI serving (optional)
# """
# import os
# import time
# import logging
# import json
# from typing import List, Optional

# import httpx
# from pydantic import BaseModel
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import HTMLResponse
# import uvicorn

# # ============================================================================
# # LOGGING CONFIGURATION
# # ============================================================================
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger("translation_gateway")

# # ============================================================================
# # CONFIGURATION
# # ============================================================================
# LID_SERVICE_URL = os.environ.get("LID_SERVICE_URL", "http://localhost:6001")
# INDIC_EN_SERVICE_URL = os.environ.get("INDIC_EN_SERVICE_URL", "http://localhost:6002")
# EN_INDIC_SERVICE_URL = os.environ.get("EN_INDIC_SERVICE_URL", "http://localhost:6003")
# SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "6005"))

# # Short code mappings
# SHORT_TO_INDICTRANS = {
#     "te": "tel_Telu", "hi": "hin_Deva", "kn": "kan_Knda", "ml": "mal_Mlym",
#     "ta": "tam_Taml", "mr": "mar_Deva", "pa": "pan_Guru", "bn": "ben_Beng",
#     "gu": "guj_Gujr", "ur": "urd_Arab", "as": "asm_Beng", "or": "ory_Orya",
#     "ne": "npi_Deva", "en": "eng_Latn", "brx": "brx_Deva", "ks": "kas_Arab",
#     "mai": "mai_Deva", "mni": "mni_Mtei", "sd": "snd_Arab", "gom": "gom_Deva"
# }

# LANGUAGE_OPTIONS = [
#     {"code": "auto", "short": "auto", "label": "Auto-Detect"},
#     {"code": "tel_Telu", "short": "te", "label": "Telugu (తెలుగు)"},
#     {"code": "hin_Deva", "short": "hi", "label": "Hindi (हिन्दी)"},
#     {"code": "kan_Knda", "short": "kn", "label": "Kannada (ಕನ್ನಡ)"},
#     {"code": "mal_Mlym", "short": "ml", "label": "Malayalam (മലയാളം)"},
#     {"code": "tam_Taml", "short": "ta", "label": "Tamil (தமிழ்)"},
#     {"code": "mar_Deva", "short": "mr", "label": "Marathi (मराठी)"},
#     {"code": "pan_Guru", "short": "pa", "label": "Punjabi (ਪੰਜਾਬੀ)"},
#     {"code": "ben_Beng", "short": "bn", "label": "Bengali (বাংলা)"},
#     {"code": "guj_Gujr", "short": "gu", "label": "Gujarati (ગુજરાતી)"},
#     {"code": "urd_Arab", "short": "ur", "label": "Urdu (اردو)"},
#     {"code": "asm_Beng", "short": "as", "label": "Assamese (অসমীয়া)"},
#     {"code": "ory_Orya", "short": "or", "label": "Odia (ଓଡ଼ିଆ)"},
#     {"code": "npi_Deva", "short": "ne", "label": "Nepali (नेपाली)"},
#     {"code": "brx_Deva", "short": "brx", "label": "Bodo (बड़ो)"},
#     {"code": "kas_Arab", "short": "ks", "label": "Kashmiri (كٲشُر)"},
#     {"code": "gom_Deva", "short": "gom", "label": "Konkani (कोंकणी)"},
#     {"code": "mai_Deva", "short": "mai", "label": "Maithili (मैथिली)"},
#     {"code": "mni_Mtei", "short": "mni", "label": "Manipuri (ꯃꯤꯇꯩꯂꯣꯟ)"},
#     {"code": "snd_Arab", "short": "sd", "label": "Sindhi (سنڌي)"},
#     {"code": "eng_Latn", "short": "en", "label": "English"},
# ]

# # ============================================================================
# # HTTP CLIENT
# # ============================================================================
# http_client = httpx.AsyncClient(timeout=60.0)

# # ============================================================================
# # FASTAPI APPLICATION
# # ============================================================================
# app = FastAPI(
#     title="Translation API Gateway",
#     version="1.0.0",
#     description="Unified endpoint for bidirectional Indic ↔ English translation"
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"]
# )


# # Request/Response Models
# class TranslateRequest(BaseModel):
#     sentences: Optional[List[str]] = None
#     text: Optional[str] = None
#     src_lang: Optional[str] = "auto"
#     tgt_lang: str = "eng_Latn"
#     num_beams: Optional[int] = 5
#     max_new_tokens: Optional[int] = 1024


# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================
# def log_full_response(request_id: str, full_response: dict):
#     """Log the full detailed response for debugging/monitoring"""
#     logger.info(f"[{request_id}] Full translation response: {json.dumps(full_response, ensure_ascii=False)}")


# def simplify_response(full_response: dict) -> dict:
#     """
#     Convert full detailed response to minimal frontend-friendly format.
    
#     For single sentence: returns just the string
#     For multiple sentences: returns list of strings
#     """
#     outputs = []
    
#     for trans in full_response.get("translations", []):
#         output = trans.get("final", "") or trans.get("translated", "")
#         outputs.append(output)
    
#     # If single translation, return just the string
#     if len(outputs) == 1:
#         return {"output": outputs[0]}
    
#     # If multiple translations, return list
#     return {"output": outputs}


# # ============================================================================
# # ENDPOINTS
# # ============================================================================
# @app.get("/", response_class=HTMLResponse)
# async def serve_ui():
#     """Serve the translation UI"""
#     ui_path = os.path.join(os.path.dirname(__file__), "final_translation_UI.HTML")
#     if os.path.exists(ui_path):
#         with open(ui_path, "r", encoding="utf-8") as f:
#             return HTMLResponse(content=f.read())
    
#     # Return a simple HTML interface
#     return HTMLResponse(content="""
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <title>Translation Gateway</title>
#         <style>
#             body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
#             h1 { color: #333; }
#             .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
#             code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
#         </style>
#     </head>
#     <body>
#         <h1>🌐 Translation API Gateway</h1>
#         <p>Unified endpoint for bidirectional Indic ↔ English translation</p>
        
#         <h2>Services</h2>
#         <div class="endpoint">
#             <strong>LID + Transliteration:</strong> <code>GET /services/lid/health</code>
#         </div>
#         <div class="endpoint">
#             <strong>Indic → English:</strong> <code>GET /services/indic-en/health</code>
#         </div>
#         <div class="endpoint">
#             <strong>English → Indic:</strong> <code>GET /services/en-indic/health</code>
#         </div>
        
#         <h2>Translation</h2>
#         <div class="endpoint">
#             <strong>Translate:</strong> <code>POST /translate</code>
#         </div>
        
#         <p><a href="/docs">📚 API Documentation (Swagger)</a></p>
#     </body>
#     </html>
#     """)


# @app.get("/health")
# async def health():
#     """Gateway health check"""
#     services = {}
    
#     # Check LID service
#     try:
#         resp = await http_client.get(f"{LID_SERVICE_URL}/health")
#         services["lid_transliteration"] = resp.json() if resp.status_code == 200 else {"status": "error"}
#     except Exception as e:
#         services["lid_transliteration"] = {"status": "unavailable", "error": str(e)}
    
#     # Check Indic→EN service
#     try:
#         resp = await http_client.get(f"{INDIC_EN_SERVICE_URL}/health")
#         services["indic_to_english"] = resp.json() if resp.status_code == 200 else {"status": "error"}
#     except Exception as e:
#         services["indic_to_english"] = {"status": "unavailable", "error": str(e)}
    
#     # Check EN→Indic service
#     try:
#         resp = await http_client.get(f"{EN_INDIC_SERVICE_URL}/health")
#         services["english_to_indic"] = resp.json() if resp.status_code == 200 else {"status": "error"}
#     except Exception as e:
#         services["english_to_indic"] = {"status": "unavailable", "error": str(e)}
    
#     all_healthy = all(
#         s.get("status") == "ok" 
#         for s in services.values()
#     )
    
#     return {
#         "status": "ok" if all_healthy else "degraded",
#         "gateway": "translation-api-gateway",
#         "services": services
#     }


# @app.get("/languages")
# def get_languages():
#     """Get supported languages"""
#     return {"languages": LANGUAGE_OPTIONS}


# @app.post("/translate")
# async def translate(req: TranslateRequest):
#     """
#     Unified translation endpoint
#     Routes to appropriate service based on source and target languages
#     Returns simplified response for frontend
#     """
#     t_start = time.time()
#     request_id = f"req_{int(t_start * 1000)}"
    
#     # Normalize input
#     sentences = req.sentences if req.sentences else ([req.text] if req.text else None)
#     if not sentences:
#         raise HTTPException(status_code=400, detail="No input text provided")
    
#     src_lang = SHORT_TO_INDICTRANS.get(req.src_lang, req.src_lang)
#     tgt_lang = SHORT_TO_INDICTRANS.get(req.tgt_lang, req.tgt_lang)
#     is_auto = src_lang in ("auto", "Auto", "AUTO")
    
#     logger.info(f"[{request_id}] Translation request: src={src_lang}, tgt={tgt_lang}, sentences={len(sentences)}")
    
#     # Determine translation direction and route
#     if tgt_lang == "eng_Latn":
#         # Indic → English flow
#         full_result = await _translate_indic_to_english(sentences, src_lang, is_auto, req, t_start)
    
#     elif src_lang == "eng_Latn":
#         # English → Indic flow
#         full_result = await _translate_english_to_indic(sentences, tgt_lang, req, t_start)
    
#     elif tgt_lang not in ("auto", "Auto", "AUTO"):
#         # Indic → Indic (via English)
#         full_result = await _translate_indic_to_indic(sentences, src_lang, tgt_lang, is_auto, req, t_start)
    
#     else:
#         raise HTTPException(status_code=400, detail="Please select a target language")
    
#     # Log full detailed response
#     log_full_response(request_id, full_result)
    
#     # Return simplified response for frontend
#     simplified = simplify_response(full_result)
#     logger.info(f"[{request_id}] Simplified response: {json.dumps(simplified, ensure_ascii=False)}")
    
#     return simplified


# @app.post("/translate/detailed")
# async def translate_detailed(req: TranslateRequest):
#     """
#     Translation endpoint that returns full detailed response.
#     Use this for debugging or when you need all the processing details.
#     """
#     t_start = time.time()
    
#     # Normalize input
#     sentences = req.sentences if req.sentences else ([req.text] if req.text else None)
#     if not sentences:
#         raise HTTPException(status_code=400, detail="No input text provided")
    
#     src_lang = SHORT_TO_INDICTRANS.get(req.src_lang, req.src_lang)
#     tgt_lang = SHORT_TO_INDICTRANS.get(req.tgt_lang, req.tgt_lang)
#     is_auto = src_lang in ("auto", "Auto", "AUTO")
    
#     # Determine translation direction and route
#     if tgt_lang == "eng_Latn":
#         return await _translate_indic_to_english(sentences, src_lang, is_auto, req, t_start)
    
#     elif src_lang == "eng_Latn":
#         return await _translate_english_to_indic(sentences, tgt_lang, req, t_start)
    
#     elif tgt_lang not in ("auto", "Auto", "AUTO"):
#         return await _translate_indic_to_indic(sentences, src_lang, tgt_lang, is_auto, req, t_start)
    
#     else:
#         raise HTTPException(status_code=400, detail="Please select a target language")


# async def _translate_indic_to_english(sentences, src_lang, is_auto, req, t_start):
#     """Route to Indic → English service"""
#     # First call LID service if needed
#     lid_results = None
    
#     if is_auto:
#         try:
#             lid_response = await http_client.post(
#                 f"{LID_SERVICE_URL}/batch_process",
#                 json={"texts": sentences, "src_lang_hint": None},
#                 timeout=30.0
#             )
#             lid_response.raise_for_status()
#             lid_results = lid_response.json().get("results", [])
#         except Exception as e:
#             logger.warning(f"LID service unavailable: {e}")
    
#     # Call translation service
#     try:
#         payload = {
#             "sentences": sentences,
#             "src_lang": src_lang,
#             "num_beams": req.num_beams,
#             "max_new_tokens": req.max_new_tokens
#         }
#         if lid_results:
#             payload["lid_results"] = [
#                 {
#                     "processed_text": r.get("processed_text"),
#                     "detected_language": r.get("detected_language"),
#                     "translit_info": r.get("translit_info")
#                 }
#                 for r in lid_results
#             ]
        
#         response = await http_client.post(
#             f"{INDIC_EN_SERVICE_URL}/batch_translate",
#             json=payload,
#             timeout=60.0
#         )
#         response.raise_for_status()
#         result = response.json()
#         result["gateway_time_seconds"] = round(time.time() - t_start, 3)
#         return result
        
#     except httpx.HTTPError as e:
#         raise HTTPException(
#             status_code=503,
#             detail=f"Translation service error: {str(e)}"
#         )


# async def _translate_english_to_indic(sentences, tgt_lang, req, t_start):
#     """Route to English → Indic service"""
#     try:
#         response = await http_client.post(
#             f"{EN_INDIC_SERVICE_URL}/batch_translate",
#             json={
#                 "sentences": sentences,
#                 "tgt_lang": tgt_lang,
#                 "num_beams": req.num_beams,
#                 "max_new_tokens": req.max_new_tokens
#             },
#             timeout=60.0
#         )
#         response.raise_for_status()
#         result = response.json()
#         result["gateway_time_seconds"] = round(time.time() - t_start, 3)
#         return result
        
#     except httpx.HTTPError as e:
#         raise HTTPException(
#             status_code=503,
#             detail=f"Translation service error: {str(e)}"
#         )


# async def _translate_indic_to_indic(sentences, src_lang, tgt_lang, is_auto, req, t_start):
#     """Route Indic → Indic translation (via English)"""
#     # Step 1: Indic → English
#     step1_result = await _translate_indic_to_english(sentences, src_lang, is_auto, req, t_start)
    
#     # Extract English translations
#     en_sentences = []
#     for t in step1_result.get("translations", []):
#         en_text = t.get("final", "") or t.get("translated", "") or ""
#         en_sentences.append(en_text)
    
#     if not en_sentences or all(not s.strip() for s in en_sentences):
#         return step1_result
    
#     # Step 2: English → Target Indic
#     try:
#         response = await http_client.post(
#             f"{EN_INDIC_SERVICE_URL}/batch_translate",
#             json={
#                 "sentences": en_sentences,
#                 "tgt_lang": tgt_lang,
#                 "num_beams": req.num_beams,
#                 "max_new_tokens": req.max_new_tokens
#             },
#             timeout=60.0
#         )
#         response.raise_for_status()
#         result = response.json()
        
#         # Add intermediate translations
#         for i, trans in enumerate(result.get("translations", [])):
#             if i < len(step1_result.get("translations", [])):
#                 trans["english_intermediate"] = step1_result["translations"][i].get("final", "")
        
#         result["direction"] = f"{step1_result.get('source_lang_detected', src_lang)} → eng → {tgt_lang}"
#         result["gateway_time_seconds"] = round(time.time() - t_start, 3)
#         return result
        
#     except httpx.HTTPError as e:
#         raise HTTPException(
#             status_code=503,
#             detail=f"Translation service error: {str(e)}"
#         )


# # ============================================================================
# # SERVICE PROXIES (for debugging)
# # ============================================================================
# @app.get("/services/lid/health")
# async def lid_health():
#     """Proxy to LID service health"""
#     resp = await http_client.get(f"{LID_SERVICE_URL}/health")
#     return resp.json()


# @app.get("/services/indic-en/health")
# async def indic_en_health():
#     """Proxy to Indic→EN service health"""
#     resp = await http_client.get(f"{INDIC_EN_SERVICE_URL}/health")
#     return resp.json()


# @app.get("/services/en-indic/health")
# async def en_indic_health():
#     """Proxy to EN→Indic service health"""
#     resp = await http_client.get(f"{EN_INDIC_SERVICE_URL}/health")
#     return resp.json()


# @app.post("/clear-cache")
# async def clear_all_caches():
#     """Clear caches in all services"""
#     results = {}
    
#     for name, url in [
#         ("lid", LID_SERVICE_URL),
#         ("indic_en", INDIC_EN_SERVICE_URL),
#         ("en_indic", EN_INDIC_SERVICE_URL)
#     ]:
#         try:
#             resp = await http_client.post(f"{url}/clear-cache")
#             results[name] = resp.json()
#         except Exception as e:
#             results[name] = {"error": str(e)}
    
#     return {"status": "caches cleared", "services": results}


# # ============================================================================
# # MAIN
# # ============================================================================
# if __name__ == "__main__":
#     print(f"\n✓ Translation API Gateway ready")
#     print(f"LID Service: {LID_SERVICE_URL}")
#     print(f"Indic→EN Service: {INDIC_EN_SERVICE_URL}")
#     print(f"EN→Indic Service: {EN_INDIC_SERVICE_URL}")
#     print(f"Swagger UI → http://localhost:{SERVICE_PORT}/docs\n")
    
#     uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)










"""
Translation API Gateway
Unified endpoint for all translation services

This gateway provides:
- Single endpoint for all translation directions
- Automatic routing based on source/target languages
- Transliteration shortcut (when detected lang == target lang, skip translation)
- Request aggregation and response formatting
- Full logging of detailed responses
- Simplified response for frontend
- UI serving (optional)
"""
import os
import re
import time
import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# Auto-scaler integration
from gateway.autoscaler import (
    get_autoscaler,
    start_autoscaler,
    AUTOSCALER_ENABLED,
)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_DIR = os.environ.get("LOG_DIR", "logs/gateway")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "gateway.log")
JSON_LOG_FILE = os.path.join(LOG_DIR, "detailed.jsonl")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger("translation_gateway")


def log_json_entry(data: Dict[str, Any]) -> None:
    """Log detailed JSON entry"""
    try:
        data["timestamp"] = datetime.now().isoformat()
        with open(JSON_LOG_FILE, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, default=str)
            f.write('\n')
            f.flush()
    except Exception as e:
        logger.error(f"Failed to write JSON log: {e}")


# ============================================================================
# CONFIGURATION
# ============================================================================
LID_SERVICE_URL = os.environ.get("LID_SERVICE_URL", "http://localhost:6001")
INDIC_EN_SERVICE_URL = os.environ.get("INDIC_EN_SERVICE_URL", "http://localhost:6002")
EN_INDIC_SERVICE_URL = os.environ.get("EN_INDIC_SERVICE_URL", "http://localhost:6003")
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "6005"))
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "")


# ============================================================================
# DYNAMIC URL RESOLUTION (Auto-scaler aware)
# ============================================================================
def _resolve_url(service: str, fallback: str) -> str:
    """Return the least-loaded healthy pod's URL, or fallback to env var."""
    if AUTOSCALER_ENABLED:
        try:
            url = get_autoscaler().get_url_for_service(service)
            if url:
                return url
        except Exception:
            pass
    return fallback


def get_lid_url() -> str:
    return _resolve_url("lid", LID_SERVICE_URL)


def get_indic_en_url() -> str:
    return _resolve_url("indic_en", INDIC_EN_SERVICE_URL)


def get_en_indic_url() -> str:
    return _resolve_url("en_indic", EN_INDIC_SERVICE_URL)


def _record_metrics(service: str, url: str, started_at: float, success: bool):
    if not AUTOSCALER_ENABLED:
        return
    try:
        latency_ms = (time.time() - started_at) * 1000
        get_autoscaler().record_request_metrics(service, url, latency_ms, success)
    except Exception:
        pass

# Short code mappings
SHORT_TO_INDICTRANS = {
    "te": "tel_Telu", "hi": "hin_Deva", "kn": "kan_Knda", "ml": "mal_Mlym",
    "ta": "tam_Taml", "mr": "mar_Deva", "pa": "pan_Guru", "bn": "ben_Beng",
    "gu": "guj_Gujr", "ur": "urd_Arab", "as": "asm_Beng", "or": "ory_Orya",
    "ne": "npi_Deva", "en": "eng_Latn", "brx": "brx_Deva", "ks": "kas_Arab",
    "mai": "mai_Deva", "mni": "mni_Mtei", "sd": "snd_Arab", "gom": "gom_Deva"
}

INDICTRANS_TO_SHORT = {v: k for k, v in SHORT_TO_INDICTRANS.items()}

# Language code normalization (handles various formats from LID)
# Maps detected language codes to standard IndicTrans2 codes
LID_TO_INDICTRANS = {
    # Telugu
    "tel_Telu": "tel_Telu", "tel_Latn": "tel_Telu", "tel": "tel_Telu",
    "telugu": "tel_Telu", "te": "tel_Telu",
    # Hindi
    "hin_Deva": "hin_Deva", "hin_Latn": "hin_Deva", "hin": "hin_Deva",
    "hindi": "hin_Deva", "hi": "hin_Deva",
    # Kannada
    "kan_Knda": "kan_Knda", "kan_Latn": "kan_Knda", "kan": "kan_Knda",
    "kannada": "kan_Knda", "kn": "kan_Knda",
    # Malayalam
    "mal_Mlym": "mal_Mlym", "mal_Latn": "mal_Mlym", "mal": "mal_Mlym",
    "malayalam": "mal_Mlym", "ml": "mal_Mlym",
    # Tamil
    "tam_Taml": "tam_Taml", "tam_Latn": "tam_Taml", "tam": "tam_Taml",
    "tamil": "tam_Taml", "ta": "tam_Taml",
    # Marathi
    "mar_Deva": "mar_Deva", "mar_Latn": "mar_Deva", "mar": "mar_Deva",
    "marathi": "mar_Deva", "mr": "mar_Deva",
    # Punjabi
    "pan_Guru": "pan_Guru", "pan_Latn": "pan_Guru", "pan": "pan_Guru",
    "punjabi": "pan_Guru", "pa": "pan_Guru",
    # Bengali
    "ben_Beng": "ben_Beng", "ben_Latn": "ben_Beng", "ben": "ben_Beng",
    "bengali": "ben_Beng", "bn": "ben_Beng",
    # Gujarati
    "guj_Gujr": "guj_Gujr", "guj_Latn": "guj_Gujr", "guj": "guj_Gujr",
    "gujarati": "guj_Gujr", "gu": "guj_Gujr",
    # Urdu
    "urd_Arab": "urd_Arab", "urd_Latn": "urd_Arab", "urd": "urd_Arab",
    "urdu": "urd_Arab", "ur": "urd_Arab",
    # Assamese
    "asm_Beng": "asm_Beng", "asm_Latn": "asm_Beng", "asm": "asm_Beng",
    "assamese": "asm_Beng", "as": "asm_Beng",
    # Odia
    "ory_Orya": "ory_Orya", "ory_Latn": "ory_Orya", "ory": "ory_Orya",
    "odia": "ory_Orya", "or": "ory_Orya",
    # Nepali
    "npi_Deva": "npi_Deva", "npi_Latn": "npi_Deva", "npi": "npi_Deva",
    "nepali": "npi_Deva", "ne": "npi_Deva",
    # Others
    "brx_Deva": "brx_Deva", "brx_Latn": "brx_Deva",
    "kas_Arab": "kas_Arab", "kas_Latn": "kas_Arab",
    "mai_Deva": "mai_Deva", "mai_Latn": "mai_Deva",
    "mni_Mtei": "mni_Mtei", "mni_Latn": "mni_Mtei",
    "snd_Arab": "snd_Arab", "snd_Latn": "snd_Arab",
    "gom_Deva": "gom_Deva", "gom_Latn": "gom_Deva",
    # English
    "eng_Latn": "eng_Latn", "eng": "eng_Latn", "english": "eng_Latn", "en": "eng_Latn",
}

LANGUAGE_OPTIONS = [
    {"code": "auto", "short": "auto", "label": "Auto-Detect"},
    {"code": "tel_Telu", "short": "te", "label": "Telugu (తెలుగు)"},
    {"code": "hin_Deva", "short": "hi", "label": "Hindi (हिन्दी)"},
    {"code": "kan_Knda", "short": "kn", "label": "Kannada (ಕನ್ನಡ)"},
    {"code": "mal_Mlym", "short": "ml", "label": "Malayalam (മലയാളം)"},
    {"code": "tam_Taml", "short": "ta", "label": "Tamil (தமிழ்)"},
    {"code": "mar_Deva", "short": "mr", "label": "Marathi (मराठी)"},
    {"code": "pan_Guru", "short": "pa", "label": "Punjabi (ਪੰਜਾਬੀ)"},
    {"code": "ben_Beng", "short": "bn", "label": "Bengali (বাংলা)"},
    {"code": "guj_Gujr", "short": "gu", "label": "Gujarati (ગુજરાતી)"},
    {"code": "urd_Arab", "short": "ur", "label": "Urdu (اردو)"},
    {"code": "asm_Beng", "short": "as", "label": "Assamese (অসমীয়া)"},
    {"code": "ory_Orya", "short": "or", "label": "Odia (ଓଡ଼ିଆ)"},
    {"code": "npi_Deva", "short": "ne", "label": "Nepali (नेपाली)"},
    {"code": "brx_Deva", "short": "brx", "label": "Bodo (बड़ो)"},
    {"code": "kas_Arab", "short": "ks", "label": "Kashmiri (كٲشُر)"},
    {"code": "gom_Deva", "short": "gom", "label": "Konkani (कोंकणी)"},
    {"code": "mai_Deva", "short": "mai", "label": "Maithili (मैथिली)"},
    {"code": "mni_Mtei", "short": "mni", "label": "Manipuri (ꯃꯤꯇꯩꯂꯣꯟ)"},
    {"code": "snd_Arab", "short": "sd", "label": "Sindhi (سنڌي)"},
    {"code": "eng_Latn", "short": "en", "label": "English"},
]

# ============================================================================
# HTTP CLIENT
# ============================================================================
_headers = {}
if API_SECRET_KEY:
    _headers["X-API-Key"] = API_SECRET_KEY
http_client = httpx.AsyncClient(timeout=60.0, headers=_headers)

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================
app = FastAPI(
    title="Translation API Gateway",
    version="1.1.0",
    description="Unified endpoint for bidirectional Indic ↔ English translation with transliteration shortcut"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# Request/Response Models
class TranslateRequest(BaseModel):
    sentences: Optional[List[str]] = None
    text: Optional[str] = None
    src_lang: Optional[str] = "auto"
    tgt_lang: str = "eng_Latn"
    num_beams: Optional[int] = 5
    max_new_tokens: Optional[int] = 1024


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def normalize_language_code(lang_code: str) -> str:
    """Normalize various language code formats to standard IndicTrans2 codes"""
    if not lang_code:
        return lang_code
    
    # Direct lookup
    if lang_code in LID_TO_INDICTRANS:
        return LID_TO_INDICTRANS[lang_code]
    
    # Try lowercase
    lower = lang_code.lower()
    if lower in LID_TO_INDICTRANS:
        return LID_TO_INDICTRANS[lower]
    
    # Try extracting base language (e.g., "tel_Latn" -> "tel")
    if "_" in lang_code:
        base = lang_code.split("_")[0].lower()
        if base in LID_TO_INDICTRANS:
            return LID_TO_INDICTRANS[base]
    
    return lang_code


def is_roman_script(lid_result: dict) -> bool:
    """Check if the detected script is Roman/Latin"""
    # Check translit_info for Roman detection
    translit_info = lid_result.get("translit_info", {})
    if translit_info:
        detected_script = translit_info.get("detected_script", "")
        is_roman = translit_info.get("is_roman", False)
        if is_roman or "roman" in detected_script.lower() or "latn" in detected_script.lower():
            return True
    
    # Check detected_language for Latn script
    detected_lang = lid_result.get("detected_language", "")
    if "_Latn" in detected_lang or "Latn" in detected_lang:
        return True
    
    # Check fasttext label
    fasttext_label = translit_info.get("fasttext_label", "")
    if "_Latn" in fasttext_label:
        return True
    
    return False


def get_base_language(lang_code: str) -> str:
    """Extract base language from language code (e.g., 'tel_Telu' -> 'tel')"""
    if not lang_code:
        return ""
    if "_" in lang_code:
        return lang_code.split("_")[0].lower()
    return lang_code.lower()


def languages_match(detected_lang: str, target_lang: str) -> bool:
    """
    Check if detected language matches target language.
    Handles various format differences.
    
    Examples:
    - "tel_Latn" matches "tel_Telu" (same base language: Telugu)
    - "hin_Deva" matches "hin_Deva" (exact match)
    - "tel" matches "tel_Telu" (base matches)
    """
    if not detected_lang or not target_lang:
        return False
    
    # Normalize both codes
    detected_normalized = normalize_language_code(detected_lang)
    target_normalized = normalize_language_code(target_lang)
    
    # Exact match after normalization
    if detected_normalized == target_normalized:
        return True
    
    # Base language match
    detected_base = get_base_language(detected_lang)
    target_base = get_base_language(target_lang)
    
    if detected_base and target_base and detected_base == target_base:
        return True
    
    return False


def log_full_response(request_id: str, full_response: dict):
    """Log the full detailed response for debugging/monitoring"""
    logger.info(f"[{request_id}] Full response logged to {JSON_LOG_FILE}")
    log_json_entry({"request_id": request_id, "response": full_response})


def simplify_response(full_response: dict) -> dict:
    """
    Convert full detailed response to minimal frontend-friendly format.
    """
    outputs = []
    
    for trans in full_response.get("translations", []):
        output = trans.get("final", "") or trans.get("translated", "") or trans.get("output", "")
        outputs.append(output)
    
    # If single translation, return just the string
    if len(outputs) == 1:
        return {"output": outputs[0]}
    
    return {"output": outputs}


# ============================================================================
# ENDPOINTS
# ============================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the translation UI"""
    ui_path = os.path.join(os.path.dirname(__file__), "final_translation_UI.HTML")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Translation Gateway</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
            .feature { background: #e8f5e9; padding: 10px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4caf50; }
        </style>
    </head>
    <body>
        <h1>🌐 Translation API Gateway</h1>
        <p>Unified endpoint for bidirectional Indic ↔ English translation</p>
        
        <div class="feature">
            <strong>✨ Transliteration Shortcut:</strong> 
            When input is in Roman script and detected language matches target language,
            returns transliterated text directly without translation.
        </div>
        
        <h2>Services</h2>
        <div class="endpoint">
            <strong>LID + Transliteration:</strong> <code>GET /services/lid/health</code>
        </div>
        <div class="endpoint">
            <strong>Indic → English:</strong> <code>GET /services/indic-en/health</code>
        </div>
        <div class="endpoint">
            <strong>English → Indic:</strong> <code>GET /services/en-indic/health</code>
        </div>
        
        <h2>Translation</h2>
        <div class="endpoint">
            <strong>Translate (simple response):</strong> <code>POST /translate</code>
        </div>
        <div class="endpoint">
            <strong>Translate (detailed response):</strong> <code>POST /translate/detailed</code>
        </div>
        
        <p><a href="/docs">📚 API Documentation (Swagger)</a></p>
    </body>
    </html>
    """)


@app.get("/health")
async def health():
    """Gateway health check"""
    services = {}
    
    for name, url in [
        ("lid_transliteration", get_lid_url()),
        ("indic_to_english", get_indic_en_url()),
        ("english_to_indic", get_en_indic_url())
    ]:
        try:
            resp = await http_client.get(f"{url}/health")
            services[name] = resp.json() if resp.status_code == 200 else {"status": "error"}
        except Exception as e:
            services[name] = {"status": "unavailable", "error": str(e)}
    
    all_healthy = all(s.get("status") == "ok" for s in services.values())
    
    return {
        "status": "ok" if all_healthy else "degraded",
        "gateway": "translation-api-gateway",
        "version": "1.1.0",
        "features": ["transliteration_shortcut"],
        "services": services
    }


@app.get("/languages")
def get_languages():
    """Get supported languages"""
    return {"languages": LANGUAGE_OPTIONS}


@app.post("/translate")
async def translate(req: TranslateRequest):
    """
    Unified translation endpoint.
    
    Features:
    - Routes to appropriate service based on source and target languages
    - SHORTCUT: If Roman input detected language == target language, returns transliterated text only
    - Returns simplified response for frontend
    """
    t_start = time.time()
    request_id = f"req_{int(t_start * 1000)}"
    
    # Normalize input
    sentences = req.sentences if req.sentences else ([req.text] if req.text else None)
    if not sentences:
        raise HTTPException(status_code=400, detail="No input text provided")
    
    src_lang = SHORT_TO_INDICTRANS.get(req.src_lang, req.src_lang) if req.src_lang else "auto"
    tgt_lang = SHORT_TO_INDICTRANS.get(req.tgt_lang, req.tgt_lang)
    is_auto = src_lang in ("auto", "Auto", "AUTO")
    
    logger.info(f"[{request_id}] Translation request: src={src_lang}, tgt={tgt_lang}, sentences={len(sentences)}")
    
    # Determine translation direction and route
    if tgt_lang == "eng_Latn":
        # Indic → English flow
        full_result = await _translate_indic_to_english(request_id, sentences, src_lang, is_auto, req, t_start)
    
    elif src_lang == "eng_Latn":
        # English → Indic flow (no shortcut possible)
        full_result = await _translate_english_to_indic(request_id, sentences, tgt_lang, req, t_start)
    
    elif is_auto or src_lang != tgt_lang:
        # Need to detect language first, then decide
        full_result = await _translate_with_lid_check(request_id, sentences, src_lang, tgt_lang, is_auto, req, t_start)
    
    else:
        raise HTTPException(status_code=400, detail="Please select a valid source and target language")
    
    # Log full detailed response
    log_full_response(request_id, full_result)
    
    # Return simplified response for frontend
    simplified = simplify_response(full_result)
    logger.info(f"[{request_id}] Simplified response: {json.dumps(simplified, ensure_ascii=False)[:200]}...")
    
    return simplified


@app.post("/translate/detailed")
async def translate_detailed(req: TranslateRequest):
    """
    Translation endpoint that returns full detailed response.
    Use this for debugging or when you need all the processing details.
    """
    t_start = time.time()
    request_id = f"req_{int(t_start * 1000)}"
    
    # Normalize input
    sentences = req.sentences if req.sentences else ([req.text] if req.text else None)
    if not sentences:
        raise HTTPException(status_code=400, detail="No input text provided")
    
    src_lang = SHORT_TO_INDICTRANS.get(req.src_lang, req.src_lang) if req.src_lang else "auto"
    tgt_lang = SHORT_TO_INDICTRANS.get(req.tgt_lang, req.tgt_lang)
    is_auto = src_lang in ("auto", "Auto", "AUTO")
    
    logger.info(f"[{request_id}] Detailed translation request: src={src_lang}, tgt={tgt_lang}")
    
    if tgt_lang == "eng_Latn":
        return await _translate_indic_to_english(request_id, sentences, src_lang, is_auto, req, t_start)
    
    elif src_lang == "eng_Latn":
        return await _translate_english_to_indic(request_id, sentences, tgt_lang, req, t_start)
    
    elif is_auto or src_lang != tgt_lang:
        return await _translate_with_lid_check(request_id, sentences, src_lang, tgt_lang, is_auto, req, t_start)
    
    else:
        raise HTTPException(status_code=400, detail="Please select a valid source and target language")


async def _call_lid_service(sentences: List[str], src_lang_hint: Optional[str] = None) -> Optional[List[dict]]:
    """Call LID service for language detection and transliteration"""
    url = get_lid_url()
    started = time.time()
    success = False
    try:
        payload = {"texts": sentences}
        if src_lang_hint and src_lang_hint not in ("auto", "Auto", "AUTO"):
            payload["src_lang_hint"] = src_lang_hint

        lid_response = await http_client.post(
            f"{url}/batch_process",
            json=payload,
            timeout=30.0
        )
        lid_response.raise_for_status()
        success = True
        return lid_response.json().get("results", [])
    except Exception as e:
        logger.warning(f"LID service unavailable: {e}")
        return None
    finally:
        _record_metrics("lid", url, started, success)


async def _translate_with_lid_check(
    request_id: str,
    sentences: List[str],
    src_lang: str,
    tgt_lang: str,
    is_auto: bool,
    req: TranslateRequest,
    t_start: float
) -> dict:
    """
    Main routing logic with LID check for transliteration shortcut.
    
    SHORTCUT: If input is Roman and detected language == target language,
    return transliterated text without translation.
    """
    logger.info(f"[{request_id}] Checking LID for potential transliteration shortcut...")
    
    # Call LID service
    lid_results = await _call_lid_service(sentences, src_lang if not is_auto else None)
    
    if not lid_results:
        # LID unavailable, fall back to normal translation
        logger.warning(f"[{request_id}] LID unavailable, proceeding with translation")
        if tgt_lang == "eng_Latn":
            return await _translate_indic_to_english(request_id, sentences, src_lang, is_auto, req, t_start)
        else:
            return await _translate_indic_to_indic(request_id, sentences, src_lang, tgt_lang, is_auto, req, t_start)
    
    # Check each sentence for transliteration shortcut
    transliteration_only = []
    needs_translation = []
    
    for idx, (sentence, lid_result) in enumerate(zip(sentences, lid_results)):
        detected_lang = lid_result.get("detected_language", "")
        translit_info = lid_result.get("translit_info", {})
        processed_text = lid_result.get("processed_text", sentence)
        
        # Check if this is Roman script
        is_roman = is_roman_script(lid_result)
        
        # Check if detected language matches target language
        lang_matches = languages_match(detected_lang, tgt_lang)
        
        logger.debug(f"[{request_id}] Sentence {idx}: detected={detected_lang}, target={tgt_lang}, "
                    f"is_roman={is_roman}, lang_matches={lang_matches}")
        
        if is_roman and lang_matches:
            # SHORTCUT: Same language, just need transliteration
            transliterated_text = translit_info.get("transliterated_text", "") or processed_text
            
            logger.info(f"[{request_id}] [SHORTCUT] Sentence {idx}: Roman {detected_lang} → {tgt_lang} "
                       f"(transliteration only, no translation needed)")
            
            transliteration_only.append({
                "idx": idx,
                "input": sentence,
                "output": transliterated_text,
                "lid_result": lid_result,
                "shortcut_applied": True
            })
        else:
            # Needs translation
            needs_translation.append({
                "idx": idx,
                "sentence": sentence,
                "lid_result": lid_result
            })
    
    # If all sentences are transliteration-only
    if not needs_translation:
        logger.info(f"[{request_id}] All {len(sentences)} sentences handled via transliteration shortcut")
        
        translations = []
        for item in sorted(transliteration_only, key=lambda x: x["idx"]):
            translations.append({
                "id": item["idx"] + 1,
                "input": item["input"],
                "language": item["lid_result"].get("detected_language", ""),
                "target_language": tgt_lang,
                "translated": item["output"],
                "final": item["output"],
                "preprocessing": {
                    "shortcut": "transliteration_only",
                    "reason": "detected_language_matches_target",
                    "is_roman": True,
                    "translit_info": item["lid_result"].get("translit_info", {})
                },
                "entity_comparison": {},
                "entity_fixes": []
            })
        
        return {
            "translations": translations,
            "direction": f"transliteration → {tgt_lang}",
            "source_lang": "roman",
            "target_lang": tgt_lang,
            "shortcut_applied": True,
            "shortcut_count": len(transliteration_only),
            "gateway_time_seconds": round(time.time() - t_start, 3)
        }
    
    # If all need translation (no shortcuts)
    if not transliteration_only:
        logger.info(f"[{request_id}] No transliteration shortcuts, proceeding with translation")
        
        if tgt_lang == "eng_Latn":
            return await _translate_indic_to_english_with_lid(
                request_id, sentences, lid_results, req, t_start
            )
        else:
            return await _translate_indic_to_indic_with_lid(
                request_id, sentences, lid_results, tgt_lang, req, t_start
            )
    
    # Mixed: some transliteration-only, some need translation
    logger.info(f"[{request_id}] Mixed: {len(transliteration_only)} transliteration, "
               f"{len(needs_translation)} translation")
    
    # Translate only the sentences that need it
    translation_sentences = [item["sentence"] for item in needs_translation]
    translation_lid_results = [item["lid_result"] for item in needs_translation]
    
    if tgt_lang == "eng_Latn":
        trans_result = await _translate_indic_to_english_with_lid(
            request_id, translation_sentences, translation_lid_results, req, t_start
        )
    else:
        trans_result = await _translate_indic_to_indic_with_lid(
            request_id, translation_sentences, translation_lid_results, tgt_lang, req, t_start
        )
    
    # Merge results back in original order
    final_translations = [None] * len(sentences)
    
    # Insert transliteration-only results
    for item in transliteration_only:
        final_translations[item["idx"]] = {
            "id": item["idx"] + 1,
            "input": item["input"],
            "language": item["lid_result"].get("detected_language", ""),
            "target_language": tgt_lang,
            "translated": item["output"],
            "final": item["output"],
            "preprocessing": {
                "shortcut": "transliteration_only",
                "reason": "detected_language_matches_target",
                "is_roman": True,
                "translit_info": item["lid_result"].get("translit_info", {})
            },
            "entity_comparison": {},
            "entity_fixes": []
        }
    
    # Insert translation results
    trans_list = trans_result.get("translations", [])
    for i, item in enumerate(needs_translation):
        if i < len(trans_list):
            trans_entry = trans_list[i]
            trans_entry["id"] = item["idx"] + 1  # Fix ID to match original position
            final_translations[item["idx"]] = trans_entry
    
    return {
        "translations": final_translations,
        "direction": f"mixed → {tgt_lang}",
        "source_lang": "auto",
        "target_lang": tgt_lang,
        "shortcut_applied": True,
        "shortcut_count": len(transliteration_only),
        "translation_count": len(needs_translation),
        "gateway_time_seconds": round(time.time() - t_start, 3)
    }


async def _translate_indic_to_english(
    request_id: str,
    sentences: List[str],
    src_lang: str,
    is_auto: bool,
    req: TranslateRequest,
    t_start: float
) -> dict:
    """Route to Indic → English service"""
    lid_results = None
    
    if is_auto:
        lid_results = await _call_lid_service(sentences)
    
    return await _translate_indic_to_english_with_lid(
        request_id, sentences, lid_results, req, t_start
    )


async def _translate_indic_to_english_with_lid(
    request_id: str,
    sentences: List[str],
    lid_results: Optional[List[dict]],
    req: TranslateRequest,
    t_start: float
) -> dict:
    """Translate Indic → English with pre-fetched LID results"""
    try:
        payload = {
            "sentences": sentences,
            "src_lang": "auto",
            "num_beams": req.num_beams,
            "max_new_tokens": req.max_new_tokens
        }
        
        if lid_results:
            payload["lid_results"] = [
                {
                    "processed_text": r.get("processed_text"),
                    "detected_language": r.get("detected_language"),
                    "translit_info": r.get("translit_info")
                }
                for r in lid_results
            ]
        
        url = get_indic_en_url()
        started = time.time()
        success = False
        try:
            response = await http_client.post(
                f"{url}/batch_translate",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            success = True
            result = response.json()
            result["gateway_time_seconds"] = round(time.time() - t_start, 3)
            return result
        finally:
            _record_metrics("indic_en", url, started, success)

    except httpx.HTTPError as e:
        logger.error(f"[{request_id}] Translation service error: {e}")
        raise HTTPException(status_code=503, detail=f"Translation service error: {str(e)}")


async def _translate_english_to_indic(
    request_id: str,
    sentences: List[str],
    tgt_lang: str,
    req: TranslateRequest,
    t_start: float
) -> dict:
    """Route to English → Indic service"""
    url = get_en_indic_url()
    started = time.time()
    success = False
    try:
        response = await http_client.post(
            f"{url}/batch_translate",
            json={
                "sentences": sentences,
                "tgt_lang": tgt_lang,
                "num_beams": req.num_beams,
                "max_new_tokens": req.max_new_tokens
            },
            timeout=60.0
        )
        response.raise_for_status()
        success = True
        result = response.json()
        result["gateway_time_seconds"] = round(time.time() - t_start, 3)
        return result

    except httpx.HTTPError as e:
        logger.error(f"[{request_id}] Translation service error: {e}")
        raise HTTPException(status_code=503, detail=f"Translation service error: {str(e)}")
    finally:
        _record_metrics("en_indic", url, started, success)


async def _translate_indic_to_indic(
    request_id: str,
    sentences: List[str],
    src_lang: str,
    tgt_lang: str,
    is_auto: bool,
    req: TranslateRequest,
    t_start: float
) -> dict:
    """Route Indic → Indic translation (via English)"""
    # Step 1: Indic → English
    step1_result = await _translate_indic_to_english(
        request_id, sentences, src_lang, is_auto, req, t_start
    )
    
    # Extract English translations
    en_sentences = []
    for t in step1_result.get("translations", []):
        en_text = t.get("final", "") or t.get("translated", "") or ""
        en_sentences.append(en_text)
    
    if not en_sentences or all(not s.strip() for s in en_sentences):
        return step1_result
    
    # Step 2: English → Target Indic
    return await _translate_english_to_indic_with_intermediate(
        request_id, en_sentences, tgt_lang, step1_result, req, t_start
    )


async def _translate_indic_to_indic_with_lid(
    request_id: str,
    sentences: List[str],
    lid_results: List[dict],
    tgt_lang: str,
    req: TranslateRequest,
    t_start: float
) -> dict:
    """Route Indic → Indic translation with pre-fetched LID results"""
    # Step 1: Indic → English
    step1_result = await _translate_indic_to_english_with_lid(
        request_id, sentences, lid_results, req, t_start
    )
    
    # Extract English translations
    en_sentences = []
    for t in step1_result.get("translations", []):
        en_text = t.get("final", "") or t.get("translated", "") or ""
        en_sentences.append(en_text)
    
    if not en_sentences or all(not s.strip() for s in en_sentences):
        return step1_result
    
    # Step 2: English → Target Indic
    return await _translate_english_to_indic_with_intermediate(
        request_id, en_sentences, tgt_lang, step1_result, req, t_start
    )


async def _translate_english_to_indic_with_intermediate(
    request_id: str,
    en_sentences: List[str],
    tgt_lang: str,
    step1_result: dict,
    req: TranslateRequest,
    t_start: float
) -> dict:
    """English → Indic translation with intermediate results tracking"""
    url = get_en_indic_url()
    started = time.time()
    success = False
    try:
        response = await http_client.post(
            f"{url}/batch_translate",
            json={
                "sentences": en_sentences,
                "tgt_lang": tgt_lang,
                "num_beams": req.num_beams,
                "max_new_tokens": req.max_new_tokens
            },
            timeout=60.0
        )
        response.raise_for_status()
        success = True
        result = response.json()

        # Add intermediate translations
        for i, trans in enumerate(result.get("translations", [])):
            if i < len(step1_result.get("translations", [])):
                trans["english_intermediate"] = step1_result["translations"][i].get("final", "")

        result["direction"] = f"{step1_result.get('source_lang_detected', 'auto')} → eng → {tgt_lang}"
        result["gateway_time_seconds"] = round(time.time() - t_start, 3)
        return result

    except httpx.HTTPError as e:
        logger.error(f"[{request_id}] Translation service error: {e}")
        raise HTTPException(status_code=503, detail=f"Translation service error: {str(e)}")
    finally:
        _record_metrics("en_indic", url, started, success)


# ============================================================================
# SERVICE PROXIES (for debugging)
# ============================================================================
@app.get("/services/lid/health")
async def lid_health():
    """Proxy to LID service health"""
    try:
        resp = await http_client.get(f"{get_lid_url()}/health")
        return resp.json()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@app.get("/services/indic-en/health")
async def indic_en_health():
    """Proxy to Indic→EN service health"""
    try:
        resp = await http_client.get(f"{get_indic_en_url()}/health")
        return resp.json()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@app.get("/services/en-indic/health")
async def en_indic_health():
    """Proxy to EN→Indic service health"""
    try:
        resp = await http_client.get(f"{get_en_indic_url()}/health")
        return resp.json()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@app.post("/clear-cache")
async def clear_all_caches():
    """Clear caches in all services"""
    results = {}

    for name, url in [
        ("lid", get_lid_url()),
        ("indic_en", get_indic_en_url()),
        ("en_indic", get_en_indic_url())
    ]:
        try:
            resp = await http_client.post(f"{url}/clear-cache")
            results[name] = resp.json()
        except Exception as e:
            results[name] = {"error": str(e)}

    return {"status": "caches cleared", "services": results}


# ============================================================================
# AUTO-SCALER
# ============================================================================
@app.on_event("startup")
async def _autoscaler_startup():
    """Start the RunPod autoscaler background loops on app startup"""
    await start_autoscaler()


@app.get("/autoscaler/status")
async def autoscaler_status():
    """View autoscaler state: pods, RPS, latency, scaling decisions"""
    if not AUTOSCALER_ENABLED:
        return {"enabled": False, "message": "Set AUTOSCALER_ENABLED=true to enable"}
    return get_autoscaler().status()


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"✓ Translation API Gateway ready")
    print(f"{'='*60}")
    print(f"LID Service: {LID_SERVICE_URL}")
    print(f"Indic→EN Service: {INDIC_EN_SERVICE_URL}")
    print(f"EN→Indic Service: {EN_INDIC_SERVICE_URL}")
    print(f"")
    print(f"FEATURES:")
    print(f"  ✓ Transliteration shortcut (Roman input + same language = no translation)")
    print(f"  ✓ Detailed logging to {LOG_DIR}")
    print(f"")
    print(f"ENDPOINTS:")
    print(f"  POST /translate         - Simple response")
    print(f"  POST /translate/detailed - Full response with debug info")
    print(f"")
    print(f"Swagger UI → http://localhost:{SERVICE_PORT}/docs")
    print(f"{'='*60}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)