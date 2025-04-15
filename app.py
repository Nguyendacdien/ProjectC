import os
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
    
@app.route('/<username>/recipes')
def recipes(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))

    recipes = mongo.db.recipes
    # Thêm điều kiện is_public: true
    all_recipes = recipes.find({"is_public": True}).sort("_id", 1)
    recipe_list = list(all_recipes)

    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)

    count = len(recipe_list)
    pages = get_pages(count, limit)
    url_list = generate_pagination_links(offset, limit, pages, 'recipes', 'null', username)

    starting_position = request.args.get('offset', default=0, type=int)
    if recipe_list and starting_position < count:
        last_id = recipe_list[starting_position]['_id']
    else:
        last_id = None

    # Thêm điều kiện is_public: true vào các truy vấn sort
    sort_default = recipes.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("_id", 1)]).limit(limit)
    sort_country = recipes.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("country", 1), ("name", 1)]).limit(limit)
    sort_name = recipes.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("name", 1)]).limit(limit)
    sort_upvotes = recipes.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("upvotes", pymongo.DESCENDING), ("name", 1)]).limit(limit)
    sort_downvotes = recipes.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("downvotes", pymongo.DESCENDING), ("name", 1)]).limit(limit)
    sort_author = recipes.find({"is_public": True, '_id': {'$gte': last_id}}).sort([("author", 1), ("name", 1)]).limit(limit)

    return render_template("recipes.html", author=sort_author,
                           default=sort_default, name=sort_name, upvotes=sort_upvotes,
                           downvotes=sort_downvotes, country=sort_country, url_list=url_list,
                           pages=pages, username=username)

#tạo route my recipes
@app.route('/<username>/my_recipes')
def my_recipes(username):
    if 'username' not in session or session['username'] != username:
        flash("Please log in first.")
        return redirect(url_for('login'))

    recipes = mongo.db.recipes
    user_recipes = recipes.find({"author": username})

    return render_template("my_recipes.html", recipes=user_recipes, username=username)


@app.route('/<username>/search', methods=['GET','POST'])
def search(username):
    #Search User Input
        wtform = Search(request.form)
        if wtform.validate():
            return redirect('/' + username + '/' + 'search' + '/' + request.form["search"] + '?limit=10&offset=0')
        return render_template("search.html", username=username, form=wtform, errors=wtform.errors )
    
@app.route('/<username>/search/<search>', methods=['GET','POST'] )
def results(username, search):
    
    # Get All Recipes
    recipes = mongo.db.recipes
    found_recipes = recipes.find({"$text": {"$search": str(search)}})
    
    # Pagination Settings
    limit = int(request.args.get('limit'))
    offset = 0 
    
    #Get Count
    count_list = []
    for doc in found_recipes:
        count_list.append(doc)
        count = len(count_list)
    
    #If No Results Found
    if len(count_list) < 1 or not search:
        return render_template('noresults.html', username=username)
    
    #Get Pages And Generate URL List
    pages = get_pages(count, limit)
    url_list = generate_pagination_links(offset, limit, pages, 'search', search, username)

    #Get _id of Last Item on a Page
    dynamic_position = request.args.get('offset')
    starting_id = recipes.find({"$text": {"$search": str(search)}}).sort('_id')
    last_id = starting_id[int(dynamic_position)]['_id']
    
    #Sort Tables
    sort_default = recipes.find({"$and":[{'_id':{'$gte' : last_id}},{"$text":{"$search": str(search)}}]}).sort([('_id',pymongo.DESCENDING)]).limit(limit)
    sort_country = recipes.find({"$and":[{'_id':{'$gte' : last_id}},{"$text":{"$search": str(search)}}]}).sort([("country",1),("name",1 )]).limit(limit)
    sort_name = recipes.find({"$and":[{'_id':{'$gte' : last_id}},{"$text":{"$search": str(search)}}]}).sort([("name", 1)]).limit(limit)
    sort_upvotes = recipes.find({"$and":[{'_id':{'$gte' : last_id}},{"$text":{"$search": str(search)}}]}).sort([("upvotes",
    pymongo.DESCENDING),("name",1 )]).limit(limit)
    sort_downvotes = recipes.find({"$and":[{'_id':{'$gte' : last_id}},{"$text":{"$search": str(search)}}]}).sort([("downvotes",pymongo.DESCENDING),("name",1 )]).limit(limit)
    sort_author = recipes.find({"$and":[{'_id':{'$gte' : last_id}},{"$text":{"$search": str(search)}}]}).sort([("author",1),("name",1 )]).limit(limit)

    return render_template("results.html", default=sort_default, count=count, 
    url_list=url_list, pages=pages, search=search, country=sort_country, name=sort_name, 
    upvotes=sort_upvotes, downvotes=sort_downvotes, author=sort_author, username=username)

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
    if 'username' not in session or session['username'] != username:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

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
    if 'username' not in session or session['username'] != username:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

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
            recipes.update({'recipeID': int(recipe_id) },{ '$set':{ 'upvotes' : upvote}})
    
            return redirect('/' + username + '/recipes?limit=10&offset=0')
         
        #If Downvote 
        elif request.form['vote'] == "downvote":
            
            #Increment upvote
            downvote = current[0]['downvotes'] + 1
            
            #Update Field
            recipes.update( {'recipeID': int(recipe_id) }, { '$set': { 'downvotes' : downvote } } )
            
            return redirect('/' + username + '/recipes?limit=10&offset=0')
         
    return render_template('view_recipe.html', recipe=the_recipe, username=username) 
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