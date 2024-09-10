import csv
import os
import json
import random
import numpy as np

from .abstract_model import AbstractModel

import math

class OptimalSolver(AbstractModel):

	REQUESTDEPLOY = []
	NODES = []
	ENABLERS = []
	
	DEPLOYED_ENABLERS = []

	TASKS = 0	
	NODESNUM = 0
	
	SOLTESTED = 0
	SOLVALID = 0
	
	SOLSPACE = 0
	NEXTPERCENTAGE = 0

	def __getSolutionPosition(self, n):
		return [int(n / len(self.NODES)), n % len(self.NODES)] # 0: software (deploy o conf); 1: nodo

	def __isValidSolution(self, state):
		self.SOLTESTED += 1
		
		if math.floor((self.SOLTESTED / self.SOLSPACE) * 10) == self.NEXTPERCENTAGE:
			print(self.NEXTPERCENTAGE*10, "%")
			#logger.info("{}% - {} of {}".format(self.NEXTPERCENTAGE*10, self.SOLTESTED, self.SOLSPACE))
			self.NEXTPERCENTAGE += 1
			
		
		# Reviso las condiciones de cada servicio
		for i in range(self.TASKS):
			# Una solucion parcial es siempre valida
			if state[i] == -1:
				return True
		
			p = self.__getSolutionPosition(state[i])
			req = self.REQUESTDEPLOY[i]
			node = self.NODES[p[1]]
			isDeploy = p[0] < len(self.ENABLERS)
			enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
			
			# Si es una reconfiguracion
			if not isDeploy:
				deployedPos = p[0]-len(self.ENABLERS)
				
				# Si no es el nodo donde está el software ya desplegado
				if not node['node_name'] in self.DEPLOYED_ENABLERS[deployedPos]['nodes']:
					return False
			
			# SOFTWARE
			
			# Compruebo si es valida la asignacion por tipo de servicio
			if req['service'] != enabler['service']:
				return False
				
			# Compruebo las capabilities pedidas para el software
			if not set(req['softwareCapabilities']).issubset(enabler['capabilities']):
				return False
				
			# Me aseguro que no sea un software baneado por la peticion
			if enabler['name'] in req['banSoftware']:
				return False
				
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
						return False
			
			
			# HARDWARE
			# Compruebo si es valida la localicacion asignada
			if req['location'] != "EUROPE" and req['location'] != node['nodes_specifications']['location']:
				return False
				
			# Me aseguro que no sea un software baneado por el nodo
			if enabler['name'] in node['nodes_specifications']['banSoftware']:
				return False
				
			# Compruebo las capabilities pedidas para el hardware
			if not set(req['hardwareCapabilities']).issubset(node['nodes_specifications']['capabilities']):
				return False
				
			# Reviso las hardConstraints
			# Latencia
			if int(req['hardConstraints']['latency']) < int(node['nodes_stats']['latency']):
				return False
			# Trust
			#if req['hardConstraints']['trust'] >  enabler['service']: 
			#	return False
			
			
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
				pTemp = self.__getSolutionPosition(state[j])
				isDeployTemp = pTemp[0] < len(self.ENABLERS)
				if pTemp[1] == i and isDeployTemp:
					usedCPU += self.ENABLERS[pTemp[0]]['cpu']
					usedRam += self.ENABLERS[pTemp[0]]['ram']
					usedDisk += self.ENABLERS[pTemp[0]]['disk']
			
			# Si alguno se pasa del limite es una solucion no valida
			if usedCPU > availableCPU or usedRam > availableRam or usedDisk > availableDisk:
				return False


		
		return True


	def __solutionValue(self, state):
		valueState = 0.0
		
		#valueState = random.random() * 100
		for i in range(self.TASKS):
			p = self.__getSolutionPosition(state[i])
			
			node = self.NODES[p[1]]
			isDeploy = p[0] < len(self.ENABLERS)
			enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
			
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
			#print(latency*8.0, avgDeployTime*0.8, avgResponseTime*0.2, (CPUspeed-8000)*0.2, (CPUspeed-8000)*CPUcost*0.2, highVulnerabilities*10)
		
		self.SOLVALID += 1
		
		return valueState
			
	def __isValidState(self, n):
		return n == self.TASKS-1

	def __isFinalState(self, state):
		return state == [self.NODESNUM-1] * self.TASKS

	def __goNextLevel(self, n):
		return n < self.TASKS-1

	# Backtracking
	def __optimalSearch(self):
		state = [-1] * self.TASKS
		nivel = 0
		bestValue = float('inf')
		solution = [-1] * self.TASKS
		while nivel != -1:
			state[nivel] += 1
			if self.__isValidState(nivel) and self.__isValidSolution(state):
				#print(state)
				valueS = self.__solutionValue(state)
				#self.__printSolution(state, valueS)
				if valueS < bestValue:
					bestValue = valueS
					solution = state.copy()
					#print(state)
			if self.__goNextLevel(nivel) and self.__isValidSolution(state):
				nivel += 1

			else:
				while state[nivel] == self.NODESNUM-1:
					state[nivel] = -1
					nivel -= 1
		return solution

	def __printSolution(self, state, value):
		print("Optimal")
		print(state)
		print(value)
		for i in range(self.TASKS):
			p = self.__getSolutionPosition(state[i])
			isDeploy = p[0] < len(self.ENABLERS)
			enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
			print(enabler['name'], "en nodo", self.NODES[p[1]]['node_name'], "reconfigurado", not isDeploy)
			#logger.info("{} en nodo {}, reconfigurado {}".format(enabler['name'], self.NODES[p[1]]['node_name'], not isDeploy))
	
	def getSolution(self, deploy, enablers, nodes, deployedEnablers):
		self.REQUESTDEPLOY = deploy
		self.ENABLERS = enablers
		self.NODES = nodes
		
		self.DEPLOYED_ENABLERS = deployedEnablers
		
		self.TASKS = len(deploy)
		self.NODESNUM = (len(enablers)+len(self.DEPLOYED_ENABLERS))*len(nodes)
		
		self.SOLSPACE = pow((len(enablers)+len(deployedEnablers))*len(nodes), len(deploy))
		
		solution = self.__optimalSearch()
		value = self.__solutionValue(solution)
		#solutionS = ';'.join(map(str, solution))
		self.__printSolution(solution, value)
		print("Soluciones comprabadas", self.SOLTESTED, ", Soluciones validas:", self.SOLVALID)
		#logger.info("Soluciones comprabadas {}, Soluciones validas:{}".format(self.SOLTESTED, self.SOLVALID))
		#solv = fitness(solution)
		
		solutionClean = []
		for i in range(self.TASKS):
			p = self.__getSolutionPosition(solution[i])
			isDeploy = p[0] < len(self.ENABLERS)
			enabler = self.ENABLERS[p[0]] if isDeploy else [e for e in self.ENABLERS if e['name'] == self.DEPLOYED_ENABLERS[p[0]-len(self.ENABLERS)]['software'] ][0]
			solutionClean.append({'mspl_object': self.REQUESTDEPLOY[i]['mspl_object'], 'name': self.REQUESTDEPLOY[i]['name'], 'service': self.REQUESTDEPLOY[i]['service'], 'software': enabler['name'], 'deploy': isDeploy, 'node': self.NODES[p[1]]['node_name']})
		
		
		return {"solution": solutionClean, "value": value}






