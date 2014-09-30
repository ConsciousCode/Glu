import string

import code
from parsebase import *

VARCHARS=string.ascii_letters+string.digits+"_$-"
OPCHARS=string.ascii_letters

class Context:
	'''
	Context for how the assembly codes are flattened.
	'''
	def __init__(self,consts,labels):
		self.consts=consts
		self.labels=labels

class Arg:
	'''
	Glu assembly compiler helper used to represent opcode arguments while
	register ids are still uncertain.
	'''
	def __init__(self,id):
		#+1 because 0 is the "null register"
		self.id=id+1
	
	def __repr__(self):
		return "@{}".format(self.id)

class Null(Arg):
	'''
	Used to represent the null register, a special-case "register" which tells
	the compiler to either throw away an opcode's result or fill in extra
	arguments for unary or nullary opcodes.
	'''
	def __init__(self):
		Arg.__init__(self,0)
	
	def flatten(self,context):
		return 0
	
	def __repr__(self):
		return "null"

class Var(Arg):
	'''
	Represents a variable register.
	'''
	def flatten(self,context):
		return len(context.consts)+self.id

class Const(Arg):
	'''
	Represents a reference to a constant in the constant table.
	'''
	def flatten(self,context):
		return self.id

class Label:
	'''
	Represents a label, which is looked up on compile time.
	'''
	def __init__(self,name):
		self.name=name
	
	def __repr__(self):
		return "#{}".format(self.name)
	
	def flatten(self,context):
		return context.labels[self.name]+1

class Opcode:
	'''
	The actual opcode.
	'''
	def __init__(self,op,dst,args):
		self.op=op
		self.dst=dst
		self.args=args
	
	def flatten(self,consts):
		return code.Opcode(
			self.dst.flatten(consts),self.op,
			[x.flatten(consts) for x in self.args]
		)
	
	def __repr__(self):
		return "({} {})".format(
			self.op,' '.join(repr(x) for x in self.args)
		)

def _numlike(c):
	return c.isdigit() or c=='.'

class Parser(ParserBase):
	def __init__(self,s=""):
		ParserBase.__init__(self,s)
		self.vars=[]
		self.consts=[]
		self.labels={}#name:const id
		self.pc=0
	
	def parse_var(self,val=True):
		if not self.maybe("%"):
			return None
		
		start=self.pos
		while self.pos<len(self.text) and self.text[self.pos] in VARCHARS:
			self.pos+=1
		
		self.col+=self.pos-start
		name=self.text[start:self.pos]
		try:
			if val:
				return Var(self.vars.index(name))
			if self.vars.index(name):
				raise ParseError("Glu asm uses SSA",self.line,self.col)
			return Var(self.vars.index(name))
		except ValueError:
			if val:
				raise ParseError(
					"Using unassigned register",self.line,self.col
				)
			self.vars.append(name)
			return Var(len(self.vars)-1)
	
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
		
		return Label(name)
	
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
				return Const(self.consts.index(val))
			except ValueError:
				self.consts.append(val)
				return Const(len(self.consts)-1)
		
		return None
	
	def parse_val(self):
		var=self.parse_var()
		if var:
			return var
		
		const=self.parse_const()
		if const:
			return const
		
		label=self.parse_labelvar()
		if label:
			return label
		
		x=self.pos
		while self.pos<len(self.text) and self.text[self.pos] in OPCHARS:
			self.pos+=1
			self.col+=1
		
		if self.text[x:self.pos]=="null":
			return Null()
		
		return None
	
	def parse_label(self):
		before=self.text[self.pos:]
		label=self.parse_labelvar()
		if label:
			if not self.maybe(":"):
				raise ParseError(
					"Label declarations require a colon.",self.line,self.col
				)
			if label.name in self.labels:
				raise ParseError(
					'Redeclaration of label "{}"'.format(label.name),
					self.line,self.col
				)
			
			self.consts.append(code.Label(self.pc))
			self.labels[label.name]=len(self.consts)-1
			return label
		
		return None
	
	def parse_expr(self,dst=Null()):
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
		
		self.pc+=1
		
		return Opcode(name,dst,args)
	
	def parse_assign(self):
		var=self.parse_var(False)
		if var is None:
			return None
		
		self.space()
		if not self.maybe('='):
			raise ParseError("Expected =",self.line,self.col)
		self.space()
		
		expr=self.parse_expr(var)
		
		return expr
	
	def parse(self,s):
		self.__init__(s)
		c=[]
		
		assign=True
		var=True
		label=True
		while assign or var or label:
			self.space()
			assign=self.parse_assign()
			if assign:
				c.append(assign)
			
			self.space()
			var=self.parse_expr()
			if var:
				c.append(var)
			
			self.space()
			label=self.parse_label()
		context=Context(self.consts,self.labels)
		c=[x.flatten(context) for x in c]
		
		return code.Code(c,self.consts)

def parse(s):
	return Parser().parse(s)