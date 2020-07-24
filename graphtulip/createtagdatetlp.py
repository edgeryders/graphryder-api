from tulip import *
from py2neo import *
import configparser

config = configparser.ConfigParser()
config.read("config.ini")


# todo create a unique Createtlp to avoid code duplication
class CreateTagDateTlp(object):
    def __init__(self, value, start, end):
        super(CreateTagDateTlp, self).__init__()
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
        tmpIDNode = self.tulip_graph.getIntegerProperty("tmpIDNode")
        tmpIDEdge = self.tulip_graph.getIntegerProperty("tmpIDEdge")
        labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
        labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
        entProperties = {}
        entProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
        entProperties["viewSize"] = self.tulip_graph.getSizeProperty("viewSize")
        entProperties["tag_id"] = self.tulip_graph.getStringProperty("tag_id")
        entProperties["occ"] = self.tulip_graph.getIntegerProperty("occ")
        indexNodes = {}
        max_occ = 1

        req = "MATCH (t1: tag {tag_id: %d}) RETURN t1.tag_id, t1" % self.tag_id_src
        result = self.neo4j_graph.run(req)

        for qr in result:
            focus_node = self.tulip_graph.addNode()
            self.managePropertiesEntity(focus_node, qr[1], entProperties)
            self.manageLabelsNode(labelsNodeTlp, focus_node, qr[1])
            tmpIDNode[focus_node] = qr[0]
            # keep the reference for edges creation
            indexNodes[qr[0]] = focus_node
            entProperties["occ"][focus_node] = 0
            break

        # Prepare node and edge request
        req = "MATCH (t1:tag {tag_id: %d})<-[:REFERS_TO]-(a1:annotation)-[:ANNOTATES]->(e) " % self.tag_id_src
        req+= "MATCH (t2:tag)<-[:REFERS_TO]-(a2:annotation)-[:ANNOTATES]->(e) "
        req+= "WHERE t1<>t2 AND a1<>a2 AND t1 <> t2 AND e.timestamp >= %d AND e.timestamp <= %d " % (self.date_start, self.date_end)
        req+= "RETURN t1.tag_id, t2.tag_id, t1.label, t2.label, count(t1) as weight"
        #req = "MATCH (t1: tag {tag_id: %d})--(a1: annotation)-[:ANNOTATES]->(e:post)<-[:ANNOTATES]-(a2: annotation)--(t2: tag) WHERE t1 <> t2 RETURN ID(t1), ID(t2), t1, t2, count(t1) as weight" % self.tag_id_src
        result = self.neo4j_graph.run(req)

        entProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
        entProperties["type"] = self.tulip_graph.getStringProperty("type")
        entProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
        entProperties["tag_1"] = self.tulip_graph.getStringProperty("tag_1")
        entProperties["label_1"] = self.tulip_graph.getStringProperty("label_1")
        entProperties["tag_2"] = self.tulip_graph.getStringProperty("tag_2")
        entProperties["label_2"] = self.tulip_graph.getStringProperty("label_2")
        # Get the edges #  RETURN ID(t1), ID(t2), t1, t2, count(t1) as weight
        result = self.neo4j_graph.run(req)
        for qr in result:
            n = self.tulip_graph.addNode()
            tmpIDNode[n] = qr[1]
            # keep the reference for edges creation
            indexNodes[qr[1]] = n
            entProperties["viewLabel"][n] = str(qr[3])
            entProperties["viewColor"][n] = self.colors['tag_id']
            entProperties["tag_id"][n] = str(qr[1])
            max_occ = max(qr[4], max_occ) 
            if qr[0] in indexNodes and qr[1] in indexNodes:
                e = self.tulip_graph.addEdge(indexNodes[qr[0]], indexNodes[qr[1]])
                entProperties["viewLabel"][e] = "REFERS_TO ("+str(qr[4])+")"
                labelEdgeTlp[e] = "REFERS_TO ("+str(qr[4])+")"
                entProperties["type"][e] = "curve"
                entProperties["viewColor"][e] = self.colors['edges']
                entProperties["tag_1"][e] = str(qr[0])
                entProperties["tag_2"][e] = str(qr[1])
                entProperties["label_1"][e] = str(qr[2])
                entProperties["label_2"][e] = str(qr[3])
                entProperties["occ"][e] = qr[4]

        for e in self.tulip_graph.getOutEdges(focus_node):
            tmp_val = (float(entProperties["occ"][e])/max_occ)*(self.nb_step-1)+1
            entProperties["occ"][e] = int(tmp_val)
            n = self.tulip_graph.target(e)
            entProperties["occ"][n] = int(tmp_val)
            #entProperties["viewSize"][n] = tlp.Size(self.nb_step,self.nb_step,self.nb_step)
            
            
        entProperties["occ"][focus_node] = -1
#        entProperties["viewSize"][n] = tlp.Size(tmp_val, tmp_val, tmp_val)

        print("Export")
        tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))


