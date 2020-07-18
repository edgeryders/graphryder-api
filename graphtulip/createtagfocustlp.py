from tulip import *
from py2neo import *
import configparser

config = configparser.ConfigParser()
config.read("config.ini")


# todo create a unique Createtlp to avoid code duplication
class CreateTagFocusTlp(object):
    def __init__(self, value, start, end):
        super(CreateTagFocusTlp, self).__init__()
        print('Initializing')

        self.neo4j_graph = Graph(
            "bolt://" + config['neo4j']['url'] + ':' + str(config['neo4j']['bolt_port']),
            user=config['neo4j']['user'],
            password=config['neo4j']['password']
        )
        self.tulip_graph = tlp.newGraph()
        self.tulip_graph.setName('opencare - tagToTag')
        # todo pass in parameters labels and colors
        self.labels = ["label", "label", "label"]
        self.colors = {"user_id": tlp.Color(51,122,183), "post_id": tlp.Color(92,184,92), "comment_id": tlp.Color(240, 173, 78), "tag_id": tlp.Color(200, 10, 10), "edges": tlp.Color(204, 204, 204)}
        self.tag_id_src = value
        self.date_start = start
        self.date_end = end
        # for normalisation
        self.nb_step = 100

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
        #tmpIDNode = self.tulip_graph.getStringProperty("tmpIDNode")
        labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
        labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
        entityType = self.tulip_graph.getStringProperty("entityType")
        nodeProperties = {}
        nodeProperties['viewLabel'] = self.tulip_graph.getStringProperty("viewLabel")
        nodeProperties['tag_id'] = self.tulip_graph.getStringProperty("tag_id")
        nodeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
        edgeProperties = {}
        indexTags = {}
        indexPosts = {}
        indexComments = {}
        max_occ = 1

        # Prepare tags and posts request
        req = "MATCH (t:tag)<-[:REFERS_TO]-(a:annotation)-[:ANNOTATES]->(e: post) "
        req+= "WHERE e.timestamp >= %d AND e.timestamp <= %d " % (self.date_start, self.date_end)
        req+= "RETURN t.tag_id, e.post_id, t.label, e.label, count(t) as strength"
        result = self.neo4j_graph.run(req)

        # Get the posts
        print("Read Posts")
        for qr in result:
            if not qr[0] in indexTags:
                n = self.tulip_graph.addNode()
                indexTags[qr[0]] = n
                #tmpIDNode[n] = qr[0]
                nodeProperties['viewLabel'][n] = str(qr[2])
                nodeProperties['tag_id'][n] = str(qr[0])
                nodeProperties["viewColor"][n] = self.colors["tag_id"]
                entityType[n] = "tag"
            if not qr[1] in indexPosts:
                n = self.tulip_graph.addNode()
                indexPosts[qr[1]] = n
                #tmpIDNode[n] = qr[1]
                nodeProperties['viewLabel'][n] = str(qr[3])
                nodeProperties["viewColor"][n] = self.colors["post_id"]
                entityType[n] = "post"

            e = self.tulip_graph.addEdge(indexTags[qr[0]], indexPosts[qr[1]])

        # Prepare tags and comments request
        req = "MATCH (t:tag)<-[:REFERS_TO]-(a:annotation)-[:ANNOTATES]->(e: comment) "
        req+= "WHERE e.timestamp >= %d AND e.timestamp <= %d " % (self.date_start, self.date_end)
        req+= "RETURN t.tag_id, e.comment_id, t.label, e.label, count(t) as strength"
        result = self.neo4j_graph.run(req)

        # Get the comments
        print("Read Comments")
        for qr in result:
            if not qr[0] in indexTags:
                n = self.tulip_graph.addNode()
                indexTags[qr[0]] = n
                #tmpIDNode[n] = qr[0]
                nodeProperties['viewLabel'][n] = str(qr[2])
                nodeProperties['tag_id'][n] = str(qr[0])
                nodeProperties["viewColor"][n] = self.colors["tag_id"]
                entityType[n] = "tag"
            if not qr[1] in indexComments:
                n = self.tulip_graph.addNode()
                indexComments[qr[1]] = n
                #tmpIDNode[n] = qr[1]
                nodeProperties['viewLabel'][n] = str(qr[3])
                nodeProperties["viewColor"][n] = self.colors["comment_id"]
                entityType[n] = "comment"

            e = self.tulip_graph.addEdge(indexTags[qr[0]], indexComments[qr[1]])

        print("Compute Tag-Tag graph")
        edgeProperties["occ"] = self.tulip_graph.getIntegerProperty("occ")
        edgeProperties["TagTagSelection"] = self.tulip_graph.getBooleanProperty("TagTagSelection")
        edgeProperties["TagTagSelection"].setAllNodeValue(False)
        edgeProperties["TagTagSelection"].setAllEdgeValue(False)
        edgeProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
        edgeProperties["type"] = self.tulip_graph.getStringProperty("type")
        edgeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
        edgeProperties["viewSize"] = self.tulip_graph.getSizeProperty("viewSize")
        edgeProperties["tag_1"] = self.tulip_graph.getStringProperty("tag_1")
        edgeProperties["label_1"] = self.tulip_graph.getStringProperty("label_1")
        edgeProperties["tag_2"] = self.tulip_graph.getStringProperty("tag_2")
        edgeProperties["label_2"] = self.tulip_graph.getStringProperty("label_2")
        for t1 in indexTags:
            edgeProperties["TagTagSelection"][indexTags[t1]] = True
            for p in self.tulip_graph.getOutNodes(indexTags[t1]):
                if entityType[p] == "post" or entityType[p] == "comment":
                    for t2 in self.tulip_graph.getInNodes(p):
                        if indexTags[t1] != t2:
                            e=self.tulip_graph.existEdge(indexTags[t1], t2, False)
                            if e.isValid():
                                edgeProperties["occ"][e] += 1
                                edgeProperties["viewLabel"][e] = "occ ("+str(edgeProperties["occ"][e])+")"
                                labelEdgeTlp[e] = "occ ("+str(edgeProperties["occ"][e]/2)+")"
                                e_val = edgeProperties['occ'][e]
                                max_occ = max(max_occ, e_val)
                                if e_val > edgeProperties["occ"][indexTags[t1]]:
                                    edgeProperties["occ"][indexTags[t1]] = e_val
                                    edgeProperties["viewSize"][indexTags[t1]] = tlp.Size(e_val, e_val, e_val)
                                if e_val > edgeProperties["occ"][t2]:
                                    edgeProperties["occ"][t2] = e_val
                                    edgeProperties["viewSize"][t2] = tlp.Size(e_val, e_val, e_val)
                            else:
                                e = self.tulip_graph.addEdge(indexTags[t1], t2)
                                edgeProperties["occ"][e] = 1
                                edgeProperties["TagTagSelection"][t2] = True
                                edgeProperties["TagTagSelection"][e] = True
                                edgeProperties["viewLabel"][e] = "occ ("+str(edgeProperties["occ"][e])+")"
                                labelEdgeTlp[e] = "occ ("+str(edgeProperties["occ"][e]/2)+")"
                                edgeProperties["type"][e] = "curve"
                                edgeProperties["viewColor"][e] = self.colors['edges']
                                edgeProperties["tag_1"][e] = str(nodeProperties['tag_id'][indexTags[t1]])
                                edgeProperties["tag_2"][e] = str(nodeProperties['tag_id'][t2])
                                edgeProperties["label_1"][e] = str(nodeProperties['viewLabel'][indexTags[t1]])
                                edgeProperties["label_2"][e] = str(nodeProperties['viewLabel'][t2])
        sg = self.tulip_graph.addSubGraph(edgeProperties["TagTagSelection"])

        print("Compute focus Tag-Tag subgraph")
        t1 = indexTags[self.tag_id_src]
        edgeProperties["viewColor"][t1] = tlp.Color(0, 175, 255)
        edgeProperties["TagTagSelection"].setAllNodeValue(False)
        edgeProperties["TagTagSelection"].setAllEdgeValue(False)
        edgeProperties["TagTagSelection"][t1] = True
        edgeProperties["occ"][t1] = -1
        for t2 in sg.getInOutNodes(t1):
            edgeProperties["TagTagSelection"][t2] = True
            e = sg.existEdge(t1, t2, False)
            edgeProperties["TagTagSelection"][e] = True
            tmp_val = (float(edgeProperties["occ"][e])/max_occ)*(self.nb_step-1)+1
            edgeProperties["occ"][e] = tmp_val
            edgeProperties["occ"][t2] = tmp_val
            for t3 in sg.getInOutNodes(t2):
                if edgeProperties["TagTagSelection"][t3] == True:
                    e = sg.existEdge(t2, t3, False)
                    edgeProperties["TagTagSelection"][e] = True
                    tmp_val = (float(edgeProperties["occ"][e])/max_occ)*(self.nb_step-1)+1
                    edgeProperties["occ"][e] = tmp_val
        ssg = sg.addSubGraph(edgeProperties["TagTagSelection"])

        print("Export")
        tlp.saveGraph(ssg, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))


