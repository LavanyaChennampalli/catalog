from flask import Flask, render_template, request, redirect
from flask import jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Categories, CategoryItem, User
from flask import session as login_session
from functools import wraps
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Movies Catalog Application"

engine = create_engine('sqlite:///moviecatalog.db',
                       connect_args={'check_same_thread': False}, echo=True)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

movielist = session.query(Categories)

# Create anti-forgery state token for the login session


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state, Categories=movielist)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already \
            connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px;border-radius: \
    150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('showLogin'))
    else:
        # If the given token was invalid notice the user.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Main page
@app.route('/')
@app.route('/category/')
def showCategories():
    categories = session.query(Categories).order_by(asc(Categories.name))
    return render_template('categories.html',
                           categories=categories, Categories=movielist)
# Create new category


@app.route('/categories/new', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Categories(name=request.form['name'],
                                 user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newcategory.html', Categories=movielist)

# Edit a category


@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedCategory = session.query(
        Categories).filter_by(id=category_id).one()
    # See if the logged in user is not the owner of book
    creator = getUserInfo(editedCategory.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You can't edit this category"
              "This is belongs to %s" % creator.name)
        return redirect(url_for('showCategories'))
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            flash('Category Successfully Edited %s' % editedCategory.name)
            return redirect(url_for('showCategories'))
    else:
        return render_template('editcategory.html',
                               category=editedCategory, Categories=movielist)

# delete a category


@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categoryToDelete = session.query(Categories).filter_by(
                            id=category_id).one()
    creator = getUserInfo(categoryToDelete.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You can't delete this category"
              "This is belongs to %s" % creator.name)
        return redirect(url_for('showCategories'))
    if request.method == 'POST':
        session.delete(categoryToDelete)
        flash('%s Successfully Deleted' % categoryToDelete.name)
        session.commit()
        return redirect(url_for('showCategories', category_id=category_id))
    else:
        return render_template('deletecategory.html',
                               category=categoryToDelete, Categories=movielist)


# Show a category items


@app.route('/categories/<int:categories_id>/')
@app.route('/categories/<int:categories_id>/items/')
def showcategoryitems(categories_id):
    categories = session.query(Categories).filter_by(id=categories_id).one()
    categoryitems = session.query(CategoryItem).filter_by(
        categories_id=categories.id).all()

    return render_template('categoryitems.html', categoryitems=categoryitems,
                           categories=categories, Categories=movielist)
# Create a new category item


@app.route('/categories/<int:categories_id>/items/new/',
           methods=['GET', 'POST'])
def newcategoryItem(categories_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Categories).filter_by(id=categories_id).one()
    # See if the logged in user is not the owner of book
    creator = getUserInfo(categories.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You can't add new category items"
              " This  belongs to %s" % creator.name)
        return redirect(url_for('showcategoryitems',
                                categories_id=categories.id))
    if request.method == 'POST':
        newcategoryItem = CategoryItem(name=request.form['name'],
                                       likes=request.form['likes'],
                                       dislikes=request.form['dislikes'],
                                       views=request.form['views'],
                                       img_url=request.form['img_url'],
                                       categories_id=categories_id,
                                       user_id=categories.user_id)
        session.add(newcategoryItem)
        session.commit()
        flash('New category  item %s  Successfully Created' %
              (newcategoryItem.name))
        return redirect(url_for('showcategoryitems',
                                categories_id=categories_id))
    else:
        return render_template('newcategoryitems.html',
                               categories_id=categories_id,
                               Categories=movielist)

# Edit a category item


@app.route('/category/<int:categories_id>/items/<int:categoryitem_id>/edit',
           methods=['GET', 'POST'])
def editcategoryItem(categories_id, categoryitem_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedcategoryItem = session.query(CategoryItem).filter_by(
                      id=categoryitem_id).one()
    categories = session.query(Categories).filter_by(id=categories_id).one()
    # See if the logged in user is not the owner of category
    creator = getUserInfo(categories.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You can't edit  this category items"
              "This is belongs to %s" % creator.name)
        return redirect(url_for('showcategoryitems',
                                categories_id=categories.id))
    if request.method == 'POST':
        if request.form['name']:
            editedcategoryItem.name = request.form['name']
        if request.form['likes']:
            editedcategoryItem.likes = request.form['likes']
        if request.form['dislikes']:
            editedcategoryItem.dislikes = request.form['dislikes']
        if request.form['views']:
            editedcategoryItem.likes = request.form['views']
        if request.form['img_url']:
            editedcategoryItem.img_url = request.form['img_url']
        session.add(editedcategoryItem)
        session.commit()
        flash('category Item Successfully Edited')
        return redirect(url_for('showcategoryitems',
                                categories_id=categories_id))
    else:
        return render_template('editcategoryitems.html',
                               categories_id=categories_id,
                               categoryitem_id=categoryitem_id,
                               categoryitem=editedcategoryItem,
                               Categories=movielist)

# Delete a menu item


@app.route('/category/<int:categories_id>/items/<int:categoryitem_id>/delete',
           methods=['GET', 'POST'])
def deletecategoryItem(categories_id, categoryitem_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Categories).filter_by(id=categories_id).one()
    itemToDelete = session.query(CategoryItem).filter_by(
                            id=categoryitem_id).one()
    # See if the logged in user is not the owner of book
    creator = getUserInfo(categories.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You can't delete this category items"
              "This is belongs to %s" % creator.name)
        return redirect(url_for('showcategoryitems',
                                categories_id=categories.id))
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Category Item Successfully Deleted')
        return redirect(url_for('showcategoryitems',
                                categories_id=categories_id))
    else:
        return render_template('deletecategoryitems.html',
                               categoryItem=itemToDelete, Categories=movielist)


@app.route('/category/<int:categories_id>/items/JSON')
def categoryitemJSON(categories_id):
    categories = session.query(Categories).filter_by(id=categories_id).one()
    categoryitems = session.query(CategoryItem).filter_by(
        categories_id=categories.id).all()
    return jsonify(categoryitems=[i.serialize for i in categoryitems])


@app.route('/category/<int:categories_id>/item/<int:categoryitem_id>/JSON')
def categoryItemJSON(categories_id, categoryitem_id):
    categoryitems = session.query(CategoryItem).filter_by(
                           id=categoryitem_id).one()
    return jsonify(categoryitems=categoryitems.serialize)


@app.route('/category/items/JSON')
def itemsJSON():
    categoryitems = session.query(CategoryItem).all()
    return jsonify(categoryitems=[i.serialize for i in categoryitems])


@app.route('/category/JSON')
def categoriesJSON():
    categories = session.query(Categories).all()
    return jsonify(categories=[r.serialize for r in categories])

if __name__ == '__main__':
    global movielist
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)    