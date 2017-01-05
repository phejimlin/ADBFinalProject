from py2neo import Graph, Node, Relationship
from passlib.hash import bcrypt
from datetime import datetime
import os
import uuid

url = os.environ.get('GRAPHENEDB_URL', 'http://localhost:7474')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')

graph = Graph(url + '/db/data/', username=username, password=password)

class User:
    def __init__(self, name, email, gender, fb_id, access_token, portrait):
        self.name = name
        self.email = email
        self.gender = gender
        self.fb_id = fb_id
        self.access_token = access_token
        self.portrait = portrait

    @staticmethod
    def find(fb_id):
        user = graph.find_one('User', 'fb_id', fb_id)
        return user

    @staticmethod
    def get_id(fb_id):
        query = '''
        MATCH (n:User {fb_id : {fb_id}}) RETURN n.id as id
        '''
        return graph.run(query, fb_id=fb_id).evaluate()

    @staticmethod
    def register(name, email, gender, fb_id, access_token, portrait):
        user = User.find(fb_id)
        if not user:
            id = str(uuid.uuid1())
            query = '''
            CREATE (u:User {id: {id}, name: {name}, email: {email}, gender: {gender}, fb_id: {fb_id}, access_token: {access_token}, portrait: {portrait}})
            RETURN u.id
            '''
            return graph.run(query, id=id, name=name, email=email, gender=gender, fb_id=fb_id, access_token=access_token, portrait=portrait).evaluate()
        elif 'id' not in user:
            print 'Giving user an ID'
            id = str(uuid.uuid1())
            query = '''
            MATCH (u:User) WHERE u.fb_id = {fb_id}
            SET u.id= {id}, u.name= {name}, u.email= {email}, u.gender= {gender}, u.fb_id= {fb_id}, u.access_token= {access_token}, u.portrait= {portrait}
            RETURN u.id
            '''
            return graph.run(query, id=id, name=name, email=email, gender=gender, fb_id=fb_id, access_token=access_token, portrait=portrait).evaluate()
        else:
            return False

    @staticmethod
    def user_info(uid):
        user = graph.find_one('User', 'id', uid)
        return user

    @staticmethod
    def update_user_info(uid):
        user = graph.find_one('User', 'id', uid)
        return user

    @staticmethod
    def add_fb_likes(uid, likes):
        user = graph.find_one('User', 'id', uid)
        for like in likes:
            rel = Relationship(user, 'LIKE', Node('Likes', name=like['name'], id=like['id']))
            graph.merge(rel)

    @staticmethod
    def add_fb_friends(uid, friends):
        user = graph.find_one('User', 'id', uid)
        for friend in friends:
            rel = Relationship(user, 'FRIEND', Node('User', name=friend['name'], fb_id=friend['id']))
            graph.merge(rel)

    @staticmethod
    def get_my_friends(uid):
        query = '''
        MATCH (n:User {id:{uid}}) - [r] - (u:User)
        WITH DISTINCT(u) as friends
        RETURN friends.id as id, friends.name as name, friends.gender as gender, friends.portrait as portrait, friends.nickname as nickname
        '''
        return graph.run(query, uid=uid).data()

    @staticmethod
    def get_friends_of_friends(uid):
        query = '''
        MATCH (n:User {id:{uid}}) -[r:FRIEND]- (u:User) - [r2:FRIEND] - (v)
        where NOT (n) - [:FRIEND] - (v) AND NOT (n) = (v)
        with DISTINCT v as friends_of_friends
        RETURN friends_of_friends.id as id, friends_of_friends.name as name, friends_of_friends.gender as gender, friends_of_friends.portrait as portrait, friends_of_friends.nickname as nickname
        '''
        return graph.run(query, uid=uid).data()

    @staticmethod
    def get_common_likes_users(uid):
        query = '''
        MATCH (n:User {id:{uid}}) - [:LIKE] - (k) - [:LIKE]- (v:User)
        return v.gender as gender, v.name as name, v.portrait as portrait, v.id as id, count(k) as amount_of_common_likes
        '''
        return graph.run(query, uid=uid).data()

    @staticmethod
    def get_common_likes(uid, other_uid):
        query = '''
        MATCH (n:User {id:{uid}}) - [:LIKE] - (k) - [:LIKE]- (v:User {id:{other_uid}}) return k as common_likes
        '''
        return graph.run(query, uid=uid, other_uid=other_uid).data()

    def add_post(self, title, tags, text):
        user = self.find()
        post = Node(
            'Post',
            id=str(uuid.uuid4()),
            title=title,
            text=text,
            timestamp=timestamp(),
            date=date()
        )
        rel = Relationship(user, 'PUBLISHED', post)
        graph.create(rel)

        tags = [x.strip() for x in tags.lower().split(',')]
        for name in set(tags):
            tag = Node('Tag', name=name)
            graph.merge(tag)

            rel = Relationship(tag, 'TAGGED', post)
            graph.create(rel)

    def like_post(self, post_id):
        user = self.find()
        post = graph.find_one('Post', 'id', post_id)
        graph.merge(Relationship(user, 'LIKED', post))

    def get_similar_users(self):
        # Find three users who are most similar to the logged-in user
        # based on tags they've both blogged about.
        query = '''
        MATCH (you:User)-[:PUBLISHED]->(:Post)<-[:TAGGED]-(tag:Tag),
              (they:User)-[:PUBLISHED]->(:Post)<-[:TAGGED]-(tag)
        WHERE you.username = {username} AND you <> they
        WITH they, COLLECT(DISTINCT tag.name) AS tags
        ORDER BY SIZE(tags) DESC LIMIT 3
        RETURN they.username AS similar_user, tags
        '''

        return graph.run(query, username=self.username)

    def get_commonality_of_user(self, other):
        # Find how many of the logged-in user's posts the other user
        # has liked and which tags they've both blogged about.
        query = '''
        MATCH (they:User {username: {they} })
        MATCH (you:User {username: {you} })
        OPTIONAL MATCH (they)-[:PUBLISHED]->(:Post)<-[:TAGGED]-(tag:Tag),
                       (you)-[:PUBLISHED]->(:Post)<-[:TAGGED]-(tag)
        RETURN SIZE((they)-[:LIKED]->(:Post)<-[:PUBLISHED]-(you)) AS likes,
               COLLECT(DISTINCT tag.name) AS tags
        '''

        return graph.run(query, they=other.username, you=self.username).next

    @staticmethod
    def update_location(uid, lat, lon):
        query = '''
        MATCH (u) WHERE u.id = {which}
        SET u.wkt = {wkt},
        u.latitude = {lat},
        u.longitude = {lon},
        WITH u AS u
        CALL spatial.addNode('member', u) YIELD node
        RETURN COUNT(node)
        '''
        return graph.run(query, which=uid, wkt=lon_lat_to_wkt(lon, lat), lat=lat, lon=lon)

    @staticmethod
    def get_nearby_member(uid, distance_km):
        user = graph.find_one('User', 'id', uid)
        query = '''
        CALL spatial.withinDistance('member',
        {latitude: {lat}, longitude: {lon}}, {distance}) YIELD node AS m
        MATCH (m) WHERE m.id <> {id}
        RETURN m.gender as gender, m.name as name, m.portrait as portrait, m.id as id, m.nickname as nickname
        '''
        return graph.run(query, lat=user['latitude'], lon=user['longitude'], distance=distance_km, id=uid)

def get_todays_recent_posts():
    query = '''
    MATCH (user:User)-[:PUBLISHED]->(post:Post)<-[:TAGGED]-(tag:Tag)
    WHERE post.date = {today}
    RETURN user.username AS username, post, COLLECT(tag.name) AS tags
    ORDER BY post.timestamp DESC LIMIT 5
    '''

    return graph.run(query, today=date())

def timestamp():
    epoch = datetime.utcfromtimestamp(0)
    now = datetime.now()
    delta = now - epoch
    return delta.total_seconds()

def date():
    return datetime.now().strftime('%Y-%m-%d')

def lon_lat_to_wkt(lon, lat):
    return 'POINT (' + str(lon) + ' ' + str(lat) + ')'

def wkt_to_lat_long(wkt):
    lon = float(wkt[wkt.find('(') + 1: wkt.find(' ', beg=wkt.find('('))])
    lat = float(wkt[wkt.find(' ', beg=wkt.find('(')) + 1: -1])
    return lat, lon

class Diary(object):
    """docstring for diary"""
    def __init__(self, owner_id):
        super(Diary, self).__init__()
        self.owner_id = owner_id

    @staticmethod
    def get_owner(owner_id):
        user = graph.find_one('User', 'id', owner_id)
        return user

    @staticmethod
    def get_all_diary(owner_id):
        query = '''
        MATCH (n:User) - [:PUBLISHED] - (D)
        where n.id={id}
        RETURN D as Diary
        ORDER BY Diary.timestamp DESC
        '''
        return graph.run(query, id=owner_id)

    @staticmethod
    def get_friends_diary(uid, timestamp):
        query = '''
        MATCH (:User {id:{uid}})- [:FRIEND] - (friend:User) - [:PUBLISHED]->(diary:Diary)
        WHERE diary.timestamp <= {timestamp} and diary.permission <> 'private'
        RETURN diary, {gender: friend.gender, name: friend.name, portrait: friend.portrait, id: friend.id} as friend
        ORDER BY diary.timestamp DESC LIMIT 20
        '''
        return graph.run(query, uid=uid, timestamp=timestamp)

    @staticmethod
    def add_diary(owner_id, title, content, latitude, longitude, category, location, address, permission):
        user = Diary.get_owner(owner_id)
        uuid_diary = str(uuid.uuid1())
        diary = Node(
            'Diary',
            id=uuid_diary,
            title=title,
            content=content,
            timestamp=timestamp(),
            date=date(),
            latitude=latitude,
            longitude=longitude,
            wkt=lon_lat_to_wkt(longitude, latitude),
            category=category,
            location=location,
            address=address,
            permission=permission
        )
        rel = Relationship(user, 'PUBLISHED', diary)
        graph.create(rel)

        query = '''
        MATCH (d:Diary) WHERE d.id = {which}
        CALL spatial.addNode('diary', d) YIELD node
        RETURN count(node)
        '''

        result = str(graph.run(query, which=uuid_diary).evaluate())
        if result != '1':
            print "spatial addNode error!" + result

        return ('', 200)

    @staticmethod
    def get_nearby_diary(uid, distance_km):
        user = graph.find_one('User', 'id', uid)
        query = '''
        CALL spatial.withinDistance('diary',
        {latitude: {lat}, longitude: {lon}}, {distance}) YIELD node AS d
        MATCH (d2:Diary)-[r:PUBLISHED]-(m:User)
        WHERE m.id <> {id}
        RETURN d2
        '''
        # TODO what to return?
        return graph.run(query, lat=user['latitude'], lon=user['longitude'], distance=distance_km, id=uid)
