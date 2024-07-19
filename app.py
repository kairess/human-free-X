from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import secrets
import threading
import random
from openai import OpenAI
from datetime import datetime

client = OpenAI()

virtual_users = [
    {"id": "@C0ff33Alch3mist", "character": "한국인", "style": "친근한 말투", "example": "헐 대박... 그 비밀 레시피 알려줘서 고마워! 내일 카페에서 바로 써먹어볼 거임 ㅋㅋ 손님들 놀라겠다"},
    {"id": "@Cyb3rN1nja_KR", "character": "한국인", "style": "진지한 말투", "example": "와... 새로운 AI 기술 개쩌네. 근데 이거 윤리적으로 좀 문제 있는 거 아님? 누가 책임질 건데?"},
    {"id": "@N00dl3Qu33n88", "character": "한국인", "style": "재치있는 말투", "example": "아 진짜? 그 라멘집 스프 12시간 끓인다고? ㄷㄷㄷ 대박이네... 근데 그 정도 했으면 맛없으면 절대 안 됨 ㅇㅈ?"},
    {"id": "@Ec0W4rri0r", "character": "한국인", "style": "환경 운동가", "example": "플라스틱 줄이기? 좋은 생각이야~ 나도 텀블러 들고 다니는 중. 근데 회사에서 일회용품 쓰는 거 보면 속에서 열불 나더라"},
    {"id": "@K_Dr4m4_Junk13", "character": "한국인", "style": "드라마 팬", "example": "아 씨... 주인공 오열하는 거 보고 나도 모르게 눈물 찔끔 났잖아 ㅠㅠ 다음 회 기대된다 진짜"},
    {"id": "@W4nd3rLu5t_KR", "character": "한국인", "style": "여행 블로거", "example": "제주도 카페 뷰 미쳤다며? 아 가고 싶다 ㅠㅠ 일출 보면서 아메 마시는 거 상상만 해도 행복하네... 부럽..."},
    {"id": "@Crypt0Ph03n1x", "character": "한국인", "style": "암호화폐 애호가", "example": "비트코인 40% 폭등?! 아 진짜 가즈아ㅏㅏㅏ!! 근데 고점에 물리면 어카지... 왜 이리 찔리냐 ㅋㅋㅋ"},
    {"id": "@T34_n_Crump3ts", "character": "영국인", "style": "전통적인 영국식 말투", "example": "Blimey! Proper Korean BBQ in London? You're having a laugh, mate. Guess I'll have to book a flight to Seoul ASAP!"},
    {"id": "@0t4kuG4m3rZ", "character": "일본인", "style": "오타쿠", "example": "マジヤバい！新作RPGのグラフィックやばすぎ... 予約しなきゃ"},
    {"id": "@F1tn3ssFreak_KR", "character": "한국인", "style": "피트니스 트레이너", "example": "헐... 그 운동법 레전드네? 내일부터 해볼 거임! 근데 관절 나가면 책임 져 ㅋㅋㅋ"},
]

count_weights = [0, 0, 0.1, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.05]

def weighted_random_choice(elements, count_weights=count_weights):
    counts = list(range(1, len(count_weights) + 1))
    chosen_count = random.choices(counts, weights=count_weights, k=1)[0]
    selected_elements = random.sample(elements, k=chosen_count)
    return selected_elements

def get_relative_time(timestamp):
    now = datetime.now()
    diff = now - datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return "방금 전"
    elif seconds < 3600:
        return f"{int(seconds // 60)}분 전"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}시간 전"
    elif seconds < 604800:
        return f"{int(seconds // 86400)}일 전"
    else:
        return timestamp


app = Flask(__name__)

@app.template_filter('reltime')
def relative_time_filter(timestamp):
    return get_relative_time(timestamp)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, timestamp TEXT, user_id TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, content TEXT, timestamp TEXT, user_id TEXT)')
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY timestamp DESC').fetchall()

    for i, post in enumerate(posts):
        comments = conn.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY timestamp DESC', (post['id'],)).fetchall()

        posts[i] = dict(posts[i])
        posts[i]['comments'] = comments

    conn.close()
    return render_template('index.html', posts=posts, now=datetime.now())

def generate_responses(prompt, post_id):
    selected_users = weighted_random_choice(virtual_users)

    responses = []

    for user in selected_users:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"너는 {user['character']} 라는 이름으로 X에서 활동하는 유저야. 다음 포스팅을 보고 {user['style']} 말투로 다음의 예시를 참고해서 댓글을 소셜 미디어 말투로 짧게 작성해줘.\n예시: {user['example']}"},
                {"role": "user", "content": prompt}
            ],
        )
        responses.append({
            "id": user['id'],
            "comment": response.choices[0].message.content.strip()
        })
    conn = get_db_connection()
    for r in responses:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO comments (post_id, content, timestamp, user_id) VALUES (?, ?, ?, ?)',
                     (post_id, r['comment'], timestamp, r['id']))
    conn.commit()
    conn.close()

@app.route('/post', methods=['POST'])
async def post():
    content = request.form['content']
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = secrets.token_hex(8)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO posts (content, timestamp, user_id) VALUES (?, ?, ?)',
                 (content, timestamp, user_id))
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()

    threading.Thread(target=generate_responses, args=(content, post_id)).start()


    response = redirect(url_for('index'))
    response.set_cookie('user_id', user_id)
    return response

@app.route('/comment', methods=['POST'])
def comment():
    post_id = request.form['post_id']
    content = request.form['content']
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = secrets.token_hex(8)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    conn.execute('INSERT INTO comments (post_id, content, timestamp, user_id) VALUES (?, ?, ?, ?)',
                 (post_id, content, timestamp, user_id))
    conn.commit()
    conn.close()
    response = redirect(url_for('index'))
    response.set_cookie('user_id', user_id)
    return response

@app.route('/timeline/<user_id>')
def timeline(user_id):
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts WHERE user_id = ? ORDER BY timestamp DESC', (user_id,)).fetchall()

    for i, post in enumerate(posts):
        comments = conn.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY timestamp DESC', (post['id'],)).fetchall()

        posts[i] = dict(posts[i])
        posts[i]['comments'] = comments
    
    conn.close()
    return render_template('timeline.html', posts=posts, user_id=user_id, now=datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0')
