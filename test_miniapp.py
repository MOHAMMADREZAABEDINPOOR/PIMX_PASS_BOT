#!/usr/bin/env python3
"""
Simple test server for the PIMXPASS mini app
Tests the webapp.html with mock data
"""

from aiohttp import web
import json
from datetime import datetime, timedelta

# Mock data matching the design image
MOCK_STATUS = {
    "is_scanning": True,
    "progress": 2,
    "total": 1000,
    "tested": 20,
    "active": 16,
    "message": "20/1000 تست شد (16 فعال)",
    "scan_completed_at": None,
    "next_scan_at": None
}

MOCK_SERVERS = []
for i in range(19):
    protocol = ["vless", "trojan"][i % 2]
    transport = ["grpc", "ws", "tcp"][i % 3]
    latency = [8, 7, 4, 62, 19][i % 5]
    
    MOCK_SERVERS.append({
        "id": i + 1,
        "config": f"{protocol}://test{i}@server{i}.example.com:{'2052' if transport == 'grpc' else '443'}?type={transport}#PIMXPASS",
        "name": "PIMXPASS",
        "protocol": protocol.upper(),
        "latency": latency,
        "country": ["IR", "US", "Unknown"][i % 3],
        "status": "active"
    })

MOCK_PROXIES = []
for i in range(25):
    MOCK_PROXIES.append(
        {
            "id": i + 1,
            "type": "mtproto",
            "host": f"proxy{i}.example.com",
            "port": 443,
            "secret": "ee" + ("ab" * 16),
            "latency": (i * 15) % 250,
            "url": f"https://t.me/proxy?server=proxy{i}.example.com&port=443&secret=ee" + ("ab" * 16),
        }
    )

async def status_handler(request):
    """Return scan status"""
    return web.json_response(MOCK_STATUS)

async def servers_handler(request):
    """Return server list"""
    response = {
        "total": len(MOCK_SERVERS),
        "per_page": 5000,
        "servers": MOCK_SERVERS
    }
    return web.json_response(response)

async def proxies_handler(request):
    """Return proxy list"""
    response = {
        "total": len(MOCK_PROXIES),
        "proxies": MOCK_PROXIES,
    }
    return web.json_response(response)

async def webapp_handler(request):
    """Serve the webapp.html"""
    with open('pimx_bot/static/webapp.html', 'r', encoding='utf-8') as f:
        content = f.read()
    return web.Response(text=content, content_type='text/html')

def create_app():
    app = web.Application()
    
    # Add routes
    app.router.add_get('/api/status', status_handler)
    app.router.add_get('/api/servers', servers_handler)
    app.router.add_get('/api/proxies', proxies_handler)
    app.router.add_get('/webapp', webapp_handler)
    app.router.add_get('/', webapp_handler)
    
    return app

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 PIMXPASS Mini App Test Server")
    print("=" * 60)
    print()
    print("Mini app URL: http://localhost:8889/webapp")
    print()
    print("Mock data:")
    print(f"  - Scanning: {MOCK_STATUS['is_scanning']}")
    print(f"  - Progress: {MOCK_STATUS['progress']}%")
    print(f"  - Tested: {MOCK_STATUS['tested']}/{MOCK_STATUS['total']}")
    print(f"  - Active: {MOCK_STATUS['active']}")
    print(f"  - Servers: {len(MOCK_SERVERS)}")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app = create_app()
    web.run_app(app, host='127.0.0.1', port=8889)
