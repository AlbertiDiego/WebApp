from flask import Flask, render_template, redirect, request, flash, jsonify
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import os
from bson import ObjectId
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user


my_secret = os.environ['MongoPassword']
uri = "mongodb+srv://Diego:" + my_secret + "@cluster0.3tah5py.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['ContenutiMultimediali']
coll_utenti = db['utenti']
coll_posts = db['nome_collezione_posts']


app = Flask(__name__)
app.secret_key = os.urandom(24)


bcrypt = Bcrypt(app)


login_manager = LoginManager(app)
login_manager.login_view = 'login'



class Utente(UserMixin):
    def __init__(self, username):
        self.username = username

    def get_id(self):
        return self.username


  
@login_manager.user_loader
def load_user(username):
    utente_db = coll_utenti.find_one({"username": username})
    if utente_db:
        return Utente(username=utente_db['username'])
    else:
        return None



@app.route('/post', methods=['POST'])
@login_required
def post():
    if request.method == 'POST':
        data = request.json
        content = data['content']
        coll_posts.insert_one({
            'author': current_user.username,
            'content': content,
            'timestamp': datetime.now(),
            'likes': 0,
            'comments': [],
            'liked_by': []
        })
        flash('Il post è stato pubblicato con successo!', 'success')
        return redirect('/')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = coll_utenti.find_one({"username": username})

        if existing_user:
            flash('Username già in uso. Scegli un altro.', 'danger')
            return redirect('/signup')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            coll_utenti.insert_one({"username": username, "password": hashed_password})
            flash('Registrazione avvenuta con successo. Effettua il login.', 'success')
            return redirect('/login')

    return render_template('signup.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        utente_db = coll_utenti.find_one({"username": username})

        if utente_db and bcrypt.check_password_hash(utente_db['password'], password):
            login_user(Utente(username=username))
            return redirect('/')
        else:
            flash('Credenziali non valide. Riprova.', 'danger')
            return redirect('/login')
    return render_template('login.html')


  
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sei stato disconnesso con successo.', 'success')
    return redirect('/login')



@app.route('/')
@login_required
def homepage():
    posts = coll_posts.find().sort('timestamp', -1)
    return render_template('homepage.html', posts=posts, current_user=current_user)



@app.route('/my_contents')
@login_required
def my_contents():
    user_contents = coll_posts.find({"author": current_user.username})
    return render_template('my_contents.html', user_contents=user_contents)


  
@app.route('/delete_post/<string:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    if request.method == 'DELETE':
        post = coll_posts.find_one({'_id': ObjectId(post_id), 'author': current_user.username})
        if post:
            coll_posts.delete_one({'_id': ObjectId(post_id)})
            flash('Il post è stato eliminato con successo!', 'success')
        else:
            flash('Non hai il permesso di eliminare questo post.', 'danger')
        return redirect('/my_contents')
    else:
        return jsonify({'message': 'Metodo non consentito'}), 405


@app.route('/like_post/<string:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    if request.method == 'POST':
        post = coll_posts.find_one({'_id': ObjectId(post_id)})
        if post:
            if current_user.username not in post['liked_by']:
                coll_posts.update_one({'_id': ObjectId(post_id)}, {'$inc': {'likes': 1}, '$push': {'liked_by': current_user.username}})
                return jsonify({'message': 'Mi Piace aggiunto con successo'}), 200
            else:
                return jsonify({'message': 'Hai già messo Mi Piace a questo post'}), 400
        else:
            return jsonify({'message': 'Post non trovato'}), 404


  
@app.route('/add_comment/<string:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    if request.method == 'POST':
        data = request.json
        content = data['content']
        comment = {
            'content': content,
            'author': current_user.username
        }
        coll_posts.update_one({'_id': ObjectId(post_id)}, {'$push': {'comments': comment}})
        return jsonify({'message': 'Commento aggiunto con successo'}), 200

      
@app.route('/filter_posts', methods=['POST'])
@login_required
def filter_posts():
    if request.method == 'POST':
        keyword = request.form.get('keywordInput', '').strip()

        if keyword:
            filtered_posts = coll_posts.find({
                '$or': [
                    {'content': {'$regex': keyword, '$options': 'i'}},
                    {'comments.content': {'$regex': keyword, '$options': 'i'}}
                ]
            }).sort('timestamp', -1)

            return render_template('homepage.html', posts=filtered_posts, current_user=current_user)

    posts = coll_posts.find().sort('timestamp', -1)
    return render_template('homepage.html', posts=posts, current_user=current_user)




  
if __name__ == '__main__':
    app.run(debug=True, port=8080)
