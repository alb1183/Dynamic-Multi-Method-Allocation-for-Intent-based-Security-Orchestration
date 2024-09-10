
from abc import ABC, abstractmethod


class AbstractModel(ABC):

	@abstractmethod
	def getSolution(self, deploy, enablers, nodes):
		pass









