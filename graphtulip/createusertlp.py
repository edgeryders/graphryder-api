from tulip import *
from py2neo import *
import configparser

config = configparser.ConfigParser()
config.read("config.ini")


# todo create a unique Createtlp to avoid code duplication
class CreateUserTlp(object):
    def __init__(self):
        super(CreateUserTlp, self).__init__()
        print('Initializing')

        self.neo4j_graph = Graph(
            "bolt://" + config['neo4j']['url'] + ':' + str(config['neo4j']['bolt_port']),
            user=config['neo4j']['user'],
            password=config['neo4j']['password']
        )
        self.tulip_graph = tlp.newGraph()
        self.tulip_graph.setName('opencare')
        # todo pass in parameters labels and colors
        self.labels = ["label", "label", "label"]
        self.colors = {"user_id": tlp.Color(51,122,183), "post_id": tlp.Color(92,184,92), "comment_id": tlp.Color(240, 173, 78),  "edges": tlp.Color(204, 204, 204)}

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

    def create(self, private_gid):
        # Entities properties
        tmpIDNode = self.tulip_graph.getIntegerProperty("tmpIDNode")
        tmpIDEdge = self.tulip_graph.getIntegerProperty("tmpIDEdge")
        labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
        labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
        nodeProperties = {}
        edgeProperties = {}
        indexNodes = {}

        # Prepare node request
        nodes_req = "MATCH (n:user) "
        nodes_req += "RETURN ID(n),n"

        # Prepare edge comments request
        comment_edges_req = "MATCH (n1:user)-[:AUTHORSHIP]->(c:comment)-[:COMMENTS]->(p:post)<-[:AUTHORSHIP]-(n2:user) "
        comment_edges_req += "RETURN ID(n1),ID(n2),ID(c),ID(p), c, p"

        # Prepare edge response request
        resp_edges_req = "MATCH (n1:user)-[:AUTHORSHIP]->(c:comment)-[:COMMENTS]->(c2:comment)<-[:AUTHORSHIP]-(n2:user) "
        resp_edges_req += "RETURN ID(n1),ID(n2), c, c2"

        #Prepare tag associate resquest

        tag_associate_req = "MATCH (n1:user)-[:AUTHORSHIP]->(content)<-[:ANNOTATES]-(:annotation)-[:REFERS_TO]->(t:tag) "
        tag_associate_req += "WHERE content:post OR content:comment "
        tag_associate_req += "RETURN ID(n1), COLLECT(DISTINCT t.tag_id)"

        postOrComment_associate_req = "MATCH (n1:user) "
        postOrComment_associate_req += "OPTIONAL MATCH (n1:user)-[:AUTHORSHIP]->(p:post) "
        postOrComment_associate_req += "OPTIONAL MATCH (n1:user)-[:AUTHORSHIP]->(c:comment) "
        postOrComment_associate_req += "RETURN ID(n1), COLLECT(DISTINCT p.post_id) + COLLECT(DISTINCT c.comment_id)"

        # Get the users
        print("Read Users")
        result = self.neo4j_graph.run(nodes_req)
        for qr in result:
            n = self.tulip_graph.addNode()
            self.managePropertiesEntity(n, qr[1], nodeProperties)
            self.manageLabelsNode(labelsNodeTlp, n, qr[1])
            tmpIDNode[n] = qr[0]
            # keep the reference for edges creation
            indexNodes[qr[0]] = n

        #add tag array as node property
        nodeProperties["tagsAssociateNodeTlp"] = self.tulip_graph.getIntegerVectorProperty("tagsAssociateNodeTlp")
        result = self.neo4j_graph.run(tag_associate_req)
        for qr in result:
            nodeProperties["tagsAssociateNodeTlp"][indexNodes[qr[0]]] = qr[1]

        #add post and comment array as node property
        nodeProperties["postsOrCommentsAssociateNodeTlp"] = self.tulip_graph.getIntegerVectorProperty("postsOrCommentsAssociateNodeTlp")
        result = self.neo4j_graph.run(postOrComment_associate_req)
        for qr in result:
            nodeProperties["postsOrCommentsAssociateNodeTlp"][indexNodes[qr[0]]] = qr[1]

        # Get the comments edges
        print("Read Edges")
        result = self.neo4j_graph.run(comment_edges_req)
        for qr in result:
            if qr[0] in indexNodes and qr[1] in indexNodes:
                e = self.tulip_graph.addEdge(indexNodes[qr[0]], indexNodes[qr[1]])
                edgeProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
                edgeProperties["viewLabel"][e] = "COMMENTS"
                labelEdgeTlp[e] = "COMMENTS"
                edgeProperties["type"] = self.tulip_graph.getStringProperty("type")
                edgeProperties["type"][e] = "curvedArrow"
                # post
                edgeProperties["post_title"] = self.tulip_graph.getStringProperty("post_title")
                if qr[5]['title']:
                    edgeProperties["post_title"][e] = qr[5]['title']
                #edgeProperties["post_content"] = self.tulip_graph.getStringProperty("post_content")
                #if qr[5]['content']:
                #    edgeProperties["post_content"][e] = qr[5]['content']
                edgeProperties["post_id"] = self.tulip_graph.getIntegerProperty("post_id")
                edgeProperties["post_id"][e] = qr[5]['post_id']
                # comment
                edgeProperties["comment_title"] = self.tulip_graph.getStringProperty("comment_title")
                if qr[4]['title']:
                    edgeProperties["comment_title"][e] = qr[4]['title']
                #edgeProperties["comment_content"] = self.tulip_graph.getStringProperty("comment_content")
                #if qr[4]['content']:
                #    edgeProperties["comment_content"][e] = qr[4]['content']
                edgeProperties["comment_id"] = self.tulip_graph.getIntegerProperty("comment_id")
                edgeProperties["comment_id"][e] = qr[4]['comment_id']
                edgeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
                edgeProperties["viewColor"][e] = self.colors['edges']


        # Get the response edges
        print("Read Edges")
        result = self.neo4j_graph.run(resp_edges_req)
        for qr in result:
            if qr[0] in indexNodes and qr[1] in indexNodes:
                e = self.tulip_graph.addEdge(indexNodes[qr[0]], indexNodes[qr[1]])
                # self.managePropertiesEntity(e, qr[4], edgeProperties)
                # manageLabelEdge(labelEdgeTlp,e,qr[3])
                edgeProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
                edgeProperties["viewLabel"][e] = "REPLY"
                labelEdgeTlp[e] = "REPLY"
                edgeProperties["type"] = self.tulip_graph.getStringProperty("type")
                edgeProperties["type"][e] = "curvedArrow"
                # comment 1
                edgeProperties["comment1_title"] = self.tulip_graph.getStringProperty("comment1_title")
                if qr[2]['title']:
                    edgeProperties["comment1_title"][e] = qr[2]['title']
                #edgeProperties["comment1_content"] = self.tulip_graph.getStringProperty("comment1_content")
                #edgeProperties["comment1_content"][e] = qr[2]['content']
                edgeProperties["comment_id1"] = self.tulip_graph.getIntegerProperty("comment_id1")
                edgeProperties["comment_id1"][e] = qr[2]['comment_id']
                # comment 2
                edgeProperties["comment2_title"] = self.tulip_graph.getStringProperty("comment2_title")
                edgeProperties["comment2_title"][e] = qr[3]['title']
                #edgeProperties["comment2_content"] = self.tulip_graph.getStringProperty("comment2_content")
                #edgeProperties["comment2_content"][e] = qr[3]['content']
                edgeProperties["comment_id2"] = self.tulip_graph.getIntegerProperty("comment_id2")
                edgeProperties["comment_id2"][e] = qr[3]['comment_id']
                edgeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
                edgeProperties["viewColor"][e] = self.colors['edges']

        print("Export")
        tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))
