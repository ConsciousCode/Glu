from collections import deque
from parsebase import *
import code
import tokenize
import ast

#Constants to make operator associativity more sensical
left=False
right=True

class Opdef:
	'''
	Used for storing information used in interpreting operators.
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
	"/":Opdef("div",2)
}

miscops={
	"(":Opdef("",0),
	")":Opdef("",998),
	";":Opdef("",999),
	"=":Opdef("alias",0,right)
}
keywords={
	"return":Opdef("return",0)
}

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
		return "({})".format(self.op.code)
	
	def apply(self,scope):
		args=deque()
		for x in range(self.args):
			args.appendleft(scope.getval())
		scope.addval(ast.OperatorNode(self.tok,self.op.code,args))

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
	
	def apply(self,scope):
		if self.tok=="if":
			body=scope.getval()
			cond=scope.getval()
			scope.addval(ast.IfNode(self.tok,cond,body))
		else:
			scope.addval(ast.CallNode(self.tok,scope.getval()))

class Assign(Operator):
	def __init__(self,tok,type=None):
		Operator.__init__(self,tok,miscops["="],2)
		self.type=type
	
	def apply(self,scope):
		val=scope.getval()
		name=scope.getval()
		if self.type:
			scope.addval(ast.DeclNode(self.type,name,val))
		else:
			scope.addval(ast.AssignNode(name,val))

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

class Scope:
	'''
	Enables separation of unrelated scopes, both for blocks and for
	subexpressions, which should only operate on the elements in the AST and 
	opstack it's created.
	'''
	def __init__(self):
		self.ast=ast.AST()
		self.opstack=ast.Opstack()
	
	def __repr__(self):
		return "Scope({}, {})".format(self.ast,self.opstack)
	
	def push(self,op):
		self.opstack.push(op,self.ast)
	
	def pop(self):
		return self.opstack.pop(self)
	
	def addval(self,node):
		self.ast.append(node)
	
	def getval(self):
		return self.ast.pop()
	
	def update(self,scope):
		scope.dump()
		self.ast.extend(scope.ast)
		if len(scope.opstack):
			raise RuntimeError("There are still operators on the opstack")
	
	def dump(self):
		while len(self.opstack):
			self.pop()

class Parser:
	'''
	Python parser for proto-Glu code using recursive descent and shunting yard.
	
	This will both parse the code and convert it into Glu assembly.
	'''
	def __init__(self,s=""):
		self.vars=[]
		self.tokenizer=None
	
	def next(self):
		return self.tokenizer.next()
	
	def hasNext(self):
		return self.tokenizer.hasNext()
	
	def parse_value(self,tok,scope):
		if tok is None:
			return None
		elif isinstance(tok,tokenize.NumberToken):
			scope.addval(ast.ValueNode(tok,tok.val))
		elif isinstance(tok,tokenize.IdentToken):
			scope.addval(ast.IdentNode(tok))
		elif tok=="(":
			nscope=Scope()
			if self.parse_expr(self.next(),nscope)!=")":
				raise ParseError(
					"Unmatched open parenthesis",tok.line,tok.col
				)
			
			scope.update(nscope)
		elif tok.text in unary:
			scope.push(Unary(tok))
		else:
			return tok
		
		return self.next()
	
	def parse_block(self,tok,scope):
		if tok!="{":
			return tok
		
		tok=self.next()
		while self.hasNext() and tok!="}":
			tok=self.parse_statement(tok,scope)
		
		return self.next()
	
	def parse_expr(self,tok,scope):
		while tok:
			lasttok=tok
			tok=self.parse_value(tok,scope)
			if not tok:
				break
			elif isinstance(tok,tokenize.OperatorToken):
				if tok.text in binary:
					scope.push(Binary(tok))
				elif tok=="(":
					fscope=Scope()
					if self.parse_expr(self.next(),fscope)!=")":
						raise ParseError(
							"Unmatched open parenthesis",tok.line,tok.col
						)
					func=scope.getval()
					scope.update(fscope)
					
					bscope=Scope()
					tok=self.parse_block(self.next(),bscope)
					if bscope.ast:
						scope.addval(ast.BlockNode(bscope.ast))
					
					Func(func).apply(scope)
					return tok
				elif tok==";":
					scope.dump()
					return self.next()
				else:
					return tok
			else:
				return tok
			tok=self.next()
		
		scope.dump()
		
		return tok
	
	def parse_statement(self,tok,scope):
		if tok is None:
			return None
		elif isinstance(tok,tokenize.IdentToken):
			if tok=="return":
				t=tok
				rscope=Scope()
				tok=self.parse_expr(self.next(),rscope)
				scope.addval(ast.ReturnNode(tok,rscope.ast[0]))
				return tok
			elif tok=="goto":
				label=self.next()
				if isinstance(label,tokenize.IdentToken):
					scope.addval(ast.GotoNode(tok,label))
					return self.next()
				raise ParseError(
					"Goto statement must take a label",
					tok.line,tok.col
				)
			elif tok=="label":
				label=self.next()
				if isinstance(label,tokenize.IdentToken):
					if label.text in self.vars:
						raise ParseError(
							"Redeclaration of label {}".format(label.text),
							label.line,label.col
						)
					self.vars.append(label.text)
					scope.addval(ast.LabelNode(tok,label))
					return self.next()
				raise ParseError(
					"Label declaration must be followed by an identifier",
					label.line,label.col
				)
			elif tok=="number":
				name=self.next()
				if isinstance(name,tokenize.IdentToken):
					if name.text in self.vars:
						raise ParseError(
							"Redeclaration of variable {}".format(name.text),
							name.line,name.col
						)
					self.vars.append(name.text)
					tok=self.next()
					if tok=="=":
						scope.addval(ast.IdentNode(name))
						scope.push(Assign(tok,"number"))
						escope=Scope()
						tok=self.parse_expr(self.next(),escope)
						scope.update(escope)
						scope.dump()
					
					return tok
				raise ParseError(
					"Variable declaration must be followed by an identifier",
					name.line,name.col
				)
		
		return self.parse_expr(tok,scope)
	
	def parse(self,s):
		'''
		Parse the given proto-Glu and return the AST.
		'''
		self.__init__(s)
		self.tokenizer=tokenize.Tokenizer(s)
		
		scope=Scope()
		tok=self.next()
		while self.tokenizer.hasNext() and tok:
			tok=self.parse_statement(tok,scope)
		
		return scope.ast
	
	def build(self,s):
		'''
		Parse the given proto-Glu and return it as a Glu assembly code object.
		'''
		return self.parse(s).build(self)

def parse(s):
	return Parser().parse(s)

def flatten(s):
	p=Parser()
	return p.parse(s).flatten(p,ast.Context(p))

def build(s):
	return Parser().build(s)