import sys
import os
import subprocess
import asyncio
import time
import signal
from pathlib import Path
from typing import Optional, List

# ── Bot path injection ────────────────────────────────────────────────────────
BOT_DIR = '/home/rawnaq_bot_extracted'
sys.path.insert(0, BOT_DIR)
OUTPUT_DIR = os.path.join(BOT_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── FastAPI imports ───────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Security
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import uvicorn

# ── Bot module imports (graceful fallback) ────────────────────────────────────
try:
    from app import generate_reel, chat_with_ai, get_stats, track_usage, generate_batch_reels
    BOT_MODULES_LOADED = True
except Exception as e:
    print(f"[WARN] Could not import bot app.py: {e}")
    BOT_MODULES_LOADED = False

    async def generate_reel(*args, **kwargs):
        raise RuntimeError("Bot modules not loaded")

    async def generate_batch_reels(*args, **kwargs):
        raise RuntimeError("Bot modules not loaded")

    def chat_with_ai(*args, **kwargs):
        return type('R', (), {'reply': 'Bot modules not loaded', 'make_reel': False, 'reel_params': None})()

    def get_stats():
        return {'unique_users': 0, 'reels_made': 0}

    def track_usage(*args, **kwargs):
        pass

try:
    from qrm.constants import SURAH_MAP_AR, SURAH_NUM_TO_AR, RECITER_NAMES, RECITER_MAP_AR, SURAH_THEMES
    CONSTANTS_LOADED = True
except Exception as e:
    print(f"[WARN] Could not import qrm.constants: {e}")
    CONSTANTS_LOADED = False
    SURAH_MAP_AR = {}
    SURAH_NUM_TO_AR = {}
    RECITER_NAMES = {}
    RECITER_MAP_AR = {}
    SURAH_THEMES = []

try:
    from qrm.font_manager import SUPPORTED_FONTS
except Exception as e:
    print(f"[WARN] Could not import qrm.font_manager: {e}")
    SUPPORTED_FONTS = {'amiri': 'Amiri', 'noto': 'Noto Naskh Arabic', 'scheherazade': 'Scheherazade'}

try:
    from qrm.nature_sounds import NATURE_SOUNDS
except Exception as e:
    print(f"[WARN] Could not import qrm.nature_sounds: {e}")
    NATURE_SOUNDS = {
        'rain': {'name_ar': 'مطر', 'name_en': 'Rain'},
        'river': {'name_ar': 'نهر', 'name_en': 'River'},
        'wind': {'name_ar': 'رياح', 'name_en': 'Wind'},
        'birds': {'name_ar': 'طيور', 'name_en': 'Birds'},
        'waves': {'name_ar': 'أمواج بحر', 'name_en': 'Ocean Waves'},
        'desert': {'name_ar': 'صحراء', 'name_en': 'Desert'},
        'waterfall': {'name_ar': 'شلال', 'name_en': 'Waterfall'},
    }

# ── Hardcoded surah English names 1-114 ──────────────────────────────────────
SURAH_EN = {
    1: 'Al-Fatihah', 2: 'Al-Baqarah', 3: "Ali 'Imran", 4: 'An-Nisa',
    5: 'Al-Ma\'idah', 6: 'Al-An\'am', 7: 'Al-A\'raf', 8: 'Al-Anfal',
    9: 'At-Tawbah', 10: 'Yunus', 11: 'Hud', 12: 'Yusuf',
    13: 'Ar-Ra\'d', 14: 'Ibrahim', 15: 'Al-Hijr', 16: 'An-Nahl',
    17: 'Al-Isra', 18: 'Al-Kahf', 19: 'Maryam', 20: 'Ta-Ha',
    21: 'Al-Anbya', 22: 'Al-Hajj', 23: 'Al-Mu\'minun', 24: 'An-Nur',
    25: 'Al-Furqan', 26: 'Ash-Shu\'ara', 27: 'An-Naml', 28: 'Al-Qasas',
    29: 'Al-\'Ankabut', 30: 'Ar-Rum', 31: 'Luqman', 32: 'As-Sajdah',
    33: 'Al-Ahzab', 34: 'Saba', 35: 'Fatir', 36: 'Ya-Sin',
    37: 'As-Saffat', 38: 'Sad', 39: 'Az-Zumar', 40: 'Ghafir',
    41: 'Fussilat', 42: 'Ash-Shura', 43: 'Az-Zukhruf', 44: 'Ad-Dukhan',
    45: 'Al-Jathiyah', 46: 'Al-Ahqaf', 47: 'Muhammad', 48: 'Al-Fath',
    49: 'Al-Hujurat', 50: 'Qaf', 51: 'Adh-Dhariyat', 52: 'At-Tur',
    53: 'An-Najm', 54: 'Al-Qamar', 55: 'Ar-Rahman', 56: 'Al-Waqi\'ah',
    57: 'Al-Hadid', 58: 'Al-Mujadila', 59: 'Al-Hashr', 60: 'Al-Mumtahanah',
    61: 'As-Saf', 62: 'Al-Jumu\'ah', 63: 'Al-Munafiqun', 64: 'At-Taghabun',
    65: 'At-Talaq', 66: 'At-Tahrim', 67: 'Al-Mulk', 68: 'Al-Qalam',
    69: 'Al-Haqqah', 70: 'Al-Ma\'arij', 71: 'Nuh', 72: 'Al-Jinn',
    73: 'Al-Muzzammil', 74: 'Al-Muddaththir', 75: 'Al-Qiyamah', 76: 'Al-Insan',
    77: 'Al-Mursalat', 78: 'An-Naba', 79: 'An-Nazi\'at', 80: '\'Abasa',
    81: 'At-Takwir', 82: 'Al-Infitar', 83: 'Al-Mutaffifin', 84: 'Al-Inshiqaq',
    85: 'Al-Buruj', 86: 'At-Tariq', 87: 'Al-A\'la', 88: 'Al-Ghashiyah',
    89: 'Al-Fajr', 90: 'Al-Balad', 91: 'Ash-Shams', 92: 'Al-Layl',
    93: 'Ad-Duha', 94: 'Ash-Sharh', 95: 'At-Tin', 96: 'Al-\'Alaq',
    97: 'Al-Qadr', 98: 'Al-Bayyinah', 99: 'Az-Zalzalah', 100: 'Al-\'Adiyat',
    101: 'Al-Qari\'ah', 102: 'At-Takathur', 103: 'Al-\'Asr', 104: 'Al-Humazah',
    105: 'Al-Fil', 106: 'Quraysh', 107: 'Al-Ma\'un', 108: 'Al-Kawthar',
    109: 'Al-Kafirun', 110: 'An-Nasr', 111: 'Al-Masad', 112: 'Al-Ikhlas',
    113: 'Al-Falaq', 114: 'An-Nas',
}

# Fallback Arabic surah names if constants not loaded
SURAH_AR_FALLBACK = {
    1: 'الفاتحة', 2: 'البقرة', 3: 'آل عمران', 4: 'النساء', 5: 'المائدة',
    6: 'الأنعام', 7: 'الأعراف', 8: 'الأنفال', 9: 'التوبة', 10: 'يونس',
    11: 'هود', 12: 'يوسف', 13: 'الرعد', 14: 'إبراهيم', 15: 'الحجر',
    16: 'النحل', 17: 'الإسراء', 18: 'الكهف', 19: 'مريم', 20: 'طه',
    21: 'الأنبياء', 22: 'الحج', 23: 'المؤمنون', 24: 'النور', 25: 'الفرقان',
    26: 'الشعراء', 27: 'النمل', 28: 'القصص', 29: 'العنكبوت', 30: 'الروم',
    31: 'لقمان', 32: 'السجدة', 33: 'الأحزاب', 34: 'سبأ', 35: 'فاطر',
    36: 'يس', 37: 'الصافات', 38: 'ص', 39: 'الزمر', 40: 'غافر',
    41: 'فصلت', 42: 'الشورى', 43: 'الزخرف', 44: 'الدخان', 45: 'الجاثية',
    46: 'الأحقاف', 47: 'محمد', 48: 'الفتح', 49: 'الحجرات', 50: 'ق',
    51: 'الذاريات', 52: 'الطور', 53: 'النجم', 54: 'القمر', 55: 'الرحمن',
    56: 'الواقعة', 57: 'الحديد', 58: 'المجادلة', 59: 'الحشر', 60: 'الممتحنة',
    61: 'الصف', 62: 'الجمعة', 63: 'المنافقون', 64: 'التغابن', 65: 'الطلاق',
    66: 'التحريم', 67: 'الملك', 68: 'القلم', 69: 'الحاقة', 70: 'المعارج',
    71: 'نوح', 72: 'الجن', 73: 'المزمل', 74: 'المدثر', 75: 'القيامة',
    76: 'الإنسان', 77: 'المرسلات', 78: 'النبأ', 79: 'النازعات', 80: 'عبس',
    81: 'التكوير', 82: 'الانفطار', 83: 'المطففين', 84: 'الانشقاق', 85: 'البروج',
    86: 'الطارق', 87: 'الأعلى', 88: 'الغاشية', 89: 'الفجر', 90: 'البلد',
    91: 'الشمس', 92: 'الليل', 93: 'الضحى', 94: 'الشرح', 95: 'التين',
    96: 'العلق', 97: 'القدر', 98: 'البينة', 99: 'الزلزلة', 100: 'العاديات',
    101: 'القارعة', 102: 'التكاثر', 103: 'العصر', 104: 'الهمزة', 105: 'الفيل',
    106: 'قريش', 107: 'الماعون', 108: 'الكوثر', 109: 'الكافرون', 110: 'النصر',
    111: 'المسد', 112: 'الإخلاص', 113: 'الفلق', 114: 'الناس',
}

# Haramain reciters
HARAMAIN_RECITERS = {
    'abdurrahmaansudais', 'saoodshuraym', 'mahermuaiqly',
    'hudhaify', 'yassereldosari', 'alijaber'
}

# ── Server start time ─────────────────────────────────────────────────────────
SERVER_START = time.time()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title='Rawnaq Dashboard', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Mount static directories
try:
    app.mount('/output', StaticFiles(directory=OUTPUT_DIR), name='output')
except Exception as e:
    print(f"[WARN] Could not mount output dir: {e}")

app.mount('/static', StaticFiles(directory='/home/-/static'), name='static')


# ── Request/Response Models ───────────────────────────────────────────────────

class BotActionRequest(BaseModel):
    action: str  # start | stop | restart


class GenerateRequest(BaseModel):
    surah_number: int = 1
    start_ayah: int = 1
    end_ayah: int = -1
    reciter: str = 'ar.alafasy'
    theme: str = 'gold'
    nature_sound: str = ''
    font_name: str = ''
    translation_enabled: bool = True
    translation_lang: str = ''
    background_query: str = ''
    batch_count: int = 0


class ChatRequest(BaseModel):
    message: str
    session_id: str = 'default'


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_bot_pid() -> Optional[int]:
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'telegram_bot.py'],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().splitlines()
        return int(pids[0]) if pids else None
    except Exception:
        return None


def read_log_file(lines: int = 100) -> List[str]:
    log_paths = [
        '/tmp/bot_output.log',
        '/home/z/my-project/bot_output.log',
    ]
    for path in log_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', errors='replace') as f:
                    all_lines = f.readlines()
                return [l.rstrip() for l in all_lines[-lines:]]
            except Exception:
                pass
    return ['[لا توجد سجلات متاحة بعد]']


def _get_surah_ar(num: int) -> str:
    if CONSTANTS_LOADED and SURAH_NUM_TO_AR:
        return SURAH_NUM_TO_AR.get(num, SURAH_AR_FALLBACK.get(num, f'سورة {num}'))
    return SURAH_AR_FALLBACK.get(num, f'سورة {num}')


# ── Optional API key auth ────────────────────────────────────────────────────
# If DASHBOARD_API_KEY env var is set, all /api/bot/action calls require
# the matching X-API-Key header. Unset = no auth (local use).
_API_KEY = os.environ.get('DASHBOARD_API_KEY', '')
_api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


def _require_auth(api_key: Optional[str] = None):
    if _API_KEY and api_key != _API_KEY:
        raise HTTPException(status_code=403, detail='Invalid or missing X-API-Key header')


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get('/', response_class=HTMLResponse)
async def serve_dashboard():
    html_path = '/home/-/static/index.html'
    with open(html_path, encoding='utf-8') as f:
        return f.read()


@app.get('/api/status')
async def api_status():
    pid = get_bot_pid()
    try:
        stats = get_stats()
    except Exception:
        stats = {'unique_users': 0, 'reels_made': 0}
    return {
        'bot_status': 'running' if pid else 'stopped',
        'bot_pid': pid,
        'stats': {
            'unique_users': stats.get('unique_users', 0),
            'reels_made': stats.get('reels_made', 0),
        },
        'uptime_seconds': int(time.time() - SERVER_START),
    }


@app.post('/api/bot/action')
async def api_bot_action(body: BotActionRequest, api_key: Optional[str] = Security(_api_key_header)):
    _require_auth(api_key)
    action = body.action.lower()
    if action not in ('start', 'stop', 'restart'):
        raise HTTPException(400, 'action must be start | stop | restart')

    pid = get_bot_pid()

    def do_stop():
        p = get_bot_pid()
        if not p:
            return True
        try:
            os.kill(p, signal.SIGTERM)
        except ProcessLookupError:
            return True
        except Exception:
            return False
        # Wait up to 5s for graceful exit
        for _ in range(10):
            time.sleep(0.5)
            if get_bot_pid() is None:
                return True
        # Escalate to SIGKILL if still alive
        p2 = get_bot_pid()
        if p2:
            try:
                os.kill(p2, signal.SIGKILL)
                time.sleep(0.5)
            except Exception:
                pass
        return get_bot_pid() is None

    def do_start():
        try:
            log_fh = open('/tmp/bot_output.log', 'a')
            subprocess.Popen(
                ['python3', os.path.join(BOT_DIR, 'telegram_bot.py')],
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                cwd=BOT_DIR,
            )
            return True
        except Exception as e:
            print(f"[ERROR] Failed to start bot: {e}")
            return False

    if action == 'start':
        if pid:
            return {'success': False, 'message': f'البوت يعمل بالفعل (PID {pid})'}
        ok = do_start()
        return {'success': ok, 'message': 'تم تشغيل البوت' if ok else 'فشل في تشغيل البوت'}

    elif action == 'stop':
        if not pid:
            return {'success': False, 'message': 'البوت غير مشغّل'}
        ok = do_stop()
        return {'success': ok, 'message': 'تم إيقاف البوت' if ok else 'فشل في إيقاف البوت'}

    elif action == 'restart':
        do_stop()
        await asyncio.sleep(1)
        ok = do_start()
        return {'success': ok, 'message': 'تمت إعادة التشغيل' if ok else 'فشل في إعادة التشغيل'}


@app.get('/api/logs')
async def api_logs(lines: int = 100):
    return {'logs': read_log_file(lines)}


@app.get('/api/surahs')
async def api_surahs():
    result = []
    for num in range(1, 115):
        result.append({
            'number': num,
            'name_ar': _get_surah_ar(num),
            'name_en': SURAH_EN.get(num, f'Surah {num}'),
        })
    return result


@app.get('/api/reciters')
async def api_reciters():
    if CONSTANTS_LOADED and RECITER_MAP_AR:
        reciters = []
        for reciter_id, name_ar in RECITER_MAP_AR.items():
            # Extract bare id (strip ar. prefix for grouping check)
            bare = reciter_id.replace('ar.', '').lower()
            group = 'قراء الحرم' if bare in HARAMAIN_RECITERS else 'قراء مشهورون'
            reciters.append({'id': reciter_id, 'name_ar': name_ar, 'group': group})
        return reciters

    # Fallback hardcoded list
    return [
        {'id': 'ar.alafasy', 'name_ar': 'مشاري العفاسي', 'group': 'قراء مشهورون'},
        {'id': 'ar.abdurrahmaansudais', 'name_ar': 'عبدالرحمن السديس', 'group': 'قراء الحرم'},
        {'id': 'ar.saoodshuraym', 'name_ar': 'سعود الشريم', 'group': 'قراء الحرم'},
        {'id': 'ar.mahermuaiqly', 'name_ar': 'ماهر المعيقلي', 'group': 'قراء الحرم'},
        {'id': 'ar.hudhaify', 'name_ar': 'علي الحذيفي', 'group': 'قراء الحرم'},
        {'id': 'ar.yassereldosari', 'name_ar': 'ياسر الدوسري', 'group': 'قراء الحرم'},
        {'id': 'ar.alijaber', 'name_ar': 'علي جابر', 'group': 'قراء الحرم'},
        {'id': 'ar.minshawi', 'name_ar': 'محمد صديق المنشاوي', 'group': 'قراء مشهورون'},
        {'id': 'ar.husary', 'name_ar': 'محمود خليل الحصري', 'group': 'قراء مشهورون'},
        {'id': 'ar.abdulbasitmurattal', 'name_ar': 'عبدالباسط عبدالصمد', 'group': 'قراء مشهورون'},
    ]


@app.get('/api/fonts')
async def api_fonts():
    fonts = [{'id': 'amiri', 'display': 'Amiri (افتراضي)'}]
    if isinstance(SUPPORTED_FONTS, dict):
        for fid, fname in SUPPORTED_FONTS.items():
            if fid != 'amiri':
                fonts.append({'id': fid, 'display': fname})
    elif isinstance(SUPPORTED_FONTS, (list, tuple)):
        for f in SUPPORTED_FONTS:
            if isinstance(f, dict):
                fid = f.get('id', f.get('name', ''))
                fname = f.get('display', f.get('name', fid))
            else:
                fid = fname = str(f)
            if fid and fid != 'amiri':
                fonts.append({'id': fid, 'display': fname})
    fonts.append({'id': 'random', 'display': '🎲 عشوائي'})
    return fonts


@app.get('/api/sounds')
async def api_sounds():
    sounds = [{'id': 'none', 'name_ar': 'بدون', 'name_en': 'None'}]
    if isinstance(NATURE_SOUNDS, dict):
        for sid, info in NATURE_SOUNDS.items():
            if isinstance(info, dict):
                sounds.append({
                    'id': sid,
                    'name_ar': info.get('name_ar', sid),
                    'name_en': info.get('name_en', sid),
                })
            else:
                sounds.append({'id': sid, 'name_ar': str(info), 'name_en': str(info)})
    elif isinstance(NATURE_SOUNDS, (list, tuple)):
        for s in NATURE_SOUNDS:
            if isinstance(s, dict):
                sounds.append({
                    'id': s.get('id', s.get('key', '')),
                    'name_ar': s.get('name_ar', ''),
                    'name_en': s.get('name_en', ''),
                })
    return sounds


@app.post('/api/generate')
async def api_generate(body: GenerateRequest):
    if not BOT_MODULES_LOADED:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'وحدات البوت غير متوفرة. تحقق من تثبيت المتطلبات.'}
        )

    try:
        kwargs = {
            'surah_number': body.surah_number,
            'start_ayah': body.start_ayah,
            'end_ayah': body.end_ayah if body.end_ayah != -1 else None,
            'reciter': body.reciter,
            'theme': body.theme,
            'nature_sound': body.nature_sound or None,
            'font_name': body.font_name or None,
            'translation_enabled': body.translation_enabled,
            'translation_lang': body.translation_lang or None,
            'background_query': body.background_query or None,
        }

        if body.batch_count and body.batch_count >= 2:
            result = await asyncio.wait_for(
                generate_batch_reels(batch_count=body.batch_count, **kwargs),
                timeout=300.0,
            )
        else:
            result = await asyncio.wait_for(
                generate_reel(**kwargs),
                timeout=300.0,
            )

        try:
            track_usage(chat_id=999999, reel_made=True)
        except Exception:
            pass

        if isinstance(result, dict):
            video_path = result.get('video_path') or result.get('output_path') or result.get('path', '')
        elif hasattr(result, 'video_path'):
            video_path = result.video_path
        else:
            video_path = str(result)

        filename = os.path.basename(video_path) if video_path else ''
        file_size_mb = 0.0
        if video_path and os.path.exists(video_path):
            file_size_mb = round(os.path.getsize(video_path) / (1024 * 1024), 2)

        surah_ar = _get_surah_ar(body.surah_number)
        surah_en = SURAH_EN.get(body.surah_number, f'Surah {body.surah_number}')

        reciter_name = body.reciter
        if CONSTANTS_LOADED and RECITER_MAP_AR:
            reciter_name = RECITER_MAP_AR.get(body.reciter, body.reciter)

        return {
            'success': True,
            'video_url': f'/api/video/{filename}' if filename else '',
            'surah_name_ar': surah_ar,
            'surah_name_en': surah_en,
            'reciter_name': reciter_name,
            'file_size_mb': file_size_mb,
        }

    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={'success': False, 'error': 'انتهت مهلة التوليد (أكثر من 5 دقائق). حاول مجدداً.'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': f'خطأ في التوليد: {str(e)}'}
        )


@app.post('/api/chat')
async def api_chat(body: ChatRequest):
    try:
        result = chat_with_ai(chat_id=888888, message=body.message)
        reply_text = ''
        make_reel = False
        reel_params = None

        if isinstance(result, dict):
            reply_text = result.get('reply', str(result))
            make_reel = result.get('make_reel', False)
            reel_params = result.get('reel_params', None)
        elif hasattr(result, 'reply'):
            reply_text = result.reply
            make_reel = getattr(result, 'make_reel', False)
            reel_params = getattr(result, 'reel_params', None)
        else:
            reply_text = str(result)

        return {'reply': reply_text, 'make_reel': make_reel, 'reel_params': reel_params}

    except Exception as e:
        return {'reply': f'حدث خطأ: {str(e)}', 'make_reel': False, 'reel_params': None}


@app.get('/api/video/{filename}')
async def serve_video(filename: str):
    # Sanitize filename
    filename = os.path.basename(filename)
    video_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(404, 'الفيديو غير موجود')
    return FileResponse(video_path, media_type='video/mp4')


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=3002, log_level='info')
