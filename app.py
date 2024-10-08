from flask import Flask, render_template, redirect, url_for, request, flash, abort
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# SQLite データベースの設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # データベース名を統一
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# カスタムフィルターを追加
@app.template_filter('format_balance')
def format_balance(value):
    # 値がNoneの場合は0を返す
    if value is None:
        return "¥0"
    return f"{value:,.0f}"  # 小数点以下を表示しない場合は0を指定

# タスクのデータベースモデル
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    importance = db.Column(db.String(10), nullable=False)
    urgency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='未着手')  # ステータスの追加
    due_date = db.Column(db.Date, nullable=True)  # 期限の追加
    memo = db.Column(db.Text, nullable=True)  # メモカラムを追加

# ユーザーモデル
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # ユーザーロールを追加

# 家計簿モデル
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # 金額
    category = db.Column(db.String(50), nullable=False)  # カテゴリー（例：入金、支出）
    date = db.Column(db.Date, nullable=False)  # 日付
    description = db.Column(db.Text, nullable=True)  # 説明

with app.app_context():
    db.create_all()

# ユーザーローダー
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 管理者のみアクセスできるデコレーター
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            return abort(403)  # 権限がない場合、403エラーページを表示
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    tasks = Task.query.all()
    current_date = datetime.today().date()  # 現在の日付を取得
    return render_template('matrix.html', tasks=tasks, current_date=current_date)  # current_dateを渡す

# タスク追加機能
@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    task_name = request.form['task_name']
    importance = request.form['importance']
    urgency = request.form['urgency']
    status = request.form['status']
    due_date = request.form['due_date']
    if due_date:
        due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
    
    new_task = Task(name=task_name, importance=importance, urgency=urgency, status=status, due_date=due_date)
    db.session.add(new_task)
    db.session.commit()

    return redirect(url_for('index'))

# タスク編集機能
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task.name = request.form['task_name']
        task.importance = request.form['importance']
        task.urgency = request.form['urgency']
        task.status = request.form['status']
        due_date_str = request.form['due_date']
        task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        task.memo = request.form['memo'] if request.form['memo'] else ''  # Noneの場合、空文字に変換
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_task.html', task=task)

# タスク削除機能
@app.route('/delete_task/<int:task_id>')
@login_required  # ログインしていることが必要
@admin_required  # 管理者権限が必要
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('index'))

# ユーザー登録機能
@app.route('/register', methods=['GET', 'POST'])
@login_required  # ログインしていることが必要
@admin_required  # 管理者権限が必要
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')  # 管理者か一般ユーザーかを選択

        user = User.query.filter_by(username=username).first()
        if user:
            flash('既に存在するユーザー名です。')
            return redirect(url_for('register'))

        new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'), role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('登録が完了しました。ログインしてください。')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# ログイン機能
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # ユーザーを取得
        user = User.query.filter_by(username=username).first()  # ユーザーを取得

        # ユーザーが存在しないか、パスワードが正しくない場合
        if user is None or not check_password_hash(user.password, password):
            flash('ユーザー名またはパスワードが間違っています。')
            return redirect(url_for('login'))

        login_user(user)  # ユーザーが正しい場合にログイン
        return redirect(url_for('dashboard'))  # ダッシュボードを経由せず直接matrix.htmlへリダイレクト

    return render_template('login.html')

# ログアウト機能
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ダッシュボード
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username)

# 403 エラーページ
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.route('/user_management')
@login_required
@admin_required  # 管理者権限が必要
def user_management():
    users = User.query.all()  # 全ユーザーを取得
    return render_template('user_management.html', users=users)

@app.route('/change_role/<int:user_id>', methods=['POST'])
@login_required
@admin_required  # 管理者権限が必要
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form['role']
    user.role = role
    db.session.commit()
    flash('ユーザーの権限が変更されました。')
    return redirect(url_for('user_management'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required  # 管理者権限が必要
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('ユーザーが削除されました。')
    return redirect(url_for('user_management'))

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']  # カテゴリーをフォームから取得
        date = request.form['date']
        description = request.form.get('description', '')

        # 入金額または支出額は必須
        if not amount or not category:
            flash('入金額または支出額を入力してください。')
            return redirect(url_for('add_expense'))

        new_expense = Expense(amount=amount, category=category, date=datetime.strptime(date, '%Y-%m-%d').date(), description=description)
        db.session.add(new_expense)
        db.session.commit()

        flash('支出が追加されました。')
        return redirect(url_for('expense_list'))

    return render_template('add_expense.html')

@app.route('/expense_list')
@login_required
def expense_list():
    expenses = Expense.query.all()
    # 支出の合計を計算
    total_expense = sum(expense.amount for expense in expenses if expense.category == '支出')
    
    # 残高の計算
    total_balance = 0
    for expense in expenses:
        if expense.category == '入金':
            total_balance += expense.amount
        elif expense.category == '支出':
            total_balance -= expense.amount

    return render_template('expense_list.html', expenses=expenses, total_balance=total_balance, total_expense=total_expense)

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if request.method == 'POST':
        expense.amount = request.form['amount']
        expense.category = request.form['category']
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        expense.description = request.form.get('description', '')

        db.session.commit()
        flash('支出が更新されました。')
        return redirect(url_for('expense_list'))

    return render_template('edit_expense.html', expense=expense)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('支出が削除されました。')
    return redirect(url_for('expense_list'))

# アプリケーションの実行
if __name__ == "__main__":
    app.run(debug=True)
