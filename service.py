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
# LID_SERVICE_URL = os.environ.get("LID_SERVICE_URL", "http://localhost:6001")
# INDIC_EN_SERVICE_URL = os.environ.get("INDIC_EN_SERVICE_URL", "http://localhost:6002")
# EN_INDIC_SERVICE_URL = os.environ.get("EN_INDIC_SERVICE_URL", "http://localhost:6003")

# E2E NETWORKS
LID_SERVICE_URL = os.environ.get("LID_SERVICE_URL", "http://165.232.178.107:6001")
INDIC_EN_SERVICE_URL = os.environ.get("INDIC_EN_SERVICE_URL", "http://164.52.194.212:6002")
EN_INDIC_SERVICE_URL = os.environ.get("EN_INDIC_SERVICE_URL", "http://164.52.194.212:6003")

# RUNPOD
# INDIC_EN_SERVICE_URL = os.environ.get("INDIC_EN_SERVICE_URL", "https://tpo8k3tqbvj39o-6002.proxy.runpod.net")
# EN_INDIC_SERVICE_URL = os.environ.get("EN_INDIC_SERVICE_URL", "https://5uv9ga9wwrrtzg-6003.proxy.runpod.net")



SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "6005"))

# Short code mappings
SHORT_TO_INDICTRANS = {
    "te": "tel_Telu", "hi": "hin_Deva", "kn": "kan_Knda", "ml": "mal_Mlym",
    "ta": "tam_Taml", "mr": "mar_Deva", "pa": "pan_Guru", "bn": "ben_Beng",
    "gu": "guj_Gujr", "ur": "urd_Arab", "as": "asm_Beng", "or": "ory_Orya",
    "ne": "npi_Deva", "en": "eng_Latn", "brx": "brx_Deva", "ks": "kas_Arab",
    "mai": "mai_Deva", "mni": "mni_Mtei", "sd": "snd_Arab", "gom": "gom_Deva"
}

INDICTRANS_TO_SHORT = {v: k for k, v in SHORT_TO_INDICTRANS.items()}
_INDICTRANS2_VALID_CODES = set(SHORT_TO_INDICTRANS.values())

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
http_client = httpx.AsyncClient(timeout=60.0)

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


# Unicode script ranges → IndicTrans2 language code
# Used as a zero-dependency fallback when the LID service is unavailable.
# For scripts shared by multiple languages (e.g. Devanagari), returns the
# most common language; the translation model handles disambiguation.
SCRIPT_RANGES = [
    (0x0C00, 0x0C7F, "tel_Telu"),    # Telugu
    (0x0C80, 0x0CFF, "kan_Knda"),    # Kannada
    (0x0D00, 0x0D7F, "mal_Mlym"),    # Malayalam
    (0x0B80, 0x0BFF, "tam_Taml"),    # Tamil
    (0x0980, 0x09FF, "ben_Beng"),    # Bengali / Assamese
    (0x0A00, 0x0A7F, "pan_Guru"),    # Gurmukhi (Punjabi)
    (0x0A80, 0x0AFF, "guj_Gujr"),    # Gujarati
    (0x0B00, 0x0B7F, "ory_Orya"),    # Odia
    (0x0900, 0x097F, "hin_Deva"),    # Devanagari (Hindi / Marathi / others)
    (0x0600, 0x06FF, "urd_Arab"),    # Arabic script (Urdu / Kashmiri / Sindhi)
    (0x0750, 0x077F, "urd_Arab"),    # Arabic supplement
    (0xABC0, 0xABFF, "mni_Mtei"),    # Meetei Mayek (Manipuri)
]


def detect_language_from_script(text: str) -> Optional[str]:
    """
    Detect language from Unicode script of characters.
    
    Simple, reliable fallback for native-script text when the LID service
    is unavailable. Returns an IndicTrans2 language code or None.
    """
    if not text:
        return None
    
    # Count characters per script
    script_counts: Dict[str, int] = {}
    total_alpha = 0
    
    for ch in text:
        cp = ord(ch)
        for start, end, lang_code in SCRIPT_RANGES:
            if start <= cp <= end:
                script_counts[lang_code] = script_counts.get(lang_code, 0) + 1
                total_alpha += 1
                break
        else:
            # Check if it's a Latin letter (English / Roman)
            if ch.isalpha() and cp < 0x0250:
                script_counts["eng_Latn"] = script_counts.get("eng_Latn", 0) + 1
                total_alpha += 1
    
    if not script_counts or total_alpha == 0:
        return None
    
    # Return the dominant script language
    dominant_lang = max(script_counts, key=script_counts.get)
    dominant_ratio = script_counts[dominant_lang] / total_alpha
    
    # Only return if dominant script is a clear majority (>60%)
    if dominant_ratio > 0.6:
        return dominant_lang
    
    return None


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
    detected_lang = lid_result.get("detected_language") or ""
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


def _build_skip_response(
    sentences: List[str],
    src_lang: str,
    tgt_lang: str,
    t_start: float
) -> dict:
    """
    Build a response that returns input as-is when detected/source language
    matches the target language — no translation needed.
    """
    translations = []
    for idx, sentence in enumerate(sentences):
        translations.append({
            "id": idx + 1,
            "input": sentence,
            "language": src_lang,
            "target_language": tgt_lang,
            "translated": sentence,
            "final": sentence,
            "preprocessing": {
                "skipped": True,
                "reason": "detected_language_matches_target",
                "detected_language": src_lang,
            },
            "entity_comparison": {},
            "entity_fixes": []
        })
    
    return {
        "translations": translations,
        "direction": f"{src_lang} → {tgt_lang} (no-op)",
        "source_lang_detected": src_lang,
        "target_lang_code": tgt_lang,
        "skipped": True,
        "time_seconds": 0.0,
        "gateway_time_seconds": round(time.time() - t_start, 3)
    }


def _resolve_src_lang_from_lid(
    lid_results: Optional[List[dict]],
    sentences: List[str]
) -> str:
    """
    Resolve source language from LID results, falling back to Unicode
    script detection. Never returns 'auto'.
    
    Returns an IndicTrans2 language code (e.g. 'tel_Telu') or 'auto' only
    as an absolute last resort.
    """
    # Try LID results first
    if lid_results:
        for r in lid_results:
            detected = r.get("detected_language", "")
            if detected:
                normalized = normalize_language_code(detected)
                if normalized and normalized.lower() not in ("auto", "unknown", ""):
                    return normalized
            # Also try translit_info fasttext_label
            translit = r.get("translit_info", {})
            ft_label = translit.get("fasttext_label", "")
            if ft_label:
                mapped = LID_TO_INDICTRANS.get(ft_label)
                if mapped:
                    return mapped
    
    # Fall back to Unicode script detection
    combined = " ".join(sentences) if sentences else ""
    script_lang = detect_language_from_script(combined)
    if script_lang:
        return script_lang
    
    return "auto"


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
        ("lid_transliteration", LID_SERVICE_URL),
        ("indic_to_english", INDIC_EN_SERVICE_URL),
        ("english_to_indic", EN_INDIC_SERVICE_URL)
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
    
    elif src_lang == tgt_lang:
        # Explicit same-language: skip translation, return input as-is
        logger.info(f"[{request_id}] [SKIP] src_lang == tgt_lang ({src_lang}), returning input as-is")
        full_result = _build_skip_response(sentences, src_lang, tgt_lang, t_start)
    
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
    
    elif src_lang == tgt_lang:
        # Explicit same-language: skip translation, return input as-is
        logger.info(f"[{request_id}] [SKIP] src_lang == tgt_lang ({src_lang}), returning input as-is")
        return _build_skip_response(sentences, src_lang, tgt_lang, t_start)
    
    else:
        raise HTTPException(status_code=400, detail="Please select a valid source and target language")


async def _call_lid_service(sentences: List[str], src_lang_hint: Optional[str] = None) -> Optional[List[dict]]:
    """Call LID service for language detection and transliteration"""
    try:
        payload = {"texts": sentences}
        if src_lang_hint and src_lang_hint not in ("auto", "Auto", "AUTO"):
            payload["src_lang_hint"] = src_lang_hint
        
        logger.info(f"Calling LID service at {LID_SERVICE_URL}/batch_process with {len(sentences)} sentences")
        
        lid_response = await http_client.post(
            f"{LID_SERVICE_URL}/batch_process",
            json=payload,
            timeout=30.0
        )
        lid_response.raise_for_status()
        lid_data = lid_response.json()
        
        results = lid_data.get("results", [])
        logger.info(f"LID service returned {len(results)} results (keys in response: {list(lid_data.keys())})")
        
        # If "results" key is empty, try other common keys
        if not results:
            for alt_key in ["predictions", "output", "data", "detections"]:
                results = lid_data.get(alt_key, [])
                if results:
                    logger.info(f"LID results found under key '{alt_key}' instead of 'results'")
                    break
        
        if not results:
            logger.warning(f"LID response had no results. Full response keys: {list(lid_data.keys())}, "
                          f"response preview: {json.dumps(lid_data, ensure_ascii=False)[:500]}")
        
        return results if results else None
        
    except Exception as e:
        logger.error(f"LID service call FAILED: {type(e).__name__}: {e}")
        return None


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
        translit_info = lid_result.get("translit_info", {}) or {}
        processed_text = lid_result.get("processed_text", sentence)

        # Fallback resolution when LID couldn't assign a language — use
        # fasttext_label, then per-sentence Unicode script detection.
        if not detected_lang:
            ft_label = translit_info.get("fasttext_label", "")
            mapped = LID_TO_INDICTRANS.get(ft_label) if ft_label else None
            if not mapped and ft_label in _INDICTRANS2_VALID_CODES:
                mapped = ft_label
            if not mapped:
                mapped = detect_language_from_script(sentence)
            if mapped:
                detected_lang = mapped
                lid_result["detected_language"] = mapped  # persist for downstream

        # Check if this is Roman script
        is_roman = is_roman_script(lid_result)

        # Check if detected language matches target language
        lang_matches = languages_match(detected_lang, tgt_lang)
        
        logger.debug(f"[{request_id}] Sentence {idx}: detected={detected_lang}, target={tgt_lang}, "
                    f"is_roman={is_roman}, lang_matches={lang_matches}")
        
        logger.info(
            f"[{request_id}] Sentence {idx}: detected={detected_lang}, "
            f"normalized={normalize_language_code(detected_lang)}, "
            f"target={tgt_lang}, is_roman={is_roman}, "
            f"lang_matches={lang_matches}, "
            f"translit_info={translit_info}"
        )
        
        if lang_matches and is_roman:
            # SHORTCUT: Roman script, same language → return transliterated text
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
        elif lang_matches and not is_roman:
            # SKIP: Native script, same language → return input as-is
            logger.info(f"[{request_id}] [SKIP] Sentence {idx}: native {detected_lang} == target {tgt_lang} "
                       f"(already in target language, no translation needed)")
            
            transliteration_only.append({
                "idx": idx,
                "input": sentence,
                "output": sentence,
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
        
        # Resolve src_lang from LID results
        resolved = _resolve_src_lang_from_lid(lid_results, sentences)
        
        if tgt_lang == "eng_Latn":
            return await _translate_indic_to_english_with_lid(
                request_id, sentences, lid_results, resolved, req, t_start
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
    
    # Resolve src_lang from LID results of sentences needing translation
    resolved = _resolve_src_lang_from_lid(translation_lid_results, translation_sentences)
    
    if tgt_lang == "eng_Latn":
        trans_result = await _translate_indic_to_english_with_lid(
            request_id, translation_sentences, translation_lid_results, resolved, req, t_start
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
    """Route to Indic → English service.
    
    CRITICAL: This function always resolves the source language before
    calling the translation service. It never sends src_lang='auto'.
    
    Resolution order:
      1. LID service (best quality)
      2. Unicode script detection (zero-dependency fallback)
      3. Explicit src_lang from the user (if not auto)
    """
    lid_results = None
    resolved_src_lang = src_lang  # may still be "auto" here
    
    if is_auto:
        # ── Step 1: Try LID service ──
        lid_results = await _call_lid_service(sentences)
        logger.info(f"[{request_id}] LID results received: {lid_results is not None}")
        
        if lid_results:
            # Extract detected language from first result
            first_detected = lid_results[0].get("detected_language", "")
            normalized = normalize_language_code(first_detected)
            if normalized and normalized != first_detected:
                logger.info(f"[{request_id}] LID detected: {first_detected} → normalized: {normalized}")
            if normalized:
                resolved_src_lang = normalized
        
        # ── Step 2: If LID failed, fall back to Unicode script detection ──
        if resolved_src_lang in ("auto", "Auto", "AUTO"):
            combined_text = " ".join(sentences)
            script_lang = detect_language_from_script(combined_text)
            if script_lang:
                resolved_src_lang = script_lang
                logger.info(f"[{request_id}] [SCRIPT-FALLBACK] Unicode script detection: {script_lang}")
            else:
                logger.warning(f"[{request_id}] Could not detect language via LID or script detection")
    
    # ── Same-language skip: if resolved lang == target (eng_Latn), return as-is ──
    if languages_match(resolved_src_lang, "eng_Latn"):
        logger.info(f"[{request_id}] [SKIP] Detected English, same as target eng_Latn — skipping translation")
        return _build_skip_response(sentences, resolved_src_lang, "eng_Latn", t_start)
    
    logger.info(f"[{request_id}] Sending to translation service with src_lang={resolved_src_lang}")
    
    return await _translate_indic_to_english_with_lid(
        request_id, sentences, lid_results, resolved_src_lang, req, t_start
    )


async def _translate_indic_to_english_with_lid(
    request_id: str,
    sentences: List[str],
    lid_results: Optional[List[dict]],
    resolved_src_lang: str,
    req: TranslateRequest,
    t_start: float
) -> dict:
    """Translate Indic → English with pre-resolved source language.
    
    Always sends an explicit src_lang to the translation service.
    Falls back to fasttext-based retry if the first attempt still fails.
    """
    try:
        payload = {
            "sentences": sentences,
            "src_lang": resolved_src_lang,
            "num_beams": req.num_beams,
            "max_new_tokens": req.max_new_tokens
        }
        
        if lid_results:
            payload["lid_results"] = [
                {
                    "processed_text": r.get("processed_text"),
                    # Patch with resolved_src_lang when LID could not resolve
                    # a language code — otherwise the downstream service will
                    # treat the sentence as "unknown" and skip translation.
                    "detected_language": (
                        normalize_language_code(r.get("detected_language"))
                        if r.get("detected_language")
                        else resolved_src_lang
                    ),
                    "translit_info": r.get("translit_info")
                }
                for r in lid_results
            ]
        
        logger.info(f"[{request_id}] Calling translation service: src_lang={resolved_src_lang}, "
                    f"has_lid_results={lid_results is not None}")
        
        response = await http_client.post(
            f"{INDIC_EN_SERVICE_URL}/batch_translate",
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()
        
        # ── Last-resort fallback: if translation service STILL fails ──
        # Extract fasttext_label from its response and retry
        translations = result.get("translations", [])
        has_detection_failure = any(
            t.get("preprocessing", {}).get("language_detection_failed", False)
            for t in translations
        )
        
        if has_detection_failure:
            resolved_lang = None
            for t in translations:
                preproc = t.get("preprocessing", {})
                if preproc.get("language_detection_failed"):
                    translit = preproc.get("transliteration", {})
                    ft_label = translit.get("fasttext_label", "")
                    ft_conf = translit.get("fasttext_confidence", 0)
                    
                    if ft_label and ft_conf > 0.5:
                        mapped = LID_TO_INDICTRANS.get(ft_label)
                        if mapped and mapped != "eng_Latn" and mapped != resolved_src_lang:
                            resolved_lang = mapped
                            logger.info(
                                f"[{request_id}] [FASTTEXT-FALLBACK] Detection failed with "
                                f"src_lang={resolved_src_lang}, but fasttext found '{ft_label}' "
                                f"(conf={ft_conf:.4f}). Retrying with src_lang={mapped}."
                            )
                            break
            
            if resolved_lang:
                retry_payload = {
                    "sentences": sentences,
                    "src_lang": resolved_lang,
                    "num_beams": req.num_beams,
                    "max_new_tokens": req.max_new_tokens
                }
                retry_response = await http_client.post(
                    f"{INDIC_EN_SERVICE_URL}/batch_translate",
                    json=retry_payload,
                    timeout=60.0
                )
                retry_response.raise_for_status()
                result = retry_response.json()
                result["fallback_applied"] = True
                result["fallback_src_lang"] = resolved_lang
                logger.info(f"[{request_id}] [FASTTEXT-FALLBACK] Retry succeeded with src_lang={resolved_lang}")
        
        result["gateway_time_seconds"] = round(time.time() - t_start, 3)
        return result
        
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
    try:
        response = await http_client.post(
            f"{EN_INDIC_SERVICE_URL}/batch_translate",
            json={
                "sentences": sentences,
                "tgt_lang": tgt_lang,
                "num_beams": req.num_beams,
                "max_new_tokens": req.max_new_tokens
            },
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()
        result["gateway_time_seconds"] = round(time.time() - t_start, 3)
        return result
        
    except httpx.HTTPError as e:
        logger.error(f"[{request_id}] Translation service error: {e}")
        raise HTTPException(status_code=503, detail=f"Translation service error: {str(e)}")


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
    resolved = _resolve_src_lang_from_lid(lid_results, sentences)
    step1_result = await _translate_indic_to_english_with_lid(
        request_id, sentences, lid_results, resolved, req, t_start
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
    try:
        response = await http_client.post(
            f"{EN_INDIC_SERVICE_URL}/batch_translate",
            json={
                "sentences": en_sentences,
                "tgt_lang": tgt_lang,
                "num_beams": req.num_beams,
                "max_new_tokens": req.max_new_tokens
            },
            timeout=60.0
        )
        response.raise_for_status()
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


# ============================================================================
# SERVICE PROXIES (for debugging)
# ============================================================================
@app.get("/services/lid/health")
async def lid_health():
    """Proxy to LID service health"""
    try:
        resp = await http_client.get(f"{LID_SERVICE_URL}/health")
        return resp.json()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@app.get("/services/indic-en/health")
async def indic_en_health():
    """Proxy to Indic→EN service health"""
    try:
        resp = await http_client.get(f"{INDIC_EN_SERVICE_URL}/health")
        return resp.json()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@app.get("/services/en-indic/health")
async def en_indic_health():
    """Proxy to EN→Indic service health"""
    try:
        resp = await http_client.get(f"{EN_INDIC_SERVICE_URL}/health")
        return resp.json()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@app.post("/clear-cache")
async def clear_all_caches():
    """Clear caches in all services"""
    results = {}
    
    for name, url in [
        ("lid", LID_SERVICE_URL),
        ("indic_en", INDIC_EN_SERVICE_URL),
        ("en_indic", EN_INDIC_SERVICE_URL)
    ]:
        try:
            resp = await http_client.post(f"{url}/clear-cache")
            results[name] = resp.json()
        except Exception as e:
            results[name] = {"error": str(e)}
    
    return {"status": "caches cleared", "services": results}


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