from flask_restful import Resource, reqparse
from neo4j.v1 import SessionError
from connector import neo4j
from routes.utils import addargs, addTimeFilter, makeResponse
import datetime

from pprint import pprint

parser = reqparse.RequestParser()

class GetPost(Resource):
    def get(self, post_id):
        result = neo4j.query_neo4j("MATCH (find:post {post_id: %d}) RETURN find" % post_id)
        try:
            return makeResponse(result.single()['find'].properties, 200)
        except ResultError:
            return makeResponse("ERROR : Cannot find post with pid: %d" % post_id, 204)


class GetPostHydrate(Resource): # todo comments on comments (with author)
    def get(self, post_id):
        req = "MATCH (find:post {post_id: %d}) " % post_id
        req += "OPTIONAL MATCH (find)<-[:AUTHORSHIP]-(author:user) "
        req += "OPTIONAL MATCH (find)<-[:COMMENTS]-(comment:comment) "
        req += "OPTIONAL MATCH (comment)<-[:AUTHORSHIP]-(commentAuthor:user) "
        req += "RETURN find, author, comment, commentAuthor ORDER BY comment.timestamp DESC"
        result = neo4j.query_neo4j(req)
        comments = []
        author = None
        for record in result:
            post = record['find'].properties
            try:
                if record['author']:
                    author = record['author'].properties
                if record['comment']:
                    comment = record['comment'].properties
                    if record['commentAuthor']:
                        comment['author'] = record['commentAuthor'].properties
                    comments.append(comment)
            except KeyError:
                pass

        # annotations
        req = "MATCH (find:post {post_id: %d}) " % post_id
        req += "OPTIONAL MATCH (find)<-[:ANNOTATES]-(a:annotation) "
        req += "OPTIONAL MATCH (a)-[:REFERS_TO]->(t:tag) "
        req += "RETURN a.annotation_id as annotation_id, a.timestamp as annotation_timestamp, t.tag_id as tag_id, t.label as tag_label ORDER BY a.timestamp DESC"
        result = neo4j.query_neo4j(req)
        annotations = []
        annotations_id = []
        tags_id = []
        for record in result:
            annotation = {} 
            try:
                if record['tag_id'] and record['annotation_id'] not in annotations_id:
                    if record['annotation_id']:
                        annotation['annotation_id'] = record['annotation_id']
                    if record['annotation_timestamp']:
                        annotation['annotation_timestamp'] = record['annotation_timestamp']
                    if record['tag_id']:
                        annotation['tag_id'] = record['tag_id']
                    if record['tag_label']:
                        annotation['tag_label'] = record['tag_label']
                    annotations.append(annotation)
                    annotations_id.append(record['annotation_id'])
                    if record['tag_id'] not in tags_id:
                        tags_id.append(record['tag_id'])
            except KeyError:
                pass

        # innovations
        req = "MATCH (p: post {post_id: %d}) <-[:COMMENTS]- (c: comment) " %post_id
        req += "MATCH (c) <-[:ANNOTATES]-(a)-[:REFERS_TO]->(t: tag) "
        req += "RETURN t.tag_id as tag_id, t.label as tag_label, c.comment_id as comment_id, c.label as comment_label ORDER BY c.timestamp DESC"
        result = neo4j.query_neo4j(req)
        innovations = []
        for record in result:
            innovation = {} 
            try:
                if record['tag_id'] and record['tag_id'] not in tags_id:
                    if record['tag_id']:
                        innovation['tag_id'] = record['tag_id']
                    if record['tag_label']:
                        innovation['tag_label'] = record['tag_label']
                    if record['comment_id']:
                        innovation['comment_id'] = record['comment_id']
                    if record['comment_label']:
                        innovation['comment_label'] = record['comment_label']
                    innovations.append(innovation)
            except KeyError:
                pass

        try:
            post
        except NameError:
            return "ERROR : Cannot find post with pid: %d" % post_id, 200
        post['comments'] = comments
        post['author'] = author
        post['annotations'] = annotations
        post['innovations'] = innovations
        return makeResponse(post, 200)


class GetPosts(Resource):
    def get(self):
        req = "MATCH (p:post)<-[:AUTHORSHIP]-(u:user) RETURN p.post_id AS post_id, p.title AS title, p.content AS content, p.timestamp AS timestamp, u.user_id AS user_id"
        req += addargs()
        result = neo4j.query_neo4j(req)
        posts = []
        for record in result:
            fmt_time = datetime.datetime.fromtimestamp(record['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
            posts.append({'post_id': record['post_id'], "title": record['title'], "content": record["content"], "timestamp": fmt_time, "user_id": record["user_id"]})
        return makeResponse(posts, 200)

class GetPostsLatest(Resource):
    def get(self):
        req = "MATCH (p:post) <-[:AUTHORSHIP]- (u: user) RETURN p.post_id AS post_id,p.label AS post_label, u.user_id AS user_id, u.label AS user_label, p.timestamp AS timestamp ORDER BY timestamp DESC LIMIT 5"
        result = neo4j.query_neo4j(req)
        posts = []
        for record in result:
            posts.append({'post_id': record['post_id'], "post_label": record['post_label'], "user_id": record['user_id'], "user_label": record['user_label'], "timestamp": record['timestamp']})
        return makeResponse(posts, 200)


class GetPostsByType(Resource):
    def get(self, post_type):
        req = "MATCH (find:post {type: '%s'}) RETURN find" % post_type
        req += addargs()
        result = neo4j.query_neo4j(req)
        posts = []
        for record in result:
            posts.append(record['find'].properties)
        return makeResponse(posts, 200)


class GetPostsByAuthor(Resource):
    def get(self, author_id):
        req = "MATCH (author:user {user_id: %d})-[:AUTHORSHIP]->(p:post) RETURN p" % author_id
        req += addargs()
        result = neo4j.query_neo4j(req)
        posts = []
        for record in result:
            posts.append(record['p'].properties)
        return makeResponse(posts, 200)


class GetPostType(Resource):
    def get(self):
        parser.add_argument('uid', action='append')
        args = parser.parse_args()

        if args['uid']:
            req = "MATCH (n:post_type)<-[r:TYPE_IS]-(p:post) "
            req += addTimeFilter()
            for user in args['uid']:
                req += "OPTIONAL MATCH (n)<-[r%s:TYPE_IS]-(p:post)<-[]-(u%s:user {uid: %s}) " % (user, user, user)
            req += "RETURN n, count(r) AS nb_posts"
            for user in args['uid']:
                req += ", count(r%s) AS u%s_posts" % (user, user)
        else:
            req = "MATCH (n:post_type)<-[r:TYPE_IS]-(p:post) "
            req += addTimeFilter()
            req += "RETURN n, count(r) AS nb_posts"
        result = neo4j.query_neo4j(req)
        labels = []
        data = [[]]
        if args['uid']:
            for user in args['uid']:
                data.append([])
        for record in result:
            labels.append(record['n'].properties['name'])
            data[0].append(record['nb_posts'])
            if args['uid']:
                count = 1
                for user in args['uid']:
                    data[count].append(record['u%s_posts' % user])
                    count += 1
        return makeResponse({'labels': labels, 'data': data}, 200)
