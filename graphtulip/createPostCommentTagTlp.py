from tulip import *
from py2neo import *
import configparser
import os

config = configparser.ConfigParser()
config.read("config.ini")


# todo create a unique Createtlp to avoid code duplication
class CreatePostCommentTagTlp(object):
    def __init__(self, start, end, force_fresh):
        super(CreatePostCommentTagTlp, self).__init__()
        print('Initializing')

        self.neo4j_graph = Graph(
            "bolt://" + config['neo4j']['url'] + ':' + str(config['neo4j']['bolt_port']),
            user=config['neo4j']['user'],
            password=config['neo4j']['password']
        )
        self.tulip_graph = tlp.newGraph()
        self.tulip_graph.setName('opencare - PostCommentTag')
        # todo pass in parameters labels and colors
        self.labels = ["label", "label", "label"]
        self.colors = {"user_id": tlp.Color(51,122,183), "post_id": tlp.Color(92,184,92), "comment_id": tlp.Color(240, 173, 78), "tag_id": tlp.Color(200, 10, 10), "edges": tlp.Color(204, 204, 204)}
        self.date_start = start
        self.date_end = end
        self.force_fresh = force_fresh

    # -----------------------------------------------------------
    # the updateVisualization(centerViews = True) function can be called
    # during script execution to update the opened views

    # the pauseScript() function can be called to pause the script execution.
    # To resume the script execution, you will have to click on the "Run script " button.

    # the runGraphScript(scriptFile, graph) function can be called to launch another edited script on a tlp.Graph object.
    # The scriptFile parameter defines the script name to call (in the form [a-zA-Z0-9_]+.py)

    # the main(graph) function must be defined
    # to run the script on the current graph
    # -----------------------------------------------------------

    # Can be used with nodes or edges
    def managePropertiesEntity(self, entTlp, entN4J, entProperties):
        # print 'WIP'
        for i in entN4J.properties:
            tmpValue = str(entN4J.properties[i])
            if i in self.labels:
                word = tmpValue.split(' ')
                if len(word) > 3:
                    tmpValue = "%s %s %s ..." % (word[0], word[1], word[2])
                entProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
                entProperties["viewLabel"][entTlp] = tmpValue
            if i in self.colors.keys():
                entProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
                entProperties["viewColor"][entTlp] = self.colors.get(i)
            if i in entProperties:
                entProperties[i][entTlp] = tmpValue
            else:
                # print type(tmpValue)
                entProperties[i] = self.tulip_graph.getStringProperty(i)
                # print 'i = ' + i
                # print 'has key ? ' + str(i in entProperties)
                entProperties[i][entTlp] = tmpValue

    def manageLabelsNode(self, labelsNode, nodeTlp, nodeN4J):
        # print "WIP"
        tmpArrayString = []
        for s in nodeN4J.properties:
            tmpArrayString.append(s)
        labelsNode[nodeTlp] = tmpArrayString


    # def manageLabelEdge(labelEdge,edgeTlp,edgeN4J):
    # 	labelEdge[edgeTlp] = edgeN4J.type

    # def testTransmmission(graph,node):
    # 	testNul = self.tulip_graph.getIntegerProperty("testNul")
    # 	strNul = "testNul"
    # 	exec(strNul)[node] = 1

    def create(self):
        # Entities properties
        tmpIDNode = self.tulip_graph.getStringProperty("tmpIDNode")
        labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
        labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
        entityType = self.tulip_graph.getStringProperty("entityType")
        nodeProperties = {}
        edgeProperties = {}
        indexTags = {}
        indexPosts = {}
        indexComments = {}

        if (not os.path.exists("%s%s.tlp" % (config['exporter']['tlp_path'], "PostCommentTag"))) or self.force_fresh == 1:
            # Prepare tags and posts request
            req = "MATCH (t:tag)<-[:REFERS_TO]-(a:annotation)-[:ANNOTATES]->(e: post) "
            req+= "WHERE e.timestamp >= %d AND e.timestamp <= %d " % (self.date_start, self.date_end)
            req+= "RETURN t.tag_id, e.post_id, t, e, count(t) as strength"
            result = self.neo4j_graph.run(req)

            # Get the posts
            print("Read Posts")
            for qr in result:
                if not qr[0] in indexTags:
                    n = self.tulip_graph.addNode()
                    indexTags[qr[0]] = n
                    tmpIDNode[n] = str(qr[0])
                    self.managePropertiesEntity(n, qr[2], nodeProperties)
                    self.manageLabelsNode(labelsNodeTlp, n, qr[2])
                    entityType[n] = "tag"
                if not qr[1] in indexPosts:
                    n = self.tulip_graph.addNode()
                    indexPosts[qr[1]] = n
                    tmpIDNode[n] = str(qr[1])
                    self.managePropertiesEntity(n, qr[3], nodeProperties)
                    self.manageLabelsNode(labelsNodeTlp, n, qr[3])
                    entityType[n] = "post"

                e = self.tulip_graph.addEdge(indexTags[qr[0]], indexPosts[qr[1]])

            # Prepare tags and comments request
            req = "MATCH (t:tag)<-[:REFERS_TO]-(a:annotation)-[:ANNOTATES]->(e: comment) "
            req+= "WHERE e.timestamp >= %d AND e.timestamp <= %d " % (self.date_start, self.date_end)
            req+= "RETURN t.tag_id, e.comment_id, t, e, count(t) as strength"
            result = self.neo4j_graph.run(req)

            # Get the comments
            print("Read Comments")
            for qr in result:
                if not qr[0] in indexTags:
                    n = self.tulip_graph.addNode()
                    indexTags[qr[0]] = n
                    tmpIDNode[n] = str(qr[0])
                    self.managePropertiesEntity(n, qr[2], nodeProperties)
                    self.manageLabelsNode(labelsNodeTlp, n, qr[2])
                    entityType[n] = "tag"
                if not qr[1] in indexComments:
                    n = self.tulip_graph.addNode()
                    indexComments[qr[1]] = n
                    tmpIDNode[n] = str(qr[1])
                    self.managePropertiesEntity(n, qr[3], nodeProperties)
                    self.manageLabelsNode(labelsNodeTlp, n, qr[3])
                    entityType[n] = "comment"

                e = self.tulip_graph.addEdge(indexTags[qr[0]], indexComments[qr[1]])


            user_associate_req = "MATCH (n1:user)-[:AUTHORSHIP]->(content)<-[:ANNOTATES]-(:annotation)-[:REFERS_TO]->(t:tag) "
            user_associate_req += "WHERE content:post OR content:comment "
            user_associate_req += "RETURN t.tag_id, COLLECT(DISTINCT n1.user_id)"

            #add user array as node property
            nodeProperties["usersAssociateNodeTlp"] = self.tulip_graph.getIntegerVectorProperty("usersAssociateNodeTlp")
            result = self.neo4j_graph.run(user_associate_req)
            for qr in result:
                nodeProperties["usersAssociateNodeTlp"][indexTags[qr[0]]] = qr[1]

            postOrComment_associate_req = "MATCH (t:tag) "
            postOrComment_associate_req += "OPTIONAL MATCH (t:tag)<-[:REFERS_TO]-(:annotation)-[:ANNOTATES]->(p:post) "
            postOrComment_associate_req += "OPTIONAL MATCH (t:tag)<-[:REFERS_TO]-(:annotation)-[:ANNOTATES]->(c:comment) "
            postOrComment_associate_req += "RETURN t.tag_id, COLLECT(DISTINCT p.post_id) + COLLECT(DISTINCT c.comment_id)"

            #add post and comment array as node property
            nodeProperties["postsOrCommentsAssociateNodeTlp"] = self.tulip_graph.getIntegerVectorProperty("postsOrCommentsAssociateNodeTlp")
            result = self.neo4j_graph.run(postOrComment_associate_req)
            for qr in result:
                if qr[0] in indexTags:
                    nodeProperties["postsOrCommentsAssociateNodeTlp"][indexTags[qr[0]]] = qr[1]


            tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], "PostCommentTag"))
