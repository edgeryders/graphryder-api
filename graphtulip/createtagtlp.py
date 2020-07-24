from tulip import *
from py2neo import *
import configparser

config = configparser.ConfigParser()
config.read("config.ini")


# todo create a unique Createtlp to avoid code duplication
class CreateTagTlp(object):
    def __init__(self, value):
        super(CreateTagTlp, self).__init__()
        print('Initializing')

        self.neo4j_graph = Graph(
            host=config['neo4j']['url'],
            http_port=int(config['neo4j']['http_port']),
            bolt_port=int(config['neo4j']['bolt_port']),
            user=config['neo4j']['user'],
            password=config['neo4j']['password']
        )
        self.tulip_graph = tlp.newGraph()
        self.tulip_graph.setName('opencare - tagToTag')
        # todo pass in parameters labels and colors
        self.labels = ["label", "label", "label"]
        self.colors = {"user_id": tlp.Color(51,122,183), "post_id": tlp.Color(92,184,92), "comment_id": tlp.Color(240, 173, 78), "tag_id": tlp.Color(200, 10, 10), "edges": tlp.Color(204, 204, 204)}
        self.tag_id_src = value

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

        req = "MATCH (t1: tag {tag_id: %d}) RETURN ID(t1), t1" % self.tag_id_src
        result = self.neo4j_graph.run(req)

        for qr in result:
            n = self.tulip_graph.addNode()
            self.managePropertiesEntity(n, qr[1], nodeProperties)
            self.manageLabelsNode(labelsNodeTlp, n, qr[1])
            tmpIDNode[n] = qr[0]
            # keep the reference for edges creation
            indexNodes[qr[0]] = n
            break

        # Prepare node and edge request
        req = "MATCH (t1: tag {tag_id: %d})--(a1: annotation)-[:ANNOTATES]->(e:post)<-[:ANNOTATES]-(a2: annotation)--(t2: tag) WHERE t1 <> t2 RETURN ID(t1), ID(t2), t1, t2, count(t1) as strength" % self.tag_id_src
        result = self.neo4j_graph.run(req)

        # Get the tags
        print("Read Tags")
        for qr in result:
            n = self.tulip_graph.addNode()
            self.managePropertiesEntity(n, qr[3], nodeProperties)
            self.manageLabelsNode(labelsNodeTlp, n, qr[3])
            tmpIDNode[n] = qr[1]
            # keep the reference for edges creation
            indexNodes[qr[1]] = n

        # Get the edges #  RETURN ID(t1), ID(t2), t1, t2, count(t1) as strength
        print("Read Edges")
        result = self.neo4j_graph.run(req)
        for qr in result:
            if qr[0] in indexNodes and qr[1] in indexNodes:
                e = self.tulip_graph.addEdge(indexNodes[qr[0]], indexNodes[qr[1]])
                edgeProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
                edgeProperties["viewLabel"][e] = "REFERS_TO ("+str(qr[4])+")"
                labelEdgeTlp[e] = "REFERS_TO ("+str(qr[4])+")"
                edgeProperties["type"] = self.tulip_graph.getStringProperty("type")
                edgeProperties["type"][e] = "curvedArrow"
                edgeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
                edgeProperties["viewColor"][e] = self.colors['edges']

        print("Export")
        tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))


