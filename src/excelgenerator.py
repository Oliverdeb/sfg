from openpyxl import Workbook
from collections import OrderedDict


""" This class generates the an excel workbook """
class workbook_generator:

	def __init__(self):
		self.wb = Workbook()
		self.wb.active.title = ("Output")

	def toexcel(self, salt_masters, headings, dontdisplay):
		headings = [heading for heading in headings if heading not in dontdisplay]
		self.wb["Output"].append(["DU","Node"]+headings)

		for ip, nodes in salt_masters.iteritems():
			if nodes == "Could not connect to server":
				continue
			for node, grains in nodes.iteritems():
				if node == 'sm':
					continue
				row = []
				row.append(salt_masters[ip]['sm'])
				row.append(node)
				
				for key, value in grains.iteritems():
					if key in dontdisplay:
						continue 
					if (type(value) is OrderedDict or type(value) is dict) and value != {}:
						app = self.getall(	value)
					elif type(value) is list and value != []:
						app = ""
						for i, v in enumerate(value):
							if type(v) is OrderedDict or type(v) is dict:
								sep = "" if i == 0 else "; "
								app += sep + self.getall(v)
							else:
								sep = "" if i == 0 else ", "
								app += sep + v

					elif value != [] and value != {}:
						app = str(value)
					else:
						app = "None"

					row.append(app)
				self.wb["Output"].append(row)

		self.wb.save("output.xlsx")
		return "output.xlsx"

	def getall(self, value):
		# print str(value)
		cell = ""
		# print str(value)
		for i,(k,v) in enumerate(value.iteritems()):
			sep = "" if i == 0 else ", "

			if (type(v) is OrderedDict or type(v) is dict) and v != {}:
				cell += sep + self.getall(v)
			elif type(v) is list and v != []:
				cell += sep
				ret = k + ": "
				for i, x in enumerate(v):
					sep = "" if i == 0 else ", "
					ret += sep + x
				cell += sep +  ret
			elif v != {} and v != []:
				cell += sep + k + ": " + v				

		return cell
		
	