import os
import json
import json5
import glob
from aiohttp import web

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(BASE_DIR, 'bot', 'json')
ITEMS_DIR = os.path.join(JSON_DIR, 'items')
LAYOUT_FILE = os.path.join(BASE_DIR, 'web', 'canvas_layout.json')

async def get_configs(request):
    try:
        # Load all configs
        with open(os.path.join(JSON_DIR, 'settings.json'), 'r', encoding='utf-8') as f:
            settings = json5.load(f)
        
        with open(os.path.join(JSON_DIR, 'premium_shop.json'), 'r', encoding='utf-8') as f:
            premium_shop = json.load(f)
            
        with open(os.path.join(JSON_DIR, 'super_shop.json'), 'r', encoding='utf-8') as f:
            super_shop = json.load(f)
            
        with open(os.path.join(JSON_DIR, 'quests_data.json'), 'r', encoding='utf-8') as f:
            quests = json.load(f)
            
        with open(os.path.join(JSON_DIR, 'mobs.json'), 'r', encoding='utf-8') as f:
            mobs = json.load(f)
            
        with open(os.path.join(JSON_DIR, 'journey_config.json'), 'r', encoding='utf-8') as f:
            journey = json.load(f)
            
        with open(os.path.join(JSON_DIR, 'combat_strategies.json'), 'r', encoding='utf-8') as f:
            combat_strategies = json5.load(f)
            
        with open(os.path.join(JSON_DIR, 'achievements.json'), 'r', encoding='utf-8') as f:
            achievements = json.load(f)
            
        # Load items
        items = {}
        for file_path in glob.glob(os.path.join(ITEMS_DIR, '*.json')):
            file_name = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                items[file_name] = json.load(f)

        # Load localization (RU)
        with open(os.path.join(BASE_DIR, 'bot', 'localization', 'ru.json'), 'r', encoding='utf-8') as f:
            localization = json.load(f)

        return web.json_response({
            "settings": settings,
            "premium_shop": premium_shop,
            "super_shop": super_shop,
            "quests": quests,
            "mobs": mobs,
            "journey": journey,
            "combat_strategies": combat_strategies,
            "achievements": achievements,
            "items": items,
            "localization": localization
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def save_config(request):
    try:
        body = await request.json()
        config_type = body.get('type')
        data = body.get('data')
        
        if config_type == 'settings':
            file_path = os.path.join(JSON_DIR, 'settings.json')
        elif config_type == 'premium_shop':
            file_path = os.path.join(JSON_DIR, 'premium_shop.json')
        elif config_type == 'super_shop':
            file_path = os.path.join(JSON_DIR, 'super_shop.json')
        elif config_type == 'quests':
            file_path = os.path.join(JSON_DIR, 'quests_data.json')
        elif config_type == 'mobs':
            file_path = os.path.join(JSON_DIR, 'mobs.json')
        elif config_type == 'journey':
            file_path = os.path.join(JSON_DIR, 'journey_config.json')
        elif config_type == 'combat_strategies':
            file_path = os.path.join(JSON_DIR, 'combat_strategies.json')
        elif config_type == 'achievements':
            file_path = os.path.join(JSON_DIR, 'achievements.json')
        elif config_type == 'item':
            file_name = body.get('file_name')
            if not file_name or not file_name.endswith('.json'):
                return web.json_response({"error": "Invalid item file name"}, status=400)
            file_path = os.path.join(ITEMS_DIR, file_name)
        else:
            return web.json_response({"error": "Unknown config type"}, status=400)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def get_layout(request):
    try:
        if os.path.exists(LAYOUT_FILE):
            with open(LAYOUT_FILE, 'r', encoding='utf-8') as f:
                layout = json.load(f)
        else:
            layout = {}
        return web.json_response(layout)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def save_layout(request):
    try:
        layout = await request.json()
        with open(LAYOUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(layout, f, ensure_ascii=False, indent=2)
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def index_handler(request):
    dist_index = os.path.join(BASE_DIR, 'web', 'dist', 'index.html')
    if os.path.exists(dist_index):
        return web.FileResponse(dist_index)
    else:
        return web.Response(text="Vue app not built yet. Run Vite development server on port 5173.", content_type="text/html")

app = web.Application()

# CORS Middleware
async def cors_middleware(app, handler):
    async def middleware(request):
        if request.method == 'OPTIONS':
            response = web.Response()
        else:
            response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    return middleware

app.middlewares.append(cors_middleware)

# Routes
app.router.add_get('/api/configs', get_configs)
app.router.add_post('/api/save', save_config)
app.router.add_get('/api/layout', get_layout)
app.router.add_post('/api/layout', save_layout)

dist_path = os.path.join(BASE_DIR, 'web', 'dist')
if os.path.exists(dist_path):
    app.router.add_static('/assets', os.path.join(dist_path, 'assets'))
app.router.add_get('/', index_handler)

if __name__ == '__main__':
    web.run_app(app, port=5000)
