import string

import code
from parsebase import *

VARCHARS=string.ascii_letters+string.digits+"_$-"
OPCHARS=string.ascii_letters

def _numlike(c):
	return c.isdigit() or c=='.'

class Parser(ParserBase):
	def __init__(self,s=""):
		ParserBase.__init__(self,s)
		self.vars={} #name:graph node
		self.consts={} #const:number node
		self.block=None
		self.entry=None
	
	def parse_var(self):
		if not self.maybe("%"):
			return None
		
		start=self.pos
		while self.pos<len(self.text) and self.text[self.pos] in VARCHARS:
			self.pos+=1
		
		self.col+=self.pos-start
		name=self.text[start:self.pos]
		
		return name
	
	def parse_labelvar(self):
		if not self.maybe("#"):
			return None
		
		start=self.pos
		while self.pos<len(self.text) and self.text[self.pos] in VARCHARS:
			self.pos+=1
		
		self.col+=self.pos-start
		name=self.text[start:self.pos]
		if not name:
			return None
		
		return name
	
	def parse_const(self):
		start=self.pos
		while self.pos<len(self.text) and _numlike(self.text[self.pos]):
			self.pos+=1
			self.col+=1
		
		if start!=self.pos:
			num=self.text[start:self.pos]
			try:
				val=int(num)
			except ValueError:
				val=float(num)
			
			try:
				return self.consts[val]
			except KeyError:
				n=NumberNode(val)
				self.consts[val]=n
				return n
		
		return None
	
	def parse_val(self):
		var=self.parse_var()
		if var is not None:
			return self.vars[var]
		
		const=self.parse_const()
		if const is not None:
			return const
		
		label=self.parse_labelvar()
		if label:
			return self.vars[label]
		
		return None
	
	def parse_label(self):
		before=self.text[self.pos:]
		label=self.parse_labelvar()
		if label is not None:
			if not self.maybe(":"):
				raise ParseError(
					"Label declarations require a colon.",self.line,self.col
				)
			
			block=self.vars[label]=code.block()
			self.block.add(code.goto(block))
			self.block=block
			
			return True
		
		return False
	
	def parse_expr(self):
		start=self.pos
		while self.pos<len(self.text) and self.text[self.pos] in OPCHARS:
			self.pos+=1
		
		if start==self.pos:
			return None
		
		name=self.text[start:self.pos]
		if name in code.binary:
			argc=2
		elif name in code.unary:
			argc=1
		else:
			raise ParseError(
				'Unknown op "{}"'.format(name),self.line,self.col
			)
		
		self.col+=self.pos-start
		
		args=[]
		for x in range(argc):
			self.space()
			v=self.parse_val()
			if v:
				args.append(v)
			else:
				raise ParseError("Expected value",self.line,self.col)
		
		return code.do(name,*args)
	
	def parse_assign(self):
		var=self.parse_var()
		if var is None:
			return False
		if var in self.vars:
			raise ParseError(
				"Redeclaration of register {}".format(var),self.line,self.col
			)
		
		self.space()
		if not self.maybe('='):
			raise ParseError("Expected =",self.line,self.col)
		self.space()
		
		self.vars[var]=self.parse_expr()
		
		return True
	
	def parse(self,s):
		self.__init__(s)
		self.block=code.block()
		self.entry=self.block
		
		assign=True
		expr=None
		label=True
		while assign or expr or label:
			self.space()
			assign=self.parse_assign()
			
			self.space()
			expr=self.parse_expr()
			
			self.space()
			label=self.parse_label()
		
		return code.Code(self.entry,self.consts)

def parse(s):
	return Parser().parse(s)