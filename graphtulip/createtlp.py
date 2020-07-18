from tulip import *
from py2neo import *
import configparser

config = configparser.ConfigParser()
config.read("config.ini")


class CreateTlp(object):
    def __init__(self):
        super(CreateTlp, self).__init__()
        print('Initializing')

        self.neo4j_graph = Graph(
            "bolt://" + config['neo4j']['url'] + ':' + str(config['neo4j']['bolt_port']),
            user=config['neo4j']['user'],
            password=config['neo4j']['password']
        )
        self.tulip_graph = tlp.newGraph()
        self.tulip_graph.setName('opencare')

        # Entities properties
        self.tmpIDNode = self.tulip_graph.getIntegerProperty("tmpIDNode")
        self.tmpIDEdge = self.tulip_graph.getIntegerProperty("tmpIDEdge")
        self.labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
        self.labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
        self.nodeProperties = {}
        self.edgeProperties = {}
        self.indexNodes = {}

        # todo pass in parameters labels and colors
        self.labels = ["label", "label", "label"]
        self.colors = {"user_id": tlp.Color(51,122,183), "post_id": tlp.Color(92,184,92), "comment_id": tlp.Color(240, 173, 78),  "edges": tlp.Color(204, 204, 204)}

    def managePropertiesEntity(self, entTlp, entN4J, entProperties):
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
                entProperties[i] = self.tulip_graph.getStringProperty(i)
                entProperties[i][entTlp] = tmpValue

    def manageLabelsNode(self, labelsNode, nodeTlp, nodeN4J):
        tmpArrayString = []
        for s in nodeN4J.properties:
            tmpArrayString.append(s)
        labelsNode[nodeTlp] = tmpArrayString

    def createNodes(self, req):
        # Expected Format :  RETURN ID(n),n
        result = self.neo4j_graph.run(req)
        for qr in result:
            if not qr[0] in self.indexNodes:
                n = self.tulip_graph.addNode()
                self.managePropertiesEntity(n, qr[1], self.nodeProperties)
                self.manageLabelsNode(self.labelsNodeTlp, n, qr[1])
                self.tmpIDNode[n] = qr[0]
                # keep the reference for edges creation
                self.indexNodes[qr[0]] = n

    def createEdges(self, req):
        # Expected Format : RETURN ID(e),ID(n1),ID(n2),n2,e
        # If n2 not exist it will be create
        result = self.neo4j_graph.run(req)
        for qr in result:
            # add new nodes
            if not qr[2] in self.indexNodes:
                n = self.tulip_graph.addNode()
                self.managePropertiesEntity(n, qr[3], self.nodeProperties)
                self.manageLabelsNode(self.labelsNodeTlp, n, qr[3])
                self.tmpIDNode[n] = qr[2]
                # keep the reference for edges creation
                self.indexNodes[qr[2]] = n

            # edge
            e = self.tulip_graph.addEdge(self.indexNodes[qr[1]], self.indexNodes[qr[2]])
            self.managePropertiesEntity(e, qr[4], self.edgeProperties)
            # manageLabelEdge(self.labelEdgeTlp,e,qr[3])
            self.edgeProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
            self.edgeProperties["viewLabel"][e] = qr[4].type()
            self.edgeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
            self.edgeProperties["viewColor"][e] = self.colors['edges']
            self.edgeProperties["type"] = self.tulip_graph.getStringProperty("type")
            self.edgeProperties["type"][e] = "curvedArrow"
            self.labelEdgeTlp[e] = qr[4].type()
            self.tmpIDEdge[e] = qr[0]

    def createWithParams(self, params, private_gid):
        # create nodes pass in params
        for param in params:
            field, value = param
            # Prepare node request
            node_req = "MATCH (n { %s : %s}) RETURN ID(n),n" % (field, value)
            # Get the nodes of Neo4J
            self.createNodes(node_req)
            # Request neighboors of main nodes
            edges_req = "MATCH (n1 {%s : %s})-[e]-(n2) " % (field, value)
            edges_req += "WHERE NOT (n1)-[e:CREATED_ON]-(n2) "
            edges_req += "AND NOT (n1)-[e:POST_ON]-(n2) "
            edges_req += "AND NOT (n1)-[e:GROUP_IS]-(n2) "
            edges_req += "RETURN ID(e),ID(n1),ID(n2),n2,e"
            # Get the edges of Neo4J
            print("Read Edges")
            self.createEdges(edges_req)

            # GOOD RESULT BUT GREEDY
        # # Search for connection between nodes
        # if len(params) > 1:
        #     for nodeActual in self.indexNodes:
        #         for nodeOther in self.indexNodes:
        #             edges_req = "MATCH (n1)-[e]->(n2) "
        #             edges_req += "WHERE ID(n1) = %s " % nodeActual
        #             edges_req += "AND ID(n2) = %s " % nodeOther
        #             edges_req += "RETURN ID(e),ID(n1),ID(n2),n2,e"
        #             self.createEdges(edges_req)

        print("Export")
        tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))

    def createWithout(self, types, private_gid):

        # Prepare node request
        node_req = "MATCH (n) "
        node_req += "WHERE NOT (n:%s) " % types[0]
        for type in types[1:]:
            node_req += "AND NOT (n:%s) " % type
        node_req += "AND NOT (n:language) "
        node_req += "AND NOT (n:group) "
        node_req += "AND NOT (n:post_type) "
        node_req += "AND NOT (n:role) "
        node_req += "AND NOT (n:tag) "
        node_req += "AND NOT (n:annotation) "
        node_req += "AND NOT (n:Day) "
        node_req += "AND NOT (n:Month) "
        node_req += "AND NOT (n:Year) "
        node_req += "AND NOT (n:TimeTreeRoot) "
        node_req += "RETURN ID(n),n"

        # Get the nodes of Neo4J
        self.createNodes(node_req)

        # Request edges
        edges_req = "MATCH (n1)-[e]->(n2) "
        edges_req += "WHERE NOT (n1)-[e:CREATED_ON]-(n2) "
        edges_req += "AND NOT (n1)-[e:POST_ON]-(n2) "
        edges_req += "AND NOT (n1)-[e:GROUP_IS]-(n2) "
        edges_req += "AND NOT (n1:%s) " % types[0]
        for type in types[1:]:
            edges_req += "AND NOT (n1:%s) " % type
        edges_req += "AND NOT (n2:%s) " % types[0]
        for type in types[1:]:
            edges_req += "AND NOT (n2:%s) " % type
        edges_req += "AND NOT (n1:Day) "
        edges_req += "AND NOT (n1:Month) "
        edges_req += "AND NOT (n1:Year) "
        edges_req += "AND NOT (n1:TimeTreeRoot) "
        edges_req += "AND NOT (n1:language) "
        edges_req += "AND NOT (n1:group) "
        edges_req += "AND NOT (n1:post_type) "
        edges_req += "AND NOT (n1:role) "
        edges_req += "AND NOT (n1:tag) "
        edges_req += "AND NOT (n1:annotation) "
        edges_req += "AND NOT (n2:language) "
        edges_req += "AND NOT (n2:group) "
        edges_req += "AND NOT (n2:post_type) "
        edges_req += "AND NOT (n2:role) "
        edges_req += "AND NOT (n2:tag) "
        edges_req += "AND NOT (n2:annotation) "
        edges_req += "AND NOT (n2:Day) "
        edges_req += "AND NOT (n2:Month) "
        edges_req += "AND NOT (n2:Year) "
        edges_req += "AND NOT (n2:TimeTreeRoot) "
        edges_req += "RETURN ID(e),ID(n1),ID(n2),n2,e"

        # Get the edges of Neo4J
        print("Read Edges")
        self.createEdges(edges_req)

        #add tag and user array as node property for the posts and comments nodes
        tag_associate_req = "MATCH (content)<-[:ANNOTATES]-(:annotation)-[:REFERS_TO]->(t:tag) "
        tag_associate_req += "WHERE content:post OR content:comment "
        tag_associate_req += "RETURN ID(content), COLLECT(DISTINCT t.tag_id)"

        self.nodeProperties["tagsAssociateNodeTlp"] = self.tulip_graph.getIntegerVectorProperty("tagsAssociateNodeTlp")
        result = self.neo4j_graph.run(tag_associate_req)
        for qr in result:
            self.nodeProperties["tagsAssociateNodeTlp"][self.indexNodes[qr[0]]] = qr[1]

        user_associate_req = "MATCH (content)<-[:AUTHORSHIP]-(n:user) "
        user_associate_req += "WHERE content:post OR content:comment "
        user_associate_req += "RETURN ID(content), COLLECT(DISTINCT n.user_id)"

        self.nodeProperties["usersAssociateNodeTlp"] = self.tulip_graph.getIntegerVectorProperty("usersAssociateNodeTlp")
        result = self.neo4j_graph.run(user_associate_req)
        for qr in result:
            self.nodeProperties["usersAssociateNodeTlp"][self.indexNodes[qr[0]]] = qr[1]

        print("Export")
        tlp.saveGraph(self.tulip_graph, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))
