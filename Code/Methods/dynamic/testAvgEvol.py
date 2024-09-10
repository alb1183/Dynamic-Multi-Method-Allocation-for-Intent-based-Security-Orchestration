import os
import json
import random
import time

from solvers.OptimalSolver import OptimalSolver
from solvers.GeneticSolver import GeneticSolver
from solvers.PSOSolver import PSOSolver
from solvers.RandomSolver import RandomSolver
from solvers.GreedySolver import GreedySolver



request = [{'name': 'front_end_rep1', 'service': 'HTTP_SERVER', 'location': 'SPAIN', 'hardConstraints': {'trust': 1, 'latency': '15'}, 'softConstraints': {'latency': 0}, 'softwareCapabilities': ['tls13', 'gzip', 'cookies'], 'hardwareCapabilities': [], 'affinity': [], 'anti-affinity': ['front_end_rep2'], 'banSoftware': ['GlassFish'], 'mspl_object': ''}, {'name': 'front_end_rep2', 'service': 'HTTP_SERVER', 'location': 'SPAIN', 'hardConstraints': {'trust': 1, 'latency': '15'}, 'softConstraints': {'latency': 0}, 'softwareCapabilities': ['tls13', 'gzip', 'cookies'], 'hardwareCapabilities': [], 'affinity': [], 'anti-affinity': ['front_end_rep1'], 'banSoftware': ['GlassFish'], 'mspl_object': ''}, {'name': 'data', 'service': 'DATABASE', 'location': 'ITALY', 'hardConstraints': {'trust': 1, 'latency': '30'}, 'softConstraints': {'latency': 0}, 'softwareCapabilities': ['SQL'], 'hardwareCapabilities': ['RAM-ECC', 'NVMe'], 'affinity': [], 'anti-affinity': [], 'banSoftware': ['PostgreSQL'], 'mspl_object': ''}, {'name': 'api', 'service': 'HTTP_SERVER', 'location': 'EUROPE', 'hardConstraints': {'trust': 1, 'latency': '50'}, 'softConstraints': {'latency': 0}, 'softwareCapabilities': ['tls13', 'PartialContent'], 'hardwareCapabilities': [], 'affinity': [], 'anti-affinity': ['front_end_rep1', 'front_end_rep2', 'database'], 'banSoftware': [], 'mspl_object': ''}, {'name': 'classificator', 'service': 'IMGCLASS', 'location': 'EUROPE', 'hardConstraints': {'trust': 1, 'latency': '50'}, 'softConstraints': {'latency': 0}, 'softwareCapabilities': ['IMAGENET'], 'hardwareCapabilities': [], 'affinity': [], 'anti-affinity': [], 'banSoftware': [], 'mspl_object': ''}]
deployed_enablers = []

softwareFile = open("metric/software.json")
softwareList = json.load(softwareFile)
softwareFile.close()

nodesFile = open("metric/nodes.json")
nodeList = json.load(nodesFile)
nodesFile.close()

solutionNumber = pow((len(softwareList)+len(deployed_enablers))*len(nodeList), len(request))
print("Request:", len(request))
print("SoftwareList:", len(softwareList))
print("NodeList:", len(nodeList))
print("Numero de soluciones posibles:", solutionNumber)

# Los muevo para forzar a que la salida no sea siempre la misma
#random.shuffle(request)
#random.shuffle(softwareList)
#random.shuffle(nodeList)


# Random changes
#for node in nodeList:
#	node['nodes_stats']['latency'] += (node['nodes_stats']['latency']/2)*random.random()
#	node['nodes_stats']['avgResponseTime'] += (node['nodes_stats']['avgResponseTime']/2)*random.random()
#	node['nodes_specifications']['CPUcost'] += (node['nodes_specifications']['CPUcost']/10)*random.random()
resultsGenetic = []
resultsPSO = []

for y in range(1, 21):
	fitnessGeneticA = 0
	timeGenetic = 0
	fitnessPSOA = 0
	timePSO = 0
	for x in range(1, 11):

		print("--------")
		start_time = time.time()
		solver = GeneticSolver()
		solution = solver.getSolution(request, softwareList, nodeList*x, deployed_enablers)
		#print(solution)
		fitnessGeneticA = fitnessGeneticA + solution['value']
		timeGenetic = timeGenetic + (time.time() - start_time)
		print("--- %s seconds ---" % (time.time() - start_time))

		print("--------")
		start_time = time.time()
		solver = PSOSolver()
		solution = solver.getSolution(request, softwareList, nodeList*x, deployed_enablers)
		#print(solution)
		fitnessPSOA = fitnessPSOA + solution['value']
		timePSO = timePSO + (time.time() - start_time)
		print("--- %s seconds ---" % (time.time() - start_time))


	resultsGenetic.append([y, fitnessGeneticA/10, timeGenetic/10])
	resultsPSO.append([y, fitnessPSOA/10, timePSO/10])
	
	print("fitnessGeneticA", fitnessGeneticA/10)
	print("fitnessPSOA", fitnessPSOA/10)
	print("timeGenetic", timeGenetic/10)
	print("timePSO", timePSO/10)
	print("Nodes: ", y)
	print("##################")
	print("##################")

print("---------------------")
print("resultsGenetic: ")
print(resultsGenetic)
print("resultsPSO:")
print(resultsPSO)
