import configparser
import uuid
from tulip import *
from py2neo import *

config = configparser.ConfigParser()
config.read("config.ini")


class CreateFullTlp(object):
    def __init__(self):
        super(CreateFullTlp, self).__init__()
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
        # View properties
        viewBorderColor = self.tulip_graph.getColorProperty("viewBorderColor")
        viewBorderWidth = self.tulip_graph.getDoubleProperty("viewBorderWidth")
        viewColor = self.tulip_graph.getColorProperty("viewColor")
        viewFont = self.tulip_graph.getStringProperty("viewFont")
        viewFontAwesomeIcon = self.tulip_graph.getStringProperty("viewFontAwesomeIcon")
        viewFontSize = self.tulip_graph.getIntegerProperty("viewFontSize")
        viewLabel = self.tulip_graph.getStringProperty("viewLabel")
        viewLabelBorderColor = self.tulip_graph.getColorProperty("viewLabelBorderColor")
        viewLabelBorderWidth = self.tulip_graph.getDoubleProperty("viewLabelBorderWidth")
        viewLabelColor = self.tulip_graph.getColorProperty("viewLabelColor")
        viewLabelPosition = self.tulip_graph.getIntegerProperty("viewLabelPosition")
        viewLayout = self.tulip_graph.getLayoutProperty("viewLayout")
        viewMetaGraph = self.tulip_graph.getGraphProperty("viewMetaGraph")
        viewMetric = self.tulip_graph.getDoubleProperty("viewMetric")
        viewRotation = self.tulip_graph.getDoubleProperty("viewRotation")
        viewSelection = self.tulip_graph.getBooleanProperty("viewSelection")
        viewShape = self.tulip_graph.getIntegerProperty("viewShape")
        viewSize = self.tulip_graph.getSizeProperty("viewSize")
        viewSrcAnchorShape = self.tulip_graph.getIntegerProperty("viewSrcAnchorShape")
        viewSrcAnchorSize = self.tulip_graph.getSizeProperty("viewSrcAnchorSize")
        viewTexture = self.tulip_graph.getStringProperty("viewTexture")
        viewTgtAnchorShape = self.tulip_graph.getIntegerProperty("viewTgtAnchorShape")
        viewTgtAnchorSize = self.tulip_graph.getSizeProperty("viewTgtAnchorSize")

        # Entities properties
        tmpIDNode = self.tulip_graph.getIntegerProperty("tmpIDNode")
        tmpIDEdge = self.tulip_graph.getIntegerProperty("tmpIDEdge")
        labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
        labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
        nodeProperties = {}
        edgeProperties = {}
        indexNodes = {}

        # Prepare node request
        nodes_req = "MATCH (n) "
        nodes_req += "WHERE NOT (n:Day) "
        nodes_req += "AND NOT (n:Month) "
        nodes_req += "AND NOT (n:Year) "
        nodes_req += "AND NOT (n:TimeTreeRoot) "
        nodes_req += "AND NOT (n:group) "
        nodes_req += "AND NOT (n:role) "
        nodes_req += "AND NOT (n:post_type) "
        nodes_req += "AND NOT (n:language) "
        nodes_req += "AND NOT (n:tag) "
        nodes_req += "AND NOT (n:annotation) "
        nodes_req += "RETURN distinct ID(n),n"

        # Prepare edge request
        edges_req = "MATCH (n1)-[e]->(n2) "
        edges_req += "RETURN ID(e),ID(n1),ID(n2),n2,e"

        # Get the nodes of Neo4J
        print("Read Nodes")
        result = self.neo4j_graph.run(nodes_req)
        for qr in result:
            n = self.tulip_graph.addNode()
            self.managePropertiesEntity(n, qr[1], nodeProperties)
            self.manageLabelsNode(labelsNodeTlp, n, qr[1])
            tmpIDNode[n] = qr[0]
            # keep the reference for edges creation
            indexNodes[qr[0]] = n

        # Get the edges of Neo4J
        print("Read Edges")
        result = self.neo4j_graph.run(edges_req)
        for qr in result:
            if qr[1] in indexNodes and qr[2] in indexNodes:
                e = self.tulip_graph.addEdge(indexNodes[qr[1]], indexNodes[qr[2]])
                self.managePropertiesEntity(e, qr[4], edgeProperties)
                # manageLabelEdge(labelEdgeTlp,e,qr[3])
                edgeProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
                edgeProperties["viewLabel"][e] = qr[4].type()
                edgeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
                edgeProperties["viewColor"][e] = self.colors['edges']
                labelEdgeTlp[e] = qr[4].type()
                tmpIDEdge[e] = qr[0]

        print("Export")
        tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))

