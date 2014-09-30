from collections import deque
from parsebase import *
import code
import tokenize

#Constants to make operator associativity more sensical
left=False
right=True

class Opdef:
	'''
	Used for storing information used in interpreting operatorss.
	'''
	def __init__(self,code,priority,assoc=left):
		self.code=code
		self.priority=priority
		self.assoc=assoc

unary={
	"-":Opdef("neg",3)
}

binary={
	"+":Opdef("add",1),
	"-":Opdef("sub",1),
	"*":Opdef("mul",2),
	"/":Opdef("div",2),
	"keyword":Opdef(None,4)
}

miscops={
	"(":Opdef("",0),
	")":Opdef("",998),
	";":Opdef("",999)
}
keywords={
	"return":Opdef("return",0)
}

class Context:
	def __init__(self,consts,labels):
		self.consts=consts
		self.varid=0
		self.pc=0
		self.labels=labels

class ValueNode:
	'''
	AST node representing a value.
	'''
	def __init__(self,tok,id):
		self.tok=tok
		self.id=id+1
	
	def __repr__(self):
		return "@{}".format(self.id)
	
	def build(self,context):
		return self.id,[]

class IdentNode:
	def __init__(self,tok):
		self.tok=tok
	
	def __repr__(self):
		return "${}".format(self.tok.text)
	
	def build(self,context):
		return 0,[]

class OperatorNode:
	'''
	AST node representing an operator.
	'''
	def __init__(self,tok,code,args):
		self.tok=tok
		self.code=code
		self.args=args
	
	def __repr__(self):
		#return "({} {})".format(self.code,self.args)
		return "({} {})".format(
			self.code,' '.join(repr(x) for x in self.args)
		)
	
	def build(self,context):
		c=[]
		args=[]
		for arg in self.args:
			reg,dep=arg.build(context)
			c.extend(dep)
			args.append(reg)
		
		context.varid+=1
		reg=0 if self.code in code.noret else context.varid+len(context.consts)
		c.append(code.Opcode(reg,self.code,args))
		
		context.pc+=1
		
		return reg,c

class GotoNode:
	'''
	AST node representing a goto statement.
	'''
	def __init__(self,tok,label):
		self.tok=tok
		self.label=label
	
	def __repr__(self):
		return "(goto {})".format(self.label.text)
	
	def build(self,context):
		context.pc+=1
		return 0,[code.Opcode("goto",0,[context.labels[self.label.text]+1])]

class LabelNode:
	'''
	AST node representing a label statement.
	'''
	def __init__(self,tok,label):
		self.tok=tok
		self.label=label
	
	def __repr__(self):
		return "(label {})".format(self.label.text)
	
	def build(self,context):
		context.consts[context.labels[self.label.text]]=code.Label(context.pc)
		return 0,[]

class CallNode:
	'''
	A function call.
	'''
	def __init__(self,func,args):
		def get_args(x):
			if x.tok==",":
				return [x.args[0]]+get_args(x.args[1])
			return [x]
		
		self.tok=func
		self.args=get_args(args)
	
	def __repr__(self):
		return "(call {} {{{}}})".format(
			self.tok,', '.join(repr(x) for x in self.args)
		)
	
	def build(self,context):
		c=[]
		args=[]
		for arg in self.args:
			reg,dep=arg.build(context)
			c.extend(dep)
			args.append(reg)
		
		context.varid+=1
		context.pc+=1
		
		reg=context.varid+len(context.consts)
		c.append(code.Opcode(reg,"call",args))
		
		return reg,c

class IfNode:
	'''
	An if statement.
	'''
	def __init__(self,func,cond,body):
		self.tok=func
		self.cond=cond
		self.body=body
	
	def __repr__(self):
		if self.body:
			return "if({}){}".format(self.cond,self.body)
		return "if({})".format(self.cond,self.body)
	
	def build(self,context):
		cond,condcode=self.cond.build(context)
		
		context.pc+=1
		
		_,bodycode=self.body.build(context)
		
		context.consts.append(code.Label(context.pc))
		
		return 0,condcode+[
			code.Opcode(0,"ifnot",[cond,len(context.consts)])
		]+bodycode

class BlockNode:
	def __init__(self,ast):
		self.ast=ast
	
	def __repr__(self):
		return "{{{}}}".format(' '.join(repr(x) for x in self.ast))
	
	def build(self,context):
		c=[]
		for expr in self.ast:
			_,ec=expr.build(context)
			c.extend(ec)
		return 0,c

class Operator:
	'''
	An operator to be applied to the AST.
	'''
	def __init__(self,tok,op,args):
		self.tok=tok
		self.op=op
		self.args=args
		self.priority=op.priority
		self.assoc=op.assoc
	
	def __repr__(self):
		return "({})".format(self.op.op)
	
	def apply(self,ast,opstack):
		args=deque()
		for x in range(self.args):
			args.appendleft(ast.pop())
		ast.append(OperatorNode(self.tok,self.op.code,args))

class Unary(Operator):
	'''
	A unary operator to be applied to the AST.
	'''
	def __init__(self,tok):
		Operator.__init__(self,tok,unary[tok.text],1)

class Binary(Operator):
	'''
	A binary operator to be applied to the AST.
	'''
	def __init__(self,tok):
		Operator.__init__(self,tok,binary[tok.text],2)

class Paren(Operator):
	'''
	A special object used to represent parentheses on the operator stack.
	'''
	def __init__(self,tok):
		Operator.__init__(self,tok,miscops[tok.text],0)
	
	def __repr__(self):
		return "()"
	
	def apply(self,ast,opstack):
		pass

class Func:
	'''
	An operator representing a function call.
	'''
	def __init__(self,func):
		self.tok=func.tok
		self.func=func
		"""
		self.args=2
		self.priority=0
		self.assoc=left
		"""
	
	def __repr__(self):
		return "{}(...)".format(self.func)
	
	def apply(self,ast,opstack):
		if self.tok=="if":
			body=ast.pop()
			cond=ast.pop()
			ast.append(IfNode(self.tok,cond,body))
		else:
			ast.append(CallNode(self.tok,ast.pop()))

"""
class Keyword:
	def __init__(self):
		opdef=binary["keyword"]
		self.args=2
		self.priority=opdef.priority
		self.assoc=right
	
	def __repr__(self):
		return "<keyword>"
	
	def apply(self,ast,opstack):
		operand=ast.pop()
		keyword=ast.pop()
		ast.append(KeywordNode("keyword",[keyword,operand]))
"""

class Parser:
	'''
	Python parser for proto-Glu code using recursive descent and shunting yard.
	
	This will both parse the code and convert it into Glu assembly.
	'''
	def __init__(self,s=""):
		self.consts=[]
		self.varid=0
		self.labels={}#name:const id
		self.tokenizer=None
		self.maybekw=False
	
	def next(self):
		return self.tokenizer.next()
	
	def hasNext(self):
		return self.tokenizer.hasNext()
	
	def popop(self,ast,opstack):
		'''
		Apply the top operator to the AST.
		'''
		opstack.pop().apply(ast,opstack)
	
	def pushop(self,op,ast,opstack):
		'''
		Rearrange the ast and opstack to include the given operator.
		'''
		if op.args==2:
			def wcond(a,b):
				return (a.args==1 and a.priority>b.priority) or (
					a.priority>b.priority or (
						a.assoc==left and a.priority==b.priority
					)
				)
			while len(opstack) and wcond(opstack[-1],op):
				self.popop(ast,opstack)
		
		opstack.append(op)
	
	def parse_value(self,tok,ast,opstack):
		if tok is None:
			return None
		elif isinstance(tok,tokenize.NumberToken):
			try:
				ast.append(ValueNode(tok,self.consts.index(tok.val)))
			except ValueError:
				self.consts.append(tok.val)
				ast.append(ValueNode(tok,len(self.consts)-1))
		elif isinstance(tok,tokenize.IdentToken):
			ast.append(IdentNode(tok))
		elif tok=="(":
			opstack.append(Paren(tok))
			if self.parse_expr(self.next(),ast,opstack)!=")":
				raise ParseError(
					"Unmatched open parenthesis",tok.line,tok.col
				)
			
			while len(opstack) and not isinstance(opstack[-1],Paren):
				self.popop(ast,opstack)
		elif tok.text in unary:
			self.pushop(Unary(tok),ast,opstack)
		else:
			return tok
		
		self.maybekw=True
		return self.next()
	
	def parse_block(self,tok,ast):
		if tok!="{":
			return tok
		
		tok=self.next()
		while self.hasNext() and tok!="}":
			tok=self.parse_statement(tok,ast)
		
		return self.next()
	
	def parse_expr(self,tok,ast,opstack):
		while tok:
			lasttok=tok
			tok=self.parse_value(tok,ast,opstack)
			if not tok:
				break
			elif isinstance(tok,tokenize.OperatorToken):
				self.maybekw=False
				if tok.text in binary:
					self.pushop(Binary(tok),ast,opstack)
				elif tok=="(":
					opstack.append(Func(ast.pop()))
					fast=[]
					if self.parse_expr(self.next(),fast,[])!=")":
						raise ParseError(
							"Unmatched open parenthesis",tok.line,tok.col
						)
					ast.append(fast[0])
					bast=[]
					tok=self.parse_block(self.next(),bast)
					if bast:
						ast.append(BlockNode(bast))
					
					while len(opstack):
						if isinstance(opstack[-1],Func):
							self.popop(ast,opstack)
							break
						self.popop(ast,opstack)
					return tok
				elif tok==";":
					while len(opstack):
						last=opstack[-1]
						if isinstance(last,Paren):
							raise ParseError(
								"Unmatched open parenthesis",
								last.tok.line,last.tok.col
							)
						self.popop(ast,opstack)
					return self.next()
				else:
					return tok
			elif self.maybekw:
				self.pushop(Keyword(),ast,opstack)
			else:
				return tok
			tok=self.next()
		
		while len(opstack):
			self.popop(ast,opstack)
		
		return tok
	
	def parse_statement(self,tok,ast):
		if tok is None:
			return None
		elif isinstance(tok,tokenize.IdentToken):
			if tok=="return":
				t=tok
				rast=[]
				tok=self.parse_expr(self.next(),rast,[])
				ast.append(OperatorNode(tok,"return",rast))
				return tok
			elif tok=="goto":
				label=self.next()
				if isinstance(label,tokenize.LabelToken):
					ast.append(GotoNode(tok,label))
					return self.next()
				raise ParseError(
					"Goto statement must be followed by a label",
					tok.line,tok.col
				)
			elif tok=="label":
				label=self.next()
				if isinstance(label,tokenize.LabelToken):
					if label.text in self.labels:
						raise ParseError(
							"Redeclaration of label {}".format(label.text),
							label.line,label.col
						)
					self.consts.append(None)
					self.labels[label.text]=len(self.consts)-1
					ast.append(LabelNode(tok,label))
					return self.next()
				raise ParseError(
					"Label declaration must be followed by an identifier",
					label.line,label.col
				)
			"""
			elif tok=="number":
				name=self.next()
				if isinstance(name,tokenize.LabelToken):
					if name.text in self.vars:
						raise ParseError(
							"Redeclaration of variable {}".format(label.text),
							label.line,label.col
						)
					self.consts.append(None)
					self.labels[label.text]=len(self.consts)-1
					ast.append(LabelNode(tok,label))
					return self.next()
				raise ParseError(
					"Variable declaration must be followed by an identifier",
					name.line,name.col
				)
			"""
		
		return self.parse_expr(tok,ast,[])
	
	def parse(self,s):
		'''
		Parse the given proto-Glu and return the AST.
		'''
		self.__init__(s)
		self.tokenizer=tokenize.Tokenizer(s)
		
		ast=[]
		tok=self.next()
		while self.tokenizer.hasNext() and tok:
			tok=self.parse_statement(tok,ast)
		
		return ast
	
	def build(self,s):
		'''
		Parse the given proto-Glu and return it as a Glu assembly code object.
		'''
		ast=self.parse(s)
		
		context=Context(self.consts,self.labels)
		
		c=[]
		for expr in ast:
			c.extend(expr.build(context)[1])
		
		return code.Code(c,context.consts)

def parse(s):
	return Parser().parse(s)

def build(s):
	return Parser().build(s)