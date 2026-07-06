#!/usr/bin/env python3
"""
English Notebook - Local Server
A lightweight local server for English course notes and vocabulary management.
Features: URL parsing, data storage, GitHub sync via SSH.
"""

import json
import os
import re
import subprocess
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

PORT = 7799
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT, "data.json")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"courses": [], "words": [], "settings": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_url(url):
    """Fetch URL and extract title, description, and main content."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""
        title = re.sub(r'\s+', ' ', title)
        
        # Extract meta description
        desc_match = re.search(r'<meta\s+(?:name|property)=["\'](?:description|og:description)["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""
        
        # Extract og:image
        img_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
        image = img_match.group(1).strip() if img_match else ""
        
        # Extract main text content (simple approach)
        # Remove scripts, styles, and HTML tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Try to find article or main content
        article_match = re.search(r'<(?:article|main)[^>]*>(.*?)</(?:article|main)>', text, re.DOTALL | re.IGNORECASE)
        if article_match:
            text = article_match.group(1)
        
        # Extract text from paragraphs
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', text, re.DOTALL | re.IGNORECASE)
        paragraphs = [re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs]
        paragraphs = [p for p in paragraphs if len(p) > 20]
        content = "\n\n".join(paragraphs[:20])  # Limit to first 20 paragraphs
        
        # Extract headings
        headings = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', text, re.DOTALL | re.IGNORECASE)
        headings = [re.sub(r'<[^>]+>', '', h).strip() for h in headings if len(h.strip()) > 2]
        
        return {
            "success": True,
            "title": title[:200],
            "description": description[:500],
            "image": image,
            "headings": headings[:10],
            "content": content[:5000],
            "url": url
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def git_sync():
    """Sync data.json to GitHub via REST API."""
    import base64
    config_path = os.path.join(ROOT, ".github_config.json")
    if not os.path.exists(config_path):
        return {"success": False, "error": "GitHub 配置文件不存在，请先创建 .github_config.json"}
    with open(config_path, "r") as f:
        config = json.load(f)
    TOKEN = config.get("token", "")
    OWNER = config.get("owner", "")
    REPO = config.get("repo", "english-notebook")
    if not TOKEN or not OWNER:
        return {"success": False, "error": "GitHub 配置不完整"}
    API = f"https://api.github.com/repos/{OWNER}/{REPO}"
    HEADERS = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    }
    try:
        # Read data.json
        data_path = os.path.join(ROOT, "data.json")
        if not os.path.exists(data_path):
            return {"success": True, "message": "No data to sync"}
        with open(data_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        
        # Get current SHA
        req = urllib.request.Request(f"{API}/contents/data.json", headers=HEADERS)
        sha = None
        try:
            with urllib.request.urlopen(req) as resp:
                info = json.loads(resp.read().decode())
                sha = info.get("sha")
        except Exception:
            pass  # File doesn't exist yet
        
        # Upload
        payload = {"message": f"Update notebook data - {datetime.now().strftime('%Y-%m-%d %H:%M')}", "content": content}
        if sha:
            payload["sha"] = sha
        body = json.dumps(payload).encode()
        req = urllib.request.Request(f"{API}/contents/data.json", data=body, headers=HEADERS, method="PUT")
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        
        if "content" in result:
            return {"success": True, "message": "数据已同步到 GitHub ✓"}
        else:
            return {"success": False, "error": str(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


class NotebookHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        
        if path == "/api/parse":
            url = params.get("url", [""])[0]
            if not url:
                self._json({"success": False, "error": "No URL provided"})
                return
            result = parse_url(url)
            self._json(result)
            return
        
        if path == "/api/data":
            data = load_data()
            self._json(data)
            return
        
        if path == "/api/sync":
            result = git_sync()
            self._json(result)
            return
        
        if path == "/api/git-status":
            try:
                os.chdir(ROOT)
                result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
                remotes = result.stdout.strip()
                self._json({"has_remote": bool(remotes), "remotes": remotes})
            except:
                self._json({"has_remote": False, "remotes": ""})
            return
        
        super().do_GET(self)
    
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == "/api/data":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                save_data(data)
                self._json({"success": True})
            except Exception as e:
                self._json({"success": False, "error": str(e)})
            return
        
        if path == "/api/sync":
            result = git_sync()
            self._json(result)
            return
        
        self._json({"error": "Not found"}, 404)
    
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, format, *args):
        # Suppress logs except errors
        if args and "404" not in str(args[1]) and "500" not in str(args[1]):
            pass  # silently
        else:
            super().log_message(format, *args)


def main():
    # Init git if needed
    if not os.path.exists(os.path.join(ROOT, ".git")):
        subprocess.run(["git", "init"], cwd=ROOT)
        # Create .gitignore
        with open(os.path.join(ROOT, ".gitignore"), "w") as f:
            f.write("__pycache__/\n*.pyc\n.DS_Store\n")
    
    # Init data file if needed
    if not os.path.exists(DATA_FILE):
        save_data({"courses": [], "words": [], "settings": {}})
    
    print(f"📖 English Notebook running at http://localhost:{PORT}")
    print(f"   Data file: {DATA_FILE}")
    print(f"   Press Ctrl+C to stop")
    
    server = HTTPServer(("127.0.0.1", PORT), NotebookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Bye!")
        server.server_close()


if __name__ == "__main__":
    main()
