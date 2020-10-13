import configparser
import json
import time
import string
from datetime import datetime
from py2neo import *
from connector.neo4j import query_neo4j
from neo4j.v1 import SessionError
import requests
import sys
import re
from tulip import *

from pprint import pprint

config = configparser.ConfigParser()
config.read("config.ini")

def cleanString(s):
#    s=s.replace("\n", "<br>")
    try:
        s=s.replace("\r", "")
    except Exception as inst:
        print(inst)
#    return s.replace("\\","")
    return s

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

class ImportFromDiscourse(object):
    verbose = False
    unmatch_post_user = 0
    unmatch_comment_user = 0
    unmatch_comment_post = 0
    unmatch_comment_parent = 0
    unmatch_tag_parent = 0
    unmatch_annotation_user = 0
    unmatch_annotation_tag = 0
    unmatch_annotation_tag_open = 0
    unmatch_annotation_entity = 0

    def __init__(self, erase=False, debug=False):
        super(ImportFromDiscourse, self).__init__()
        print('Initializing')
        self.neo4j_graph = Graph(
            host=config['neo4j']['url'],
            http_port=int(config['neo4j']['http_port']),
            bolt_port=int(config['neo4j']['bolt_port']),
            user=config['neo4j']['user'],
            password=config['neo4j']['password']
        )
        if erase:
            self.neo4j_graph.delete_all()
        ImportFromDiscourse.verbose=debug
        self.tags = {}
        self.users = {}
#        self.existing_elements = {'users': {}, 'posts': {}, 'comments': {}, 'annotations': {}, 'tags': {}}
        self.existing_elements = {'users': [], 'posts': [], 'comments': [], 'annotations': [], 'tags': []}
#        self.graph = tlp.newGraph()
        self.unavailable_users_id = []
        self.unavailable_posts_id = []
        self.unavailable_comments_id = []
        self.unavailable_tags_id = []
        self.map_tag_to_tag = {}


    def createUser(self, id, label, avatar):
        user_node = Node('user')
        user_node['user_id'] = id
        user_node['label'] = cleanString(label)
        user_node['avatar'] = config['importer_discourse']['abs_path']+avatar
        user_node['url'] = config['importer_discourse']['abs_path']+config['importer_discourse']['user_rel_path']+label
        try:
            self.neo4j_graph.merge(user_node)
        except ConstraintError:
            if ImportFromDiscourse.verbose:
                print("WARNING: user id "+str(user_node['user_id'])+" already exists")

#        idp = self.graph.getIntegerProperty('id')
#        labelp = self.graph.getStringProperty('label')
#        typep = self.graph.getStringProperty('type')
#        avatarp = self.graph.getStringProperty('avatar')
#        n = self.graph.addNode()
#        idp[n] = id
#        labelp[n] = label
#        typep[n] = 'user'
#        avatarp[n] = avatar
#        return n


    def create_users(self):
        query_neo4j("CREATE CONSTRAINT ON (n:user) ASSERT n.user_id IS UNIQUE")

        print('Import users')
        Continue = True
        page_val = 0
        while Continue:
            user_url = config['importer_discourse']['abs_path']+config['importer_discourse']['users_rel_path']+".json?api_key="+config['importer_discourse']['admin_api_key']+"&page="+str(page_val)
            # The Discource consent.json API requires an "Accept:application/json" header. This requirement
            headers = {'User-Agent': config['importer_discourse']['user_agent'], 'Api-Key': config['importer_discourse']['admin_api_key'], 'Accept': 'application/json'}
            not_ok = True
            print('user_url = ' + user_url)
            while not_ok:
                try:
                    user_req = requests.get(user_url, headers=headers)
                except:
                    print('request problem on user page '+str(page_val))
                    continue
                try:
                    user_json = user_req.json()
                except:
                    print("failed read user on page "+str(page_val))
                    continue
                not_ok = False

            # get all users
            for user in user_json:
                # create tag if not existing
                if not(user['id'] in self.users):
                    if (config['importer_discourse']['ensure_consent'] == "0"):
                        self.users[user['id']] = user['username']
                        print(user['username'] + ' added to self.users')
                    else:
                        if (user['edgeryders_consent']=="1"):
                            self.users[user['id']] = user['username']

            if len(user_json) == 100:
                page_val += 1
            else:
                Continue = False
                break


    def createContent(self, id, type, label, content, timestamp, url):
        content_node = Node(type)
        content_node[type+'_id'] = id
        content_node['label'] = cleanString(label)
        content_node['title'] = cleanString(label)
        content_node['content'] = cleanString(content)
        timestamp = (timestamp[0:23]+'000')
        content_node['timestamp'] = int(time.mktime(datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f").timetuple()) * 1000)
        content_node['url'] = config['importer_discourse']['abs_path']+config['importer_discourse']['topic_rel_path']+cleanString(url)
        try:
            self.neo4j_graph.merge(content_node)
        except ConstraintError:
            if ImportFromDiscourse.verbose:
                print("WARNING: "+type+" id "+str(content_node[type+'_id'])+" already exists")
#        idp = self.graph.getIntegerProperty('id')
#        labelp = self.graph.getStringProperty('label')
#        contentp = self.graph.getStringProperty('content')
#        typep = self.graph.getStringProperty('type')
#        timestampp = self.graph.getDoubleProperty('timestamp')
#        n = self.graph.addNode()
#        idp[n] = id
#        labelp[n] = label
#        contentp[n] = content
#        typep[n] = type
#        timestamp = (timestamp[0:23]+'000')
#        timestampp[n] = int(time.mktime(datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f").timetuple()) * 1000)
#        return n


    def create_posts(self, id, title):
        query_neo4j("CREATE CONSTRAINT ON (p:post) ASSERT p.post_id IS UNIQUE")
        ImportFromDiscourse.unmatch_post_user = 0
        ImportFromDiscourse.unmatch_comment_post = 0
#        idp = self.graph.getIntegerProperty('id')
#        labelp = self.graph.getStringProperty('label')
#        typep = self.graph.getStringProperty('type')

        # get list of posts from topic
        post_url = config['importer_discourse']['abs_path']+config['importer_discourse']['topic_rel_path']+str(id)+".json"
        headers = {'Api-Key': config['importer_discourse']['admin_api_key']}
        not_ok = True
        while not_ok:
            try:
                post_req = requests.get(post_url, headers=headers)
            except:
                print('request problem on topic '+str(id))
                time.sleep(2)
                continue
            try:
                post_json = post_req.json()
                if 'error_type' in post_json.keys() and (post_json['error_type'] == 'rate_limit'):
                    print('rate limit hit during import of topic ' + str(id) + ', sleeping for 60 seconds')
                    time.sleep(60)
                    continue
            except:
                print("failed read on topic "+str(id))
                post_json = []
                time.sleep(2)
                continue
            print('topic ' + str(id) + ' read')
            not_ok = False
        edgeToCreate = []
        commentList = {}

        index_post = 0
        # create all elements
        for comment_id in post_json['post_stream']['stream']:
            #print(str(len(post_json['post_stream']['stream'])) +' : '+str(i)+' '+str(comment_id))
            if index_post >= len(post_json['post_stream']['posts']):
            # if comment resume is unavailable (not one of the first 20 posts)
                comment_url = config['importer_discourse']['abs_path']+config['importer_discourse']['posts_rel_path']+str(comment_id)+".json"
                not_ok = True
                while not_ok:
                    try:
                        comment_req = requests.get(comment_url, headers=headers)
                    except:
                        print('request problem on post '+str(comment_id))
                        time.sleep(2)
                        continue
                    try:
                        comment = comment_req.json()
                        if 'error_type' in comment.keys() and (post_json['error_type'] == 'rate_limit'):
                            print('rate limit hit during import of post ' + str(comment_id) + ', sleeping for 60 seconds')
                            time.sleep(60)
                            continue
                        print('read post ' + str(comment_id) + ' by ' + str(comment['username']))
                    except:
                        print("failed read on post "+str(comment_id))
                        time.sleep(2)
                        continue
                    not_ok = False
    #            time.sleep(1)
            else:
            # else get available resume
                comment = post_json['post_stream']['posts'][index_post]
                print('read post ' + str(comment_id) + ' by ' + str(comment['username']))

            if not(comment['user_id'] in self.users):
            # author of the piece of content has not given the authorisation to publish it
                print(str(comment['username']) + ' is not in self.users')
                continue

            commentList[comment['post_number']] = comment['id']
            if index_post == 0:
            # first 'comment' of the topic is the main post
                type = 'post'
                self.createContent(comment['id'], type, title, comment['cooked'], comment['created_at'], str(comment['topic_id'])+'/'+str(comment['post_number']))
#                self.existing_elements['posts'][comment['id']] = post_n
                self.existing_elements['posts'].append(comment['id'])
#                self.existing_elements['comments'][comment['id']] = post_n
                self.existing_elements['comments'].append(comment['id'])
#                comment_n = post_n
                id = comment['id']

            else:
            # check as a comment
                type = 'comment'
                # extract the title
                tmp = comment['cooked'].split('</b></p>\n\n')
                if len(tmp) > 1:
                    label = tmp[0][6:]
                    content = tmp[1]
                    for tmp_content in tmp[2:]:
                        content+='</b></p>\n\n'+tmp_content
                else:
                    tmp = clean_html(comment['cooked']).split(" ")
                    label = ""
                    for j in range(min(8, len(tmp))):
                        label += tmp[j] + " "
                    content = comment['cooked']
                # replace relative url
                content = content.replace('href=\"//', 'target=\"_blank\" href=\"https://')
                content = content.replace('href=\"/', 'target=\"_blank\" href=\"'+config['importer_discourse']['abs_path'])
                content = content.replace('src=\"//', 'src=\"https://')
                content = content.replace('src=\"/', 'src=\"'+config['importer_discourse']['abs_path'])

                self.createContent(comment['id'], type, label, content, comment['created_at'], str(comment['topic_id'])+'/'+str(comment['post_number']))
#                self.existing_elements['comments'][comment['id']] = comment_n
                self.existing_elements['comments'].append(comment['id'])

                # response to a comment
                if not(comment['reply_to_post_number'] is None):
                    #reply_id = comment['reply_to_post_number']
                    #print("post " + str(id) + " reply from " + str(comment['id']) + " to "+ str( post_json['post_stream']['stream'][reply_id]))
                    edgeToCreate.append([comment['id'], comment['reply_to_post_number']])
                else:
                # direct response to post
                    edgeToCreate.append([comment['id'], 1])

            # link with author
            if not(comment['user_id'] in self.existing_elements['users']):
                self.createUser(comment['user_id'], comment['username'], comment['avatar_template'])
#                self.existing_elements['users'][comment['user_id']] = user_n
                self.existing_elements['users'].append(comment['user_id'])
#            self.graph.addEdge(self.existing_elements['users'][comment['user_id']], comment_n)
            try :
                req = "MATCH (e:%s { %s_id : %d })" % (type, type, comment['id'])
                req += " MATCH (u:user { user_id : %s })" % comment['user_id']
                req += " CREATE UNIQUE (u)-[:AUTHORSHIP]->(e) RETURN u"
                query_neo4j(req).single()
            except ResultError:
                if ImportFromDiscourse.verbose:
                    print("WARNING : %s id %d has no author user_id %s" % (type, comment['id'], comment['user_id']))
                ImportFromDiscourse.unmatch_post_user+=1
                query_neo4j("MATCH (p:%s {%s_id : %s}) DETACH DELETE p" % (type, type, comment['id']))
                self.unavailable_users_id.append(comment['user_id'])

            # build timetree
            if 'timestamp' in comment:
            # TimeTree
                timestamp = (comment['timestamp'][0:23]+'000')
                timestamp = int(time.mktime(datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f").timetuple()) * 1000)
                req = "MATCH (p:%s { %s_id : %d }) WITH p " % (type, type, post_node['post_id'])
                req += "CALL ga.timetree.events.attach({node: p, time: %s, relationshipType: 'POST_ON'}) " % timestamp
                req += "YIELD node RETURN p"
                query_neo4j(req)

            # link betwixt comment and post
            if index_post > 0:
#                self.graph.addEdge(self.existing_elements['comments'][comment['id']], self.existing_elements['comments'][commentList[1]])
                try:
                    req = "MATCH (c:comment { comment_id : %d }) " % comment['id']
                    req += "MATCH (p:post { post_id : %s }) " % commentList[1]
                    req += "CREATE UNIQUE (c)-[:COMMENTS]->(p) RETURN p"
                    query_neo4j(req).single()
                except ResultError:
                    if ImportFromDiscourse.verbose:
                        print("WARNING : comment %d has no post parent %s" % (comment['id'], commentList[1]))
                    ImportFromDiscourse.unmatch_comment_post+=1
                    query_neo4j("MATCH (c:comment {comment_id : %s}) DETACH DELETE c" % comment['id'])

            index_post+=1

        # add edges between comments
        for e in edgeToCreate:
            if not(e[1] in commentList):
            # ignore bad mapping and link back to root post instead
                print("bad mapping: from "+str(e[0])+" to "+str(e[1])+" for thread "+str(id)+" ("+title+") and post "+str(comment_id))
                e[1] = 1
            if e[1] == 1:
                continue

            try:
                req = "MATCH (c1:comment { comment_id : %d }) " % e[0]
                req += "MATCH (c2:comment { comment_id : %d }) " % commentList[e[1]]
                req += "CREATE UNIQUE (c1)-[:COMMENTS]->(c2) RETURN c2"
                query_neo4j(req).single()
            except ResultError:
                if ImportFromDiscourse.verbose:
                    print("WARNING : comment %d has no parent %d" % (e[0], commentList[e[1]]))
                query_neo4j("MATCH (c:comment {comment_id : %s}) DETACH DELETE c" % commentList[e[1]])
                ImportFromDiscourse.unmatch_comment_post+=1
                if e[1] not in self.unavailable_posts_id:
                    self.unavailable_posts_id.append(e[1])


    def createTag(self, id, label):
        tag_node = Node('tag')
        tag_node['tag_id'] = id
        tag_node['label'] = cleanString(label)
        tag_node['name'] = cleanString(label)
        try:
            self.neo4j_graph.merge(tag_node)
        except ConstraintError:
            if ImportFromDiscourse.verbose:
                print("WARNING: tag id "+str(tag_node['tag_id'])+" already exists")
#        idp = self.graph.getIntegerProperty('id')
#        labelp = self.graph.getStringProperty('label')
#        typep = self.graph.getStringProperty('type')
#        n = self.graph.addNode()
#        idp[n] = id
#        labelp[n] = label
#        typep[n] = 'tag'
#        return n


    def create_tags(self):
        query_neo4j("CREATE CONSTRAINT ON (t:tag) ASSERT t.tag_id IS UNIQUE")
        print('Import tags')
        Continue = True
        page_val = 0
        while Continue:
            tag_url = config['importer_discourse']['abs_path']+config['importer_discourse']['codes_rel_path']+".json?per_page=5000&page="+str(page_val)
            headers = {'Api-Key': config['importer_discourse']['admin_api_key']}
            not_ok = True
            while not_ok:
                try:
                    tag_req = requests.get(tag_url, headers=headers)
                except:
                    print('request problem on tag page '+str(page_val))
                    time.sleep(2)
                    continue
                try:
                    tag_json = tag_req.json()
                except:
                    print("failed read tag on page "+str(page_val))
                    time.sleep(2)
                    continue
                not_ok = False

            # get all tags
            for tag in tag_json:
                # create tag if not existing
                if not(tag['id'] in self.existing_elements['tags']):

                    # Use the English code name if available, otherwise the first code name.
                    english_name = next((tag_name['name'] for tag_name in tag['names'] if tag_name['locale'] == 'en'), '')
                    tag['name'] = tag['names'][0]['name'] if english_name == '' else english_name

                    if not(tag['name'].lower() in self.tags):
                        self.createTag(tag['id'], tag['name'].lower())
                        self.map_tag_to_tag[tag['id']] = tag['id']
                        self.tags[tag['name'].lower()] = tag['id']
                    else:
                    # if duplicate using mapping
#                        tag_n = self.existing_elements['tags'][self.tags[tag['name'].lower()]]
                        self.map_tag_to_tag[tag['id']] = self.tags[tag['name'].lower()]
#                    self.existing_elements['tags'][tag['id']] = tag_n
                    self.existing_elements['tags'].append(tag['id'])

                # no need to create tag hierarchy as the route does not give ancestry info

            if len(tag_json) == 5000:
                page_val += 1
            else:
                Continue = False
                break


    def createAnnotation(self, id, quote, timestamp):
        annotation_node = Node('annotation')
        annotation_node['annotation_id'] = id
        annotation_node['quote'] = cleanString(quote)
        timestamp = (timestamp[0:23]+'000')
        annotation_node['timestamp'] = int(time.mktime(datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f").timetuple()) * 1000)
        self.neo4j_graph.merge(annotation_node)

#        idp = self.graph.getIntegerProperty('id')
#        quotep = self.graph.getStringProperty('quote')
#        typep = self.graph.getStringProperty('type')
#        timestampp = self.graph.getDoubleProperty('timestamp')
#        n = self.graph.addNode()
#        idp[n] = id
#        quotep[n] = quote
#        typep[n] = 'annotation'
#        timestamp = (timestamp[0:23]+'000')
#        timestampp[n] = int(time.mktime(datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f").timetuple()) * 1000)
#        return n


    def create_annotations(self):
        query_neo4j("CREATE CONSTRAINT ON (a:annotation) ASSERT a.annotation_id IS UNIQUE")
        print('Import annotations')
        #json_annotations = json.load(open(config['importer']['json_annotations_path']))
        ImportFromDiscourse.unmatch_annotation_user = 0
        ImportFromDiscourse.unmatch_annotation_tag = 0
        ImportFromDiscourse.unmatch_annotation_entity = 0
        ImportFromDiscourse.unmatch_annotation_tag_req = 0
        ImportFromDiscourse.unmatch_annotation_entity_req = 0
        Continue = True
        page_val = 0
        while Continue:
        # get pages of 1000 annotations
            ann_url = config['importer_discourse']['abs_path']+config['importer_discourse']['annotations_rel_path']+".json?discourse_tag="+config['importer_discourse']['tag_focus']+"&per_page=1000&page="+str(page_val)
            not_ok = True
            headers = {'Api-Key': config['importer_discourse']['admin_api_key']}
            while not_ok:
                try:
                    ann_req = requests.get(ann_url, headers=headers)
                except:
                    print('request problem on annotation page '+str(page_val))
                    time.sleep(2)
                    continue
                try:
                    ann_json = ann_req.json()
                except:
                    print("failed read annotation on page "+str(page_val))
                    time.sleep(2)
                    continue
                not_ok = False

            # get all annotations
            for annotation in ann_json:
                # only select annotations which link to existing posts and tags
                if annotation['post_id'] in self.existing_elements['comments']:
                    if not(annotation['code_id'] in self.map_tag_to_tag):
                        if not(str(annotation['code_id']) in self.unavailable_tags_id):
                            self.unavailable_tags_id.append(str(annotation['code_id']))
                        ImportFromDiscourse.unmatch_annotation_tag +=1
                        continue
###
#                        if not(annotation['tag_id'] in self.tags):
#                            tag_n = self.createTag(annotation['tag_id'], str(annotation['tag_id']))
#                        else:
#                            tag_n = self.existing_elements['tags'][self.tags[annotation['tag_id']]]
#                        self.existing_elements['tags'][annotation['tag_id']] = tag_n
#                        self.tags[annotation['tag_id']] = annotation['tag_id']
###

                    if not(annotation['post_id'] in self.existing_elements['comments']):
                        if not(str(annotation['post_id']) in self.unavailable_comments_id):
                            self.unavailable_comments_id.append(str(annotation['post_id']))
                        ImportFromDiscourse.unmatch_annotation_entity +=1
                        continue
###
#                        type = 'post'
#                        post_n = self.createContent(annotation['post_id'], 'other', "NOTHING", "MISSING CONTENT", "1971-01-01T00:00:01.000Z", str(annotation['post_id'])+'/'+str(0))
#                        self.existing_elements['posts'][annotation['post_id']] = post_n
#                        self.existing_elements['comments'][annotation['post_id']] = post_n
###

                    annotation_n = self.createAnnotation(annotation['id'], annotation['quote'], annotation['created_at'])
                    # link annotation to tag
#                    self.graph.addEdge(annotation_n, self.existing_elements['tags'][annotation['code_id']])
                    try:
                        req = "MATCH (a:annotation { annotation_id : %d }) " % annotation['id']
                        req += "MATCH (t:tag { tag_id : %s }) " % self.map_tag_to_tag[annotation['code_id']]
                        req += "CREATE UNIQUE (a)-[:REFERS_TO]->(t) RETURN t"
                        query_neo4j(req).single()
                    except ResultError:
                        if ImportFromDiscourse.verbose:
                            print("WARNING : annotation %d has no corresponding tag %s (image of %s)" % (annotation['id'], annotation['code_id'], self.map_tag_to_tag[annotation['code_id']]))
                        ImportFromDiscourse.unmatch_annotation_tag_req +=1
                        if not(str(annotation['code_id']) in self.unavailable_tags_id):
                            self.unavailable_tags_id.append(str(annotation['code_id']))
                        query_neo4j("MATCH (a:annotation {annotation_id : %s}) DETACH DELETE a" % annotation['id'])
                        continue
                    # link to content
                    type = 'comment'
                    if  annotation['post_id'] in self.existing_elements['posts']:
                        type = 'post'
#                    self.graph.addEdge(annotation_n, self.existing_elements['comments'][annotation['post_id']])
                    try:
                        req = "MATCH (a:annotation { annotation_id : %d }) " % annotation['id']
                        req += "MATCH (e:%s { %s_id : %s }) " % (type, type, annotation['post_id'])
                        req += "CREATE UNIQUE (a)-[:ANNOTATES]->(e) RETURN e"
                        query_neo4j(req).single()
                    except ResultError:
                        if ImportFromDiscourse.verbose:
                            print("WARNING : annotation %d has no corresponding %s id %s" % (annotation['id'], type, annotation['post_id']))
                        ImportFromDiscourse.unmatch_annotation_entity_req +=1
                        query_neo4j("MATCH (a:annotation {annotation_id : %s}) DETACH DELETE a" % annotation['id'])
                        continue
                    # link to creator
                    #if annotation['creator_id'] in self.existing_elements['users']:
                    #    self.graph.addEdge(annotation_n, self.existing_elements['users'][annotation['creator_id']])
                    #    try:
                    #        req = "MATCH (a:annotation { annotation_id : %d }) " % annotation['id']
                    #        req += "MATCH (u:user { user_id : %s }) " % annotation['creator_id']
                    #        req += "CREATE UNIQUE (u)-[:AUTHORSHIP]->(a) RETURN u"
                    #        query_neo4j(req).single()
                    #    except ResultError:
                    #        if ImportFromDiscourse.verbose:
                    #            print("WARNING : annotation id %d has no author id %s" % (annotation['id'], annotation['creator_id']))
                    #        ImportFromDiscourse.unmatch_annotation_user+=1
                    #        query_neo4j("MATCH (a:annotation {annotation_id : %s}) DETACH DELETE a" % annotation['id'])
                    #        if annotation['creator_id'] not in self.unavailable_users_id:
                    #            self.unavailable_users_id.append(annotation['creator_id'])
                    #else:
                    #    self.unavailable_users_id.append(str(annotation['creator_id']))
                    #    print("Unknown creator "+str(annotation['creator_id'])+" for annotation "+str(annotation['id'])+" on registered post "+str(annotation['post_id']))

            if len(ann_json) == 1000:
                page_val += 1
            else:
                Continue = False
                break


    def end_import(self):

        #tlp.saveGraph(self.graph, "/usr/src/myapp/discourse.tlpb")
        response = {'users': self.unavailable_users_id, "posts": self.unavailable_posts_id, 'comments': self.unavailable_comments_id, "tags":  self.unavailable_tags_id}
        print(response)
        print(" unmatch post -> (user): ", ImportFromDiscourse.unmatch_post_user,"\n",
        "unmatch comment -> (user): ", ImportFromDiscourse.unmatch_comment_user,"\n",
        "unmatch comment -> (post): ", ImportFromDiscourse.unmatch_comment_post,"\n",
        "unmatch comment -> (parent): ", ImportFromDiscourse.unmatch_comment_parent,"\n",
        "unmatch code -> (parent): ", ImportFromDiscourse.unmatch_tag_parent,"\n",
        "unmatch annotation -> (user): ", ImportFromDiscourse.unmatch_annotation_user,"\n",
        "unmatch annotation -> (code): ", ImportFromDiscourse.unmatch_annotation_tag,"\n",
        "unmatch req annotation -> (code): ", ImportFromDiscourse.unmatch_annotation_tag_req,"\n",
        "unmatch annotation -> (entity): ", ImportFromDiscourse.unmatch_annotation_entity,"\n"
        "unmatch req annotation -> (entity): ", ImportFromDiscourse.unmatch_annotation_entity_req,"\n")
        return response