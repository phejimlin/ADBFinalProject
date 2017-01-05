from .api import member
from .api import diary
# from .api import pair
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory, jsonify
from invalidusage import InvalidUsage
from flask.json import jsonify


app = Flask(__name__)

@app.route('/')
def index():
    if 'id' in session:
        return redirect(url_for('main'))
    else:
        return redirect(url_for('login'))

@app.route('/index', methods=['GET'])
def main():
    session_check('render_page')
    return render_template('index.html')

@app.route('/create_diary', methods=['GET'])
def create_diary():
    session_check('render_page')
    return render_template('create_diary.html')

@app.route('/friends', methods=['GET'])
def friends():
    session_check('render_page')
    return render_template('friends.html')

@app.route('/search', methods=['GET'])
def search():
    session_check('render_page')
    return render_template('search.html')

@app.route('/profile', methods=['GET'])
def profile():
    session_check('render_page')
    return render_template('profile.html', me=member.get_my_info())

# serving static file such as js css.
@app.route('/static/<path:filename>')
def send_static(filename):
    return send_from_directory('static', filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return member.register()
    if 'id' in session:
        return redirect(url_for('main'))
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    # remove the id from the session if it's there
    session.pop('id', None)
    return redirect(url_for('login'))

@app.route('/member/<path:path>', methods=['GET', 'POST'])
def member_api(path):
    print 'Request path: %s' % path
    if request.method == 'GET':
        session_check('api')
        if path == 'api/v1/me/info':
            return member.get_my_info()
        # API GET: /member/api/v1/friends/me
        elif path == 'api/v1/friends/me':
           return member.get_my_friends()
        # API GET: /member/api/v1/frineds/common-friends
        elif path == 'api/v1/friends/common-friends':
            return member.get_common_friends()
        # API GET: /member/api/v1/friends/common-likes/users
        elif path == 'api/v1/friends/common-likes/users':
            return member.get_common_likes_users()
        # API GET: /member/pi/v1/frineds/common-likes?other_id=x
        elif path == 'api/v1/friends/common-likes':
            # params: other_id
            return member.get_common_likes()
        else:
            raise InvalidUsage("Wrong URL", 404)
    elif request.method == 'POST':
        session_check('api')
        # API TODO POST- update user info
        if path == 'api/v1/me/update-info':
            pass
        else:
            raise InvalidUsage("Wrong URL", 404)
    else:
        raise InvalidUsage("Something Wrong.", 404)

@app.route('/diary/<path:path>', methods=['GET', 'POST'])
def diary_api(path):
    print 'Request path: %s' % path
    if request.method == 'GET':
        session_check('api')
        # API GET: /diary/api/v1/get?id=x
        if path == 'api/v1/get':
           return diary.get_all_diary()
        else:
            raise InvalidUsage("Wrong URL", 404)
    elif request.method == 'POST':
        session_check('api')
        # API POST: /diary/api/v1/create
        if path == 'api/v1/create':
            return diary.create()
        else:
            raise InvalidUsage("Wrong URL", 404)
    else:
        raise InvalidUsage("Something Wrong.", 404)


@app.route('/member/<path:path>', methods=['GET'])
def member_API(path):
    print 'Request path: %s' % path
    if request.method == 'GET':
        # API GET: /member/api/v1/get?id=x
        session_check('api')
        if path == 'api/v1/get':
            return member.get_nearby_member()

        else:
            raise InvalidUsage("Wrong URL", 404)
    else:
        raise InvalidUsage("Something Wrong.", 404)


# @app.route('/pair/<path:path>', methods=['GET', 'POST'])
# def pair_API(path):
#     print 'Request path: %s' % path
#     if request.method == 'GET':
#         # session_check('api')  # when online uncomment this.
#         # API GET: /pair/api/v1/get?id=x
#         if path == 'api/v1/get':
#            return pair.get_all_diary()
#         else:
#             raise InvalidUsage("Wrong URL", 404)
#     elif request.method == 'POST':
#         # API POST: /pair/api/v1/create
#         if path == 'api/v1/create':
#             return pair.create()
#         else:
#             raise InvalidUsage("Wrong URL", 404)
#     else:
#         raise InvalidUsage("Something Wrong.", 404)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    if error.get_error_type() == 'redirectToLoginPage':
        return redirect(url_for('login'))
    else:
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

def session_check(request_type):
    # request_type only will be api or render_page.
    if request_type == 'api':
        if 'id' not in session:
            raise InvalidUsage("unauthorized", 401)
    elif request_type == 'render_page':
        if 'id' not in session:
            raise InvalidUsage(None, None, None, "redirectToLoginPage")
