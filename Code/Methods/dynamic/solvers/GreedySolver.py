import csv
import os
import json
import random
import numpy as np

from .abstract_model import AbstractModel

class GreedySolver(AbstractModel):

	REQUESTDEPLOY = []
	ENABLERS = []
	NODES = []

	DEPLOYED_ENABLERS = []
	
	TASKS = 0	
	NODESNUM = 0

	def __getSolutionPosition(self, n):
		return [int(n / len(self.NODES)), n % len(self.NODES)] # 0: software (deploy o conf); 1: nodo
		
	def __isValidElement(self, state, i, element):
		valueState = 0.0
		# Una solucion parcial es siempre valida
		if element == -1:
			return 0.0
	
		p = self.__getSolutionPosition(element)
		req = self.REQUESTDEPLOY[i]
		node = self.NODES[p[1]]
		isDeploy = p[0] < len(self.ENABLERS)
		enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
		
		
		# Si es una reconfiguracion
		if not isDeploy:
			deployedPos = p[0]-len(self.ENABLERS)
			
			# Si no es el nodo donde está el software ya desplegado
			if not node['node_name'] in self.DEPLOYED_ENABLERS[deployedPos]['nodes']:
				valueState += 10.0
		
		# SOFTWARE
		
		# Compruebo si es valida la asignacion por tipo de servicio
		if req['service'] != enabler['service']:
			valueState += 10.0
			
		# Compruebo las capabilities pedidas para el software
		if not set(req['softwareCapabilities']).issubset(enabler['capabilities']):
			valueState += 7.0
			
		# Me aseguro que no sea un software baneado por la peticion
		if enabler['name'] in req['banSoftware']:
			valueState += 6.0
			
		# Compruebo la affinity
		# TODO
		
		# Compruebo la anti-affinity
		# Reviso el resto de tareas
		for j in range(self.TASKS):
			# Solucion parcial
			if state[j] == -1:
				break
			
			# No es la tarea actual
			if j != i:
				p2 = self.__getSolutionPosition(state[j])
				req2 = self.REQUESTDEPLOY[j]
				# Si está tarea está asignada en el mismo nodo que la principal, compruebo que no esté en las antiafinidades
				if p2[1] == p[1] and req2['name'] in req['anti-affinity']:
					valueState += 8.0
					break
		
		
		# HARDWARE
		# Compruebo si es valida la localicacion asignada
		if req['location'] != "EUROPE" and req['location'] != node['nodes_specifications']['location']:
			valueState += 6.0
			
		# Me aseguro que no sea un software baneado por el nodo
		if enabler['name'] in node['nodes_specifications']['banSoftware']:
			valueState += 5.0
			
		# Compruebo las capabilities pedidas para el hardware
		if not set(req['hardwareCapabilities']).issubset(node['nodes_specifications']['capabilities']):
			valueState += 7.0
			
		# Reviso las hardConstraints
		# Latencia
		if int(req['hardConstraints']['latency']) < int(node['nodes_stats']['latency']):
			valueState += 7.0
		# Trust
		#if req['hardConstraints']['trust'] >  enabler['service']: 
		#	return False
		
		return valueState
		
	def __isValidSolution(self, state):
		valueState = 0.0
		
		# Reviso las condiciones de cada servicio
		for i in range(self.TASKS):
			valueState += self.__isValidElement(state, i, state[i])
			
		
		# Si no se cumple alguna condicion salgo directamente y me ahorro la comprobacion de abajo (es costosa)
		if valueState > 0: # Poner algun valor mas alto? p.e. 14.0? asi dejo que alguna entre a abajo
			return valueState
		
		# Reviso los equipos para asegurar sus restricciones
		# Checks, por nodo
		for i in range(len(self.NODES)):
			usedCPU = 0
			usedRam = 0
			usedDisk = 0
			
			availableCPU = self.NODES[i]['cpu_allocatable']
			availableRam = self.NODES[i]['ram_allocatable']
			availableDisk = self.NODES[i]['disk_allocatable']
			
			# Reviso las tareas asignadas a este nodo
			for j in range(self.TASKS):
				p = self.__getSolutionPosition(state[j])
				if p[1] == i:
					usedCPU += self.ENABLERS[p[0]]['cpu']
					usedRam += self.ENABLERS[p[0]]['ram']
					usedDisk += self.ENABLERS[p[0]]['disk']
			
			# Si alguno se pasa del limite es una solucion no valida
			if usedCPU > availableCPU or usedRam > availableRam or usedDisk > availableDisk:
				valueState += 8.0
				break # Seguro?


		return valueState

	def __fitnessElement(self, node, enabler, isDeploy):
	
		valueState = 0.0
		avgDeployTime = enabler['stats']['avgDeployTime'] #+ random.random()*100
		if isDeploy:
			avgDeployTime = avgDeployTime*10
		
		highVulnerabilities = enabler['stats']['highVulnerabilities']
		
		latency = node['nodes_stats']['latency']
		#latency += (latency/2)*random.random()
		
		avgResponseTime = node['nodes_stats']['avgResponseTime']
		#avgResponseTime += (avgResponseTime/2)*random.random()
		
		CPUspeed = node['nodes_specifications']['CPUspeed']
		
		CPUcost = node['nodes_specifications']['CPUcost']
		#CPUcost += (CPUcost/10)*random.random()
		
		valueState += latency*8.0 + avgDeployTime*0.8 + avgResponseTime*0.2 - (CPUspeed-8000)*0.15 + (CPUspeed-8000)*CPUcost*0.15 + highVulnerabilities*10
		return valueState

	def __fitness(self, individual):
		valueState = 0.0
		
		for i in range(self.TASKS):
			p = self.__getSolutionPosition(individual[i])
			
			node = self.NODES[p[1]]
			isDeploy = p[0] < len(self.ENABLERS)
			enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
			
			valueState += self.__fitnessElement(node, enabler, isDeploy)
			#print(latency*8.0, avgDeployTime*0.8, avgResponseTime*0.2, (CPUspeed-8000)*0.2, (CPUspeed-8000)*CPUcost*0.2, highVulnerabilities*10)

		invalidSolutionValue = 10000*self.__isValidSolution(individual)
		valueState += invalidSolutionValue
		#if not self.__isValidSolution(individual):
		#	valueState += 100000

		return valueState 


	def __greedy_algorithm(self):
		state = [-1] * self.TASKS
		for i in range(self.TASKS):
			req = self.REQUESTDEPLOY[i]
			
			#enablersReq = [e for e in self.ENABLERS if e['service'] == req['service']]
			valueFit = 9999999
			bestEn = -1
			bestNode = -1
			for en in range(len(self.ENABLERS)):
				if self.ENABLERS[en]['service'] != req['service']:
					continue
				
				for n in range(len(self.NODES)):
					value = self.__isValidElement(state, i, en*len(self.NODES) + n)*100 + self.__fitnessElement(self.NODES[n], self.ENABLERS[en], False)
					#print(req['name'], "-", self.ENABLERS[en]['name'], "->", self.NODES[n]['node_name'], ":", value)
					if value < valueFit:
						valueFit = value
						bestEn = en
						bestNode = n
						
			
			state[i] = bestEn*len(self.NODES) + bestNode
		
		return state
		

	def __printSolution(self, state, value):
		print("Greedy")
		print(state)
		print(value)
		print(self.__isValidSolution(state))
		for i in range(self.TASKS):
			p = self.__getSolutionPosition(state[i])
			isDeploy = p[0] < len(self.ENABLERS)
			enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
			print(enabler['name'], "en nodo", self.NODES[p[1]]['node_name'], "reconfigurado", not isDeploy)
			
	def getSolution(self, deploy, enablers, nodes, deployedEnablers):
		self.REQUESTDEPLOY = deploy
		self.ENABLERS = enablers
		self.NODES = nodes
		
		self.DEPLOYED_ENABLERS = deployedEnablers
		
		self.TASKS = len(deploy)
		self.NODESNUM = (len(enablers)+len(self.DEPLOYED_ENABLERS))*len(nodes)
	
		solution = self.__greedy_algorithm()
		fitness = self.__fitness(solution)
		#solutionS = ';'.join(map(str, solution))
		self.__printSolution(solution, fitness)
		#solv = fitness(solution)
		
		solutionClean = []
		for i in range(self.TASKS):
			p = self.__getSolutionPosition(solution[i])
			isDeploy = p[0] < len(self.ENABLERS)
			enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
			solutionClean.append({'mspl_object': self.REQUESTDEPLOY[i]['mspl_object'], 'name': self.REQUESTDEPLOY[i]['name'], 'service': self.REQUESTDEPLOY[i]['service'], 'software': enabler['name'], 'deploy': isDeploy, 'node': self.NODES[p[1]]['node_name']})
		
		
		return {"solution": solutionClean, "value": fitness}







