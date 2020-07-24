from tulip import *
from py2neo import *
import configparser
import os
from graphtulip.createPostCommentTagTlp import CreatePostCommentTagTlp

config = configparser.ConfigParser()
config.read("config.ini")


# todo create a unique Createtlp to avoid code duplication
class CreateTagFullTlp(object):
    def __init__(self, value, start, end, force_fresh):
        super(CreateTagFullTlp, self).__init__()
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
        self.filter_occ = value
        self.date_start = start
        self.date_end = end
        self.force_fresh = force_fresh
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
        nodeProperties = {}
        edgeProperties = {}
        max_occ = 1

        if (not os.path.exists("%s%s.tlp" % (config['exporter']['tlp_path'], "TTT"))) or self.force_fresh == 1:
            creatorPCT = CreatePostCommentTagTlp(self.date_start, self.date_end, self.force_fresh)
            creatorPCT.create()
            self.tulip_graph = tlp.loadGraph("%s%s.tlp" % (config['exporter']['tlp_path'], "PostCommentTag"))

            print("Compute Tag-Tag graph")
            tmpIDNode = self.tulip_graph.getStringProperty("tmpIDNode")
            labelsNodeTlp = self.tulip_graph.getStringVectorProperty("labelsNodeTlp")
            labelEdgeTlp = self.tulip_graph.getStringProperty("labelEdgeTlp")
            entityType = self.tulip_graph.getStringProperty("entityType")
            edgeProperties["occ"] = self.tulip_graph.getIntegerProperty("occ")
            edgeProperties["TagTagSelection"] = self.tulip_graph.getBooleanProperty("TagTagSelection")
            edgeProperties["TagTagSelection"].setAllNodeValue(False)
            edgeProperties["TagTagSelection"].setAllEdgeValue(False)
            edgeProperties["viewLabel"] = self.tulip_graph.getStringProperty("viewLabel")
            edgeProperties["type"] = self.tulip_graph.getStringProperty("type")
            edgeProperties["viewColor"] = self.tulip_graph.getColorProperty("viewColor")
            edgeProperties["viewSize"] = self.tulip_graph.getSizeProperty("viewSize")
            edgeProperties['tag_1'] = self.tulip_graph.getStringProperty("tag_1")
            edgeProperties['tag_2'] = self.tulip_graph.getStringProperty("tag_2")
            for t1 in self.tulip_graph.getNodes():
                if entityType[t1] == "tag":
                    edgeProperties["TagTagSelection"][t1] = True
                    for p in self.tulip_graph.getOutNodes(t1):
                        if entityType[p] == "post" or entityType[p] == "comment":
                            for t2 in self.tulip_graph.getInNodes(p):
                                if t1 != t2:
                                    e=self.tulip_graph.existEdge(t1, t2, False)
                                    if e.isValid():
                                        edgeProperties["occ"][e] += 1
                                        edgeProperties["viewLabel"][e] = "occ ("+str(edgeProperties["occ"][e]/2)+")"
                                        labelEdgeTlp[e] = "occ ("+str(edgeProperties["occ"][e]/2)+")"
                                        e_val = edgeProperties['occ'][e]
                                        max_occ = max(max_occ, e_val)
                                        if e_val > edgeProperties["occ"][t1]:
                                            edgeProperties["occ"][t1] = e_val
                                            edgeProperties["viewSize"][t1] = tlp.Size(e_val, e_val, e_val)
                                        if e_val > edgeProperties["occ"][t2]:
                                            edgeProperties["occ"][t2] = e_val
                                            edgeProperties["viewSize"][t2] = tlp.Size(e_val, e_val, e_val)
                                    else:
                                        e = self.tulip_graph.addEdge(t1, t2)
                                        edgeProperties["occ"][e] = 1
                                        edgeProperties["TagTagSelection"][t2] = True
                                        edgeProperties["TagTagSelection"][e] = True
                                        edgeProperties["viewLabel"][e] = "occ ("+str(edgeProperties["occ"][e]/2)+")"
                                        labelEdgeTlp[e] = "occ ("+str(edgeProperties["occ"][e]/2)+")"
                                        edgeProperties["type"][e] = "curve"
                                        edgeProperties["viewColor"][e] = self.colors['edges']
                                        edgeProperties['tag_1'][e] = tmpIDNode[t1]
                                        edgeProperties['tag_2'][e] = tmpIDNode[t2]
            sg = self.tulip_graph.addSubGraph(edgeProperties["TagTagSelection"])
            tlp.saveGraph(sg, "%s%s.tlp" % (config['exporter']['tlp_path'], "TTT"))
        else:
            sg = tlp.loadGraph("%s%s.tlp" % (config['exporter']['tlp_path'], "TTT"))
            edgeProperties["occ"] = sg.getIntegerProperty("occ")
            max_occ = edgeProperties["occ"].getNodeMax()

        print("Filter occ")
        edgeProperties["occ"] = sg.getIntegerProperty("occ")
        for t in sg.getNodes():
            if edgeProperties["occ"][t]/2 < self.filter_occ:
                sg.delNode(t)
                continue
            tmp_val = (float(edgeProperties["occ"][t])/max_occ)*(self.nb_step-1)+1
            edgeProperties["occ"][t] = int(tmp_val)
            for e in sg.getOutEdges(t):
                if edgeProperties["occ"][e]/2 < self.filter_occ:
                    sg.delEdge(e)
                    continue
                tmp_val = (float(edgeProperties["occ"][e])/max_occ)*(self.nb_step-1)+1
                edgeProperties["occ"][e] = int(tmp_val)


        print("Export")
        tlp.saveGraph(sg, "%s%s.tlp" % (config['exporter']['tlp_path'], private_gid))


