import collections
from typing import List
import heapq
import pprint

class Network:
    def __init__(self, filepath: str):
        self.directory = {}                             #holds key-value pairs for every person in the population of email:[name, risklevel] (risklevel from 0 to 4, 4 being a positive test case)
        self.network = collections.defaultdict(list)    #graph that holds all friend connections in the format email1 : [[email2,frequency2], [email3,frequency3], ... ] (frequency from 1 to 7 based on how many times per week email1 and email2 see each other). Graph is undirected so email2 -> email1 also exists
        self.buildNetwork(filepath)                     #builds the directory and network based on the input file at filepath

    #adds person to the directory
    def addPerson(self, email: str, name: str, risk:int):
        if email not in self.directory :
            self.directory[email] = [name,risk]

    #adds connection between two people to the network. Again, the graph is undirected so we cover both directions.
    def addConnection(self, email1:str, email2:str, frequency:int):
        self.network[email1].append([email2,frequency])
        self.network[email2].append([email1,frequency])

    #parses the input file, adding each person to the directory with initial risklevel of 0, and each connection to the network
    def buildNetwork(self, filepath: str):
        connection_list = open(filepath, "r")
        for connection in connection_list:
            person1,person2,frequency = connection.split(' ')
            person1_name,person1_email = person1.split(',')
            person2_name,person2_email = person2.split(',')
            self.addPerson(person1_email, person1_name, 0)
            self.addPerson(person2_email, person2_name, 0)
            self.addConnection(person1_email, person2_email, int(frequency))

    # detects 'dangerous connections'
    # A dangerous connection is a single friendship which bridges between friend groups. Both groups can be exposed to the virus if one group gets it.
    # In CS terms, we are finding bridges between strongly connected components using Tarjan's Algorithm
    def findBridges(self, sendAlert: bool) -> List[List[int]] :
        bridges = []
        dfs_order = 0
        parent = {email:None for email in self.directory}    #PERFORMANCE IMPROVEMENT: could move to just info{} key:value would be email:[parent,order,low]. Would save some memory and def would save computation time. Leaving it for now for readability
        order = {email:None for email in self.directory}     #order of visitation (crucial for Tarjan's)
        low = {email:None for email in self.directory}       #earliest visited node reachable from this node without moving back over parent. (follows Tarjans's)

        #the heart of Tarjan's algorithm is implemented here, in search
        def search(node:str): #node is just an email to represent the node in the graph
            if order[node] == None:
                nonlocal dfs_order
                order[node] = low[node] = dfs_order
                dfs_order += 1
                for neighbor_data in self.network[node]:
                    neighbor = neighbor_data[0]     #neighbor's email (used for keying into network and directory)
                    if order[neighbor] == None:
                        parent[neighbor] = node
                        search(neighbor)
                        if low[neighbor] > low[node]:
                            nonlocal bridges
                            bridges.append([neighbor,node])
                        else:
                            low[node] = min(low[node], low[neighbor])
                    elif neighbor != parent[node]:
                        low[node] = min(low[neighbor],low[node])
        #run on each person in our population, even those in seperate components of the graph (network)
        for email in self.directory:
            search(email)
        if(sendAlert):
            self.sendBridgeNotifications(bridges)
        return bridges

    #simulates a person testing positive for COVID, and updates the people in their network with a corresponding risk factor
    # RISK LEVELS
    #     5 : INFECTED
    #     4 : VERY HIGH
    #     3 : HIGH
    #     2 : MEDIUMHIGH
    #     1: MEDIUM
    #     0: LOW
    # the risk factor for each neighbor is determined by the frequency they see each other
    # the risk factor will propogate appropriately to "friends of friends"
    # We will use a modified version of Dijkstra's algorithm
    def positiveCase(self, infected_email: str, sendAlert: bool):
        #mark this person as infected.
        self.directory[infected_email][1] = 5
        #mark infected person's immediate neighbors as "very high risk"
        for neighbor_data in self.network[infected_email]:
            self.directory[neighbor_data[0]][1] = 4

        visited = set()
        queue = []
        #building the unvisited queue, each element is [-risk,email]. Risk is negative because it will work better with heapq as a min heap
        for email in self.directory:
            queue.append([-self.directory[email][1], email])
        heapq.heapify(queue)

        #starting the main logic of modified Dijkstra's algorithm
        while(len(queue)):
            source = heapq.heappop(queue)[1]    #source's email
            visited.add(source)

            for neighbor_data in self.network[source]:
                neighbor = neighbor_data[0]     #neighbor's email for keying into directory and network
                if neighbor in visited:
                    continue
                frequency = neighbor_data[1]    #frequency of visitation between neighbor and source
                source_risk = self.directory[source][1]
                new_risk = self.risk(source_risk,frequency) #risk transferrable from source to neighbor. Depends on frequency of visitation and the risk of the source node.

                if new_risk > self.directory[neighbor][1]: #if the risk between these two is greater than others encountered so far for neighbor, update neighbor's risk
                    #update directory with new risk
                    self.directory[neighbor][1] = new_risk
                    #update visited_queue with new risk
                    for i in range(len(queue)):
                        if queue[i][1] == neighbor:
                            queue[i][0] = -new_risk
                            heapq.heapify(queue)
        if(sendAlert):
            self.sendRiskNotifications(infected_email)

    #handles all rules about risk transmission between people of various risk types.
    def risk(self, source_risk:int, frequency:int) -> int:
        if source_risk == 0 or frequency >= 4:
            return source_risk
        #if frequency is 2 or 3, risk will be reduced by 1 for the neighbor
        if frequency >= 2:
            if source_risk >= 1:
                 return source_risk - 1
            else:
                return source_risk
        #if frequency is 1, risk will be reduced by 2 for the neighbor if possible
        else:
            if source_risk >= 2:
                 return source_risk - 2
            else:
                return 0

    #given the email of someone who just tested positive, notify others in their network about their new risk level
    def sendRiskNotifications(self, infected_email: str):
        def sendMessage(recipient_email: str):
            if(infected_email == recipient_email):
                print(f"(Sent to {recipient_email}) Attention {self.directory[recipient_email][0]}: You have tested positive for COVID-19. Please immediately enter into self-quarantine for 14 days.")
            else:
                print(f"(Sent to {recipient_email}) Attention {self.directory[recipient_email][0]}: {self.directory[infected_email][0]} has tested positive for COVID-19. Our records indicate you are in the same social circle. Your risk factor for contracting COVID-19 is listed as {self.directory[recipient_email][1]}, on a scale from 0 (low risk) to 5(infected).")

        #Depth first search through the network from the infected email and send each person in this component a notification
        visited = set()
        def dfs(node: str):
            if node not in visited:
                sendMessage(node)
                visited.add(node)
                for neighbor_data in self.network[node]:
                    dfs(neighbor_data[0])
        dfs(infected_email)
        print("\n")

    #Takes in pairs of emails which form dangerous connections (as described in findBridges) and notifies both parties.
    def sendBridgeNotifications(self, bridges: List[List[str]]):
        def sendMessage(emails: List[str]):
            print(f"(Sent to {emails[0]}) Dear {self.directory[emails[0]][0]}, our data indicates that your relationship with {self.directory[emails[1]][0]} could potentially be dangerous for public health because it bridges two social circles who otherwise would not be in contact. Please wear a mask and socially distance if you are around them. They have recieved this same message.")
            print(f"(Sent to {emails[1]}) Dear {self.directory[emails[1]][0]}, our data indicates that your relationship with {self.directory[emails[0]][0]} could potentially be dangerous for public health because it bridges two social circles who otherwise would not be in contact. Please wear a mask and socially distance if you are around them. They have recieved this same message.")
        for bridge in bridges:
            sendMessage(bridge)
        print("\n")


    #helper function designed for visualizing the network and directory
    def prettyprint(self, obj) :
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(obj)

if __name__ == "__main__":
    FILEPATH = "friends.txt"
    test_network = Network(FILEPATH)
    bridges = test_network.findBridges(sendAlert=True)
    test_network.positiveCase("liam@email.com", sendAlert=True)




    #pp.pprint(test_network.network)