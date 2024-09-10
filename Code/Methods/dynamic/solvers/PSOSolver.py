import csv
import os
import json
import random
import numpy as np

from .abstract_model import AbstractModel

class PSOSolver(AbstractModel):
	
	REQUESTDEPLOY = []
	ENABLERS = []
	NODES = []

	DEPLOYED_ENABLERS = []

	TASKS = 0	
	NODESNUM = 0
	
	POPULATION_SIZE = 600 # 600
	MAX_ITERATIONS = 80 # 80

	def __getSolutionPosition(self, n):
		return [int(n / len(self.NODES)), n % len(self.NODES)] # 0: software (deploy o conf); 1: nodo
		
	def __isValidSolution(self, state):		
		valueState = 0.0
		
		# Reviso las condiciones de cada servicio
		for i in range(self.TASKS):
			# Una solucion parcial es siempre valida
			if state[i] == -1:
				return 0.0
		
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
					valueState += 10.0
					continue
			
			
			# SOFTWARE
			
			# Compruebo si es valida la asignacion por tipo de servicio
			if req['service'] != enabler['service']:
				valueState += 10.0
				continue
				
			# Compruebo las capabilities pedidas para el software
			if not set(req['softwareCapabilities']).issubset(enabler['capabilities']):
				valueState += 7.0
				continue
				
			# Me aseguro que no sea un software baneado por la peticion
			if enabler['name'] in req['banSoftware']:
				valueState += 6.0
				continue
				
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
				continue
				
			# Me aseguro que no sea un software baneado por el nodo
			if enabler['name'] in node['nodes_specifications']['banSoftware']:
				valueState += 5.0
				continue
				
			# Compruebo las capabilities pedidas para el hardware
			if not set(req['hardwareCapabilities']).issubset(node['nodes_specifications']['capabilities']):
				valueState += 7.0
				continue
				
			# Reviso las hardConstraints
			# Latencia
			if  int(req['hardConstraints']['latency']) <  int(node['nodes_stats']['latency']):
				valueState += 7.0
				continue
			# Trust
			#if req['hardConstraints']['trust'] >  enabler['service']: 
			#	return False
			
			
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


	def __fitness(self, position):
		valueState = 0.0
		
		for i in range(self.TASKS):
			p = self.__getSolutionPosition(position[i])
			
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

		invalidSolutionValue = 10000*self.__isValidSolution(position)
		valueState += invalidSolutionValue

		return valueState 

	def __initialize_particles(self):
		particles = []
		for _ in range(self.POPULATION_SIZE):
			particle = {
				'position': [random.randint(0, self.NODESNUM-1) for _ in range(self.TASKS)],
				'velocity': [random.uniform(-1, 1) for _ in range(self.TASKS)],
				'best_position': [-1 for _ in range(self.TASKS)],
				'best_fitness': float('inf')
			}
			particles.append(particle)
		return particles

	def __update_particle(self, particle, global_best_position, w, c1, c2):
		for i in range(self.TASKS):
			r1 = random.random()
			r2 = random.random()

			particle['velocity'][i] = w * particle['velocity'][i] + c1 * r1 * (particle['best_position'][i] - particle['position'][i]) + c2 * r2 * (global_best_position[i] - particle['position'][i])

			# Apply velocity limits if necessary
			particle['velocity'][i] = max(particle['velocity'][i], -1)
			particle['velocity'][i] = min(particle['velocity'][i], 1)

			particle['position'][i] += int(round(particle['velocity'][i]))

			# Apply position limits if necessary
			particle['position'][i] = max(particle['position'][i], 0)
			particle['position'][i] = min(particle['position'][i], self.NODESNUM-1)

		particle_fitness = self.__fitness(particle['position'])
		if particle_fitness < particle['best_fitness']:
			particle['best_position'] = particle['position'].copy()
			particle['best_fitness'] = particle_fitness

	def __update_global_best(self, particles):
		global_best_position = particles[0]['best_position'].copy()
		global_best_fitness = particles[0]['best_fitness']
		for particle in particles:
			if particle['best_fitness'] < global_best_fitness:
				global_best_position = particle['best_position'].copy()
				global_best_fitness = particle['best_fitness']
		return global_best_position, global_best_fitness

	def __particle_swarm_optimization(self):
		particles = self.__initialize_particles()
		global_best_position, global_best_fitness = self.__update_global_best(particles)

		for _ in range(self.MAX_ITERATIONS):
			for particle in particles:
				self.__update_particle(particle, global_best_position, 0.7, 1.4, 1.4)
			global_best_position, global_best_fitness = self.__update_global_best(particles)

		return global_best_position

	def __printSolution(self, state, value):
		print("PSO")
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
		
		solution = self.__particle_swarm_optimization()
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






