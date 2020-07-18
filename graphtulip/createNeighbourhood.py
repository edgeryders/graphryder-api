from tulip import *
from py2neo import *
import time
import configparser
import os
from graphtulip.createPostCommentTagTlp import CreatePostCommentTagTlp

config = configparser.ConfigParser()
config.read("config.ini")


# todo create a unique Createtlp to avoid code duplication
class CreateNeighbourhood(object):
    def __init__(self, element_type, element_id):
        super(CreateNeighbourhood, self).__init__()
        print('Initializing')

        self.neo4j_graph = Graph(
            "bolt://" + config['neo4j']['url'] + ':' + str(config['neo4j']['bolt_port']),
            user=config['neo4j']['user'],
            password=config['neo4j']['password']
        )
        self.tulip_graph = tlp.newGraph()
        self.tulip_graph.setName('opencare - neighbourhood')
        # todo pass in parameters labels and colors
        self.labels = ["label", "label", "label"]
        self.colors = {"user_id": tlp.Color(51,122,183), "post_id": tlp.Color(92,184,92), "comment_id": tlp.Color(240, 173, 78), "tag_id": tlp.Color(200, 10, 10), "edges": tlp.Color(204, 204, 204)}
        self.element_id = element_id
        self.element_type = element_type

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

    def extractSubgraph(self, source, selected):
        for ngb in self.tulip_graph.getInOutNodes(source):
            if self.entityType[ngb] == 'tag':
                selected[ngb] = True
                selected[self.tulip_graph.existEdge(source, ngb, False)] = True
                self.weight[ngb]+=1
                if self.entityType[source] == 'post':
                    self.innovation[ngb] = False
            else:
                if not selected[ngb]:
                    selected[ngb] = True
                    selected[self.tulip_graph.existEdge(source, ngb, False)] = True
                    self.extractSubgraph(ngb, selected)

    # def manageLabelEdge(labelEdge,edgeTlp,edgeN4J):
    # 	labelEdge[edgeTlp] = edgeN4J.type

    # def testTransmmission(graph,node):
    # 	testNul = self.tulip_graph.getIntegerProperty("testNul")
    # 	strNul = "testNul"
    # 	exec(strNul)[node] = 1

    def create(self, private_gid):
        # Entities properties
        nodeProperties = {}
        edgeProperties = {}
        indexTags = {}
        indexPosts = {}
        indexComments = {}


        if (not os.path.exists("%s%s.tlp" % (config['exporter']['tlp_path'], "PostTagCommentGlobal"))):

            tmpIDNode = self.tulip_graph.getStringProperty("tmpIDNode")
            entityType = self.tulip_graph.getStringProperty("entityType")
            labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
            labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
            colorProp = self.tulip_graph.getColorProperty("viewColor")

            # Prepare posts and comments request
            req = "MATCH (e)<-[:COMMENTS]-(c: comment) "
            #req+= "WHERE e.timestamp >= %d AND e.timestamp <= %d " % (self.date_start, self.date_end)
            #req+= "AND c.timestamp >= %d AND c.timestamp <= %d " % (self.date_start, self.date_end)
            req+= "RETURN c.comment_id AS src_id, c AS src, CASE e.post_id WHEN null THEN e.comment_id ELSE e.post_id END AS tgt_id, CASE e.post_id WHEN null THEN 'comment' ELSE 'post' END AS tgt_entity_type, e AS tgt"
            result = self.neo4j_graph.run(req)

            # Get the posts
            print("Connecting...")
            for qr in result:
                if not qr[0] in indexComments:
                    n = self.tulip_graph.addNode()
                    indexComments[qr[0]] = n
                    tmpIDNode[n] = str(qr[0])
                    self.managePropertiesEntity(n, qr[1], nodeProperties)
                    self.manageLabelsNode(labelsNodeTlp, n, qr[1])
                    entityType[n] = "comment"

                if qr[3] == "post":
                    if not qr[2] in indexPosts:
                        n = self.tulip_graph.addNode()
                        indexPosts[qr[2]] = n
                        tmpIDNode[n] = str(qr[2])
                        self.managePropertiesEntity(n, qr[4], nodeProperties)
                        self.manageLabelsNode(labelsNodeTlp, n, qr[4])
                        entityType[n] = "post"
                    e = self.tulip_graph.addEdge(indexComments[qr[0]], indexPosts[qr[2]])
                    colorProp[e] = self.colors["edges"]
                else:
                    if not qr[2] in indexComments:
                        n = self.tulip_graph.addNode()
                        indexComments[qr[2]] = n
                        tmpIDNode[n] = str(qr[2])
                        self.managePropertiesEntity(n, qr[4], nodeProperties)
                        self.manageLabelsNode(labelsNodeTlp, n, qr[4])
                        entityType[n] = "comment"
                    e = self.tulip_graph.addEdge(indexComments[qr[0]], indexComments[qr[2]])
                    colorProp[e] = self.colors["edges"]

            # delete shortcuts between comments to post when comments are mere responses
            for n in self.tulip_graph.getNodes():
                if entityType[n] == 'comment':
                    tmp_e_to_post = None
                    isResponse = False
                    for ngb in self.tulip_graph.getOutNodes(n):
                        if entityType[ngb] == 'post':
                            tmp_e_to_post = self.tulip_graph.existEdge(n, ngb)
                        if entityType[ngb] == 'comment':
                            isResponse = True
                    if isResponse and tmp_e_to_post != None:
                        self.tulip_graph.delEdge(tmp_e_to_post)

    # Prepare tags and posts request
            req = "MATCH (t:tag)<-[:REFERS_TO]-(a:annotation)-[:ANNOTATES]->(e: post) "
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
                colorProp[e] = self.colors["edges"]

            # Prepare tags and comments request
            req = "MATCH (t:tag)<-[:REFERS_TO]-(a:annotation)-[:ANNOTATES]->(e: comment) "
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
                colorProp[e] = self.colors["edges"]

            tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], "PostTagCommentGlobal"))
        else:
            self.tulip_graph = tlp.loadGraph("%s%s.tlp" % (config['exporter']['tlp_path'], "PostTagCommentGlobal"))

        print("Compute Neighbourhood graph")
        tmpIDNode = self.tulip_graph.getStringProperty("tmpIDNode")
        self.entityType = self.tulip_graph.getStringProperty("entityType")
        self.innovation = self.tulip_graph.getBooleanProperty("innovation")
        self.innovation.setAllNodeValue(True)
        edgeProperties["ngbSelection"] = self.tulip_graph.getBooleanProperty("ngbSelection")
        edgeProperties["ngbSelection"].setAllNodeValue(False)
        edgeProperties["ngbSelection"].setAllEdgeValue(False)
        self.weight = self.tulip_graph.getIntegerProperty("weight")
        elem_found = False
        for n in self.tulip_graph.getNodes():
            if self.entityType[n] == self.element_type and str(tmpIDNode[n]) == str(self.element_id):
                elem_found = True
                edgeProperties["ngbSelection"][n] = True
                self.extractSubgraph(n, edgeProperties["ngbSelection"])

        sg = self.tulip_graph.addSubGraph(edgeProperties["ngbSelection"])

        # visual attributes
        colorProp = self.tulip_graph.getColorProperty("viewColor")
        sizeProp = self.tulip_graph.getSizeProperty("viewSize")
        max_scale = max(self.weight.getNodeMax(), 1)
        color_max = tlp.Color(200, 10, 10)
        color_min = tlp.Color(200, 180, 180)
        color_delta = tlp.Color(abs(color_max[0]-color_min[0])/max_scale, abs(color_max[1]-color_min[1])/max_scale, abs(color_max[2]-color_min[2])/max_scale)
        for n in sg.getNodes():
            if self.entityType[n] == 'tag':
                colorProp[n]=tlp.Color(color_min[0]-color_delta[0]*self.weight[n],color_min[1]-color_delta[1]*self.weight[n], color_min[2]-color_delta[2]*self.weight[n])

        print("Export")
        tlp.saveGraph(sg, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))


