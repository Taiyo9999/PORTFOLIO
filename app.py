import os

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import pymysql

def load_local_env():
    if not os.path.exists(".env"):
        return

    with open(".env", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_local_env()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME", "board_db")
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "profiles")
POST_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "posts")
DB_ERROR_MESSAGE = "데이터베이스 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요."
schema_ready = False

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


def add_column_if_missing(cursor, table_name, column_name, definition):
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name)
    )

    if cursor.fetchone()["count"] == 0:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_schema():
    os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(POST_UPLOAD_FOLDER, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    add_column_if_missing(cursor, "users", "nickname", "VARCHAR(100)")
    add_column_if_missing(cursor, "users", "birthdate", "DATE")
    add_column_if_missing(cursor, "users", "email", "VARCHAR(255)")
    add_column_if_missing(cursor, "users", "profile_image", "VARCHAR(255)")
    add_column_if_missing(cursor, "posts", "user_id", "INT")
    add_column_if_missing(cursor, "posts", "is_secret", "TINYINT(1) DEFAULT 0")
    add_column_if_missing(cursor, "posts", "file_name", "VARCHAR(255)")
    add_column_if_missing(cursor, "posts", "file_path", "VARCHAR(255)")

    conn.commit()
    conn.close()


@app.before_request
def prepare_app():
    global schema_ready

    if not schema_ready:
        try:
            ensure_schema()
        except pymysql.MySQLError:
            pass
        schema_ready = True


def get_posts(keyword=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except pymysql.MySQLError:
        return []

    current_user_id = session.get("user_id")

    if keyword:
        cursor.execute(
            """
            SELECT posts.*, users.nickname AS author_nickname, users.username AS author_username
            FROM posts
            LEFT JOIN users ON posts.user_id = users.id
            WHERE posts.title LIKE %s OR posts.content LIKE %s
            ORDER BY posts.id DESC
            """,
            ("%" + keyword + "%", "%" + keyword + "%")
        )
    else:
        cursor.execute(
            """
            SELECT posts.*, users.nickname AS author_nickname, users.username AS author_username
            FROM posts
            LEFT JOIN users ON posts.user_id = users.id
            ORDER BY posts.id DESC
            """
        )

    posts = cursor.fetchall()

    for post in posts:
        post["is_secret"] = bool(post.get("is_secret"))
        post["can_view"] = not post["is_secret"] or post.get("user_id") == current_user_id
        post["can_manage"] = post.get("user_id") == current_user_id

    conn.close()

    return posts


def save_user_session(user):
    session["user_id"] = user.get("id")
    session["username"] = user.get("username")
    session["nickname"] = user.get("nickname")
    session["name"] = user.get("name")
    session["birthdate"] = str(user.get("birthdate") or "")
    session["school"] = user.get("school")
    session["email"] = user.get("email")
    session["profile_image"] = user.get("profile_image")


def password_matches(stored_password, plain_password):
    try:
        return check_password_hash(stored_password, plain_password)
    except ValueError:
        return False


def current_user():
    if not session.get("user_id"):
        return None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
        user = cursor.fetchone()
        conn.close()
        return user
    except pymysql.MySQLError:
        return None


@app.route("/")
def index():
    keyword = request.args.get("keyword")
    posts = get_posts(keyword)

    return render_template("index.html", posts=posts, keyword=keyword)

@app.route("/board")
def board():
    return redirect(url_for("index", section="board"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
        except pymysql.MySQLError:
            return render_template("login.html", error=DB_ERROR_MESSAGE)

        if user and password_matches(user["password"], password):
            save_user_session(user)
            conn.close()
            return redirect(url_for("index"))

        conn.close()
        return render_template("login.html", error="아이디 또는 비밀번호가 틀렸습니다.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/mypage")
def mypage():
    user = current_user()

    if not user:
        return redirect(url_for("login"))

    return render_template("mypage.html", user=user)


@app.route("/profile/<int:user_id>")
def profile(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, nickname, name, birthdate, school, email, profile_image FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        conn.close()
    except pymysql.MySQLError:
        return redirect(url_for("index"))

    if not user:
        return redirect(url_for("index"))

    return render_template("profile.html", user=user)


@app.route("/profile/update", methods=["POST"])
def update_profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    nickname = request.form.get("nickname")
    name = request.form.get("name")
    birthdate = request.form.get("birthdate") or None
    school = request.form.get("school")
    email = request.form.get("email")
    profile_image = session.get("profile_image")
    uploaded_file = request.files.get("profile_image")

    if uploaded_file and uploaded_file.filename:
        original_name = secure_filename(uploaded_file.filename)
        profile_image = f"{session['user_id']}_{original_name}"
        uploaded_file.save(os.path.join(PROFILE_UPLOAD_FOLDER, profile_image))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET nickname=%s, name=%s, birthdate=%s, school=%s, email=%s, profile_image=%s
            WHERE id=%s
            """,
            (nickname, name, birthdate, school, email, profile_image, session["user_id"])
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
        user = cursor.fetchone()
        conn.close()
    except pymysql.MySQLError:
        user = {
            "username": session.get("username"),
            "nickname": session.get("nickname"),
            "name": session.get("name"),
            "birthdate": session.get("birthdate"),
            "school": session.get("school"),
            "email": session.get("email"),
            "profile_image": session.get("profile_image"),
        }
        return render_template("mypage.html", user=user, error=DB_ERROR_MESSAGE)

    save_user_session(user)
    return redirect(url_for("mypage"))


@app.route("/uploads/profiles/<filename>")
def profile_image(filename):
    return send_from_directory(PROFILE_UPLOAD_FOLDER, filename)


@app.route("/add_post", methods=["POST"])
def add_post():
    data = request.get_json(silent=True) or {}
    title = data.get("title") or request.form.get("title")
    content = data.get("content") or request.form.get("content")
    is_secret = 1 if request.form.get("is_secret") and session.get("user_id") else 0
    uploaded_file = request.files.get("attachment")
    file_name = None
    file_path = None

    if uploaded_file and uploaded_file.filename:
        file_name = secure_filename(uploaded_file.filename)
        saved_name = f"{session.get('user_id') or 'guest'}_{file_name}"
        uploaded_file.save(os.path.join(POST_UPLOAD_FOLDER, saved_name))
        file_path = saved_name

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO posts (title, content, user_id, is_secret, file_name, file_path) VALUES (%s, %s, %s, %s, %s, %s)",
            (title, content, session.get("user_id"), is_secret, file_name, file_path)
        )
        conn.commit()
        conn.close()
    except pymysql.MySQLError:
        return jsonify({"message": DB_ERROR_MESSAGE}), 503

    return jsonify({"message": "ok"})


@app.route("/download/<int:post_id>")
def download_file(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id=%s", (post_id,))
        post = cursor.fetchone()
        conn.close()
    except pymysql.MySQLError:
        return redirect(url_for("index", section="board"))

    if not post or not post.get("file_path"):
        return redirect(url_for("index", section="board"))

    if post.get("is_secret") and post.get("user_id") != session.get("user_id"):
        return redirect(url_for("index", section="board"))

    return send_from_directory(POST_UPLOAD_FOLDER, post["file_path"], as_attachment=True, download_name=post["file_name"])

@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM posts WHERE id = %s AND user_id = %s", (post_id, session.get("user_id")))
        conn.commit()
        conn.close()
    except pymysql.MySQLError:
        pass

    return redirect(request.referrer or url_for("index", section="board"))


@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if request.method == "GET":
        return redirect(url_for("index", section="board"))

    title = request.form.get("title")
    content = request.form.get("content")
    is_secret = 1 if request.form.get("is_secret") else 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE posts SET title=%s, content=%s, is_secret=%s WHERE id=%s AND user_id=%s",
            (title, content, is_secret, post_id, session.get("user_id"))
        )
        conn.commit()
        conn.close()
    except pymysql.MySQLError:
        pass

    return redirect(url_for("index", section="board"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        if password != password_confirm:
            return render_template("signup.html", error="비밀번호가 일치하지 않습니다.")
        
        nickname = request.form.get("nickname")
        name = request.form.get("name")
        birthdate = request.form.get("birthdate")
        school = request.form.get("school")
        email = request.form.get("email")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 아이디 중복 검사
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
        except pymysql.MySQLError:
            return render_template("signup.html", error=DB_ERROR_MESSAGE)

        if user:
            conn.close()
            return render_template("signup.html", error="이미 존재하는 아이디입니다.")

        hashed_password = generate_password_hash(password)

        try:
            cursor.execute(
                "INSERT INTO users (username, password, name, school, nickname, birthdate, email) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (username, hashed_password, name, school, nickname, birthdate, email)
            )
            conn.commit()
            conn.close()
        except pymysql.MySQLError:
            return render_template("signup.html", error=DB_ERROR_MESSAGE)

        return render_template("signup.html", success="회원가입이 완료되었습니다.")

    return render_template("signup.html")


@app.route("/find-id", methods=["GET", "POST"])
def find_id():
    found_username = None
    error = None

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE name=%s AND email=%s", (name, email))
            user = cursor.fetchone()
            conn.close()
        except pymysql.MySQLError:
            user = None
            error = DB_ERROR_MESSAGE

        if user:
            found_username = user["username"]
        elif not error:
            error = "일치하는 회원 정보를 찾지 못했습니다."

    return render_template("find_id.html", found_username=found_username, error=error)


@app.route("/find-password", methods=["GET", "POST"])
def find_password():
    success = None
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        new_password = request.form.get("new_password")
        new_password_confirm = request.form.get("new_password_confirm")

        if new_password != new_password_confirm:
            error = "새 비밀번호가 일치하지 않습니다."
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username=%s AND email=%s", (username, email))
                user = cursor.fetchone()

                if user:
                    cursor.execute(
                        "UPDATE users SET password=%s WHERE id=%s",
                        (generate_password_hash(new_password), user["id"])
                    )
                    conn.commit()
                    success = "비밀번호가 변경되었습니다."
                else:
                    error = "일치하는 회원 정보를 찾지 못했습니다."

                conn.close()
            except pymysql.MySQLError:
                error = DB_ERROR_MESSAGE

    return render_template("find_password.html", success=success, error=error)


if __name__ == "__main__":
    app.run(debug=True)
