from flask import Flask, request, render_template, redirect, session
import os, json, time, requests

app = Flask(__name__, template_folder='')
app.secret_key = "toniks-secret"

ADMIN_PASSWORD = "toniks123"

DATA_DIR = os.path.join(os.path.expanduser("~"), "TONIKS_BASE")
FILES = {
    "comments": "comments.json",
    "orders": "orders.json",
    "settings": "settings.json",
    "banned": "banned.json"   # новый файл для банов
}

def toniks_ping():
    url = "https://toniks.onrender.com"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TONIKS-Bot/1.0)"}
    while True:
        try:
            response = requests.get(url, headers=headers)
            print(f"[BOT] Переход на {url} — статус: {response.status_code}")
        except Exception as e:
            print(f"[BOT] Ошибка: {e}")
        time.sleep(20)

def ensure_base_exists():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        for fname in FILES.values():
            path = os.path.join(DATA_DIR, fname)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("❌ Ошибка при создании базы:", e)
        return False

def load(name):
    path = os.path.join(DATA_DIR, FILES[name])
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save(name, entry):
    path = os.path.join(DATA_DIR, FILES[name])
    data = load(name)
    data.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def too_fast(action):
    now = time.time()
    last = session.get(f"last_{action}", 0)
    if now - last < 10:
        return True
    session[f"last_{action}"] = now
    return False

@app.route("/", methods=["GET", "POST"])
def home():
    if not ensure_base_exists():
        return "База не доступна", 503

    role = request.args.get("role", "")
    comments = load("comments")
    orders = load("orders")
    settings = load("settings")
    banned = load("banned")

    if request.method == "POST":
        role = request.form.get("nickname", "").strip().lower()

        # Проверка пароля только при входе
        if role == "admin" and "password" in request.form:
            password = request.form.get("password", "")
            if password != ADMIN_PASSWORD:
                return "⛔ Неверный пароль администратора", 403

        # Проверка на бан
        if role != "admin" and role in banned:
            return "⛔ Вы заблокированы администратором", 403

        if "comment" in request.form:
            text = request.form["comment"].strip()
            if len(text) < 3:
                return "⛔ Комментарий слишком короткий", 400
            if too_fast("comment"):
                return "⛔ Слишком частые комментарии", 429
            save("comments", {"nick": role, "text": text})

        elif "order" in request.form:
            if too_fast("order"):
                return "⛔ Слишком частые заказы", 429
            save("orders", {
                "nick": role,
                "text": request.form["order"].strip(),
                "phone": request.form.get("phone", "")
            })

        elif "setting" in request.form:
            save("settings", {"nick": role, "value": request.form["setting"].strip()})

        elif "delete" in request.form:
            index = int(request.form["delete"])
            if 0 <= index < len(orders):
                orders.pop(index)
                with open(os.path.join(DATA_DIR, FILES["orders"]), "w", encoding="utf-8") as f:
                    json.dump(orders, f, ensure_ascii=False, indent=2)

        elif "delete_comment" in request.form:
            index = int(request.form["delete_comment"])
            if 0 <= index < len(comments):
                comments.pop(index)
                with open(os.path.join(DATA_DIR, FILES["comments"]), "w", encoding="utf-8") as f:
                    json.dump(comments, f, ensure_ascii=False, indent=2)

        elif "ban" in request.form:
            nick_to_ban = request.form["ban"].strip().lower()
            if nick_to_ban not in banned:
                banned.append(nick_to_ban)
                with open(os.path.join(DATA_DIR, FILES["banned"]), "w", encoding="utf-8") as f:
                    json.dump(banned, f, ensure_ascii=False, indent=2)

        elif "unban" in request.form:
            nick_to_unban = request.form["unban"].strip().lower()
            if nick_to_unban in banned:
                banned.remove(nick_to_unban)
                with open(os.path.join(DATA_DIR, FILES["banned"]), "w", encoding="utf-8") as f:
                    json.dump(banned, f, ensure_ascii=False, indent=2)

        return redirect(f"/?role={role}")

    return render_template("Web.html", role=role, comments=comments, orders=orders, settings=settings, banned=banned)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
    toniks_ping()
