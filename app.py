import os
import json
from os import environ
from flask import Flask, render_template, redirect, request, url_for, jsonify, flash
from flask_pymongo import PyMongo, pymongo
from dotenv import load_dotenv, find_dotenv
from bson.objectid import ObjectId
from bson import SON
from pymongo import ASCENDING, DESCENDING, TEXT
from utils import get_pages, generate_pagination_links, get_countries, increment_field, search_name
from flask_wtf import FlaskForm, Form
from wtforms import StringField, SelectField, TextAreaField, validators, SubmitField
from forms import Username, ReusableForm, Search
from flask import session
from flask_bcrypt import Bcrypt

load_dotenv(find_dotenv())

app = Flask(__name__)

#For Local .env file
app.secret_key = os.getenv('SECRET')

app.config["MONGO_DBNAME"] = os.getenv('DBNAME')
app.config["MONGO_URI"] = os.getenv('URI')

mongo = PyMongo(app)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Kiểm tra xem username hoặc email đã tồn tại chưa
        existing_user = users.find_one({"$or": [{"username": username}, {"email": email}]})

        if existing_user:
            flash('Username or Email already exists.')
            return redirect(url_for('register'))
        
        # Thêm user mới
        users.insert_one({
            "username": username,
            "email": email,
            "password": password  # không hash
        })

        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        username = request.form['username']
        password = request.form['password']

        user = users.find_one({'username': username, 'password': password})
        
        if user:
            session['username'] = username
            flash('Logged in successfully.')
            return redirect(url_for('recipes', username=username))  # <-- chuyển đến /<username>/recipes
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/<username>/user_index')
def user_index(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))
    
    # Giả sử bạn muốn hiển thị danh sách recipe nổi bật ở đây
    public_recipes = mongo.db.recipes.find({"upvotes": {"$gt": 1}}).sort("upvotes", DESCENDING)

    return render_template("user_index.html", username=username, recipes=public_recipes)


# @app.route('/', methods=['GET','POST'])
# def index():
#     #Username form
#     wtform = Username(request.form)
#     if wtform.validate():
#         return redirect('/' + request.form['username'] + '/recipes?limit=10&offset=0')
    
#     return render_template("index.html", form=wtform, errors=wtform.errors)
    
@app.route('/books', methods=['GET'])
def books():
    books_collection = mongo.db.books
    books_list = list(books_collection.find())  
    return render_template('book_list.html', books=books_list)  
@app.route('/books/<book_id>')
def view_book(book_id):
    book = mongo.db.books.find_one({ '_id': ObjectId(book_id) })
    if not book:
        return "Book not found", 404
    return render_template('book.html', book=book) 

@app.route('/<username>/recipes')
def recipes(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))

    recipes_collection = mongo.db.recipes
    # Truy vấn tất cả công thức với is_public: True
    all_recipes = recipes_collection.find({"is_public": True}).sort("_id", 1)
    recipe_list = list(all_recipes)

    # Phân trang
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    count = len(recipe_list)
    pages = get_pages(count, limit)
    url_list = generate_pagination_links(offset, limit, pages, 'recipes', 'null', username)

    # Lấy last_id để phân trang
    starting_position = offset
    if recipe_list and starting_position < count:
        last_id = recipe_list[starting_position]['_id']
    else:
        last_id = None

    # Tạo 5 danh sách công thức đã sắp xếp
    sort_default = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("_id", 1)]).limit(limit))
    sort_name = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("name", 1)]).limit(limit))
    sort_upvotes = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("upvotes", pymongo.DESCENDING), ("name", 1)]).limit(limit))
    sort_downvotes = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("downvotes", pymongo.DESCENDING), ("name", 1)]).limit(limit))
    sort_author = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("author", 1), ("name", 1)]).limit(limit))

    # Kiểm tra và gán đường dẫn ảnh cho từng công thức trong các danh sách
    for sort_list in [sort_default, sort_name, sort_upvotes, sort_downvotes, sort_author]:
        for recipe in sort_list:
            avatar_path = f"static/images/{recipe['author']}_avt.jpg"
            # Nếu recipe.author không phải người dùng hiện tại
            if recipe['author'] != session['username']:
                # Chỉ hiển thị ảnh mặc định nếu không có ảnh của author
                if os.path.exists(avatar_path):
                    recipe['avatar_url'] = url_for('static', filename=f"images/{recipe['author']}_avt.jpg")
                else:
                    recipe['avatar_url'] = url_for('static', filename="images/default.jpg")
            else:
                # Nếu là người dùng hiện tại, giữ nguyên logic hiện tại
                if os.path.exists(avatar_path):
                    recipe['avatar_url'] = url_for('static', filename=f"images/{recipe['author']}_avt.jpg")
                else:
                    recipe['avatar_url'] = url_for('static', filename="images/default.jpg")

    # Đọc dữ liệu từ countries.json
    with open('data/countries.json', 'r', encoding='utf-8') as f:
        countries_data = json.load(f)
    
    # Lấy danh sách tên quốc gia (bỏ mục đầu tiên "Choose a Country of Origin")
    countries = [country['name'] for country in countries_data if country['name'] != "Choose a Country of Origin"]

    return render_template(
        "recipes.html",
        author=sort_author,
        default=sort_default,
        name=sort_name,
        upvotes=sort_upvotes,
        downvotes=sort_downvotes,
        url_list=url_list,
        pages=pages,
        current_page=(offset // limit) + 1,
        username=username,
        countries=countries
    )

#tạo route my recipes
@app.route('/<username>/my_recipes')
def my_recipes(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))

    recipes = mongo.db.recipes
    user_recipes = recipes.find({"author": username})
    

    return render_template("my_recipes.html", recipes=user_recipes, username=username)


    
@app.route('/<username>/search', methods=['GET'])
def search(username):
    # Lấy tham số query, limit, offset từ yêu cầu GET
    query = request.args.get('query', '').strip()
    try:
        limit = int(request.args.get('limit', 10))  # Mặc định 10 kết quả/trang
        offset = int(request.args.get('offset', 0))  # Mặc định bắt đầu từ 0
    except ValueError:
        limit = 10
        offset = 0
    
    # Truy vấn MongoDB
    recipes = mongo.db.recipes
    search_query = {"$text": {"$search": query}} if query else {}
    
    # Nếu không có query, trả về trang rỗng
    if not query:
        return render_template('search_results.html', username=username, recipes=[], query=query, count=0, pages=0, url_list=[])
    
    # Đếm tổng số kết quả
    count = recipes.count_documents(search_query)
    
    # Tính số trang và tạo liên kết phân trang
    pages = get_pages(count, limit)
    url_list = generate_pagination_links(offset, limit, pages, 'search', query, username)
    
    # Lấy danh sách công thức cho trang hiện tại
    found_recipes = recipes.find(search_query).sort('_id', pymongo.DESCENDING).skip(offset).limit(limit)
    
    # Chuyển cursor thành list để truyền vào template
    recipes_list = list(found_recipes)
    
    return render_template(
        'search_results.html',
        username=username,
        recipes=recipes_list,
        query=query,
        count=count,
        pages=pages,
        url_list=url_list,
        limit=limit,
        offset=offset
    )

@app.route('/<username>/add_recipe',methods=['GET','POST']  )
def add_recipe(username):
    if 'username' not in session or session['username'] != username:
        flash('Login first', 'error')
        return redirect(url_for('login'))
   #Load form
    wtform = ReusableForm(request.form)
    
    #Get danh sach ten cong thuc
    name_list = list(mongo.db.recipes.find({}, {'name': 1, '_id': 0}))
    
    #Get recipe co ID cao nhat
    count_list = list(mongo.db.recipes.find({}, {'recipeID': 1, '_id': 0}).sort([('recipeID', pymongo.DESCENDING)]))
   
    if request.method == 'POST' and wtform.validate():
        
        # Get All Recipes
        recipes = mongo.db.recipes
        
        #Merge Additional Instruction Fields
        instructions = request.form.getlist('instruction2')
        instructions.insert(0, request.form['instruction1'])
    
        #Merge Additional Ingredients Fields
        ingredients = request.form.getlist('ingredient2')
        ingredients.insert(0, request.form['ingredient1'])
    
        #Merge Additional Allergens Fields
        allergens = request.form.getlist('allergen2')
        if request.form['allergen1'] != '':
            allergens.insert(0, request.form['allergen1'])
        
        if search_name(request.form['name'], name_list):
            flash('That recipe already exists. Please enter another.', 'error')
            return render_template("add_recipe.html", form=wtform, errors=wtform.errors, username=username)
        else:
            #Get public from form
            is_public = wtform.is_public.data
            #Insert New Recipe to Database
            recipes.insert_one({
                        'name': request.form['name'],
                        'description': request.form['description'],
                        'instructions': instructions,
                        'upvotes': 0,
                        'downvotes': 0,
                        'ingredients': ingredients,
                        'allergens': allergens,
                        'country': request.form['country'],
                        'author': session['username'],
                        'recipeID': (count_list[0]['recipeID'] + 1) if count_list else 1,
                        'is_public': is_public
                    })
            flash('Recipe added successfully!')
            return redirect(url_for('recipes', username=username, limit=10, offset=0))
    #Render Add Recipe Page
    return render_template("add_recipe.html", form=wtform, errors=wtform.errors, username=username)
 
@app.route('/<username>/edit_recipe/<recipe_id>', methods=['GET', 'POST'])
def edit_recipe(username, recipe_id):
    if 'username' not in session:
        flash('Vui long đăng nhập trước', 'error')
        return redirect(url_for('login'))
    if session['username'] != username:
        flash('Bạn không thể chỉnh sửa công thức của người khác', 'error')
        return redirect(url_for('recipes', username = session['username']))
    # Lấy công thức
    the_recipe = mongo.db.recipes.find_one({"recipeID": int(recipe_id), "author": username})
    if not the_recipe:
        flash('Recipe not found or you do not have permission to edit.', 'error')
        return redirect(url_for('my_recipes', username=username))

    wtform = ReusableForm()  # Khởi tạo form

    if request.method == 'POST' and wtform.validate_on_submit():
        recipes = mongo.db.recipes

        # Kiểm tra tên trùng (loại trừ công thức hiện tại)
        name_list = [doc['name'] for doc in recipes.find({"recipeID": {"$ne": int(recipe_id)}}, {'name': 1, '_id': 0})]
        if request.form['name'] in name_list:
            flash('That recipe name already exists. Please choose another.', 'error')
            return render_template('edit_recipe.html', recipe=the_recipe, form=wtform, username=username)

        # Xử lý instructions
        instructions = request.form.getlist('instruction2')
        instructions.insert(0, request.form['instruction1'])

        # Xử lý ingredients
        ingredients = request.form.getlist('ingredient2')
        ingredients.insert(0, request.form['ingredient1'])

        # Xử lý allergens
        allergens = request.form.getlist('allergen2')
        if request.form.get('allergen1'):
            allergens.insert(0, request.form['allergen1'])

        # Cập nhật công thức
        recipes.update_one(
            {"recipeID": int(recipe_id)},
            {"$set": {
                'name': request.form['name'],
                'description': request.form['description'],
                'instructions': instructions,
                'ingredients': ingredients,
                'allergens': allergens,
                'country': request.form['country'],
                'author': username,  # Lấy từ session
                'is_public': wtform.is_public.data,
                'upvotes': the_recipe['upvotes'],
                'downvotes': the_recipe['downvotes']
            }}
        )

        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('my_recipes', username=username))

    # Điền sẵn dữ liệu cho form khi GET
    wtform.name.data = the_recipe['name']
    wtform.description.data = the_recipe['description']
    wtform.instruction1.data = the_recipe['instructions'][0] if the_recipe['instructions'] else ''
    wtform.ingredient1.data = the_recipe['ingredients'][0] if the_recipe['ingredients'] else ''
    wtform.allergen1.data = the_recipe['allergens'][0] if the_recipe['allergens'] else ''
    wtform.country.data = the_recipe['country']
    wtform.is_public.data = the_recipe.get('is_public', True)

    return render_template('edit_recipe.html', recipe=the_recipe, form=wtform, username=username)

@app.route('/<username>/delete_recipe/<recipe_id>', methods=['GET'])
def delete_recipe(username, recipe_id):
    if 'username' not in session:
        flash('Vui lòng đăng nhập trước.', 'error')
        return redirect(url_for('login'))
    if session['username'] != username:
        flash('Bạn không thể chỉnh sửa công thức của người khác.', 'error')
        return redirect(url_for('recipes', username=session['username']))

    # Lấy công thức để kiểm tra quyền
    recipe = mongo.db.recipes.find_one({"recipeID": int(recipe_id), "author": username})
    if not recipe:
        flash('Recipe not found or you do not have permission to delete.', 'error')
        return redirect(url_for('my_recipes', username=username))

    # Xóa công thức
    mongo.db.recipes.delete_one({"recipeID": int(recipe_id)})

    flash('Recipe deleted successfully!', 'success')
    return redirect(url_for('my_recipes', username=username))
 
@app.route('/<username>/view_recipe/<recipe_id>', methods=['GET','POST'])
def view_recipe(username, recipe_id):
    
    #Get Recipes
    recipes = mongo.db.recipes
    
    #Get Details of Selected Recipe
    the_recipe = mongo.db.recipes.find_one({"recipeID":int(recipe_id)})
    
    #Get Voting Details of Selected Recipe
    the_recipe_vote = mongo.db.recipes.find_one({"recipeID":int(recipe_id)}, { 'upvotes': 1, 'downvotes': 1 })
    
    #Store Voting Details of Selected Recipe
    current = []
    current.append(the_recipe_vote)
 
    #If a Button is Pressed
    if request.method == "POST":
        
        #If Upvote
        if request.form['vote'] == "upvote":
            
            #Increment upvote
            upvote = current[0]['upvotes'] + 1
            
            #Update Field
            recipes.update_one({'recipeID': int(recipe_id) },{ '$set':{ 'upvotes' : upvote}})
            flash('Đã tăng lượt thích!', 'success')
            return redirect('/' + username + '/recipes?limit=10&offset=0')
         
        #If Downvote 
        elif request.form['vote'] == "downvote":
            
            #Increment upvote
            downvote = current[0]['downvotes'] + 1
            
            #Update Field
            recipes.update_one( {'recipeID': int(recipe_id) }, { '$set': { 'downvotes' : downvote } } )
            flash('Đã tăng lượt không thích!', 'success')
            return redirect('/' + username + '/recipes?limit=10&offset=0')
         
    return render_template('view_recipe.html', recipe=the_recipe, username=username) 
#chức năng cài đặt cho người dùng
@app.route('/settings')
def settings():
    if 'username' not in session:
        flash('Vui lòng đăng nhập để xem cài đặt.')
        return redirect(url_for('login'))
    
    username = session['username']
    print(f"Session username: {session.get('username')}")
    return render_template('settings.html', username=username)
# up ảnh avt
@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'username' not in session:
        flash('Vui lòng đăng nhập để tải ảnh hồ sơ.')
        return redirect(url_for('login'))
    
    if 'profile_picture' not in request.files:
        flash('Không có file nào được chọn.')
        return redirect(url_for('settings'))
    
    file = request.files['profile_picture']
    if file.filename == '':
        flash('Không có file nào được chọn.')
        return redirect(url_for('settings'))
    
    if file:
        # Lưu ảnh với tên username_avt.jpg
        filename = f"{session['username']}_avt.jpg"
        file.save(os.path.join('static/images', filename))
        flash('Ảnh hồ sơ đã được cập nhật thành công.')
        return redirect(url_for('settings'))
    
    flash('Lỗi khi tải ảnh hồ sơ.')
    return redirect(url_for('settings'))
# update username
@app.route('/update_username', methods=['POST'])
def update_username():
    if 'username' not in session:
        flash('Vui lòng đăng nhập để cập nhật tên người dùng.')
        return redirect(url_for('login'))
    
    new_username = request.form.get('new_username')
    if not new_username:
        flash('Tên người dùng mới không được để trống.')
        return redirect(url_for('settings'))
    
    users = mongo.db.users
    
    # Kiểm tra xem tên người dùng mới đã tồn tại chưa
    if users.find_one({'username': new_username}):
        flash('Tên người dùng đã tồn tại. Vui lòng chọn tên khác.')
        return redirect(url_for('settings'))
    
    # Cập nhật tên người dùng trong database
    users.update_one(
        {'username': session['username']},
        {'$set': {'username': new_username}}
    )
    
    # Cập nhật session với tên người dùng mới
    old_username = session['username']
    session['username'] = new_username
    
    # Đổi tên file ảnh hồ sơ (nếu có)
    old_image_path = os.path.join('static/images', f"{old_username}_avt.jpg")
    new_image_path = os.path.join('static/images', f"{new_username}_avt.jpg")
    if os.path.exists(old_image_path):
        os.rename(old_image_path, new_image_path)
    
    flash('Tên người dùng đã được cập nhật thành công.')
    return redirect(url_for('settings'))
# doi mk
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        flash('Vui lòng đăng nhập để đổi mật khẩu.')
        return redirect(url_for('login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    if not current_password or not new_password:
        flash('Mật khẩu hiện tại và mật khẩu mới không được để trống.')
        return redirect(url_for('settings'))
    
    users = mongo.db.users
    user = users.find_one({'username': session['username'], 'password': current_password})
    
    if not user:
        flash('Mật khẩu hiện tại không đúng.')
        return redirect(url_for('settings'))
    
    # Cập nhật mật khẩu mới (plaintext)
    users.update_one(
        {'username': session['username']},
        {'$set': {'password': new_password}}
    )
    
    flash('Mật khẩu đã được cập nhật thành công.')
    return redirect(url_for('settings'))
def create_collections_and_indexes():
    try:
        # Tạo collection 'recipes' và các chỉ mục
        recipes_collection = mongo.db.recipes
        recipes_collection.create_index([("name", ASCENDING)], name="name_index")
        recipes_collection.create_index([("country", ASCENDING)], name="country_index")
        recipes_collection.create_index([("upvotes", DESCENDING)], name="upvotes_index")
        recipes_collection.create_index([("downvotes", DESCENDING)], name="downvotes_index")
        recipes_collection.create_index([("recipeID", ASCENDING)], name="recipeID_index")
        recipes_collection.create_index([("author", ASCENDING)], name="author_index")
        print("Collection 'recipes' created and indexes are set.")
        
        # Tạo collection 'users' và các chỉ mục
        users_collection = mongo.db.users
        users_collection.create_index([("username", ASCENDING)], unique=True, name="username_index")
        users_collection.create_index([("email", ASCENDING)], unique=True, name="email_index")
        print("Collection 'users' created and indexes are set.")
    
    except CollectionInvalid:
        print("One or more collections already exist.")
        
if __name__ == '__main__':
    app.run(
        host=os.environ.get('IP', '0.0.0.0'),  # IP mặc định là 0.0.0.0 nếu không có biến môi trường
        port=int(os.environ.get('PORT', 5000)),  # Cổng mặc định là 5000 nếu không có biến môi trường
        debug=True
    )