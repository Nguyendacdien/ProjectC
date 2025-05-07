import os
import json
from os import environ
from flask import Flask, render_template, redirect, request, url_for, jsonify, flash, Response
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
from werkzeug.utils import secure_filename
from datetime import datetime
from forms import CommentForm
from flask_session import Session
from unidecode import unidecode
from datetime import datetime
from os.path import basename
load_dotenv(find_dotenv())

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dienmoidaide'  # Thay bằng một chuỗi ngẫu nhiên
app.config['SESSION_TYPE'] = 'filesystem'  # Hoặc 'mongodb', 'redis'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session kéo dài 1 giờ
Session(app)

# Cấu hình thư mục lưu file
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.getenv('SECRET')

app.config["MONGO_DBNAME"] = os.getenv('DBNAME')
app.config["MONGO_URI"] = os.getenv('URI')
#tạo thưu muc upload nếu ch có
UPLOAD_FOLDER = 'static/uploads/recipes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
mongo = PyMongo(app)

# Hàm kiểm tra định dạng file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# Helper function to create notification
def create_notification(username, type, recipe_id, from_username, message):
    notification = {
        "username": username,
        "type": type,
        "recipe_id": recipe_id,
        "from_username": from_username,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "read": False
    }
    mongo.db.notifications.insert_one(notification)
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
    
@app.route('/<username>/books', methods=['GET'])
def books(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))
    books_collection = mongo.db.books
    books_list = list(books_collection.find())  
    return render_template('book_list.html', books=books_list, username=username)   

@app.route('/view_book/<username>/<book_id>', methods=['GET'])
def view_book(username, book_id):
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    if not book:
        flash("Sách không tồn tại.", "danger")
        return redirect(url_for('books', username=username))

    # Lấy trang hiện tại từ query string (mặc định là trang 1)
    current_page = int(request.args.get('page', 1))  # Lấy giá trị page từ query string
    total_pages = len(book['pages'])  # Số trang tổng cộng

    # Kiểm tra nếu current_page không vượt quá tổng số trang
    if current_page > total_pages:
        current_page = total_pages
    elif current_page < 1:
        current_page = 1

    return render_template('book.html', username=username, book=book, current_page=current_page, total_pages=total_pages)

@app.route('/save_book/<username>/<book_id>', methods=['POST'])
def save_book(username, book_id):
    if 'username' not in session or session['username'] != username:
        flash("Vui lòng đăng nhập", "danger")
        return redirect(url_for('login')) 

    # Kiểm tra nếu sách tồn tại trong database
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    if book:
        if username not in book.get("username", []):
            mongo.db.books.update_one(
                {"_id": ObjectId(book_id)},
                {"$push": {"username": username}}  
            )
            flash("Sách đã được lưu vào My Book", "success")
        else:
            flash("Sách đã được lưu rồi.", "info")
    else:
        flash("Không tìm thấy sách.", "danger")

    return redirect(url_for('my_books', username=username))  
@app.route('/<username>/unsave_book/<book_id>', methods=['POST'])
def unsave_book(username, book_id):
    if 'username' not in session or session['username'] != username:
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 400

    try:
        book_id_obj = ObjectId(book_id)
        book = mongo.db.books.find_one({"_id": book_id_obj})
        if not book:
            return jsonify({'success': False, 'message': 'Không tìm thấy sách.'}), 400

        if username in book.get("username", []):
            result = mongo.db.books.update_one(
                {"_id": book_id_obj},
                {"$pull": {"username": username}}
            )
            if result.modified_count > 0:
                return jsonify({'success': True})
            return jsonify({'success': False, 'message': 'Không thể xóa sách khỏi danh sách đã lưu.'}), 400
        else:
            return jsonify({'success': False, 'message': 'Sách không nằm trong danh sách đã lưu của bạn.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'}), 400
@app.route('/my_books/<username>')
def my_books(username):
    if 'username' not in session or session['username'] != username:
        flash("Vui lòng đăng nhập trước khi xem My Books", "danger")
        return redirect(url_for('login'))

    # Lọc sách theo username
    books_cursor = mongo.db.books.find({"username": username})
    books = list(books_cursor)  # Chuyển đổi Cursor thành danh sách

    # Tính số lượng sách
    book_count = len(books)

    return render_template('my_book.html', books=books, book_count=book_count, username=username)
@app.route('/<username>/recipes')
def recipes(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))

    recipes_collection = mongo.db.recipes
    all_recipes = recipes_collection.find({"is_public": True}).sort("_id", 1)
    recipe_list = list(all_recipes)

    limit = request.args.get('limit', default=9, type=int)  # 9 card (3x3 mỗi trang)
    offset = request.args.get('offset', default=0, type=int)
    
    count = len(recipe_list)
    pages = get_pages(count, limit)
    url_list = generate_pagination_links(offset, limit, pages, 'recipes', 'null', username)

    starting_position = offset
    if recipe_list and starting_position < count:
        last_id = recipe_list[starting_position]['_id']
    else:
        last_id = None

    sort_default = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("_id", 1)]).limit(limit))
    sort_name = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("name", 1)]).limit(limit))
    sort_upvotes = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("upvotes", pymongo.DESCENDING), ("name", 1)]).limit(limit))
    sort_downvotes = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("downvotes", pymongo.DESCENDING), ("name", 1)]).limit(limit))
    sort_author = list(recipes_collection.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("author", 1), ("name", 1)]).limit(limit))

    for sort_list in [sort_default, sort_name, sort_upvotes, sort_downvotes, sort_author]:
        for recipe in sort_list:
            avatar_path = f"static/images/{recipe['author']}_avt.jpg"
            if os.path.exists(avatar_path):
                recipe['avatar_url'] = url_for('static', filename=f"images/{recipe['author']}_avt.jpg")
            else:
                recipe['avatar_url'] = url_for('static', filename="images/default.jpg")
            recipe['image_path'] = recipe.get('image_path', 'dishDF.jpg')

    with open('data/countries.json', 'r', encoding='utf-8') as f:
        countries_data = json.load(f)
    
    countries = [country['name'] for country in countries_data if country['name'] != "Choose a Country of Origin"]
    unread_notifications = mongo.db.notifications.count_documents({
        "username": username,
        "read": False
    })

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
        countries=countries,
        unread_notifications=unread_notifications
    )

#tạo route my recipes
@app.route('/<username>/my_recipes')
def my_recipes(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))

    recipes = mongo.db.recipes
    user_recipes = recipes.find({"author": username})
    unread_notifications = mongo.db.notifications.count_documents({
        "username": username,
        "read": False
    })

    return render_template("my_recipes.html", recipes=user_recipes, username=username, unread_notifications=unread_notifications)


    
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

#cho phep add anh vao cong thucthuc
@app.route('/<username>/add_recipe', methods=['GET', 'POST'])
def add_recipe(username):
    if 'username' not in session or session['username'] != username:
        flash('Login first', 'error')
        return redirect(url_for('login'))

    unread_notifications = mongo.db.notifications.count_documents({
        "username": username,
        "read": False
    })

    # Load form
    wtform = ReusableForm()

    # Get danh sách tên công thức
    name_list = list(mongo.db.recipes.find({}, {'name': 1, '_id': 0}))

    # Get recipe có ID cao nhất
    count_list = list(mongo.db.recipes.find({}, {'recipeID': 1, '_id': 0}).sort([('recipeID', pymongo.DESCENDING)]))

    if request.method == 'POST' and wtform.validate_on_submit():
        # Get All Recipes
        recipes = mongo.db.recipes

        # Merge Additional Instruction Fields
        instructions = request.form.getlist('instruction2')
        instructions.insert(0, request.form['instruction1'])

        # Merge Additional Ingredients Fields
        ingredients = request.form.getlist('ingredient2')
        ingredients.insert(0, request.form['ingredient1'])

        # Merge Additional Allergens Fields
        allergens = request.form.getlist('allergen2')
        if request.form['allergen1']:
            allergens.insert(0, request.form['allergen1'])

        # Xử lý danh sách ảnh
        images = request.files.getlist('images')
        if not images or all(img.filename == '' for img in images):
            flash('Please upload at least one image for the recipe.', 'error')
            return render_template("add_recipe.html", form=wtform, errors=wtform.errors, username=username, unread_notifications=unread_notifications)

        # Kiểm tra xem tên công thức đã tồn tại chưa
        if search_name(request.form['name'], name_list):
            flash('That recipe already exists. Please enter another.', 'error')
            return render_template("add_recipe.html", form=wtform, errors=wtform.errors, username=username, unread_notifications=unread_notifications)

        # Tạo recipeID
        recipe_id = (count_list[0]['recipeID'] + 1) if count_list else 1

        # Lưu các ảnh vào thư mục và chuẩn hóa tên
        image_paths = []
        for index, image in enumerate(images):
            if image and image.filename != '' and allowed_file(image.filename):
                # Chuẩn hóa tên file
                original_filename = secure_filename(image.filename)
                extension = os.path.splitext(original_filename)[1]
                short_name = f"{recipe_id}_{index}{extension}"
                image_name = short_name
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
                image.save(image_path)
                image_paths.append(f"uploads/recipes/{image_name}")

        # Lấy chỉ số ảnh được chọn làm background
        background_index = int(request.form.get('background_image', 0))
        if background_index >= len(image_paths):
            background_index = 0

        # Lấy các trường mới
        serves = int(request.form['serves'])
        prep_time = int(request.form['prep_time'])
        cook_time = int(request.form['cook_time'])
        total_time = prep_time + cook_time

        # Get public from form
        is_public = wtform.is_public.data

        # Insert New Recipe to Database
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
            'recipeID': recipe_id,
            'is_public': is_public,
            'images': image_paths,
            'background_image': image_paths[background_index],
            # Thêm các trường mới
            'serves': serves,
            'prep_time': prep_time,
            'cook_time': cook_time,
            'total_time': total_time
        })

        flash('Recipe added successfully!')
        return redirect(url_for('recipes', username=username, limit=10, offset=0))

    # Render Add Recipe Page
    return render_template("add_recipe.html", form=wtform, errors=wtform.errors, username=username, unread_notifications=unread_notifications)
 
# @app.route('/<username>/edit_recipe/<recipe_id>', methods=['GET', 'POST'])
# def edit_recipe(username, recipe_id):
#     if 'username' not in session:
#         flash('Vui long đăng nhập trước', 'error')
#         return redirect(url_for('login'))
#     if session['username'] != username:
#         flash('Bạn không thể chỉnh sửa công thức của người khác', 'error')
#         return redirect(url_for('recipes', username = session['username']))
#     # Lấy công thức
#     the_recipe = mongo.db.recipes.find_one({"recipeID": int(recipe_id), "author": username})
#     if not the_recipe:
#         flash('Recipe not found or you do not have permission to edit.', 'error')
#         return redirect(url_for('my_recipes', username=username))

#     wtform = ReusableForm()  # Khởi tạo form

#     if request.method == 'POST' and wtform.validate_on_submit():
#         recipes = mongo.db.recipes

#         # Kiểm tra tên trùng (loại trừ công thức hiện tại)
#         name_list = [doc['name'] for doc in recipes.find({"recipeID": {"$ne": int(recipe_id)}}, {'name': 1, '_id': 0})]
#         if request.form['name'] in name_list:
#             flash('That recipe name already exists. Please choose another.', 'error')
#             return render_template('edit_recipe.html', recipe=the_recipe, form=wtform, username=username)

#         # Xử lý instructions
#         instructions = request.form.getlist('instruction2')
#         instructions.insert(0, request.form['instruction1'])

#         # Xử lý ingredients
#         ingredients = request.form.getlist('ingredient2')
#         ingredients.insert(0, request.form['ingredient1'])

#         # Xử lý allergens
#         allergens = request.form.getlist('allergen2')
#         if request.form.get('allergen1'):
#             allergens.insert(0, request.form['allergen1'])

#         # Cập nhật công thức
#         recipes.update_one(
#             {"recipeID": int(recipe_id)},
#             {"$set": {
#                 'name': request.form['name'],
#                 'description': request.form['description'],
#                 'instructions': instructions,
#                 'ingredients': ingredients,
#                 'allergens': allergens,
#                 'country': request.form['country'],
#                 'author': username,  # Lấy từ session
#                 'is_public': wtform.is_public.data,
#                 'upvotes': the_recipe['upvotes'],
#                 'downvotes': the_recipe['downvotes']
#             }}
#         )

#         flash('Recipe updated successfully!', 'success')
#         return redirect(url_for('my_recipes', username=username))

#     # Điền sẵn dữ liệu cho form khi GET
#     wtform.name.data = the_recipe['name']
#     wtform.description.data = the_recipe['description']
#     wtform.instruction1.data = the_recipe['instructions'][0] if the_recipe['instructions'] else ''
#     wtform.ingredient1.data = the_recipe['ingredients'][0] if the_recipe['ingredients'] else ''
#     wtform.allergen1.data = the_recipe['allergens'][0] if the_recipe['allergens'] else ''
#     wtform.country.data = the_recipe['country']
#     wtform.is_public.data = the_recipe.get('is_public', True)

#     return render_template('edit_recipe.html', recipe=the_recipe, form=wtform, username=username)
#route edit moimoi
@app.route('/<username>/edit_recipe/<recipe_id>', methods=['GET', 'POST'])
def edit_recipe(username, recipe_id):
    if 'username' not in session or session['username'] != username:
        flash('Please log in to edit this recipe.', 'error')
        return redirect(url_for('login'))

    # Get the recipe
    recipes = mongo.db.recipes
    recipe = recipes.find_one({"recipeID": int(recipe_id), "author": username})

    if not recipe:
        flash('Recipe not found or you do not have permission to edit it.', 'error')
        return redirect(url_for('my_recipes', username=username))

    # Load form
    form = ReusableForm()

    # Get unread notifications count
    unread_notifications = mongo.db.notifications.count_documents({
        "username": username,
        "read": False
    })

    if request.method == 'POST' and form.validate_on_submit():
        # Merge Additional Instruction Fields
        instructions = request.form.getlist('instruction2')
        instructions.insert(0, request.form['instruction1'])

        # Merge Additional Ingredients Fields
        ingredients = request.form.getlist('ingredient2')
        ingredients.insert(0, request.form['ingredient1'])

        # Merge Additional Allergens Fields
        allergens = request.form.getlist('allergen2')
        allergens.insert(0, request.form['allergen1'])

        # Get current images
        current_images = recipe['images']

        # Handle images to remove
        images_to_remove_raw = request.form.get('images_to_remove', '[]')
        try:
            images_to_remove = json.loads(images_to_remove_raw)
        except json.JSONDecodeError:
            images_to_remove = []
        for image_path in images_to_remove:
            if image_path in current_images:
                current_images.remove(image_path)
                # Delete the file from static folder
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(image_path))
                if os.path.exists(file_path):
                    os.remove(file_path)

        # Handle new images
        new_images = request.files.getlist('new_images')
        new_image_paths = []
        for index, image in enumerate(new_images):
            if image and image.filename != '' and allowed_file(image.filename):
                image_name = f"{recipe['recipeID']}_{len(current_images) + index}{os.path.splitext(image.filename)[1]}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
                image.save(image_path)
                new_image_paths.append(f"uploads/recipes/{image_name}")

        # Update images list
        updated_images = current_images + new_image_paths

        # Handle background image selection
        background_index = int(request.form.get('background_image', 0))
        if not updated_images:
            flash('At least one image is required for the recipe.', 'error')
            return redirect(url_for('edit_recipe', username=username, recipe_id=recipe_id))
        if background_index >= len(updated_images):
            background_index = 0
        background_image = updated_images[background_index]

        # Lấy các trường mới
        serves = int(request.form['serves'])
        prep_time = int(request.form['prep_time'])
        cook_time = int(request.form['cook_time'])
        total_time = prep_time + cook_time

        # Update recipe in MongoDB
        recipes.update_one(
            {"recipeID": int(recipe_id)},
            {
                "$set": {
                    "name": request.form['name'],
                    "description": request.form['description'],
                    "instructions": instructions,
                    "ingredients": ingredients,
                    "allergens": allergens,
                    "country": request.form['country'],
                    "is_public": form.is_public.data,
                    "images": updated_images,
                    "background_image": background_image,
                    # Cập nhật các trường mới
                    "serves": serves,
                    "prep_time": prep_time,
                    "cook_time": cook_time,
                    "total_time": total_time
                }
            }
        )

        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('my_recipes', username=username))

    # Pre-fill form with current recipe data
    form.name.data = recipe['name']
    form.description.data = recipe['description']
    form.instruction1.data = recipe['instructions'][0] if recipe['instructions'] else ''
    form.ingredient1.data = recipe['ingredients'][0] if recipe['ingredients'] else ''
    form.allergen1.data = recipe['allergens'][0] if recipe['allergens'] else ''
    form.country.data = recipe['country']
    form.is_public.data = recipe['is_public']
    # Điền giá trị cho các trường mới
    form.serves.data = recipe.get('serves', 1)
    form.prep_time.data = recipe.get('prep_time', 0)
    form.cook_time.data = recipe.get('cook_time', 0)

    return render_template(
        "edit_recipe.html",
        form=form,
        recipe=recipe,
        username=username,
        unread_notifications=unread_notifications
    )
@app.route('/<username>/delete_recipe/<recipe_id>', methods=['GET'])
def delete_recipe(username, recipe_id):
    if 'username' not in session:
        flash('Vui lòng đăng nhập trước.', 'error')
        return redirect(url_for('login'))

    # Lấy công thức để kiểm tra quyền
    recipe = mongo.db.recipes.find_one({"recipeID": int(recipe_id)})
    if not recipe:
        flash('Không tìm thấy công thức.', 'error')
        return redirect(url_for('my_recipes', username=session['username']))

    # Kiểm tra quyền xoá
    if session['username'] != recipe['author']:
        flash('You are not authorized this recipe .', 'error')
        return redirect(url_for('view_recipe', username=recipe['author'], recipe_id=recipe_id))

    # Xoá công thức
    mongo.db.recipes.delete_one({"recipeID": int(recipe_id)})

    flash('Xoá công thức thành công!', 'success')
    return redirect(url_for('my_recipes', username=session['username']))

 #thêm comment
@app.route('/<username>/view_recipe/<recipe_id>', methods=['GET', 'POST'])
def view_recipe(username, recipe_id):
    # Get Recipes
    recipes = mongo.db.recipes
    
    # Get Details of Selected Recipe
    the_recipe = mongo.db.recipes.find_one({"recipeID": int(recipe_id)})
    
    if not the_recipe or (the_recipe.get('is_public', False) == False and session.get('username') != username):
        return jsonify({'success': False, 'message': 'Recipe not found or not accessible.'})

    # Tạo danh sách URL ảnh cho carousel
    image_urls = []
    if the_recipe.get('images'):
        for img in the_recipe['images']:
            image_urls.append(url_for('static', filename=img))
    background_image = the_recipe.get('background_image')
    if background_image and url_for('static', filename=background_image) not in image_urls:
        image_urls.insert(0, url_for('static', filename=background_image))

    # Get Voting Details
    the_recipe_vote = mongo.db.recipes.find_one({"recipeID": int(recipe_id)}, {'upvotes': 1, 'downvotes': 1})
    current = []
    current.append(the_recipe_vote)

    # Form comment
    comment_form = CommentForm()

    # Kiểm tra lịch sử bỏ phiếu
    user_vote = mongo.db.votes.find_one({
        "username": session.get('username', 'anonymous'),
        "recipe_id": int(recipe_id)
    })

    # Thêm avatar_url vào comments
    for comment in the_recipe.get('comments', []):
        user = mongo.db.users.find_one({"username": comment['username']})
        avatar_filename = f"{comment['username']}_avt.jpg"
        comment['avatar_url'] = url_for('static', filename=f'images/{avatar_filename}') if user else url_for('static', filename='images/default.jpg')

    # If a Button is Pressed
    if request.method == "POST":
        print(f"Received POST request: {request.form}")  # Debug log
        if 'vote' in request.form:
            current_user = session.get('username', 'anonymous')
            if user_vote:
                return jsonify({'success': False, 'message': 'You have already voted on this recipe.'})
            elif current_user == the_recipe['author']:
                return jsonify({'success': False, 'message': 'You cannot vote on your own recipe.'})

            if request.form['vote'] == "upvote":
                upvote = current[0]['upvotes'] + 1
                recipes.update_one({'recipeID': int(recipe_id)}, {'$set': {'upvotes': upvote}})
                mongo.db.votes.insert_one({
                    "username": current_user,
                    "recipe_id": int(recipe_id),
                    "vote_type": "upvote",
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                })
                flash('Đã tăng lượt thích!', 'success')
                if current_user != the_recipe['author']:
                    create_notification(
                        the_recipe['author'],
                        "upvote",
                        int(recipe_id),
                        current_user,
                        f"{current_user} upvoted your recipe '{the_recipe['name']}'"
                    )
            
            elif request.form['vote'] == "downvote":
                downvote = current[0]['downvotes'] + 1
                recipes.update_one({'recipeID': int(recipe_id)}, {'$set': {'downvotes': downvote}})
                mongo.db.votes.insert_one({
                    "username": current_user,
                    "recipe_id": int(recipe_id),
                    "vote_type": "downvote",
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                })
                flash('Đã tăng lượt không thích!', 'success')
                if current_user != the_recipe['author']:
                    create_notification(
                        the_recipe['author'],
                        "downvote",
                        int(recipe_id),
                        current_user,
                        f"{current_user} downvoted your recipe '{the_recipe['name']}'"
                    )
            
            return jsonify({'success': True})
        
        elif comment_form.validate_on_submit() and 'comment' in request.form:
            if 'username' not in session:
                return jsonify({'success': False, 'message': 'Please log in to comment.'})
            if the_recipe.get('is_public', False):
                comment_text = request.form['comment']
                new_comment = {
                    '_id': str(ObjectId()),
                    'username': session['username'],
                    'comment_text': comment_text,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                recipes.update_one(
                    {'recipeID': int(recipe_id)},
                    {'$push': {'comments': new_comment}}
                )
                flash('Comment added successfully!', 'success')
                if session['username'] != the_recipe['author']:
                    create_notification(
                        the_recipe['author'],
                        "comment",
                        int(recipe_id),
                        session['username'],
                        f"{session['username']} commented on your recipe '{the_recipe['name']}'"
                    )
            else:
                return jsonify({'success': False, 'message': 'Only public recipes can be commented on.'})
            return jsonify({'success': True})
        
        # Xử lý chỉnh sửa comment
        for comment in the_recipe.get('comments', []):
            edit_field = f'edit_comment_{comment["_id"]}'
            if edit_field in request.form:
                print(f"Processing edit for comment {comment['_id']}")  # Debug log
                if 'username' not in session:
                    return jsonify({'success': False, 'message': 'Please log in to edit comment.'})
                if comment['username'] != session['username']:
                    return jsonify({'success': False, 'message': 'You can only edit your own comments.'})
                new_comment_text = request.form[edit_field].strip()
                if new_comment_text:
                    result = recipes.update_one(
                        {'recipeID': int(recipe_id), 'comments._id': comment['_id']},
                        {'$set': {'comments.$.comment_text': new_comment_text}}
                    )
                    print(f"Update result: {result.modified_count} document(s) modified")  # Debug log
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'message': 'Comment cannot be empty.'})
        
        # Xử lý xóa comment
        for comment in the_recipe.get('comments', []):
            delete_field = f'delete_comment_{comment["_id"]}'
            if delete_field in request.form and request.form[delete_field] == '1':
                print(f"Processing delete for comment {comment['_id']}")  # Debug log
                if 'username' not in session:
                    return jsonify({'success': False, 'message': 'Please log in to delete comment.'})
                if comment['username'] != session['username']:
                    return jsonify({'success': False, 'message': 'You can only delete your own comments.'})
                result = recipes.update_one(
                    {'recipeID': int(recipe_id)},
                    {'$pull': {'comments': {'_id': comment['_id']}}}
                )
                print(f"Delete result: {result.modified_count} document(s) modified")  # Debug log
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'message': 'Invalid request.'})  # Thêm phản hồi mặc định
    
    # Lấy số lượng thông báo chưa đọc
    unread_notifications = mongo.db.notifications.count_documents({
        "username": username,
        "read": False
    })
    return render_template('view_recipe.html', recipe=the_recipe, username=username, comment_form=comment_form, unread_notifications=unread_notifications, image_urls=image_urls)
@app.route('/<username>/notifications')
def notifications(username):
    if 'username' not in session or session['username'] != username:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('login'))
    notifications = mongo.db.notifications.find({"username": username}).sort("timestamp", -1)
    # Đánh dấu tất cả thông báo là đã đọc
    mongo.db.notifications.update_many({"username": username, "read": False}, {"$set": {"read": True}})
    return render_template('notifications.html', username=username, notifications=notifications)
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
@app.route('/<username>/recipe/<recipe_id>/comment/<comment_id>/edit', methods=['GET', 'POST'])
def edit_comment(username, recipe_id, comment_id):
    if 'username' not in session or session['username'] != username:
        flash('You are not authorized to edit this comment.', 'error')
        return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))

    recipe = mongo.db.recipes.find_one({"recipeID": int(recipe_id)})
    if not recipe or int(comment_id) >= len(recipe.get('comments', [])):
        flash('Comment not found.', 'error')
        return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))

    comment = recipe['comments'][int(comment_id)]
    if comment['username'] != username:
        flash('You can only edit your own comments.', 'error')
        return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))

    if request.method == 'POST':
        new_comment_text = request.form.get('comment')
        if new_comment_text:
            mongo.db.recipes.update_one(
                {"recipeID": int(recipe_id)},
                {"$set": {f"comments.{comment_id}.comment_text": new_comment_text}}
            )
            flash('Comment updated successfully!', 'success')
        else:
            flash('Comment cannot be empty.', 'error')
        return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))

    return render_template('edit_comment.html', comment=comment, username=username, recipe_id=recipe_id, comment_id=comment_id)
@app.route('/<username>/recipe/<recipe_id>/comment/<comment_id>/delete', methods=['POST'])
def delete_comment(username, recipe_id, comment_id):
    if 'username' not in session or session['username'] != username:
        flash('You are not authorized to delete this comment.', 'error')
        return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))

    recipe = mongo.db.recipes.find_one({"recipeID": int(recipe_id)})
    if not recipe or int(comment_id) >= len(recipe.get('comments', [])):
        flash('Comment not found.', 'error')
        return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))

    comment = recipe['comments'][int(comment_id)]
    if comment['username'] != username:
        flash('You can only delete your own comments.', 'error')
        return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))

    mongo.db.recipes.update_one(
        {"recipeID": int(recipe_id)},
        {"$pull": {"comments": {"username": comment['username'], "comment_text": comment['comment_text'], "timestamp": comment['timestamp']}}}
    )
    flash('Comment deleted successfully!', 'success')
    return redirect(url_for('view_recipe', username=username, recipe_id=recipe_id))


# Hàm kiểm tra file hợp lệ
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Hàm chuẩn hóa tên file
def generate_image_name(recipe_id, original_filename, index):
    filename = os.path.splitext(original_filename)[0]
    slug = unidecode(filename.lower()).replace(" ", "-")
    slug = slug[:50] if len(slug) > 50 else slug
    return f"{recipe_id}_{index}_{slug}.jpg"

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